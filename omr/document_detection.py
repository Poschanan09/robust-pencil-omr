"""Step 2: Document Boundary & Corner Detection Module
Course: ICE415 Digital Image Processing (KMUTT)

This module detects the physical boundary of the answer sheet from mobile camera captures:
1. Preprocessing: Grayscale conversion (BT.601) + Gaussian Smoothing (5x5, σ=1.2)
   to attenuate high-frequency sensor noise while preserving edge boundaries.
2. Canny Edge Detection (Canny, 1986):
   - Computes spatial gradients |G| and direction θ using Sobel operators.
   - Applies Non-Maximum Suppression (NMS) to thin edges to 1-pixel width.
   - Employs Hysteresis Dual-Thresholding (T_low=50, T_high=150) to retain connected edges.
3. Contour Extraction & Topological Border Following (Suzuki & Abe, 1985 via cv2.findContours):
   - Extracts external contours and filters by area.
4. Polygonal Approximation via Ramer-Douglas-Peucker (RDP) Algorithm (Douglas & Peucker, 1973):
   - Uses cv2.approxPolyDP with epsilon = 0.02 * perimeter to find 4 quadrilateral vertices.
5. Fallback Mechanism - Fiducial Markers Detection:
   - If document contour merges with low-contrast tables, detects 4 solid black square fiducial markers.
6. Geometric Corner Ordering:
   - Orders 4 corner coordinates strictly as [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
"""

from typing import Tuple, Optional, Dict, Any, List
import cv2
import numpy as np


def preprocess_for_edges(image: np.ndarray, blur_ksize: int = 5, sigma: float = 1.2) -> np.ndarray:
    """Convert image to grayscale and apply Gaussian blur to suppress noise.
    
    Args:
        image: BGR or Grayscale input image.
        blur_ksize: Gaussian kernel size (must be odd, default 5).
        sigma: Gaussian standard deviation (default 1.2).
        
    Returns:
        Filtered single-channel grayscale image.
    """
    if len(image.shape) == 3:
        # ITU-R BT.601: Y = 0.299R + 0.587G + 0.114B
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
        
    blurred = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), sigmaX=sigma, sigmaY=sigma)
    return blurred


def order_corner_points(pts: np.ndarray) -> np.ndarray:
    """Sort a 4-point quadrilateral into standard order: [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
    
    Uses centroid and coordinate polar angles / coordinate sum-diff to ensure robust ordering
    even under severe perspective skew or rotation up to 45 degrees.
    
    Args:
        pts: Array of shape (4, 2) or (4, 1, 2) containing corner coordinates (x, y).
        
    Returns:
        np.ndarray of shape (4, 2) with dtype float32 ordered as [TL, TR, BR, BL].
    """
    pts = pts.reshape(4, 2).astype(np.float32)
    ordered = np.zeros((4, 2), dtype=np.float32)
    
    # Method 1: Sum and difference of coordinates
    # Top-Left has smallest sum (x + y)
    # Bottom-Right has largest sum (x + y)
    s = pts.sum(axis=1)
    ordered[0] = pts[np.argmin(s)]
    ordered[2] = pts[np.argmax(s)]
    
    # Top-Right has largest difference (x - y)
    # Bottom-Left has smallest difference (x - y)
    diff = pts[:, 0] - pts[:, 1]
    ordered[1] = pts[np.argmax(diff)]
    ordered[3] = pts[np.argmin(diff)]
    
    return ordered


def detect_document_contour(
    image: np.ndarray,
    canny_low: int = 50,
    canny_high: int = 150,
    min_area_ratio: float = 0.15
) -> Tuple[Optional[np.ndarray], Optional[float], np.ndarray]:
    """Detect the quadrilateral outer boundary of the document using Canny and Douglas-Peucker.
    
    Args:
        image: BGR or Grayscale input image.
        canny_low: Lower threshold for Canny hysteresis.
        canny_high: Upper threshold for Canny hysteresis.
        min_area_ratio: Minimum fraction of total image area the contour must span.
        
    Returns:
        Tuple of:
            - corners: np.ndarray of shape (4, 2) or None if detection fails.
            - area: Contour area in square pixels or None.
            - edge_map: Binary edge map from Canny detection.
    """
    blurred = preprocess_for_edges(image)
    h, w = blurred.shape[:2]
    total_area = h * w
    min_area = total_area * min_area_ratio
    
    # 1. Canny Edge Detection
    edge_map = cv2.Canny(blurred, canny_low, canny_high)
    
    # Slight morphological dilation to bridge small fractures in paper border
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edge_dilated = cv2.dilate(edge_map, kernel, iterations=1)
    
    # 2. Extract external contours (Suzuki & Abe, 1985)
    contours, _ = cv2.findContours(edge_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None, edge_map
        
    valid_quads = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
            
        perimeter = cv2.arcLength(cnt, closed=True)
        # Douglas-Peucker approximation with epsilon = 2% of perimeter
        approx = cv2.approxPolyDP(cnt, epsilon=0.02 * perimeter, closed=True)
        
        # We need a convex quadrilateral (4 vertices)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            pts = approx.reshape(4, 2)
            ordered_corners = order_corner_points(pts)
            cy = float(np.mean(ordered_corners[:, 1]))
            valid_quads.append({
                "corners": ordered_corners,
                "area": float(area),
                "cy": cy
            })
            
    if valid_quads:
        max_area = max(q["area"] for q in valid_quads)
        # Filter top-tier candidates (within 15% of max area, e.g. dual A5 sheets on A4)
        top_candidates = [q for q in valid_quads if q["area"] >= 0.85 * max_area]
        # Sort top-to-bottom so Sheet 1 (top) is prioritized on uncut sheets
        top_candidates.sort(key=lambda q: q["cy"])
        chosen = top_candidates[0]
        return chosen["corners"], chosen["area"], edge_map

    return None, None, edge_map


def detect_fiducial_markers(
    image: np.ndarray,
    expected_count: int = 4
) -> Tuple[Optional[np.ndarray], List[Dict[str, Any]]]:
    """Fallback method: Detect the 4 solid black square corner fiducial markers.
    
    Used when document border blends into the background table.
    Fiducial markers are solid black squares (aspect ratio ~1.0, high solidity).
    
    Args:
        image: BGR or Grayscale input image.
        expected_count: Number of markers expected (default 4).
        
    Returns:
        Tuple of:
            - corners: np.ndarray of shape (4, 2) representing document corners derived from markers,
                       or None if 4 markers cannot be resolved.
            - markers_info: List of detected marker candidate dictionaries.
    """
    gray = preprocess_for_edges(image)
    h, w = gray.shape[:2]
    total_area = h * w
    
    # Threshold for solid dark components (inverted: dark markers become white foreground)
    # Using Otsu or local adaptive threshold
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    candidate_markers = []
    # Marker criteria:
    # 1. Area is between 0.05% and 2.5% of total image area
    min_marker_area = total_area * 0.0005
    max_marker_area = total_area * 0.025
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if min_marker_area <= area <= max_marker_area:
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect_ratio = float(bw) / bh if bh > 0 else 0
            # Aspect ratio close to 1.0 (square: 0.75 - 1.33)
            if 0.70 <= aspect_ratio <= 1.40:
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                # Solid filled shape has high solidity (> 0.85)
                if solidity >= 0.82:
                    M = cv2.moments(cnt)
                    if M["m00"] > 0:
                        cx = M["m10"] / M["m00"]
                        cy = M["m01"] / M["m00"]
                        candidate_markers.append({
                            "contour": cnt,
                            "centroid": (cx, cy),
                            "area": area,
                            "bbox": (x, y, bw, bh)
                        })
                        
    if len(candidate_markers) < expected_count:
        return None, candidate_markers
        
    # If more than 4, find the 4 markers closest to the 4 corners of the image
    image_corners = [
        np.array([0, 0]),           # Top-Left
        np.array([w, 0]),           # Top-Right
        np.array([w, h]),           # Bottom-Right
        np.array([0, h])            # Bottom-Left
    ]
    
    chosen_points = []
    centroids = np.array([m["centroid"] for m in candidate_markers], dtype=np.float32)
    
    used_indices = set()
    for ic in image_corners:
        dists = np.linalg.norm(centroids - ic, axis=1)
        for idx in np.argsort(dists):
            if idx not in used_indices:
                used_indices.add(idx)
                chosen_points.append(centroids[idx])
                break
                
    if len(chosen_points) == 4:
        pts = np.array(chosen_points, dtype=np.float32)
        ordered = order_corner_points(pts)
        return ordered, candidate_markers
        
    return None, candidate_markers


def find_document(
    image: np.ndarray,
    canny_low: int = 50,
    canny_high: int = 150,
    min_area_ratio: float = 0.15
) -> Dict[str, Any]:
    """End-to-end Step 2 gateway: detect document corners with automatic fallback.
    
    Args:
        image: BGR or Grayscale input image.
        canny_low: Canny lower threshold.
        canny_high: Canny upper threshold.
        min_area_ratio: Minimum area fraction of document relative to image.
        
    Returns:
        Dict containing:
            - corners: np.ndarray of shape (4, 2) with dtype float32 [TL, TR, BR, BL], or None.
            - method: 'contour' | 'fiducial' | 'failed'
            - debug_image: Annotated BGR image with corners and contour drawn.
            - contour_area: Detected area in pixels or None.
            - edge_map: Canny edge detection result.
    """
    if len(image.shape) == 2:
        debug_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        debug_img = image.copy()
        
    # 1. Primary method: Outer Document Contour
    corners, area, edge_map = detect_document_contour(
        image, canny_low=canny_low, canny_high=canny_high, min_area_ratio=min_area_ratio
    )
    method = "contour"
    
    # 2. Fallback method: Fiducial Markers
    if corners is None:
        corners, _ = detect_fiducial_markers(image)
        if corners is not None:
            method = "fiducial"
            area = float(cv2.contourArea(corners.astype(np.int32)))
        else:
            method = "failed"
            
    # 3. Create visual annotations
    if corners is not None:
        pts_int = corners.reshape(4, 2).astype(np.int32)
        # Draw bounding polygon (Green)
        cv2.polylines(debug_img, [pts_int], isClosed=True, color=(0, 255, 0), thickness=6)
        
        # Color code 4 corners:
        # TL = Red (0, 0, 255), TR = Green (0, 255, 0), BR = Blue (255, 0, 0), BL = Yellow (0, 255, 255)
        corner_colors = [
            (0, 0, 255),      # TL (Red)
            (0, 255, 0),      # TR (Green)
            (255, 0, 0),      # BR (Blue)
            (0, 255, 255)     # BL (Yellow)
        ]
        corner_labels = ["TL", "TR", "BR", "BL"]
        
        for i, (pt, color, label) in enumerate(zip(pts_int, corner_colors, corner_labels)):
            pt_tuple = (int(pt[0]), int(pt[1]))
            cv2.circle(debug_img, pt_tuple, radius=16, color=color, thickness=-1)
            cv2.circle(debug_img, pt_tuple, radius=20, color=(255, 255, 255), thickness=3)
            # Label text
            cv2.putText(
                debug_img,
                label,
                (pt_tuple[0] + 15, pt_tuple[1] - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                (255, 255, 255),
                4,
                cv2.LINE_AA
            )
            cv2.putText(
                debug_img,
                label,
                (pt_tuple[0] + 15, pt_tuple[1] - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                color,
                2,
                cv2.LINE_AA
            )
            
        cv2.putText(
            debug_img,
            f"Method: {method.upper()} | Area: {int(area or 0):,} px",
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3,
            cv2.LINE_AA
        )
    else:
        cv2.putText(
            debug_img,
            "DETECTION FAILED: 4 Document Corners Not Found",
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3,
            cv2.LINE_AA
        )
        
    return {
        "corners": corners,
        "method": method,
        "debug_image": debug_img,
        "contour_area": area,
        "edge_map": edge_map
    }
