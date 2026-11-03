"""API Route: Human-in-the-Loop Review Queue Handlers
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.storage import SessionStorage

router = APIRouter(prefix="/api/review", tags=["Review"])


class HumanDecisionRequest(BaseModel):
    """Payload for submitting teacher review decision on an ambiguous question."""
    question: int = Field(..., ge=1, le=50, description="Question number being reviewed")
    decision: str = Field(..., description="Selected choice ('A', 'B', 'C', 'D', 'E') or 'Blank'")


@router.get("/{image_id}/queue")
async def get_ambiguous_queue(image_id: str) -> Dict[str, Any]:
    """Retrieve the queue of ambiguous questions requiring teacher verification."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
        
    all_results = res.get("results", [])
    ambiguous_items = [
        item for item in all_results if item.get("status") == "AMBIGUOUS"
    ]
    
    return {
        "image_id": image_id,
        "total_ambiguous": len(ambiguous_items),
        "queue": ambiguous_items,
        "summary": res.get("summary")
    }


@router.get("/{image_id}/{question}/roi/{roi_type}")
async def get_zoomed_roi(image_id: str, question: int, roi_type: str):
    """Retrieve a zoomed patch image ('orig' or 'bin') for an ambiguous question row."""
    s_dir = SessionStorage.get_session_dir(image_id)
    if not s_dir:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
        
    patches_dir = s_dir / "patches"
    type_clean = "orig" if "orig" in roi_type.lower() else "bin"
    patch_path = patches_dir / f"q{question}_{type_clean}.jpg"
    
    if not patch_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"ROI patch not found for question {question} ({type_clean})."
        )
        
    return FileResponse(str(patch_path), media_type="image/jpeg")


@router.post("/{image_id}/decide")
async def submit_human_decision(
    image_id: str,
    payload: HumanDecisionRequest
) -> Dict[str, Any]:
    """Submit teacher confirmation on an ambiguous question, overriding uncertainty."""
    updated_res = SessionStorage.update_human_decision(
        image_id=image_id,
        question_number=payload.question,
        human_decision=payload.decision
    )
    
    if not updated_res:
        raise HTTPException(
            status_code=400,
            detail=f"Could not update question {payload.question} for session '{image_id}'."
        )
        
    summary = updated_res.get("summary", {})
    return {
        "image_id": image_id,
        "question": payload.question,
        "decision": payload.decision.upper(),
        "status": "updated",
        "remaining_ambiguous": summary.get("ambiguous_count", 0),
        "summary": summary
    }
