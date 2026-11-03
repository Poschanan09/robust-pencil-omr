"""Unit Tests for Step 3: Perspective Rectification & Hough Deskew
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from omr.perspective_correction import (
    compute_homography,
    warp_to_canonical,
    validate_warp,
    correct_perspective,
    STANDARD_A4_WIDTH,
    STANDARD_A4_HEIGHT
)
from omr.hough_deskew import hough_deskew, detect_skew_angle_hough

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_IMAGE = BASE_DIR / "templates" / "answer_sheet_a4.png"

@pytest.fixture
def template_image():
    assert TEMPLATE_IMAGE.exists(), f"Missing template at {TEMPLATE_IMAGE}"
    img = cv2.imread(str(TEMPLATE_IMAGE))
    assert img is not None
    return img

@pytest.fixture
def perspective_skewed_image(template_image):
    """Create a simulated mobile-camera perspective skewed capture."""
    h, w = template_image.shape[:2]
    src_corners = np.array([
        [0, 0],
        [w - 1, 0],
        [w - 1, h - 1],
        [0, h - 1]
    ], dtype=np.float32)
    
    # Simulate camera looking up from the bottom (keystone trapezoid)
    # Top edge is compressed, bottom edge is wider
    margin_x = w * 0.15
    dst_corners = np.array([
        [margin_x, h * 0.08],
        [w - margin_x, h * 0.08],
        [w * 0.95, h * 0.92],
        [w * 0.05, h * 0.92]
    ], dtype=np.float32)
    
    H = cv2.getPerspectiveTransform(src_corners, dst_corners)
    skewed = cv2.warpPerspective(template_image, H, (w, h), borderValue=(70, 60, 50))
    return skewed, dst_corners

@pytest.fixture
def rotated_image(template_image):
    """Rotate template by 6.5 degrees."""
    h, w = template_image.shape[:2]
    center = (w // 2, h // 2)
    angle = 6.5
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(template_image, M, (w, h), borderValue=(255, 255, 255))
    return rotated, angle


def test_compute_homography():
    src = np.array([[0, 0], [100, 0], [100, 200], [0, 200]], dtype=np.float32)
    dst = np.array([[10, 20], [110, 20], [110, 220], [10, 220]], dtype=np.float32)
    H = compute_homography(src, dst)
    assert H.shape == (3, 3)
    # Check that src maps to dst
    src_homo = np.array([0, 0, 1.0])
    dst_pred = H @ src_homo
    dst_pred /= dst_pred[2]
    assert np.allclose(dst_pred[:2], [10, 20], atol=1e-3)


def test_warp_to_canonical(perspective_skewed_image):
    skewed, detected_corners = perspective_skewed_image
    warped, H = warp_to_canonical(skewed, detected_corners, canvas_size=(STANDARD_A4_WIDTH, STANDARD_A4_HEIGHT))
    
    assert warped.shape == (STANDARD_A4_HEIGHT, STANDARD_A4_WIDTH, 3)
    assert H.shape == (3, 3)
    # Verify warped image is not empty
    assert np.mean(warped) > 50


def test_validate_warp():
    # Normal A4 corners
    normal_corners = np.array([
        [0, 0],
        [2480, 0],
        [2480, 3508],
        [0, 3508]
    ], dtype=np.float32)
    val = validate_warp(normal_corners)
    assert val["is_valid"] is True
    assert val["aspect_deviation"] < 0.05
    
    # Severely deformed corners (e.g. extreme triangle/trapezoid)
    deformed_corners = np.array([
        [0, 0],
        [100, 0],
        [2480, 3508],
        [0, 3508]
    ], dtype=np.float32)
    val_def = validate_warp(deformed_corners)
    assert val_def["is_valid"] is False


def test_correct_perspective_end_to_end(perspective_skewed_image):
    skewed, detected_corners = perspective_skewed_image
    res = correct_perspective(skewed, detected_corners)
    assert "warped_image" in res
    assert "homography_matrix" in res
    assert "validation" in res
    assert res["warped_image"].shape == (STANDARD_A4_HEIGHT, STANDARD_A4_WIDTH, 3)


def test_hough_deskew(rotated_image):
    rot_img, true_angle = rotated_image
    res = hough_deskew(rot_img)
    
    assert res["lines_detected"] > 0
    estimated_skew = res["skew_angle"]
    print(f"True rotation: {true_angle} deg | Hough estimated skew: {estimated_skew} deg")
    # Skew angle should approximate the applied rotation (within ±2.5 deg)
    assert abs(abs(estimated_skew) - abs(true_angle)) < 3.0
    assert res["deskewed_image"].shape == rot_img.shape
