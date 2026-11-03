"""Step 1: Image Quality Assessment Module
Course: ICE415 Digital Image Processing (KMUTT)

This module provides early-stage validation of incoming answer sheet captures:
1. Blur Detection via Laplacian Variance (Pech-Pacheco et al., 2000):
   Evaluates second-order spatial derivatives to detect defocus or motion blur.
   Formula: σ²_L = Var(∇² I) = Var(∂²I/∂x² + ∂²I/∂y²)
   A sharp edge produces large positive and negative spikes, yielding high variance.
   A blurry image smooths these transitions, causing low variance (σ²_L < threshold).

2. Illumination & Exposure Verification via Histogram Analysis:
   Inspects grayscale intensity distributions to detect over-exposure (glare clipping),
   under-exposure (harsh shadows), or insufficient dynamic range.
"""

from pathlib import Path
from typing import Union, Tuple, Optional, Dict, Any
import cv2
import numpy as np


def ensure_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert input image to single-channel 8-bit grayscale if it is BGR/RGB."""
    if len(image.shape) == 2:
        return image
    elif len(image.shape) == 3:
        if image.shape[2] == 3:
            # ITU-R BT.601 standard luminance conversion: Y = 0.299R + 0.587G + 0.114B
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    raise ValueError(f"Unsupported image shape for grayscale conversion: {image.shape}")


def check_blur(image: np.ndarray, threshold: float = 100.0) -> Dict[str, Any]:
    """Assess image sharpness using the Laplacian Variance metric.
    
    Args:
        image: Input image (BGR or Grayscale numpy array).
        threshold: Blur cutoff threshold. Below this value, image is classified as blurry.
                   Standard value is 100.0 for document photographs.
                   
    Returns:
        Dict containing:
            - is_sharp (bool): True if blur_score >= threshold, False otherwise.
            - blur_score (float): Calculated variance of the Laplacian.
            - threshold (float): Cutoff threshold used.
            - metric_name (str): 'Laplacian Variance'
    """
    gray = ensure_grayscale(image)
    
    # Compute the Laplacian (2nd derivative) using 64-bit float to prevent overflow/saturation
    # Kernel: [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=1)
    blur_score = float(laplacian.var())
    
    is_sharp = blur_score >= threshold
    
    return {
        "is_sharp": is_sharp,
        "blur_score": round(blur_score, 2),
        "threshold": float(threshold),
        "metric_name": "Laplacian Variance"
    }


def check_exposure(
    image: np.ndarray,
    over_thresh: int = 240,
    under_thresh: int = 15,
    ratio_limit: float = 0.95,
    under_ratio_limit: float = 0.30,
    min_dynamic_range: int = 100
) -> Dict[str, Any]:
    """Inspect grayscale histogram to detect overexposure, underexposure, or low contrast.
    
    In document processing, clean paper backgrounds naturally occupy 80-92% of the canvas.
    Overexposure is triggered when saturated bright pixels exceed 95% (washing out text/grids)
    or when dynamic range falls below acceptable limits (< 100).
    
    Args:
        image: Input image (BGR or Grayscale numpy array).
        over_thresh: Pixel intensity [0-255] above which is considered near-white/saturated.
        under_thresh: Pixel intensity [0-255] below which is considered near-black/underexposed.
        ratio_limit: Maximum permissible fraction of pixels allowed in the saturated band (> 240).
                     Default is 0.95 to accommodate clean document paper.
        under_ratio_limit: Maximum permissible fraction in the deep shadow band (< 15).
        min_dynamic_range: Minimum required difference between maximum and minimum intensities.
        
    Returns:
        Dict containing:
            - is_valid (bool): True if exposure and dynamic range are acceptable.
            - mean_brightness (float): Mean grayscale intensity across the image.
            - dynamic_range (int): Difference between max and min pixel values.
            - over_ratio (float): Fraction of pixels >= over_thresh.
            - under_ratio (float): Fraction of pixels <= under_thresh.
            - issue (str | None): Description of the exposure defect, if any.
    """
    gray = ensure_grayscale(image)
    total_pixels = gray.size
    
    mean_brightness = float(np.mean(gray))
    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    dynamic_range = int(max_val - min_val)
    
    over_count = int(np.count_nonzero(gray >= over_thresh))
    under_count = int(np.count_nonzero(gray <= under_thresh))
    
    over_ratio = float(over_count / total_pixels)
    under_ratio = float(under_count / total_pixels)
    
    issues = []
    if dynamic_range < min_dynamic_range:
        issues.append(f"Insufficient dynamic range ({dynamic_range} < {min_dynamic_range})")
        
    if over_ratio > ratio_limit:
        issues.append(f"Severe overexposure / glare clipping ({over_ratio*100:.1f}% > {ratio_limit*100:.0f}%)")
        
    if under_ratio > under_ratio_limit:
        issues.append(f"Severe underexposure / heavy shadows ({under_ratio*100:.1f}% > {under_ratio_limit*100:.0f}%)")
        
    is_valid = len(issues) == 0
    issue_desc = "; ".join(issues) if issues else None
    
    return {
        "is_valid": is_valid,
        "mean_brightness": round(mean_brightness, 2),
        "dynamic_range": dynamic_range,
        "over_ratio": round(over_ratio, 4),
        "under_ratio": round(under_ratio, 4),
        "issue": issue_desc
    }


def assess_quality(
    image_input: Union[str, Path, np.ndarray],
    blur_threshold: float = 100.0,
    over_thresh: int = 240,
    under_thresh: int = 15,
    ratio_limit: float = 0.95
) -> Dict[str, Any]:
    """Execute complete Step 1 quality assessment on an image file or numpy array.
    
    Args:
        image_input: File path (str/Path) or numpy BGR/Grayscale array.
        blur_threshold: Minimum Laplacian variance for sharpness.
        over_thresh: Saturation cutoff intensity.
        under_thresh: Underexposure cutoff intensity.
        ratio_limit: Maximum allowed extreme pixel fraction.
        
    Returns:
        Dict containing:
            - passed (bool): Overall quality check pass/fail.
            - blur (dict): Results from check_blur.
            - exposure (dict): Results from check_exposure.
            - recommendation (str): Human-readable advice for re-capture or confirmation.
            - rejection_reason (str | None): Specific reason if image was rejected.
    """
    # 1. Load image if path provided
    if isinstance(image_input, (str, Path)):
        path_obj = Path(image_input)
        if not path_obj.exists():
            return {
                "passed": False,
                "blur": None,
                "exposure": None,
                "recommendation": f"File not found: {path_obj}",
                "rejection_reason": "FILE_NOT_FOUND"
            }
        # Read with OpenCV (supports unicode paths on Windows via numpy fromfile)
        try:
            data = np.fromfile(str(path_obj), dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            image = cv2.imread(str(path_obj))
            
        if image is None:
            return {
                "passed": False,
                "blur": None,
                "exposure": None,
                "recommendation": f"Failed to decode image file: {path_obj}",
                "rejection_reason": "IMAGE_DECODE_FAILED"
            }
    elif isinstance(image_input, np.ndarray):
        image = image_input
    else:
        raise TypeError(f"Expected file path or np.ndarray, got {type(image_input)}")

    # 2. Perform assessments
    blur_res = check_blur(image, threshold=blur_threshold)
    expo_res = check_exposure(image, over_thresh=over_thresh, under_thresh=under_thresh, ratio_limit=ratio_limit)
    
    # 3. Decision & Recommendations
    rejection_reasons = []
    recommendations = []
    
    if not blur_res["is_sharp"]:
        rejection_reasons.append("MOTION_OR_DEFOCUS_BLUR")
        recommendations.append(
            f"ภาพเบลอหรือสั่นไหว (Blur Score: {blur_res['blur_score']} < {blur_res['threshold']}) "
            "กรุณาถือกล้องให้นิ่งหรือแตะหน้าจอเพื่อโฟกัสใหม่"
        )
        
    if not expo_res["is_valid"]:
        rejection_reasons.append("IMPROPER_EXPOSURE")
        recommendations.append(f"สภาวะแสงไม่เหมาะสม: {expo_res['issue']} กรุณาจัดแสงให้สม่ำเสมอหรือปิดแฟลช")
        
    passed = len(rejection_reasons) == 0
    
    if passed:
        recommendations.append("ภาพมีความคมชัดและระดับแสงสว่างอยู่ในเกณฑ์มาตรฐาน พร้อมเข้าสู่กระบวนการประมวลผล")
        
    return {
        "passed": passed,
        "blur": blur_res,
        "exposure": expo_res,
        "recommendation": " | ".join(recommendations),
        "rejection_reason": " & ".join(rejection_reasons) if rejection_reasons else None
    }
