"""Step 4: Adaptive Thresholding & Mathematical Morphology Module
Course: ICE415 Digital Image Processing (KMUTT) - Unit 08 Morphology

This module segments dark pencil marks from the paper background under adverse illumination:
1. Local Adaptive Gaussian Thresholding (Bradley & Roth, 2007):
   Computes a dynamic local cutoff threshold T(x, y) for each pixel based on a Gaussian-weighted
   mean of its local WxW neighborhood window:
   T(x, y) = μ_Gaussian(x, y) - C
   B(x, y) = 255 if I(x, y) <= T(x, y) else 0  (THRESH_BINARY_INV)
   Unlike Global Otsu's thresholding which fails under illumination gradients (where shadowed paper
   is falsely classified as dark marks), local adaptive thresholding tracks spatial lighting variations.

2. Global Otsu's Thresholding Baseline (Otsu, 1979):
   Included specifically for the ICE415 Ablation Study to quantitatively demonstrate
   why global bimodal thresholding fails on mobile shadow captures.

3. Mathematical Morphology (ICE415 Unit 08 - Binary Morphology):
   - Structuring Element (SE): Elliptical kernel matching round bubble geometry.
   - Morphological Closing (B • S = (B ⊕ S) ⊖ S):
     Dilation followed by erosion. Fills microscopic internal pores and cracks in pencil graphite
     shading, converting loose pencil shading into a solid blob without distorting outer bubble geometry.
   - Morphological Opening (B ∘ S = (B ⊖ S) ⊕ S):
     Erosion followed by dilation. Eliminates isolated single-pixel noise, rubber eraser specks,
     and paper texture dust outside of the bubbles.
"""

from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np


def ensure_grayscale(image: np.ndarray) -> np.ndarray:
    """Ensure image is 2D single-channel grayscale."""
    if len(image.shape) == 2:
        return image
    elif len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raise ValueError(f"Invalid image shape: {image.shape}")


def adaptive_threshold(
    gray_image: np.ndarray,
    block_size: int = 41,
    C: int = 8
) -> np.ndarray:
    """Segment image using Local Adaptive Gaussian Thresholding (THRESH_BINARY_INV).
    
    Pencil marks become foreground white (255) and paper becomes background black (0).
    
    Args:
        gray_image: Single-channel grayscale image.
        block_size: Size of neighborhood window (must be odd, e.g. 31, 41, 51).
        C: Constant subtracted from the mean (compensates for paper texture noise).
        
    Returns:
        Binary mask (uint8) with values in {0, 255}.
    """
    gray = ensure_grayscale(gray_image)
    if block_size % 2 == 0:
        block_size += 1  # Block size must be odd
        
    binary = cv2.adaptiveThreshold(
        gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY_INV,
        blockSize=block_size,
        C=C
    )
    return binary


def otsu_threshold(gray_image: np.ndarray) -> Tuple[np.ndarray, float]:
    """Segment image using Global Otsu's Thresholding (Baseline for Ablation Study).
    
    Maximizes Between-Class Variance σ²_B(T) across the entire image histogram.
    
    Args:
        gray_image: Single-channel grayscale image.
        
    Returns:
        Tuple of (binary_mask, computed_otsu_threshold_value).
    """
    gray = ensure_grayscale(gray_image)
    thresh_val, binary = cv2.threshold(
        gray,
        thresh=0,
        maxval=255,
        type=cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    return binary, float(thresh_val)


def apply_morphology(
    binary_image: np.ndarray,
    kernel_size: int = 3
) -> Dict[str, np.ndarray]:
    """Apply morphological Closing and Opening using an elliptical structuring element.
    
    Mathematical Formulation (ICE415 Unit 08):
    1. Closing: B • S = (B ⊕ S) ⊖ S (Connects disconnected graphite flakes, seals internal voids)
    2. Opening: B ∘ S = (B ⊖ S) ⊕ S (Removes stray eraser residue, dust specks, and paper fibers)
    
    Args:
        binary_image: Input binary image (values 0 or 255).
        kernel_size: Size of structuring element (e.g. 3 or 5).
        
    Returns:
        Dict containing:
            - cleaned: Image after both Closing and Opening
            - after_closing: Image after Closing only
            - after_opening: Image after Opening only
            - kernel: The elliptical structuring element used
    """
    if kernel_size % 2 == 0:
        kernel_size += 1
        
    # Elliptical structuring element matching round circular bubbles
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    # 1. Closing: Dilation then Erosion
    closed = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # 2. Opening: Erosion then Dilation on the closed image
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Also compute isolated opening for ablation comparison
    only_opened = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return {
        "cleaned": cleaned,
        "after_closing": closed,
        "after_opening": only_opened,
        "kernel": kernel
    }


def binarize_document(
    warped_image: np.ndarray,
    use_morphology: bool = True,
    block_size: int = 41,
    C: int = 8,
    morph_kernel_size: int = 3,
    max_white_ratio_limit: float = 0.40
) -> Dict[str, Any]:
    """Execute complete Step 4 binarization and morphological cleaning pipeline.
    
    Args:
        warped_image: Rectified A4 canvas image (BGR or Grayscale).
        use_morphology: Whether to apply Morphological Closing and Opening (default True).
        block_size: Local neighborhood window size for Adaptive Gaussian Threshold.
        C: Intensity offset constant.
        morph_kernel_size: Structuring element diameter.
        max_white_ratio_limit: Permissible fraction of foreground white pixels (default 40%).
        
    Returns:
        Dict containing:
            - binary_clean: Final cleaned binary mask.
            - binary_raw: Binary mask directly after thresholding (before morphology).
            - adaptive_params: Dict of parameters used.
            - use_morphology: Boolean flag.
            - white_pixel_ratio: Ratio of white pixels across canvas.
            - is_valid: Boolean indicating whether binarization succeeded without severe distortion.
            - warning: Warning message if white_pixel_ratio exceeded normal range.
    """
    gray = ensure_grayscale(warped_image)
    
    # 1. Local Adaptive Gaussian Thresholding
    binary_raw = adaptive_threshold(gray, block_size=block_size, C=C)
    
    # 2. Mathematical Morphology
    if use_morphology:
        morph_res = apply_morphology(binary_raw, kernel_size=morph_kernel_size)
        binary_clean = morph_res["cleaned"]
    else:
        binary_clean = binary_raw.copy()
        
    # 3. Validation
    white_count = int(np.count_nonzero(binary_clean == 255))
    total_pixels = binary_clean.size
    white_pixel_ratio = float(white_count / total_pixels)
    
    warnings = []
    if white_pixel_ratio > max_white_ratio_limit:
        warnings.append(
            f"Excessive foreground white pixels ({white_pixel_ratio*100:.1f}% > {max_white_ratio_limit*100:.0f}%). "
            "Possible inverted image or severe illumination gradient."
        )
    elif white_pixel_ratio < 0.005:
        warnings.append(
            f"Extremely low foreground density ({white_pixel_ratio*100:.2f}%). "
            "Grid and markings may not have been segmented properly."
        )
        
    is_valid = len(warnings) == 0
    
    return {
        "binary_clean": binary_clean,
        "binary_raw": binary_raw,
        "adaptive_params": {"block_size": block_size, "C": C},
        "use_morphology": use_morphology,
        "white_pixel_ratio": round(white_pixel_ratio, 4),
        "is_valid": is_valid,
        "warning": "; ".join(warnings) if warnings else None
    }
