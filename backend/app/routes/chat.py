from fastapi import APIRouter, Request

from app.agents.orchestrator import run_agent
from app.services.audio_service import transcribe_audio
from app.utils.file_utils import save_upload

router = APIRouter()


@router.post("/chat")
async def chat(request: Request):
    content_type = request.headers.get("content-type", "")
    message = ""
    context = ""
    saved_path = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        message = str(form.get("message") or "")
        context = str(form.get("context") or "")
        file = form.get("file")
        if getattr(file, "filename", None):
            saved_path = await save_upload(file)
    else:
        data = await request.json()
        message = str(data.get("message") or "")
        context = str(data.get("context") or "")

    result = run_agent(message=message, file_path=saved_path, context=context)
    return result.model_dump()


@router.post("/dictate")
async def dictate(request: Request):
    form = await request.form()
    file = form.get("file")
    if not getattr(file, "filename", None):
        return {
            "transcript": "",
            "warnings": ["No microphone audio chunk was received."],
            "metadata": {},
        }

    saved_path = await save_upload(file)
    result = transcribe_audio(saved_path)
    return {
        "transcript": result.text,
        "warnings": result.warnings,
        "metadata": result.metadata,
    }
