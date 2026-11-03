"""Page Views Router: Serves HTML templates for the Web UI
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from app.storage import SessionStorage

router = APIRouter(tags=["Pages"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/")
async def dashboard_page(request: Request):
    """Render main Dashboard view."""
    sessions = SessionStorage.list_all_sessions()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"sessions": sessions[:10]}
    )


@router.get("/upload")
async def upload_page(request: Request):
    """Render File Upload & Camera Capture view."""
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={}
    )


@router.get("/processing/{image_id}")
async def processing_page(request: Request, image_id: str):
    """Render Processing Result & Step-by-Step Visualization view."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
    return templates.TemplateResponse(
        request=request,
        name="processing.html",
        context={"image_id": image_id, "data": res}
    )


@router.get("/review/{image_id}")
async def review_page(request: Request, image_id: str):
    """Render Human-in-the-Loop Verification Review view."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={"image_id": image_id, "data": res}
    )


@router.get("/results/{image_id}")
async def result_detail_page(request: Request, image_id: str):
    """Render detailed results and score report for a specific sheet."""
    res = SessionStorage.load_result(image_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Session '{image_id}' not found.")
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"image_id": image_id, "data": res}
    )


@router.get("/results")
async def results_overview_page(request: Request):
    """Render overall results table."""
    sessions = SessionStorage.list_all_sessions()
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"sessions": sessions, "data": None}
    )
