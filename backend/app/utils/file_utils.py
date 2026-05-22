from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def safe_upload_path(filename: str) -> Path:
    original = Path(filename or "upload.bin").name
    suffix = Path(original).suffix.lower()
    stem = Path(original).stem[:60] or "upload"
    return UPLOAD_DIR / f"{stem}-{uuid4().hex[:10]}{suffix}"


async def save_upload(file: UploadFile) -> Path:
    path = safe_upload_path(file.filename or "upload.bin")
    with path.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            handle.write(chunk)
    await file.seek(0)
    return path


def detect_source_type(path: Path | None, text: str = "") -> str:
    if text.strip().lower().startswith(("http://", "https://")) and "youtu" in text.lower():
        return "youtube"
    if path is None:
        return "text"
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}:
        return "image"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm"}:
        return "audio"
    return "unknown"
