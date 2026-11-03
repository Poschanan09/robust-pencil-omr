"""API Route: File Upload Handlers
Course: ICE415 Digital Image Processing (KMUTT)
"""

from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.storage import SessionStorage, UPLOAD_DIR

router = APIRouter(prefix="/api/upload", tags=["Upload"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_single_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a single answer sheet image for OMR processing.
    
    Accepts JPG, PNG, BMP formats up to 20MB.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB."
        )
        
    image_id, _ = SessionStorage.create_session(file.filename or "upload.jpg")
    saved_path = SessionStorage.save_original(image_id, contents, file.filename or "upload.jpg")
    
    return {
        "image_id": image_id,
        "filename": file.filename,
        "size_bytes": len(contents),
        "status": "uploaded",
        "file_path": str(saved_path.relative_to(UPLOAD_DIR.parent))
    }


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def upload_batch_files(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """Upload multiple answer sheet images for batch evaluation."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
        
    uploaded_records = []
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext in ALLOWED_EXTENSIONS:
            contents = await f.read()
            if len(contents) <= MAX_FILE_SIZE:
                img_id, _ = SessionStorage.create_session(f.filename or "upload.jpg")
                SessionStorage.save_original(img_id, contents, f.filename or "upload.jpg")
                uploaded_records.append({
                    "image_id": img_id,
                    "filename": f.filename,
                    "size_bytes": len(contents)
                })
                
    return {
        "total_uploaded": len(uploaded_records),
        "sessions": uploaded_records
    }
