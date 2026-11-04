"""FastAPI Web Application Entry Point: Robust Pencil OMR System
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routes.pages import router as pages_router
from app.routes.upload import router as upload_router
from app.routes.process import router as process_router
from app.routes.review import router as review_router
from app.routes.results import router as results_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "img").mkdir(parents=True, exist_ok=True)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Robust Pencil OMR System",
    description="Mobile-Captured Optical Mark Recognition with Tri-State Rejection & Human-in-the-Loop Review. Course: ICE415 Digital Image Processing (KMUTT).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 1. CORS Middleware (Supports mobile browsers and cross-origin tools)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 3. Mount API Routers
app.include_router(upload_router)
app.include_router(process_router)
app.include_router(review_router)
app.include_router(results_router)

# 4. Mount Page Router (HTML views)
app.include_router(pages_router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the browser tab icon (Favicon)."""
    ico_path = STATIC_DIR / "favicon.ico"
    if ico_path.exists():
        return FileResponse(ico_path, media_type="image/x-icon")
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/download-template", tags=["Templates"])
async def download_template_pdf():
    """Download the printable vector A4 Answer Sheet (PDF) for real pencil examination."""
    pdf_path = BASE_DIR / "templates" / "answer_sheet_a4.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Template PDF not found.")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename="KMUTT_ICE415_Robust_OMR_Answer_Sheet_A4.pdf"
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "system": "Robust Pencil OMR",
        "course": "KMUTT ICE415 Digital Image Processing"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
