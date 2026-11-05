"""Unit Tests for Step 7: Pipeline Orchestrator & Visualization
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from omr.pipeline import OMRPipeline
from omr.visualization import draw_overlay, crop_ambiguous_patches

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_IMAGE = BASE_DIR / "templates" / "answer_sheet_a4.png"
TEMPLATE_CONFIG = BASE_DIR / "templates" / "template_config.json"


@pytest.fixture
def pipeline():
    return OMRPipeline(
        template_config_path=str(TEMPLATE_CONFIG),
        t_low=0.15,
        t_high=0.40,
        delta_min=0.20,
        use_morphology=True
    )


@pytest.fixture
def template_image():
    assert TEMPLATE_IMAGE.exists()
    img = cv2.imread(str(TEMPLATE_IMAGE))
    assert img is not None
    return img


@pytest.fixture
def marked_template_image(template_image, pipeline):
    """Simulate a student shading questions on the template canvas."""
    marked = template_image.copy()
    cfg = pipeline.template_config
    h, w = marked.shape[:2]
    
    # Shade Question 1 Option A (Filled)
    q1_a = cfg["questions"][0]["options"]["A"]
    cx1 = int(round((q1_a["cx_mm"] / 210.0) * w))
    cy1 = int(round((q1_a["cy_mm"] / 297.0) * h))
    r1 = int(round((q1_a["r_mm"] / 210.0) * w * 0.90))
    cv2.circle(marked, (cx1, cy1), r1, (30, 30, 30), thickness=-1)
    
    # Shade Question 2 Option B with residual smudge on Option C (Ambiguous / Ghost mark)
    q2_b = cfg["questions"][1]["options"]["B"]
    cx2 = int(round((q2_b["cx_mm"] / 210.0) * w))
    cy2 = int(round((q2_b["cy_mm"] / 297.0) * h))
    r2 = int(round((q2_b["r_mm"] / 210.0) * w * 0.90))
    cv2.circle(marked, (cx2, cy2), r2, (30, 30, 30), thickness=-1)
    
    q2_c = cfg["questions"][1]["options"]["C"]
    cx2c = int(round((q2_c["cx_mm"] / 210.0) * w))
    cy2c = int(round((q2_c["cy_mm"] / 297.0) * h))
    # Incomplete erasure smudge
    cv2.circle(marked, (cx2c, cy2c), int(r2 * 0.7), (140, 140, 140), thickness=-1)
    
    return marked


def test_pipeline_single_image_success(pipeline, marked_template_image, tmp_path):
    res = pipeline.process_single_image(
        marked_template_image,
        output_debug_dir=str(tmp_path),
        save_debug_images=True
    )
    
    assert res["status"] == "success"
    assert res["rejection_reason"] is None
    assert len(res["results"]) == 40
    assert "visual_overlay" in res
    assert res["visual_overlay"].shape[:2] in [(3508, 2480), (1728, 2480)]
    assert res["processing_time_ms"] > 0
    
    # Verify Question 1 was detected as FILLED with answer A
    q1_res = res["results"][0]
    assert q1_res["question"] == 1
    assert q1_res["status"] == "FILLED"
    assert q1_res["answer"] == "A"
    
    # Check that debug images were saved
    debug_folder = tmp_path / "image"
    assert (debug_folder / "01_original.jpg").exists()
    assert (debug_folder / "05_overlay.jpg").exists()


def test_pipeline_early_rejection_blurry(pipeline):
    # Completely flat blurry image
    blurry = np.full((1000, 1000, 3), 150, dtype=np.uint8)
    res = pipeline.process_single_image(blurry)
    
    assert res["status"] == "rejected"
    assert "QUALITY_CHECK_FAILED" in res["rejection_reason"]


def test_pipeline_batch_and_export(pipeline, marked_template_image, tmp_path):
    # Process batch of 1 image
    batch_res = pipeline.process_batch([marked_template_image])
    assert len(batch_res) == 1
    assert batch_res[0]["status"] == "success"
    
    # Export CSV
    csv_file = tmp_path / "results.csv"
    exported_csv = pipeline.export_results(batch_res, csv_file, export_format="csv")
    assert exported_csv.exists()
    
    # Check CSV contents
    content = exported_csv.read_text(encoding="utf-8")
    assert "image_id,question,status,answer" in content
    assert "1,FILLED,A" in content
    
    # Export JSON
    json_file = tmp_path / "results.json"
    exported_json = pipeline.export_results(batch_res, json_file, export_format="json")
    assert exported_json.exists()


def test_crop_ambiguous_patches(pipeline, marked_template_image):
    res = pipeline.process_single_image(marked_template_image)
    patches = res["ambiguous_patches"]
    print(f"\nAmbiguous questions needing review: {len(patches)}")
    
    # If any question is ambiguous, patches should contain zoomed original and binary images
    for p in patches:
        assert "original_patch" in p
        assert "binary_patch" in p
        assert p["original_patch"].size > 0
        assert p["binary_patch"].size > 0
