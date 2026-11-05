"""Step 7: Diagnostic Visual Overlay & ROI Slicing Module
Course: ICE415 Digital Image Processing (KMUTT)

This module produces color-coded diagnostic visual overlays on top of the
rectified A4 document canvas and extracts zoomed ROI patches for the Human-in-the-Loop UI:
- 🟢 Green Bounding Polygon & Label: Confirmed FILLED bubble (HIGH confidence)
- 🟠 Amber/Orange Bounding Box: AMBIGUOUS bubble (flagged for review)
- ⬜ Neutral Gray Outline: Confirmed BLANK bubble
- Summary Header Banner: Reports total, scored, blank, ambiguous counts, and rejection rate.
"""

from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np


def draw_overlay(
    warped_image: np.ndarray,
    results: List[Dict[str, Any]],
    template_config: Dict[str, Any]
) -> np.ndarray:
    """Render a comprehensive diagnostic visual overlay on top of the A4 document canvas.
    
    Args:
        warped_image: Rectified A4 canvas (BGR or Grayscale).
        results: List of 50 decision dictionaries from TriStateDecisionEngine.
        template_config: Loaded template dictionary with bubble coordinates.
        
    Returns:
        Annotated BGR image with bounding indicators and summary statistics.
    """
    if len(warped_image.shape) == 2:
        overlay_canvas = cv2.cvtColor(warped_image, cv2.COLOR_GRAY2BGR)
    else:
        overlay_canvas = warped_image.copy()
        
    h_canvas, w_canvas = overlay_canvas.shape[:2]
    
    # Map questions for quick lookup
    q_lookup = {item["q"]: item for item in template_config.get("questions", [])}
    
    # Color definitions (BGR)
    COLOR_FILLED = (40, 200, 40)        # Vibrant Green
    COLOR_FILLED_INNER = (60, 230, 60)  # Bright Lime Green
    COLOR_AMBIGUOUS = (0, 140, 255)     # Amber / Orange
    COLOR_BLANK_RING = (220, 175, 120)  # Soft Slate / Cyan (Subtle sampling ring)
    COLOR_BLANK_TEXT = (150, 150, 150)  # Muted Gray
    COLOR_TEXT = (25, 25, 25)           # Near Black
    
    for dec in results:
        q_num = dec["question"]
        status = dec["status"]
        answer = dec["answer"]
        top_two = dec.get("top_two", ["A", "B"])
        fill_ratios = dec.get("fill_ratios", {})
        
        q_meta = q_lookup.get(q_num)
        if not q_meta:
            continue
            
        options = q_meta["options"]
        
        # 1. Draw subtle Concentric Inner Sampling Ring & center crosshair on all option bubbles
        for opt_key, opt_info in options.items():
            ocx = int(round(opt_info["cx_pct"] * w_canvas))
            ocy = int(round(opt_info["cy_pct"] * h_canvas))
            or_px = int(round(opt_info["r_pct"] * w_canvas))
            inner_r = max(2, int(round(or_px * 0.82)))
            
            # Show inner sampling boundary for every bubble
            is_active_filled = (status == "FILLED" and opt_key == answer)
            is_active_ambig = (status == "AMBIGUOUS" and opt_key in top_two)
            
            if not is_active_filled and not is_active_ambig:
                cv2.circle(overlay_canvas, (ocx, ocy), inner_r, COLOR_BLANK_RING, 1, cv2.LINE_AA)
                cv2.drawMarker(overlay_canvas, (ocx, ocy), (190, 190, 190), cv2.MARKER_CROSS, 4, 1)

        # 2. Status-specific annotations
        if status == "FILLED":
            chosen_opt = answer
            if chosen_opt and chosen_opt in options:
                opt_info = options[chosen_opt]
                cx = int(round(opt_info["cx_pct"] * w_canvas))
                cy = int(round(opt_info["cy_pct"] * h_canvas))
                r = int(round(opt_info["r_pct"] * w_canvas))
                inner_r = max(2, int(round(r * 0.82)))
                
                # Double ring: solid outer boundary + glowing inner measurement mask
                cv2.circle(overlay_canvas, (cx, cy), r + 4, COLOR_FILLED, 3, cv2.LINE_AA)
                cv2.circle(overlay_canvas, (cx, cy), inner_r, COLOR_FILLED_INNER, 2, cv2.LINE_AA)
                
                # Checkmark badge beside bubble with fill %
                f_val = fill_ratios.get(chosen_opt, 0.0)
                badge_text = f"✓ {chosen_opt} ({int(round(f_val*100))}%)"
                # Text shadow for maximum contrast
                cv2.putText(overlay_canvas, badge_text, (cx - 24, cy - r - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 3, cv2.LINE_AA)
                cv2.putText(overlay_canvas, badge_text, (cx - 24, cy - r - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_FILLED, 2, cv2.LINE_AA)
                
        elif status == "AMBIGUOUS":
            opt1 = top_two[0] if len(top_two) > 0 else "A"
            opt2 = top_two[1] if len(top_two) > 1 else "B"
            for opt_key in [opt1, opt2]:
                if opt_key in options:
                    opt_info = options[opt_key]
                    cx = int(round(opt_info["cx_pct"] * w_canvas))
                    cy = int(round(opt_info["cy_pct"] * h_canvas))
                    r = int(round(opt_info["r_pct"] * w_canvas))
                    
                    # Amber warning box
                    box_pad = r + 4
                    cv2.rectangle(
                        overlay_canvas,
                        (cx - box_pad, cy - box_pad),
                        (cx + box_pad, cy + box_pad),
                        COLOR_AMBIGUOUS,
                        2,
                        cv2.LINE_AA
                    )
                    f_val = fill_ratios.get(opt_key, 0.0)
                    cv2.putText(
                        overlay_canvas,
                        f"{opt_key}:{int(round(f_val*100))}%",
                        (cx - 18, cy + r + 16),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.42,
                        COLOR_AMBIGUOUS,
                        1,
                        cv2.LINE_AA
                    )
                    
            # Warning banner above question
            opt1_info = options.get(opt1, {})
            if opt1_info:
                cx1 = int(round(opt1_info["cx_pct"] * w_canvas))
                cy1 = int(round(opt1_info["cy_pct"] * h_canvas))
                warning_text = f"⚠️ Q{q_num} AMBIGUOUS: {opt1} vs {opt2}"
                cv2.putText(overlay_canvas, warning_text, (cx1 - 25, cy1 - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 3, cv2.LINE_AA)
                cv2.putText(overlay_canvas, warning_text, (cx1 - 25, cy1 - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, COLOR_AMBIGUOUS, 2, cv2.LINE_AA)
                
        elif status == "BLANK":
            # Clean indicator positioned to the right of option E
            last_opt = options.get("E", {})
            if last_opt:
                cx_e = int(round(last_opt["cx_pct"] * w_canvas))
                cy_e = int(round(last_opt["cy_pct"] * h_canvas))
                cv2.putText(
                    overlay_canvas,
                    "—",
                    (cx_e + 20, cy_e + 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    COLOR_BLANK_TEXT,
                    1,
                    cv2.LINE_AA
                )

    # Render Summary Dashboard Header Bar (top of sheet: y=0 to y=65)
    total_q = len(results)
    filled_q = sum(1 for d in results if d["status"] == "FILLED")
    blank_q = sum(1 for d in results if d["status"] == "BLANK")
    ambig_q = sum(1 for d in results if d["status"] == "AMBIGUOUS")
    rejection_rate = (ambig_q / total_q * 100) if total_q > 0 else 0.0

    header_h = 65
    banner_bg = np.full((header_h, w_canvas, 3), (248, 249, 250), dtype=np.uint8)
    cv2.line(banner_bg, (0, header_h - 1), (w_canvas, header_h - 1), (190, 195, 200), 2)

    cv2.putText(
        banner_bg,
        f"ICE415 Robust Pencil OMR | Total: {total_q} | Filled: {filled_q} (Green) | Blank: {blank_q} (Circles) | Ambiguous: {ambig_q} (Amber)",
        (30, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        COLOR_TEXT,
        2,
        cv2.LINE_AA
    )
    
    # Composite banner
    overlay_canvas[0:header_h, 0:w_canvas] = banner_bg
    return overlay_canvas


def crop_ambiguous_patches(
    warped_image: np.ndarray,
    binary_image: np.ndarray,
    results: List[Dict[str, Any]],
    template_config: Dict[str, Any],
    padding: int = 15
) -> List[Dict[str, Any]]:
    """Crop zoomed side-by-side patches (Original vs Binary Mask) for ambiguous questions.
    
    Args:
        warped_image: Rectified A4 canvas.
        binary_image: Cleaned binary mask.
        results: Decision list from Step 6.
        template_config: Loaded template dict.
        padding: Pixel padding around the question row.
        
    Returns:
        List of ambiguous question review objects with cropped image arrays.
    """
    h_canvas, w_canvas = warped_image.shape[:2]
    q_lookup = {item["q"]: item for item in template_config.get("questions", [])}
    
    ambiguous_patches = []
    
    for dec in results:
        if dec["status"] != "AMBIGUOUS":
            continue
            
        q_num = dec["question"]
        q_meta = q_lookup.get(q_num)
        if not q_meta:
            continue
            
        options = q_meta["options"]
        xs = [int(round(opt["cx_pct"] * w_canvas)) for opt in options.values()]
        ys = [int(round(opt["cy_pct"] * h_canvas)) for opt in options.values()]
        r = int(round(list(options.values())[0]["r_pct"] * w_canvas))
        
        x0 = max(0, min(xs) - r - padding - 40)  # include Q# label
        x1 = min(w_canvas, max(xs) + r + padding)
        y0 = max(0, min(ys) - r - padding)
        y1 = min(h_canvas, max(ys) + r + padding)
        
        orig_crop = warped_image[y0:y1, x0:x1]
        bin_crop = binary_image[y0:y1, x0:x1]
        
        ambiguous_patches.append({
            "question": q_num,
            "decision": dec,
            "bbox": (x0, y0, x1, y1),
            "original_patch": orig_crop,
            "binary_patch": bin_crop
        })
        
    return ambiguous_patches
