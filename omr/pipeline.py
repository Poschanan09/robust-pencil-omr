"""Main Pipeline Orchestrator: Robust Pencil OMR Pipeline
Course: ICE415 Digital Image Processing (KMUTT)

Integrates all 7 steps of the processing pipeline into a unified, modular architecture:
[Step 1] Quality Assessment (Blur & Exposure Check)
   ↓ (pass)
[Step 2] Document Boundary Detection (Canny & Douglas-Peucker / Fiducial Fallback)
   ↓ (pass)
[Step 3] Perspective Rectification (4-Point Homography Warp to A4 Canvas)
   ↓
[Step 4] Illumination-Robust Binarization (Adaptive Gaussian Threshold & Morphology)
   ↓
[Step 5] Grid Slicing & Concentric Inner Masking (Fill-Ratio & Glare Analysis)
   ↓
[Step 6] Tri-State Decision Engine (Filled / Blank / Ambiguous Classification)
   ↓
[Step 7] Diagnostic Visual Overlay & Human-in-the-Loop Review Queue Preparation
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import json
import cv2
import numpy as np
import pandas as pd

from omr.quality_check import assess_quality
from omr.document_detection import find_document, order_corner_points
from omr.perspective_correction import correct_perspective, STANDARD_A4_WIDTH, STANDARD_A4_HEIGHT
from omr.hough_deskew import hough_deskew
from omr.thresholding import binarize_document
from omr.grid_extraction import load_template
from omr.feature_extraction import extract_features
from omr.decision_engine import TriStateDecisionEngine
from omr.visualization import draw_overlay, crop_ambiguous_patches


class OMRPipeline:
    """Master orchestrator class executing end-to-end OMR image processing and scoring."""

    def __init__(
        self,
        template_config_path: Optional[str] = None,
        t_low: float = 0.15,
        t_high: float = 0.40,
        delta_min: float = 0.20,
        use_morphology: bool = True,
        auto_calibrate: bool = True
    ):
        """Initialize the pipeline with configurable parameters and template definitions.
        
        Args:
            template_config_path: Path to template_config.json. If None, default is loaded.
            t_low: Lower fill-ratio boundary for blank bubbles.
            t_high: Upper fill-ratio boundary for filled bubbles.
            delta_min: Minimum margin required between top two choices.
            use_morphology: Whether to apply Morphological Closing and Opening in Step 4.
            auto_calibrate: Whether to automatically analyze and calibrate thresholds per sheet.
        """
        self.template_config = load_template(template_config_path)
        self.t_low = float(t_low)
        self.t_high = float(t_high)
        self.delta_min = float(delta_min)
        self.use_morphology = bool(use_morphology)
        
        # If user explicitly passed custom thresholds different from defaults, respect manual overrides
        is_default_params = (self.t_low == 0.15 and self.t_high == 0.40 and self.delta_min == 0.20)
        self.auto_calibrate = bool(auto_calibrate and is_default_params)
        
        self.decision_engine = TriStateDecisionEngine(
            t_low=self.t_low,
            t_high=self.t_high,
            delta_min=self.delta_min,
            auto_calibrate=self.auto_calibrate
        )

    def process_single_image(
        self,
        image_input: Union[str, Path, np.ndarray],
        output_debug_dir: Optional[Union[str, Path]] = None,
        save_debug_images: bool = False
    ) -> Dict[str, Any]:
        """Execute the end-to-end 7-step OMR pipeline on a single document image.
        
        Args:
            image_input: File path (str or Path) or numpy image array (BGR/Grayscale).
            output_debug_dir: Directory to save step-by-step intermediate images.
            save_debug_images: If True, writes intermediate step images to disk.
            
        Returns:
            Dictionary containing:
                - status: 'success' | 'rejected'
                - rejection_reason: str or None
                - quality: Quality assessment results from Step 1
                - document: Document boundary results from Step 2
                - perspective: Rectification results from Step 3
                - thresholding: Binarization metrics from Step 4
                - features: Extracted features for all bubbles from Step 5
                - results: 50 individual question decision objects from Step 6
                - summary: Overall summary statistics (filled, blank, ambiguous, rejection rate)
                - visual_overlay: Annotated A4 canvas image from Step 7
                - ambiguous_patches: Cropped original vs mask patches for ambiguous review
                - processing_time_ms: Total execution time in milliseconds
        """
        start_time = time.perf_counter()
        
        # 0. Load image if path provided
        image_name = "image"
        if isinstance(image_input, (str, Path)):
            img_path = Path(image_input)
            image_name = img_path.stem
            if not img_path.exists():
                return {
                    "status": "rejected",
                    "rejection_reason": f"FILE_NOT_FOUND: {img_path}",
                    "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }
            # Load with PIL + ImageOps.exif_transpose to automatically respect mobile camera orientation
            try:
                from PIL import Image, ImageOps
                with Image.open(str(img_path)) as pil_img:
                    pil_img = ImageOps.exif_transpose(pil_img)
                    if pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")
                    raw_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception:
                # Fallback to standard numpy fromfile + imdecode
                data = np.fromfile(str(img_path), dtype=np.uint8)
                raw_image = cv2.imdecode(data, cv2.IMREAD_COLOR)

            if raw_image is None:
                return {
                    "status": "rejected",
                    "rejection_reason": f"IMAGE_DECODE_FAILED: {img_path}",
                    "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }
        elif isinstance(image_input, np.ndarray):
            raw_image = image_input.copy()
        else:
            raise TypeError(f"Unsupported image_input type: {type(image_input)}")

        # =============================================================
        # [Step 1] Image Quality Assessment
        # =============================================================
        quality_res = assess_quality(raw_image)
        if not quality_res["passed"]:
            return {
                "status": "rejected",
                "rejection_reason": f"QUALITY_CHECK_FAILED: {quality_res['rejection_reason']}",
                "quality": quality_res,
                "recommendation": quality_res["recommendation"],
                "debug_images": {
                    "original": raw_image
                },
                "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        # =============================================================
        # [Sheet Layout & Template Selection]
        # Auto-detect whether input is Landscape Kaggle 30Q or KMUTT ICE415 Sheet (A4 / A5)
        # =============================================================
        h_raw, w_raw = raw_image.shape[:2]
        raw_aspect = w_raw / h_raw if h_raw > 0 else 1.0
        # Kaggle 30Q benchmark sheets are ultra-wide table crops (aspect > 1.68, width <= 1200)
        is_landscape_kaggle = (raw_aspect > 1.65 and w_raw <= 1500)

        if is_landscape_kaggle:
            # Load Kaggle Benchmark 30Q 4Opts Template
            kaggle_tpl_path = Path(__file__).resolve().parent.parent / "templates" / "kaggle_30q_template.json"
            if kaggle_tpl_path.exists():
                with open(kaggle_tpl_path, "r", encoding="utf-8") as f:
                    active_template = json.load(f)
            else:
                active_template = self.template_config

            # Deskew with Hough Line Analysis (ICE415 Unit 06)
            deskew_res = hough_deskew(raw_image)
            deskewed_image = deskew_res["deskewed_image"]

            # Compute genuine Canny edge map (ICE415 Unit 05)
            gray_deskewed = cv2.cvtColor(deskewed_image, cv2.COLOR_BGR2GRAY) if len(deskewed_image.shape) == 3 else deskewed_image
            blurred_deskewed = cv2.GaussianBlur(gray_deskewed, (5, 5), 1.2)
            edge_map = cv2.Canny(blurred_deskewed, 50, 150)

            # Table Bounding & 4-Point Homography Warp (ICE415 Unit 04 & 07)
            # Rectifies perspective keystone slope across the table to ensure bubble alignment
            dilated = cv2.dilate(edge_map, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=2)
            cnts, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            h_img, w_img = deskewed_image.shape[:2]
            table_c = max(cnts, key=cv2.contourArea) if len(cnts) > 0 else None

            if table_c is not None:
                gx, gy, gw, gh = cv2.boundingRect(table_c)
            else:
                gx, gy, gw, gh = 0, 0, w_img, h_img

            # If the sheet is already cropped flush with image borders (e.g. sheets 1-62):
            if gw > 0.94 * w_img and gh > 0.90 * h_img and gx < 15 and gy < 15:
                warped_image = cv2.resize(deskewed_image, (1024, 556), interpolation=cv2.INTER_LINEAR)
                edge_map_display = cv2.resize(edge_map, (1024, 556), interpolation=cv2.INTER_NEAREST)
                corners = np.array([[0, 0], [1024, 0], [1024, 556], [0, 556]], dtype=np.float32)
            elif table_c is not None and cv2.contourArea(table_c) > (w_img * h_img * 0.4):
                peri = cv2.arcLength(table_c, True)
                approx = cv2.approxPolyDP(table_c, 0.02 * peri, True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2).astype(np.float32)
                else:
                    rect = cv2.minAreaRect(table_c)
                    pts = cv2.boxPoints(rect).astype(np.float32)

                ordered = order_corner_points(pts)
                dst = np.array([[0, 0], [1024, 0], [1024, 556], [0, 556]], dtype=np.float32)
                M = cv2.getPerspectiveTransform(ordered, dst)
                warped_image = cv2.warpPerspective(deskewed_image, M, (1024, 556), flags=cv2.INTER_LINEAR)
                edge_map_display = cv2.warpPerspective(edge_map, M, (1024, 556), flags=cv2.INTER_NEAREST)
                corners = ordered
            else:
                warped_image = cv2.resize(deskewed_image, (1024, 556), interpolation=cv2.INTER_LINEAR)
                edge_map_display = cv2.resize(edge_map, (1024, 556), interpolation=cv2.INTER_NEAREST)
                corners = np.array([[0, 0], [1024, 0], [1024, 556], [0, 556]], dtype=np.float32)

            doc_res = {
                "method": "hough_deskew_table_homography",
                "rotation_angle": deskew_res.get("skew_angle", 0.0),
                "edge_map": edge_map_display,
                "corners": corners,
                "contour_area": float(1024 * 556)
            }
            persp_res = {
                "warped_image": warped_image,
                "H": np.eye(3),
                "status": "rectified_table_homography",
                "validation": {"valid": True, "aspect_ratio": round(1024/556, 4)},
                "canvas_size": (1024, 556)
            }
        else:
            # Standard Portrait A4 Sheet (50 questions, 5 choices A-E)
            active_template = self.template_config
            # [Step 2] Document Boundary Detection
            doc_res = find_document(raw_image)
            corners = doc_res["corners"]
            
            # If portrait detection failed, check if image is a 90-degree rotated landscape sheet
            if corners is None or doc_res["method"] == "failed":
                rotated_attempt = cv2.rotate(raw_image, cv2.ROTATE_90_CLOCKWISE)
                h_rot, w_rot = rotated_attempt.shape[:2]
                if (w_rot / h_rot) > 1.25:
                    # Retry pipeline with rotated image
                    return self.process_single_image(rotated_attempt, output_debug_dir=output_debug_dir, save_debug_images=save_debug_images)

                return {
                    "status": "rejected",
                    "rejection_reason": "DOCUMENT_DETECTION_FAILED: Could not locate 4 document corners",
                    "quality": quality_res,
                    "document": {
                        "corners": None,
                        "method": doc_res.get("method", "failed"),
                        "contour_area": doc_res.get("contour_area")
                    },
                    "debug_images": {
                        "original": raw_image,
                        "corners": doc_res.get("debug_image", raw_image),
                        "edges": doc_res.get("edge_map")
                    },
                    "recommendation": "กรุณาถ่ายภาพกระดาษคำตอบให้เห็นขอบกระดาษครบทั้ง 4 มุมบนพื้นผิวที่มีสีตัดกันชัดเจน (เช่น วางบนโต๊ะไม้หรือแผ่นรองสีเข้ม)",
                    "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }

            # [Step 3] Perspective Rectification (Homography Warp to A5 or A4)
            # Check aspect ratio of detected corners:
            # - If landscape (w/h > 1.05, e.g. A5 sheet frame 196x136.5 mm): warp to canonical A5 canvas (2480, 1728)
            # - If portrait (w/h <= 1.05, e.g. full A4 sheet): warp to canonical A4 canvas (2480, 3508)
            w_top = float(np.linalg.norm(corners[1] - corners[0]))
            w_bot = float(np.linalg.norm(corners[2] - corners[3]))
            h_left = float(np.linalg.norm(corners[3] - corners[0]))
            h_right = float(np.linalg.norm(corners[2] - corners[1]))
            avg_w = (w_top + w_bot) / 2.0
            avg_h = (h_left + h_right) / 2.0
            corner_aspect = avg_w / avg_h if avg_h > 0 else 1.0

            if corner_aspect > 1.05:
                canonical_canvas = (2480, 1728)
            else:
                canonical_canvas = (STANDARD_A4_WIDTH, STANDARD_A4_HEIGHT)

            persp_res = correct_perspective(
                raw_image,
                corners,
                canvas_size=canonical_canvas
            )
            warped_image = persp_res["warped_image"]

        # =============================================================
        # [Step 4] Illumination-Robust Binarization & Morphology
        # =============================================================
        thresh_res = binarize_document(
            warped_image,
            use_morphology=self.use_morphology
        )
        binary_clean = thresh_res["binary_clean"]

        # =============================================================
        # [Step 5] Grid Extraction & Feature Computation
        # =============================================================
        features = extract_features(
            warped_image,
            binary_clean,
            template_config=active_template
        )

        # =============================================================
        # [Step 6] Tri-State Decision Engine
        # =============================================================
        decision_pack = self.decision_engine.decide_all(features)
        results = decision_pack["results"]
        summary = decision_pack["summary"]

        # =============================================================
        # [Step 7] Diagnostic Visualization & Ambiguity Patch Slicing
        # =============================================================
        overlay_img = draw_overlay(warped_image, results, active_template)
        ambiguous_patches = crop_ambiguous_patches(warped_image, binary_clean, results, active_template)

        total_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Optional: Save debug images
        debug_images_dict = {
            "original": raw_image,
            "corners": doc_res.get("debug_image", raw_image),
            "edges": doc_res["edge_map"],
            "warped": warped_image,
            "binary": binary_clean,
            "overlay": overlay_img
        }

        if save_debug_images and output_debug_dir:
            out_dir = Path(output_debug_dir) / image_name
            out_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_dir / "01_original.jpg"), raw_image)
            cv2.imwrite(str(out_dir / "02_edges.png"), doc_res["edge_map"])
            cv2.imwrite(str(out_dir / "03_warped.jpg"), warped_image)
            cv2.imwrite(str(out_dir / "04_binary.png"), binary_clean)
            cv2.imwrite(str(out_dir / "05_overlay.jpg"), overlay_img)

        return {
            "status": "success",
            "rejection_reason": None,
            "image_name": image_name,
            "quality": quality_res,
            "document": {
                "corners": corners.tolist(),
                "method": doc_res["method"],
                "contour_area": doc_res["contour_area"]
            },
            "perspective": {
                "validation": persp_res["validation"],
                "canvas_size": persp_res["canvas_size"]
            },
            "thresholding": {
                "white_pixel_ratio": thresh_res["white_pixel_ratio"],
                "use_morphology": thresh_res["use_morphology"]
            },
            "results": results,
            "summary": summary,
            "visual_overlay": overlay_img,
            "ambiguous_patches": ambiguous_patches,
            "debug_images": debug_images_dict,
            "processing_time_ms": total_time_ms
        }

    def process_batch(
        self,
        image_paths: List[Union[str, Path]],
        output_debug_dir: Optional[Union[str, Path]] = None,
        save_debug_images: bool = False
    ) -> List[Dict[str, Any]]:
        """Process a collection of answer sheet images in batch mode.
        
        Args:
            image_paths: List of file paths.
            output_debug_dir: Optional directory to store debug outputs.
            save_debug_images: Whether to save intermediate image steps.
            
        Returns:
            List of result dictionaries.
        """
        batch_results = []
        for p in image_paths:
            res = self.process_single_image(
                p,
                output_debug_dir=output_debug_dir,
                save_debug_images=save_debug_images
            )
            batch_results.append(res)
        return batch_results

    @staticmethod
    def export_results(
        batch_results: List[Dict[str, Any]],
        output_path: Union[str, Path],
        export_format: str = "csv"
    ) -> Path:
        """Export grading and decision results across all processed sheets to CSV or JSON.
        
        Args:
            batch_results: List of result dictionaries from process_batch or process_single_image.
            output_path: Destination file path.
            export_format: 'csv' or 'json' (default 'csv').
            
        Returns:
            Path object of exported file.
        """
        records = []
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        
        for sheet in batch_results:
            img_name = sheet.get("image_name", "unknown")
            status = sheet.get("status", "rejected")
            
            if status != "success":
                records.append({
                    "image_id": img_name,
                    "question": None,
                    "status": "REJECTED",
                    "answer": None,
                    "confidence": None,
                    "delta_f": None,
                    "fill_ratio_first": None,
                    "reason": sheet.get("rejection_reason", "UNKNOWN_REJECTION")
                })
                continue
                
            for dec in sheet.get("results", []):
                top_opts = dec.get("top_two", ["A", "B"])
                f_ratios = dec.get("fill_ratios", {})
                first_opt = top_opts[0] if top_opts else "A"
                records.append({
                    "image_id": img_name,
                    "question": dec["question"],
                    "status": dec["status"],
                    "answer": dec["answer"],
                    "confidence": dec["confidence"],
                    "delta_f": dec["delta_f"],
                    "fill_ratio_first": f_ratios.get(first_opt, 0.0),
                    "reason": dec["reason"]
                })
                
        df = pd.DataFrame(records)
        if export_format.lower() == "csv":
            df.to_csv(str(out_p), index=False, encoding="utf-8")
        elif export_format.lower() == "json":
            df.to_json(str(out_p), orient="records", indent=2, force_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {export_format}. Use 'csv' or 'json'.")
            
        return out_p
