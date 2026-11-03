"""Unit Tests for Step 1: Quality Check
Course: ICE415 Digital Image Processing (KMUTT)
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from omr.quality_check import check_blur, check_exposure, assess_quality, ensure_grayscale

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_IMAGE = BASE_DIR / "templates" / "answer_sheet_a4.png"

@pytest.fixture
def sharp_image():
    """Load canonical A4 answer sheet image."""
    assert TEMPLATE_IMAGE.exists(), f"Template image missing at {TEMPLATE_IMAGE}"
    img = cv2.imread(str(TEMPLATE_IMAGE))
    assert img is not None
    return img

@pytest.fixture
def blurry_image(sharp_image):
    """Create a heavily blurred copy using a large Gaussian kernel (25x25)."""
    return cv2.GaussianBlur(sharp_image, (25, 25), 10.0)

@pytest.fixture
def overexposed_image():
    """Create a predominantly white, clipped image simulating harsh direct glare."""
    img = np.full((1000, 1000, 3), 250, dtype=np.uint8)
    # Add minor noise
    noise = np.random.randint(0, 5, (1000, 1000, 3), dtype=np.uint8)
    return np.clip(img + noise, 0, 255)

@pytest.fixture
def underexposed_image():
    """Create a predominantly dark image simulating deep room shadows."""
    img = np.full((1000, 1000, 3), 10, dtype=np.uint8)
    return img


def test_ensure_grayscale(sharp_image):
    gray = ensure_grayscale(sharp_image)
    assert len(gray.shape) == 2
    assert gray.shape[0] == sharp_image.shape[0]
    assert gray.shape[1] == sharp_image.shape[1]
    # Pass already grayscale
    gray_again = ensure_grayscale(gray)
    assert np.array_equal(gray, gray_again)


def test_check_blur_sharp(sharp_image):
    res = check_blur(sharp_image, threshold=100.0)
    assert res["is_sharp"] is True
    assert res["blur_score"] > 100.0
    print(f"Sharp image blur score: {res['blur_score']}")


def test_check_blur_blurred(blurry_image):
    res = check_blur(blurry_image, threshold=100.0)
    assert res["is_sharp"] is False
    assert res["blur_score"] < 100.0
    print(f"Blurred image blur score: {res['blur_score']}")


def test_check_exposure_normal(sharp_image):
    res = check_exposure(sharp_image)
    assert res["is_valid"] is True
    assert res["dynamic_range"] >= 100
    assert res["issue"] is None


def test_check_exposure_overexposed(overexposed_image):
    res = check_exposure(overexposed_image, over_thresh=240, ratio_limit=0.30)
    assert res["is_valid"] is False
    assert "overexposure" in res["issue"].lower()


def test_check_exposure_underexposed(underexposed_image):
    res = check_exposure(underexposed_image, under_thresh=15, ratio_limit=0.30)
    assert res["is_valid"] is False
    assert "underexposure" in res["issue"].lower()


def test_assess_quality_passed(sharp_image):
    res = assess_quality(sharp_image)
    assert res["passed"] is True
    assert res["rejection_reason"] is None
    assert "เกณฑ์มาตรฐาน" in res["recommendation"]


def test_assess_quality_rejected_blur(blurry_image):
    res = assess_quality(blurry_image)
    assert res["passed"] is False
    assert "BLUR" in res["rejection_reason"]
    assert "สั่นไหว" in res["recommendation"]


def test_assess_quality_file_path():
    res = assess_quality(str(TEMPLATE_IMAGE))
    assert res["passed"] is True
    assert res["blur"]["is_sharp"] is True
