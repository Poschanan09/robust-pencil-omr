"""Unit Tests for Step 5: Grid Extraction & Feature Extraction
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from omr.grid_extraction import (
    load_template,
    create_inner_mask,
    get_bubble_roi,
    extract_all_bubbles
)
from omr.feature_extraction import (
    compute_fill_ratio,
    compute_texture_std,
    detect_glare,
    extract_features
)
from omr.thresholding import binarize_document

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_IMAGE = BASE_DIR / "templates" / "answer_sheet_a4.png"
TEMPLATE_CONFIG = BASE_DIR / "templates" / "template_config.json"


@pytest.fixture
def template_config():
    assert TEMPLATE_CONFIG.exists()
    return load_template(str(TEMPLATE_CONFIG))


@pytest.fixture
def template_image():
    assert TEMPLATE_IMAGE.exists()
    img = cv2.imread(str(TEMPLATE_IMAGE))
    assert img is not None
    return img


@pytest.fixture
def binary_canvas(template_image):
    res = binarize_document(template_image, use_morphology=True)
    return res["binary_clean"]


def test_load_template(template_config):
    assert template_config["questions_count"] == 40
    assert len(template_config["questions"]) == 40
    q1 = template_config["questions"][0]
    assert q1["q"] == 1
    assert set(q1["options"].keys()) == {"A", "B", "C", "D", "E"}


def test_create_inner_mask():
    radius = 30.0
    roi_shape = (100, 100)
    mask = create_inner_mask(roi_shape, radius=radius, radius_ratio=0.82)
    
    assert mask.shape == roi_shape
    assert set(np.unique(mask)).issubset({0, 1})
    # Center should be 1
    assert mask[50, 50] == 1
    # Corners should be 0
    assert mask[0, 0] == 0
    # Outer radius region (> 0.82 * radius) should be 0
    expected_inner_r = int(round(radius * 0.82))
    assert mask[50, 50 + expected_inner_r + 2] == 0


def test_inner_mask_eliminates_printed_ring():
    """Verify that the concentric inner mask effectively omits the printed circular rim."""
    roi_shape = (100, 100)
    center = (50, 50)
    r = 35
    
    # Simulate a printed unfilled bubble: black ring outline (converted to white 255 in binary mask)
    # Inside and outside are blank paper (0 in inverted binary)
    printed_bubble_binary = np.zeros(roi_shape, dtype=np.uint8)
    cv2.circle(printed_bubble_binary, center, r, 255, thickness=4)  # 4px ring outline
    
    # 1. Without inner mask (evaluating full circle)
    full_circle_mask = np.zeros(roi_shape, dtype=np.uint8)
    cv2.circle(full_circle_mask, center, r, 1, thickness=-1)
    ratio_without = compute_fill_ratio(printed_bubble_binary, full_circle_mask)
    
    # 2. With concentric inner mask (radius scaled to 0.82)
    inner_mask = create_inner_mask(roi_shape, radius=r, radius_ratio=0.82)
    ratio_with_inner_mask = compute_fill_ratio(printed_bubble_binary, inner_mask)
    
    print(f"\nFill ratio without inner mask (ring included): {ratio_without:.3f}")
    print(f"Fill ratio with inner mask (ring eliminated): {ratio_with_inner_mask:.3f}")
    
    assert ratio_without >= 0.10, "Full mask mistakenly registers printed ring as fill"
    assert ratio_with_inner_mask < 0.01, "Inner mask must eliminate the printed ring to near 0.0"


def test_compute_fill_ratio():
    roi = np.full((60, 60), 255, dtype=np.uint8)  # Full shaded mark
    mask = np.zeros((60, 60), dtype=np.uint8)
    cv2.circle(mask, (30, 30), 20, 1, -1)
    
    ratio_full = compute_fill_ratio(roi, mask)
    assert np.isclose(ratio_full, 1.0)
    
    blank_roi = np.zeros((60, 60), dtype=np.uint8)  # Empty mark
    ratio_blank = compute_fill_ratio(blank_roi, mask)
    assert np.isclose(ratio_blank, 0.0)


def test_detect_glare():
    # Normal blank paper (smooth, low std)
    is_glare_paper = detect_glare(fill_ratio=0.03, texture_std=4.5, mean_intensity=235.0)
    assert is_glare_paper is False
    
    # Clean dark shaded pencil
    is_glare_shaded = detect_glare(fill_ratio=0.85, texture_std=15.0, mean_intensity=45.0)
    assert is_glare_shaded is False
    
    # Shaded pencil reflecting camera flash (bright mean, low binary fill, high texture std)
    is_glare_flash = detect_glare(fill_ratio=0.20, texture_std=26.5, mean_intensity=190.0)
    assert is_glare_flash is True


def test_extract_features_end_to_end(template_image, binary_canvas, template_config):
    features = extract_features(template_image, binary_canvas, template_config)
    
    assert len(features) == 40
    q1 = features[0]
    assert q1["question"] == 1
    assert set(q1["options"].keys()) == {"A", "B", "C", "D", "E"}
    
    # On an unshaded template, all fill ratios should be near 0
    opt_a = q1["options"]["A"]
    assert "fill_ratio" in opt_a
    assert "texture_std" in opt_a
    assert "has_glare" in opt_a
    assert opt_a["fill_ratio"] < 0.15
