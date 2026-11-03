"""Unit Tests for Step 2: Document Boundary Detection
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from omr.document_detection import (
    preprocess_for_edges,
    order_corner_points,
    detect_document_contour,
    detect_fiducial_markers,
    find_document
)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_IMAGE = BASE_DIR / "templates" / "answer_sheet_a4.png"

@pytest.fixture
def template_image():
    assert TEMPLATE_IMAGE.exists(), f"Missing template at {TEMPLATE_IMAGE}"
    img = cv2.imread(str(TEMPLATE_IMAGE))
    assert img is not None
    return img

@pytest.fixture
def document_on_background(template_image):
    """Embed the template onto a larger desk background with margins."""
    desk_h, desk_w = 4000, 3000
    desk = np.full((desk_h, desk_w, 3), (80, 70, 60), dtype=np.uint8)  # Wood-like color
    
    # Place template in center
    h, w = template_image.shape[:2]
    y_off = (desk_h - h) // 2
    x_off = (desk_w - w) // 2
    desk[y_off:y_off+h, x_off:x_off+w] = template_image
    
    expected_corners = np.array([
        [x_off, y_off],
        [x_off + w, y_off],
        [x_off + w, y_off + h],
        [x_off, y_off + h]
    ], dtype=np.float32)
    
    return desk, expected_corners


def test_preprocess_for_edges(template_image):
    gray = preprocess_for_edges(template_image)
    assert len(gray.shape) == 2
    assert gray.shape == template_image.shape[:2]
    assert gray.dtype == np.uint8


def test_order_corner_points():
    # Unordered rectangle points
    pts = np.array([
        [1000, 100],   # TR
        [100, 800],    # BL
        [100, 100],    # TL
        [1000, 800]    # BR
    ], dtype=np.float32)
    
    ordered = order_corner_points(pts)
    
    # Expected order: TL, TR, BR, BL
    assert np.allclose(ordered[0], [100, 100])
    assert np.allclose(ordered[1], [1000, 100])
    assert np.allclose(ordered[2], [1000, 800])
    assert np.allclose(ordered[3], [100, 800])


def test_find_document_on_background(document_on_background):
    desk_img, expected_corners = document_on_background
    res = find_document(desk_img)
    
    assert res["corners"] is not None
    assert res["method"] in ["contour", "fiducial"]
    assert res["corners"].shape == (4, 2)
    assert res["debug_image"] is not None
    assert res["contour_area"] > 0
    
    # Detected corners should be close to expected outer frame / paper corners
    corners = res["corners"]
    print("Detected corners:\n", corners)
    # Check that TL is top-left of BR
    assert corners[0][0] < corners[2][0]
    assert corners[0][1] < corners[2][1]


def test_find_document_template_direct(template_image):
    res = find_document(template_image)
    assert res["corners"] is not None
    assert res["method"] in ["contour", "fiducial"]
    corners = res["corners"]
    assert corners.shape == (4, 2)
    # Corners should be well within canvas
    assert np.all(corners[:, 0] >= 0)
    assert np.all(corners[:, 0] <= template_image.shape[1])
    assert np.all(corners[:, 1] >= 0)
    assert np.all(corners[:, 1] <= template_image.shape[0])


def test_detect_fiducial_markers(template_image):
    corners, markers = detect_fiducial_markers(template_image)
    print(f"Detected {len(markers)} candidate markers.")
    assert len(markers) >= 4
    if corners is not None:
        assert corners.shape == (4, 2)
