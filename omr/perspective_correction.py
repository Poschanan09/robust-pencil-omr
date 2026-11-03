"""Step 3: Perspective Rectification Module
Course: ICE415 Digital Image Processing (KMUTT)

This module performs geometric rectification to eliminate 3D perspective distortion
caused by non-parallel camera planes when capturing answer sheets with smartphones:
1. Projective Geometry & Homography Matrix H (Hartley & Zisserman, 2004):
   A 2D perspective transformation is represented by a 3x3 non-singular matrix H:
   [x']       [h11  h12  h13] [x]
   [y']  =  H [h21  h22  h23] [y]
   [1 ]       [h31  h32  h33] [1]
   With 4 non-collinear point correspondences, Direct Linear Transformation (DLT)
   solves the 8 degrees of freedom (cv2.getPerspectiveTransform).

2. Backward Mapping & Bilinear Interpolation:
   cv2.warpPerspective performs inverse mapping from target canonical canvas (A4 aspect ratio)
   back to the source capture coordinates, sampling pixel intensities via bilinear interpolation
   to prevent discrete sampling holes and moiré artifacts.

3. Geometric Distortion Validation:
   Checks whether the quadrilateral physical geometry respects planar document constraints
   (rejecting severe non-planar folds or extreme tilt).
"""

from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np
from omr.document_detection import order_corner_points

# Standard A4 Canvas Dimensions at 300 DPI
STANDARD_A4_WIDTH = 2480
STANDARD_A4_HEIGHT = 3508
STANDARD_A4_ASPECT = STANDARD_A4_WIDTH / STANDARD_A4_HEIGHT  # ~0.70695 (1 / sqrt(2))


def compute_homography(
    src_points: np.ndarray,
    dst_points: np.ndarray
) -> np.ndarray:
    """Compute the 3x3 perspective transformation matrix H using cv2.getPerspectiveTransform.
    
    Args:
        src_points: Source 4 corner coordinates shape (4, 2) dtype float32.
        dst_points: Destination 4 corner coordinates shape (4, 2) dtype float32.
        
    Returns:
        3x3 Homography matrix H as float64.
    """
    src = src_points.reshape(4, 2).astype(np.float32)
    dst = dst_points.reshape(4, 2).astype(np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    return H


def warp_to_canonical(
    image: np.ndarray,
    corners: np.ndarray,
    canvas_size: Tuple[int, int] = (STANDARD_A4_WIDTH, STANDARD_A4_HEIGHT),
    interpolation: int = cv2.INTER_LINEAR
) -> Tuple[np.ndarray, np.ndarray]:
    """Warp the quadrilateral document region to a flat top-down A4 canonical canvas.
    
    Args:
        image: Source image (BGR or Grayscale).
        corners: 4 document corners shape (4, 2), ordered or unordered.
        canvas_size: Target dimensions as (width, height), default (2480, 3508).
        interpolation: Interpolation flag (cv2.INTER_LINEAR or cv2.INTER_CUBIC).
        
    Returns:
        Tuple of:
            - warped_image: Rectified image of shape (height, width, channels)
            - H: 3x3 Homography transformation matrix
    """
    ordered_corners = order_corner_points(corners)
    width, height = canvas_size
    
    # Destination points for standard rectangular canvas: [TL, TR, BR, BL]
    dst_corners = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ], dtype=np.float32)
    
    H = compute_homography(ordered_corners, dst_corners)
    
    # Apply perspective transformation using backward mapping
    warped = cv2.warpPerspective(
        image,
        H,
        (width, height),
        flags=interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(image.shape) == 3 else 255
    )
    
    return warped, H


def validate_warp(
    corners: np.ndarray,
    canvas_size: Tuple[int, int] = (STANDARD_A4_WIDTH, STANDARD_A4_HEIGHT),
    tolerance: float = 0.20
) -> Dict[str, Any]:
    """Inspect the physical quadrilateral geometry before/after warping.
    
    Examines:
    1. Aspect ratio of the bounding box relative to standard A4 (1 / sqrt(2) ≈ 0.707).
    2. Parallel edge length ratios:
       - Width ratio: top_edge / bottom_edge
       - Height ratio: left_edge / right_edge
       Severe deviations (> 20%) indicate excessive non-planar page wrinkles or extreme perspective.
       
    Args:
        corners: 4 corner points [TL, TR, BR, BL].
        canvas_size: Target (width, height).
        tolerance: Maximum permitted deviation fraction from expected aspect ratio.
        
    Returns:
        Dict with validation metrics and validity boolean.
    """
    pts = order_corner_points(corners)
    tl, tr, br, bl = pts
    
    # Edge lengths
    width_top = float(np.linalg.norm(tr - tl))
    width_bottom = float(np.linalg.norm(br - bl))
    height_left = float(np.linalg.norm(bl - tl))
    height_right = float(np.linalg.norm(br - tr))
    
    avg_width = (width_top + width_bottom) / 2.0
    avg_height = (height_left + height_right) / 2.0
    
    measured_aspect = avg_width / avg_height if avg_height > 0 else 0.0
    target_aspect = canvas_size[0] / canvas_size[1]
    aspect_deviation = abs(measured_aspect - target_aspect) / target_aspect
    
    # Ratio between opposite edges
    w_ratio = min(width_top, width_bottom) / max(width_top, width_bottom) if max(width_top, width_bottom) > 0 else 0
    h_ratio = min(height_left, height_right) / max(height_left, height_right) if max(height_left, height_right) > 0 else 0
    
    issues = []
    if aspect_deviation > tolerance:
        issues.append(f"Aspect ratio deviation ({aspect_deviation*100:.1f}% > {tolerance*100:.0f}%)")
    if w_ratio < 0.65 or h_ratio < 0.65:
        issues.append(f"Extreme perspective trapezoid skew (w_ratio={w_ratio:.2f}, h_ratio={h_ratio:.2f})")
        
    is_valid = len(issues) == 0
    
    return {
        "is_valid": is_valid,
        "measured_aspect_ratio": round(measured_aspect, 4),
        "target_aspect_ratio": round(target_aspect, 4),
        "aspect_deviation": round(aspect_deviation, 4),
        "edge_ratios": {"width_symmetry": round(w_ratio, 3), "height_symmetry": round(h_ratio, 3)},
        "issue": "; ".join(issues) if issues else None
    }


def correct_perspective(
    image: np.ndarray,
    corners: np.ndarray,
    canvas_size: Tuple[int, int] = (STANDARD_A4_WIDTH, STANDARD_A4_HEIGHT),
    tolerance: float = 0.20
) -> Dict[str, Any]:
    """Execute complete Step 3 perspective rectification and validation pipeline.
    
    Args:
        image: BGR or Grayscale capture image.
        corners: Detected 4 quadrilateral corners.
        canvas_size: Target canonical dimensions.
        tolerance: Geometry tolerance limit.
        
    Returns:
        Dict containing:
            - warped_image: Rectified canonical image (canvas_size).
            - homography_matrix: 3x3 transformation matrix.
            - validation: Results from validate_warp.
            - canvas_size: Tuple (W, H).
    """
    validation = validate_warp(corners, canvas_size=canvas_size, tolerance=tolerance)
    warped_img, H = warp_to_canonical(image, corners, canvas_size=canvas_size)
    
    return {
        "warped_image": warped_img,
        "homography_matrix": H,
        "validation": validation,
        "canvas_size": canvas_size
    }
