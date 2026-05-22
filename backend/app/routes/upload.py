from fastapi import APIRouter, File, UploadFile

from app.utils.file_utils import save_upload

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = await save_upload(file)
    return {
        "filename": file.filename,
        "path": str(file_path),
        "message": "File uploaded successfully",
    }
