"""API Route: OMR Image Processing Handlers
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse

from app.storage import SessionStorage, UPLOAD_DIR
from omr.pipeline import OMRPipeline

router = APIRouter(prefix="/api/process", tags=["Processing"])

# Global pipeline instance (cached)
_PIPELINE: Optional[OMRPipeline] = None


def get_pipeline() -> OMRPipeline:
    """Retrieve or initialize the cached OMRPipeline instance."""
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = OMRPipeline()
    return _PIPELINE


@router.post("/{image_id}")
async def process_image_endpoint(
    image_id: str,
    t_low: float = Query(0.15, ge=0.0, le=1.0),
    t_high: float = Query(0.40, ge=0.0, le=1.0),
    delta_min: float = Query(0.20, ge=0.0, le=1.0),
    use_morphology: bool = Query(True),
    auto_calibrate: Optional[bool] = Query(None)
) -> Dict[str, Any]:
    """Execute the 7-step OMR processing pipeline on an uploaded image session.
    
    Args:
        image_id: Unique session ID returned from /api/upload.
        t_low: Lower fill-ratio threshold for blank bubbles.
        t_high: Upper fill-ratio threshold for filled bubbles.
        delta_min: Minimum contrast margin required.
        use_morphology: Whether to apply Mathematical Morphology (Closing & Opening).
        auto_calibrate: Whether to auto-calibrate optimal thresholds per sheet (Otsu clustering).
    """
    try:
        s_dir = SessionStorage.get_session_dir(image_id)
        if not s_dir:
            raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
            
        # Locate original image
        candidates = list(s_dir.glob("original.*"))
        if not candidates:
            raise HTTPException(status_code=404, detail=f"Original image for '{image_id}' missing.")
        orig_path = candidates[0]
        
        # If auto_calibrate is not explicitly passed:
        # Auto-calibrate if default parameters were submitted; otherwise respect manual fine-tuning
        if auto_calibrate is None:
            is_default = (round(t_low, 2) == 0.15 and round(t_high, 2) == 0.40 and round(delta_min, 2) == 0.20)
            should_auto_calibrate = is_default
        else:
            should_auto_calibrate = auto_calibrate
        
        # Initialize pipeline
        pipeline = OMRPipeline(
            t_low=t_low,
            t_high=t_high,
            delta_min=delta_min,
            use_morphology=use_morphology,
            auto_calibrate=should_auto_calibrate
        )
        
        result = pipeline.process_single_image(orig_path)
        # Save results to session directory
        SessionStorage.save_result(image_id, result)
        
        return {
            "image_id": image_id,
            "status": result["status"],
            "rejection_reason": result.get("rejection_reason"),
            "summary": result.get("summary"),
            "processing_time_ms": result.get("processing_time_ms"),
            "debug_urls": {
                "original": f"/api/process/{image_id}/debug/original",
                "edges": f"/api/process/{image_id}/debug/edges",
                "warped": f"/api/process/{image_id}/debug/warped",
                "binary": f"/api/process/{image_id}/debug/binary",
                "overlay": f"/api/process/{image_id}/debug/overlay"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb_lines = traceback.format_exc().strip().splitlines()
        last_call = tb_lines[-2].strip() if len(tb_lines) >= 2 else ""
        err_msg = f"{type(e).__name__}: {str(e)} [{last_call}]"
        print(f"[ERROR in process_image_endpoint]: {err_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {err_msg}")


@router.get("/{image_id}/status")
async def get_processing_status(image_id: str) -> Dict[str, Any]:
    """Retrieve processing status and metrics for an image session."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Results for '{image_id}' not found.")
    return res


@router.get("/{image_id}/debug/{step_name}")
async def get_debug_image(image_id: str, step_name: str):
    """Retrieve an intermediate step image (original, edges, warped, binary, overlay)."""
    s_dir = SessionStorage.get_session_dir(image_id)
    if not s_dir:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
        
    step_clean = step_name.lower().strip()
    
    if step_clean == "overlay":
        img_path = s_dir / "overlay.jpg"
    elif step_clean == "original":
        candidates = list(s_dir.glob("original.*"))
        img_path = candidates[0] if candidates else None
    else:
        # Check debug folder
        debug_dir = s_dir / "debug"
        img_path = debug_dir / f"{step_clean}.jpg"
        if not img_path.exists():
            img_path = debug_dir / f"{step_clean}.png"
        if not img_path.exists() and step_clean == "corners":
            candidates = list(s_dir.glob("original.*"))
            img_path = candidates[0] if candidates else None
            
    if not img_path or not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Debug image '{step_name}' not found for '{image_id}'.")
        
    media_type = "image/png" if img_path.suffix == ".png" else "image/jpeg"
    return FileResponse(str(img_path), media_type=media_type)


@router.delete("/{image_id}")
@router.post("/{image_id}/delete")
async def delete_processing_session(image_id: str) -> Dict[str, Any]:
    """Delete a processed sheet session and all its associated artifacts."""
    success = SessionStorage.delete_session(image_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found or could not be deleted.")
    return {"status": "deleted", "image_id": image_id}


@router.post("/sessions/clear-all")
async def clear_all_processing_sessions() -> Dict[str, Any]:
    """Clear all past processed sheet sessions."""
    deleted_count = SessionStorage.clear_all_sessions()
    return {"status": "cleared", "deleted_count": deleted_count}
