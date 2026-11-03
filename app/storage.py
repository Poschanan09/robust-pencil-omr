"""Storage and Session Manager for OMR Web Application
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import json
import shutil
import uuid
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class SessionStorage:
    """Manages file storage, intermediate debug images, and JSON results for processed sheets."""

    @staticmethod
    def create_session(filename: str) -> Tuple[str, Path]:
        """Create a new unique image session directory."""
        image_id = uuid.uuid4().hex[:12]
        session_dir = UPLOAD_DIR / image_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return image_id, session_dir

    @staticmethod
    def get_session_dir(image_id: str) -> Optional[Path]:
        """Retrieve the session directory path."""
        s_dir = UPLOAD_DIR / image_id
        return s_dir if s_dir.exists() else None

    @staticmethod
    def save_original(image_id: str, file_bytes: bytes, filename: str) -> Path:
        """Save the uploaded original image to disk."""
        s_dir = UPLOAD_DIR / image_id
        s_dir.mkdir(parents=True, exist_ok=True)
        
        ext = Path(filename).suffix.lower() or ".jpg"
        orig_path = s_dir / f"original{ext}"
        with open(orig_path, "wb") as f:
            f.write(file_bytes)
            
        return orig_path

    @staticmethod
    def save_result(image_id: str, result_data: Dict[str, Any]) -> Path:
        """Save the OMR pipeline result dictionary as result.json (excluding heavy numpy arrays)."""
        s_dir = UPLOAD_DIR / image_id
        s_dir.mkdir(parents=True, exist_ok=True)
        
        # Deepcopy or filter out non-serializable fields (like numpy arrays)
        serializable = {
            "image_id": image_id,
            "status": result_data.get("status"),
            "rejection_reason": result_data.get("rejection_reason"),
            "recommendation": result_data.get("recommendation"),
            "quality": result_data.get("quality"),
            "document": result_data.get("document"),
            "perspective": result_data.get("perspective"),
            "thresholding": result_data.get("thresholding"),
            "summary": result_data.get("summary"),
            "processing_time_ms": result_data.get("processing_time_ms"),
            "results": result_data.get("results", [])
        }
        
        # Save debug images to disk
        debug_imgs = result_data.get("debug_images", {})
        debug_dir = s_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        for name, img in debug_imgs.items():
            if isinstance(img, np.ndarray):
                cv2.imwrite(str(debug_dir / f"{name}.jpg"), img)
                
        # Save visual overlay directly
        if "visual_overlay" in result_data and isinstance(result_data["visual_overlay"], np.ndarray):
            cv2.imwrite(str(s_dir / "overlay.jpg"), result_data["visual_overlay"])
            
        # Save ambiguous patches
        patches = result_data.get("ambiguous_patches", [])
        patches_dir = s_dir / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)
        
        patch_records = []
        for p in patches:
            q_num = p["question"]
            orig_patch_path = patches_dir / f"q{q_num}_orig.jpg"
            bin_patch_path = patches_dir / f"q{q_num}_bin.jpg"
            
            cv2.imwrite(str(orig_patch_path), p["original_patch"])
            cv2.imwrite(str(bin_patch_path), p["binary_patch"])
            
            patch_records.append({
                "question": q_num,
                "bbox": p["bbox"],
                "decision": p["decision"]
            })
            
        serializable["ambiguous_patch_records"] = patch_records
        
        json_path = s_dir / "result.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
            
        return json_path

    @staticmethod
    def load_result(image_id: str) -> Optional[Dict[str, Any]]:
        """Load result.json for a given image session."""
        s_dir = UPLOAD_DIR / image_id
        json_path = s_dir / "result.json"
        if not json_path.exists():
            return None
            
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def update_human_decision(
        image_id: str,
        question_number: int,
        human_decision: str
    ) -> Optional[Dict[str, Any]]:
        """Apply human-in-the-loop decision, updating status from AMBIGUOUS to FILLED or BLANK."""
        res = SessionStorage.load_result(image_id)
        if not res:
            return None
            
        decision_clean = human_decision.strip().upper()
        found = False
        
        for item in res.get("results", []):
            if item["question"] == question_number:
                found = True
                old_status = item["status"]
                
                if decision_clean in ["A", "B", "C", "D", "E"]:
                    item["status"] = "FILLED"
                    item["answer"] = decision_clean
                    item["confidence"] = "HIGH (HUMAN CONFIRMED)"
                    item["reason"] = f"Confirmed by human operator (Overridden from {old_status})"
                elif decision_clean in ["BLANK", "EMPTY", "NONE", "NO_ANSWER"]:
                    item["status"] = "BLANK"
                    item["answer"] = None
                    item["confidence"] = "HIGH (HUMAN CONFIRMED)"
                    item["reason"] = f"Confirmed as blank by human operator (Overridden from {old_status})"
                break
                
        if not found:
            return None
            
        # Recalculate summary metrics
        results = res.get("results", [])
        total = len(results)
        filled = sum(1 for r in results if r["status"] == "FILLED")
        blank = sum(1 for r in results if r["status"] == "BLANK")
        ambig = sum(1 for r in results if r["status"] == "AMBIGUOUS")
        ambig_qs = [r["question"] for r in results if r["status"] == "AMBIGUOUS"]
        
        res["summary"] = {
            "total_questions": total,
            "filled_count": filled,
            "blank_count": blank,
            "ambiguous_count": ambig,
            "rejection_rate_pct": round((ambig / total) * 100, 2) if total > 0 else 0.0,
            "ambiguous_questions": ambig_qs,
            "human_reviewed": True
        }
        
        # Save updated json
        s_dir = UPLOAD_DIR / image_id
        json_path = s_dir / "result.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
            
        return res

    @staticmethod
    def list_all_sessions() -> List[Dict[str, Any]]:
        """List summary of all processed sessions."""
        sessions = []
        if not UPLOAD_DIR.exists():
            return sessions
            
        for s_dir in sorted(UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if s_dir.is_dir():
                json_path = s_dir / "result.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            sessions.append({
                                "image_id": s_dir.name,
                                "status": data.get("status"),
                                "summary": data.get("summary"),
                                "processing_time_ms": data.get("processing_time_ms"),
                                "modified_at": s_dir.stat().st_mtime
                            })
                    except Exception:
                        pass
        return sessions

    @staticmethod
    def delete_session(image_id: str) -> bool:
        """Delete a single image session directory and all its artifacts."""
        s_dir = UPLOAD_DIR / image_id
        if s_dir.exists() and s_dir.is_dir():
            try:
                shutil.rmtree(s_dir)
                return True
            except Exception:
                return False
        return False

    @staticmethod
    def clear_all_sessions() -> int:
        """Delete all image session directories in uploads."""
        count = 0
        if not UPLOAD_DIR.exists():
            return 0
        for s_dir in list(UPLOAD_DIR.iterdir()):
            if s_dir.is_dir():
                try:
                    shutil.rmtree(s_dir)
                    count += 1
                except Exception:
                    pass
        return count
