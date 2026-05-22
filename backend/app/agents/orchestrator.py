from pathlib import Path
import re

from app.agents.executor import execute_intent
from app.agents.intent_agent import detect_intent
from app.agents.planner import build_plan
from app.models.schemas import AgentResponse, ExtractedContent
from app.services.audio_service import transcribe_audio
from app.services.cost_service import estimate_cost
from app.services.ocr_service import extract_image_text
from app.services.ollama_service import OLLAMA_MODEL
from app.services.pdf_service import extract_pdf_text
from app.services.youtube_service import fetch_youtube_transcript, find_youtube_url
from app.utils.file_utils import detect_source_type


TASK_WORDS = (
    "summarize",
    "summarise",
    "summary",
    "sentiment",
    "analyze",
    "analyse",
    "explain",
    "action item",
    "todo",
    "extract",
    "transcribe",
)


def _has_inline_task_content(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False

    if ":" in text:
        before, after = text.split(":", 1)
        if any(word in before.lower() for word in TASK_WORDS) and len(after.strip()) >= 8:
            return True

    question_match = re.search(r"\?\s*(.+)$", text)
    if question_match and len(question_match.group(1).strip()) >= 12:
        return True

    return False


def should_use_previous_context(message: str, context: str) -> bool:
    if not context.strip():
        return False
    text = (message or "").strip().lower()
    if not text:
        return True
    if _has_inline_task_content(message):
        return False
    if re.search(r"\b(this|that|uploaded|previous|attached)\s+(file|document|pdf|image|audio|text|upload|content)\b", text):
        return True
    if re.search(r"\b(this|that|it)\b", text) and any(word in text for word in TASK_WORDS):
        return True
    return any(word in text for word in TASK_WORDS)


def extract_input(
    message: str,
    file_path: Path | None = None,
    context: str = "",
) -> ExtractedContent:
    source_type = detect_source_type(file_path, message)
    if file_path is None:
        if find_youtube_url(message):
            return fetch_youtube_transcript(message)
        if should_use_previous_context(message, context):
            return ExtractedContent(
                source_type="text",
                text=context.strip(),
                metadata={"context_source": "previous_extraction"},
            )
        return ExtractedContent(source_type="text", text=message)
    if source_type == "pdf":
        return extract_pdf_text(file_path)
    if source_type == "image":
        return extract_image_text(file_path)
    if source_type == "audio":
        return transcribe_audio(file_path)
    return ExtractedContent(
        source_type="unknown",
        warnings=[f"Unsupported file type: {file_path.suffix or 'unknown'}"],
        metadata={"filename": file_path.name},
    )


def run_agent(
    message: str = "",
    file_path: Path | None = None,
    context: str = "",
) -> AgentResponse:
    logs: list[str] = ["Received request."]
    extracted = extract_input(message, file_path, context)
    logs.append(f"Input router selected `{extracted.source_type}`.")
    if extracted.metadata.get("context_source") == "previous_extraction":
        logs.append("Used previous extracted text as context for this turn.")
    logs.extend(extracted.warnings)

    intent = detect_intent(message, extracted)
    logs.append(f"Intent agent selected `{intent.intent}`.")
    cost_estimate = estimate_cost(message, extracted, intent)
    logs.append(
        "Cost estimator projected "
        f"{cost_estimate['total_tokens_estimate']} tokens and "
        f"${cost_estimate['estimated_cost_usd']:.2f} API cost."
    )
    plan = build_plan(intent, extracted, cost_estimate)
    response = execute_intent(message, extracted, intent)
    logs.append(f"LLM preference: Ollama `{OLLAMA_MODEL}` with heuristic fallback.")

    metadata = dict(extracted.metadata)
    if extracted.confidence is not None:
        metadata["extraction_confidence"] = extracted.confidence
    metadata["cost_estimate"] = cost_estimate

    return AgentResponse(
        response=response,
        extracted_text=extracted.text,
        intent=intent,
        plan=plan,
        logs=logs,
        metadata=metadata,
    )
