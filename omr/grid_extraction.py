"""Step 5a: Grid Slicing & Concentric Inner Masking Module
Course: ICE415 Digital Image Processing (KMUTT)

This module maps normalized template coordinates to the canonical A4 canvas:
1. Relative Coordinate Mapping:
   Since the document has been warped to a canonical canvas (e.g. 2480x3508 px),
   all bubble centers (cx, cy) and radii (r) are located at known proportional offsets:
   x_px = round(cx_pct * Canvas_Width)
   y_px = round(cy_pct * Canvas_Height)
   r_px = round(r_pct * Canvas_Width)

2. Concentric Inner Circular Masking (Key Anti-Artifact Technique):
   Every printed answer sheet has black ink outline rings around empty bubbles.
   If the full bounding box or full circle is evaluated, the printed rim contributes
   substantial dark pixels, causing False Positives on empty bubbles.
   By applying a concentric inner mask with radius R_inner = 0.82 * R_bubble:
   M_inner(x, y) = 1 if (x - cx)² + (y - cy)² <= R_inner² else 0
   The printed rim is mathematically eliminated from the calculation, ensuring that
   an empty bubble yields a fill-ratio of ~0.0.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json
import cv2
import numpy as np


def load_template(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load answer sheet relative coordinate configuration JSON file.
    
    Args:
        config_path: Path to template_config.json. If None, resolves default path.
        
    Returns:
        Dictionary containing template configuration and relative coordinates.
    """
    if config_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = str(base_dir / "templates" / "template_config.json")
        
    path_obj = Path(config_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Template configuration file not found at: {config_path}")
        
    with open(path_obj, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    return config


def create_inner_mask(
    roi_shape: Tuple[int, int],
    radius: float,
    radius_ratio: float = 0.82
) -> np.ndarray:
    """Create a centered circular binary mask excluding the printed outer rim.
    
    Args:
        roi_shape: Shape of the cropped ROI (height, width).
        radius: Original bubble radius in pixels.
        radius_ratio: Scale factor for inner radius (default 0.82).
        
    Returns:
        Binary mask (uint8) of shape roi_shape with 1s inside inner circle and 0s outside.
    """
    h, w = roi_shape[:2]
    center = (w // 2, h // 2)
    inner_radius = int(round(radius * radius_ratio))
    
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, inner_radius, 1, thickness=-1)
    return mask


def get_bubble_roi(
    image: np.ndarray,
    cx: float,
    cy: float,
    radius: float,
    is_pct: bool = False,
    padding_factor: float = 1.35
) -> Tuple[np.ndarray, Tuple[int, int, int, int], Tuple[int, int], float]:
    """Crop Region of Interest (ROI) centered at the bubble coordinates.
    
    Args:
        image: Canvas image (Height, Width, Channels) or (Height, Width).
        cx: Center x coordinate (pixels or percentage [0-1]).
        cy: Center y coordinate (pixels or percentage [0-1]).
        radius: Bubble radius (pixels or percentage [0-1]).
        is_pct: If True, cx, cy, radius are interpreted as fractions of image dimensions.
        padding_factor: Multiplier to include surrounding buffer for alignment tolerance.
        
    Returns:
        Tuple of:
            - roi: Cropped image region.
            - bbox: (x0, y0, x1, y1) in canvas coordinates.
            - local_center: (cx_local, cy_local) within the cropped ROI.
            - r_px: Radius in pixels.
    """
    h_img, w_img = image.shape[:2]
    
    if is_pct:
        cx_px = int(round(cx * w_img))
        cy_px = int(round(cy * h_img))
        r_px = float(radius * w_img)
    else:
        cx_px = int(round(cx))
        cy_px = int(round(cy))
        r_px = float(radius)
        
    half_box = int(round(r_px * padding_factor))
    x0 = max(0, cx_px - half_box)
    y0 = max(0, cy_px - half_box)
    x1 = min(w_img, cx_px + half_box)
    y1 = min(h_img, cy_px + half_box)
    
    roi = image[y0:y1, x0:x1]
    local_center = (cx_px - x0, cy_px - y0)
    
    return roi, (x0, y0, x1, y1), local_center, r_px


def extract_all_bubbles(
    warped_image: np.ndarray,
    binary_image: np.ndarray,
    template_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Iterate through all questions and options to extract aligned ROIs and inner masks.
    
    Args:
        warped_image: Grayscale or BGR rectified A4 canvas.
        binary_image: Cleaned binary mask (from Step 4).
        template_config: Loaded template dictionary.
        
    Returns:
        List of 50 question dictionaries, each containing:
            - question: Question number (1 to 50)
            - options: Dict mapping 'A', 'B', 'C', 'D', 'E' to:
                - gray_roi: Cropped grayscale patch
                - binary_roi: Cropped binary mask patch
                - inner_mask: Concentric circular mask (0 or 1)
                - bbox: Canvas coordinates (x0, y0, x1, y1)
                - radius_px: Bubble radius in pixels
    """
    if len(warped_image.shape) == 3:
        gray_canvas = cv2.cvtColor(warped_image, cv2.COLOR_BGR2GRAY)
    else:
        gray_canvas = warped_image
        
    h_canon, w_canon = gray_canvas.shape[:2]
    inner_mask_ratio = template_config.get("inner_mask_radius_ratio", 0.82)
    
    extracted_questions = []
    
    for q_item in template_config.get("questions", []):
        q_num = q_item["q"]
        opts_dict = {}
        
        for opt_key, opt_data in q_item["options"].items():
            cx_pct = opt_data["cx_pct"]
            cy_pct = opt_data["cy_pct"]
            r_pct = opt_data["r_pct"]
            
            # Crop ROIs
            gray_roi, bbox, local_center, r_px = get_bubble_roi(
                gray_canvas, cx_pct, cy_pct, r_pct, is_pct=True, padding_factor=1.30
            )
            bin_roi, _, _, _ = get_bubble_roi(
                binary_image, cx_pct, cy_pct, r_pct, is_pct=True, padding_factor=1.30
            )
            
            # Create centered inner mask
            mask = np.zeros(gray_roi.shape[:2], dtype=np.uint8)
            inner_r = int(round(r_px * inner_mask_ratio))
            cv2.circle(mask, local_center, inner_r, 1, thickness=-1)
            
            opts_dict[opt_key] = {
                "gray_roi": gray_roi,
                "binary_roi": bin_roi,
                "inner_mask": mask,
                "bbox": bbox,
                "radius_px": r_px,
                "inner_radius_px": inner_r
            }
            
        extracted_questions.append({
            "question": q_num,
            "options": opts_dict
        })
        
    return extracted_questions
