"""Unit Tests for Step 4: Adaptive Thresholding & Morphology
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from omr.thresholding import (
    adaptive_threshold,
    otsu_threshold,
    apply_morphology,
    binarize_document
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
def image_with_shadow(template_image):
    """Simulate a severe illumination gradient (shadow cast from top-left to bottom-right)."""
    gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    
    # Create linear gradient ramp from 0.35 (dark shadow) to 1.0 (bright light)
    x = np.linspace(0.35, 1.0, w)
    y = np.linspace(0.35, 1.0, h)
    xx, yy = np.meshgrid(x, y)
    shadow_map = (xx + yy) / 2.0
    
    shadowed = np.clip(gray * shadow_map, 0, 255).astype(np.uint8)
    return shadowed

@pytest.fixture
def noisy_bubble_patch():
    """Create a simulated pencil bubble with internal graphite grain voids and external dust specks."""
    # 100x100 white patch
    patch = np.zeros((100, 100), dtype=np.uint8)
    # Circle of radius 30 at center
    cv2.circle(patch, (50, 50), 30, 255, -1)
    
    # Simulate internal graphite pores (holes inside the bubble)
    patch[48:52, 48:52] = 0
    patch[38:42, 50:54] = 0
    patch[58:62, 45:49] = 0
    
    # Simulate external eraser dust / stray dots (outside the bubble)
    patch[10, 10] = 255
    patch[12, 85] = 255
    patch[90, 15] = 255
    patch[88, 88] = 255
    
    return patch


def test_adaptive_threshold_binary_values(template_image):
    binary = adaptive_threshold(template_image, block_size=41, C=8)
    assert binary.dtype == np.uint8
    unique_vals = set(np.unique(binary))
    assert unique_vals.issubset({0, 255})
    # Most of the background should be 0 (paper)
    zero_ratio = np.count_nonzero(binary == 0) / binary.size
    assert zero_ratio > 0.80


def test_adaptive_vs_otsu_under_shadow(image_with_shadow):
    """Demonstrate why Adaptive Thresholding is superior to Otsu under uneven lighting."""
    binary_adapt = adaptive_threshold(image_with_shadow, block_size=41, C=8)
    binary_otsu, thresh_val = otsu_threshold(image_with_shadow)
    
    # Under heavy shadow, Global Otsu misclassifies large parts of the shadowed paper as foreground (white)
    otsu_white_ratio = np.count_nonzero(binary_otsu == 255) / binary_otsu.size
    adapt_white_ratio = np.count_nonzero(binary_adapt == 255) / binary_adapt.size
    
    print(f"\nOtsu White Ratio under shadow: {otsu_white_ratio:.3f} | Adaptive White Ratio: {adapt_white_ratio:.3f}")
    # Adaptive threshold maintains a clean foreground ratio (typically 5-15%)
    assert adapt_white_ratio < 0.25
    # Otsu threshold fails, generating huge false positive dark patches
    assert otsu_white_ratio > adapt_white_ratio


def test_morphology_closing_bridges_gaps(noisy_bubble_patch):
    res = apply_morphology(noisy_bubble_patch, kernel_size=5)
    closed = res["after_closing"]
    
    # Check that internal pores (e.g. (50, 50)) were sealed by closing
    assert closed[50, 50] == 255
    assert closed[40, 52] == 255
    assert closed[60, 47] == 255


def test_morphology_opening_removes_dust(noisy_bubble_patch):
    res = apply_morphology(noisy_bubble_patch, kernel_size=3)
    cleaned = res["cleaned"]
    
    # Check that isolated single-pixel dust dots outside the circle were eliminated
    assert cleaned[10, 10] == 0
    assert cleaned[12, 85] == 0
    assert cleaned[90, 15] == 0
    assert cleaned[88, 88] == 0


def test_binarize_document_end_to_end(template_image):
    res = binarize_document(template_image, use_morphology=True)
    assert res["is_valid"] is True
    assert "binary_clean" in res
    assert "binary_raw" in res
    assert res["binary_clean"].shape == template_image.shape[:2]
    assert 0.01 <= res["white_pixel_ratio"] <= 0.25
    assert res["warning"] is None
