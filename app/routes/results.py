"""API Route: Results and Data Export Handlers
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Query, Body
from fastapi.responses import FileResponse
import pandas as pd

from app.storage import SessionStorage, UPLOAD_DIR

router = APIRouter(prefix="/api/results", tags=["Results"])


class ScoreRequest(BaseModel):
    """Payload for auto-grading against an Answer Key."""
    answer_key: Dict[str, str]  # e.g. {"1": "A", "2": "B", ...}


@router.get("/summary")
async def get_all_sessions_summary() -> Dict[str, Any]:
    """Retrieve summary metrics across all processed answer sheets."""
    sessions = SessionStorage.list_all_sessions()
    total_processed = len(sessions)
    
    total_q = 0
    total_filled = 0
    total_blank = 0
    total_ambig = 0
    
    for s in sessions:
        summ = s.get("summary") or {}
        total_q += summ.get("total_questions", 0)
        total_filled += summ.get("filled_count", 0)
        total_blank += summ.get("blank_count", 0)
        total_ambig += summ.get("ambiguous_count", 0)
        
    avg_rejection = (total_ambig / total_q * 100) if total_q > 0 else 0.0
    
    return {
        "total_sessions": total_processed,
        "aggregate": {
            "total_questions_evaluated": total_q,
            "total_filled": total_filled,
            "total_blank": total_blank,
            "total_ambiguous": total_ambig,
            "average_rejection_rate_pct": round(avg_rejection, 2)
        },
        "sessions": sessions
    }


@router.get("/{image_id}")
async def get_session_result(image_id: str) -> Dict[str, Any]:
    """Retrieve full result object for an image session."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Results for '{image_id}' not found.")
    return res


@router.post("/{image_id}/score")
async def score_sheet_against_key(
    image_id: str,
    payload: ScoreRequest
) -> Dict[str, Any]:
    """Grade the answer sheet against an instructor answer key."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Results for '{image_id}' not found.")
        
    ans_key = {str(k): str(v).strip().upper() for k, v in payload.answer_key.items()}
    results = res.get("results", [])
    
    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0
    ambiguous_unreviewed = 0
    
    graded_details = []
    
    for item in results:
        q_str = str(item["question"])
        student_ans = item.get("answer")
        status_val = item.get("status")
        correct_ans = ans_key.get(q_str)
        
        is_correct = False
        if status_val == "AMBIGUOUS":
            ambiguous_unreviewed += 1
            verdict = "AMBIGUOUS_NEED_REVIEW"
        elif status_val == "BLANK" or not student_ans:
            unattempted_count += 1
            verdict = "BLANK"
        elif correct_ans and student_ans == correct_ans:
            correct_count += 1
            is_correct = True
            verdict = "CORRECT"
        else:
            incorrect_count += 1
            verdict = "INCORRECT"
            
        graded_details.append({
            "question": item["question"],
            "student_answer": student_ans,
            "correct_answer": correct_ans,
            "verdict": verdict,
            "is_correct": is_correct
        })
        
    score_pct = (correct_count / len(ans_key) * 100) if len(ans_key) > 0 else 0.0
    
    grading_summary = {
        "score_obtained": correct_count,
        "total_key_questions": len(ans_key),
        "score_percentage": round(score_pct, 2),
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unattempted_count": unattempted_count,
        "ambiguous_pending": ambiguous_unreviewed,
        "graded_questions": graded_details
    }
    
    return grading_summary


@router.get("/{image_id}/export/{format_type}")
async def export_sheet_results(image_id: str, format_type: str):
    """Download results as CSV or JSON file."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Results for '{image_id}' not found.")
        
    fmt = format_type.lower().strip()
    s_dir = SessionStorage.get_session_dir(image_id)
    
    if fmt == "csv":
        csv_path = s_dir / "export.csv"
        rows = []
        for dec in res.get("results", []):
            f_ratios = dec.get("fill_ratios", {})
            rows.append({
                "image_id": image_id,
                "question": dec["question"],
                "status": dec["status"],
                "answer": dec.get("answer") or "",
                "confidence": dec.get("confidence") or "",
                "delta_f": dec.get("delta_f") or 0.0,
                "fill_ratio_A": f_ratios.get("A", 0.0),
                "fill_ratio_B": f_ratios.get("B", 0.0),
                "fill_ratio_C": f_ratios.get("C", 0.0),
                "fill_ratio_D": f_ratios.get("D", 0.0),
                "fill_ratio_E": f_ratios.get("E", 0.0),
                "reason": dec.get("reason") or ""
            })
        df = pd.DataFrame(rows)
        df.to_csv(str(csv_path), index=False, encoding="utf-8")
        return FileResponse(str(csv_path), media_type="text/csv", filename=f"omr_result_{image_id}.csv")
        
    elif fmt == "json":
        json_path = s_dir / "result.json"
        return FileResponse(str(json_path), media_type="application/json", filename=f"omr_result_{image_id}.json")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{format_type}'. Use 'csv' or 'json'.")
