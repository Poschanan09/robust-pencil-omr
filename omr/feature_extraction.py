"""Step 5b: Feature Extraction & Graphite Glare Analysis Module
Course: ICE415 Digital Image Processing (KMUTT)

This module computes numerical features for each bubble to enable confident decision making:
1. Fill-Ratio Metric (F_i):
   The fundamental metric indicating the proportion of bubble area filled by pencil graphite:
   F_i = (∑_{p ∈ Mask} B(p)) / (255 · N_pixels(Mask))  ∈ [0.0, 1.0]
   Where:
   - B(p) ∈ {0, 255} is the binary foreground intensity (white = pencil mark).
   - Mask is the Concentric Inner Circular Mask (omitting printed form ring outlines).
   
2. Graphite Glare & Texture Variance Compensation:
   Pencil graphite forms a microscopic polycrystalline surface. Under direct lamp illumination
   or camera flashes, specular reflection ("Graphite Sheen / Glare") can cause shaded marks
   to reflect bright light directly into the lens.
   While a purely binary threshold may underestimate the fill-ratio (mistaking the bright sheen
   for paper), the physical texture variance within the mask differs fundamentally:
   - Clean Paper: Uniform, smooth intensity (σ_gray ≤ 8.0)
   - Shaded Pencil under Glare: Micro-facets of graphite crystals produce high variance (σ_gray ≥ 20.0)
   When detected, the system flags the bubble as a potential Glare Anomaly to trigger
   the Tri-State Rejection threshold instead of false blank classification.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from omr.grid_extraction import extract_all_bubbles, load_template


def compute_fill_ratio(binary_roi: np.ndarray, inner_mask: np.ndarray) -> float:
    """Compute the fill ratio of pencil graphite within the inner circular mask.
    
    Args:
        binary_roi: Single-channel binary image patch (0 = paper, 255 = mark).
        inner_mask: Binary mask with 1s inside the inner circle and 0s elsewhere.
        
    Returns:
        Float fill-ratio value bounded in [0.0, 1.0].
    """
    mask_pixels = np.count_nonzero(inner_mask == 1)
    if mask_pixels == 0:
        return 0.0
        
    # Count foreground white pixels inside the inner mask
    active_foreground = np.count_nonzero((binary_roi == 255) & (inner_mask == 1))
    fill_ratio = float(active_foreground / mask_pixels)
    
    return round(float(np.clip(fill_ratio, 0.0, 1.0)), 4)


def compute_texture_std(gray_roi: np.ndarray, inner_mask: np.ndarray) -> Tuple[float, float]:
    """Compute standard deviation and mean of grayscale intensities inside the mask.
    
    Args:
        gray_roi: Single-channel grayscale patch [0-255].
        inner_mask: Binary mask with 1s inside inner circle.
        
    Returns:
        Tuple of (std_dev, mean_intensity).
    """
    valid_pixels = gray_roi[inner_mask == 1]
    if len(valid_pixels) == 0:
        return 0.0, 0.0
        
    std_val = float(np.std(valid_pixels))
    mean_val = float(np.mean(valid_pixels))
    
    return round(std_val, 2), round(mean_val, 2)


def detect_glare(
    fill_ratio: float,
    texture_std: float,
    mean_intensity: float,
    glare_std_thresh: float = 20.0,
    glare_fill_min: float = 0.12,
    glare_fill_max: float = 0.38,
    glare_max_brightness: float = 215.0
) -> bool:
    """Detect whether a bubble suffers from graphite specular reflection (glare).
    
    A glare anomaly occurs when a bubble was shaded with pencil, but specular flash/light
    reflection brightens part of the graphite crystals, causing:
    1. Borderline or suppressed fill ratio (glare_fill_min <= fill_ratio < glare_fill_max)
    2. High textural standard deviation (texture_std >= glare_std_thresh)
    3. Intermediate reflection intensity (100 <= mean_intensity <= glare_max_brightness),
       which differs distinctly from pure unshaded paper (> 215).
    
    Args:
        fill_ratio: Measured fill ratio.
        texture_std: Grayscale standard deviation inside mask.
        mean_intensity: Mean grayscale intensity.
        glare_std_thresh: Minimum texture std dev indicating crystal micro-facets (default 20.0).
        glare_fill_min: Minimum fill ratio to consider (default 0.12).
        glare_fill_max: Maximum fill ratio where glare is considered ambiguous (default 0.38).
        glare_max_brightness: Maximum brightness cutoff above which is clean unshaded paper (default 215.0).
        
    Returns:
        True if graphite glare anomaly is suspected, False otherwise.
    """
    if (glare_fill_min <= fill_ratio < glare_fill_max and 
        texture_std >= glare_std_thresh and 
        100.0 <= mean_intensity <= glare_max_brightness):
        return True
    return False


def extract_features(
    warped_image: np.ndarray,
    binary_image: np.ndarray,
    template_config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute complete Step 5 grid extraction and feature computation across all questions.
    
    Args:
        warped_image: Rectified A4 canvas (BGR or Grayscale).
        binary_image: Cleaned binary mask (from Step 4).
        template_config: Loaded template dict. If None, loaded automatically.
        
    Returns:
        List of 50 question records, each containing:
            - question: Question number (1 to 50)
            - options: Mapping from 'A'-'E' to:
                - fill_ratio: float [0.0 - 1.0]
                - texture_std: float
                - mean_intensity: float
                - has_glare: bool
                - bbox: (x0, y0, x1, y1)
    """
    if template_config is None:
        template_config = load_template()
        
    extracted_bubbles = extract_all_bubbles(warped_image, binary_image, template_config)
    
    questions_features = []
    
    for q_item in extracted_bubbles:
        q_num = q_item["question"]
        opts_features = {}
        
        for opt_key, bubble_data in q_item["options"].items():
            gray_roi = bubble_data["gray_roi"]
            bin_roi = bubble_data["binary_roi"]
            inner_mask = bubble_data["inner_mask"]
            bbox = bubble_data["bbox"]
            
            fill_r = compute_fill_ratio(bin_roi, inner_mask)
            tex_std, mean_val = compute_texture_std(gray_roi, inner_mask)
            is_glare = detect_glare(fill_r, tex_std, mean_val)
            
            opts_features[opt_key] = {
                "fill_ratio": fill_r,
                "texture_std": tex_std,
                "mean_intensity": mean_val,
                "has_glare": is_glare,
                "bbox": bbox
            }
            
        questions_features.append({
            "question": q_num,
            "options": opts_features
        })
        
    return questions_features
