"""Alternative / Comparative Deskewing Module: Hough Line Transform
Course: ICE415 Digital Image Processing (KMUTT) - Unit 06 Feature Extraction

This module implements 2D Affine Deskewing via the Probabilistic Hough Line Transform
(Hough, 1962; Duda & Hart, 1972) to serve as a comparative baseline in the Ablation Study:
1. Normal Parameterization of Lines in Polar Coordinates:
   ρ = x · cos(θ) + y · sin(θ)
   where ρ is perpendicular distance from the origin and θ is angle of normal vector.
2. In-Plane Rotation Estimation:
   Detects dominant document grid lines with cv2.HoughLinesP, computes angle of near-horizontal
   segments, and estimates median skew angle θ_skew.
3. 2D Affine Rotation:
   Rotates the canvas using cv2.getRotationMatrix2D and cv2.warpAffine.

NOTE FOR ICE415 ABLATION STUDY:
Hough deskewing only compensates for 1 Degree-of-Freedom (2D in-plane roll θ_z).
It cannot correct 3D out-of-plane perspective pitch and yaw (keystoning/trapezoid distortion),
which is why 4-point Homography (Step 3) is superior for mobile camera captures.
"""

from typing import Dict, Any, Tuple, Optional, List
import cv2
import numpy as np


def detect_skew_angle_hough(
    image: np.ndarray,
    canny_low: int = 50,
    canny_high: int = 150,
    hough_threshold: int = 80,
    min_line_length: int = 100,
    max_line_gap: int = 20
) -> Tuple[float, int, np.ndarray]:
    """Estimate in-plane document tilt angle using Probabilistic Hough Transform (cv2.HoughLinesP).
    
    Args:
        image: Input image (BGR or Grayscale).
        canny_low: Lower Canny threshold.
        canny_high: Upper Canny threshold.
        hough_threshold: Accumulator threshold parameter.
        min_line_length: Minimum line length in pixels.
        max_line_gap: Maximum allowed gap between points on the same line to link them.
        
    Returns:
        Tuple of:
            - median_skew_angle: Estimated rotation angle in degrees (-45 to +45).
            - lines_detected_count: Total lines detected.
            - line_debug_image: Image with detected line segments drawn.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        debug_img = image.copy()
    else:
        gray = image.copy()
        debug_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        
    # Edge detection
    edges = cv2.Canny(gray, canny_low, canny_high, apertureSize=3)
    
    # Probabilistic Hough Line Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1.0,
        theta=np.pi / 180.0,
        threshold=hough_threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap
    )
    
    if lines is None or len(lines) == 0:
        return 0.0, 0, debug_img
        
    angles = []
    # Reshape safely to handle both (N, 1, 4) and (N, 4) return shapes across OpenCV versions
    lines_flat = lines.reshape(-1, 4)
    for x1, y1, x2, y2 in lines_flat:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        # Calculate angle of line in degrees
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0:
            continue
            
        angle_deg = np.degrees(np.arctan2(dy, dx))
        
        # Consider nearly horizontal lines (angle within [-45, 45])
        if -45.0 <= angle_deg <= 45.0:
            angles.append(angle_deg)
            cv2.line(debug_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        # Consider nearly vertical lines (angles around 90 or -90)
        elif angle_deg > 45.0:
            vert_skew = angle_deg - 90.0
            angles.append(vert_skew)
            cv2.line(debug_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        elif angle_deg < -45.0:
            vert_skew = angle_deg + 90.0
            angles.append(vert_skew)
            cv2.line(debug_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            
    if not angles:
        return 0.0, int(len(lines_flat)), debug_img
        
    # Use median angle to suppress outliers
    median_angle = float(np.median(angles))
    
    return median_angle, int(len(lines_flat)), debug_img


def hough_deskew(
    image: np.ndarray,
    canny_low: int = 50,
    canny_high: int = 150,
    hough_threshold: int = 80,
    min_line_length: int = 100,
    max_line_gap: int = 20
) -> Dict[str, Any]:
    """Deskew document using Hough Line Transform and 2D Affine Rotation.
    
    Args:
        image: BGR or Grayscale input image.
        canny_low: Lower Canny threshold.
        canny_high: Upper Canny threshold.
        hough_threshold: Hough accumulator threshold.
        min_line_length: Min line length in pixels.
        max_line_gap: Max line gap in pixels.
        
    Returns:
        Dict containing:
            - deskewed_image: Rotated image.
            - skew_angle: Rotation angle in degrees applied.
            - lines_detected: Count of lines found.
            - debug_image: Image with plotted Hough line segments.
            - rotation_matrix: 2x3 affine rotation matrix.
    """
    angle, count, debug_img = detect_skew_angle_hough(
        image,
        canny_low=canny_low,
        canny_high=canny_high,
        hough_threshold=hough_threshold,
        min_line_length=min_line_length,
        max_line_gap=max_line_gap
    )
    
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Rotation matrix: angle in degrees (counter-clockwise)
    M = cv2.getRotationMatrix2D(center, angle, scale=1.0)
    
    # Rotate canvas with white border padding
    deskewed = cv2.warpAffine(
        image,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(image.shape) == 3 else 255
    )
    
    return {
        "deskewed_image": deskewed,
        "skew_angle": round(angle, 3),
        "lines_detected": count,
        "debug_image": debug_img,
        "rotation_matrix": M
    }
