from app.models.schemas import ExtractedContent, IntentResult
from app.services.ollama_service import (
    llm_action_items,
    llm_answer,
    llm_code_explanation,
    llm_sentiment,
    llm_summarize,
)
from app.services.text_tools import (
    analyze_sentiment,
    answer_question,
    explain_code,
    extract_action_items,
    summarize,
    strip_task_instruction,
)
from app.services.youtube_service import fetch_youtube_transcript


ASSIGNMENT_SUMMARY_FORMAT = "all_formats"


def execute_intent(message: str, extracted: ExtractedContent, intent: IntentResult) -> str:
    content = extracted.text or message or ""

    if extracted.source_type in {"image", "pdf", "audio", "youtube"} and not extracted.text.strip() and extracted.warnings:
        return "\n".join(extracted.warnings)

    if intent.needs_clarification:
        prompt = (
            "The user's goal is ambiguous. Ask one short follow-up question. "
            f"User message: {message}\nExtracted content preview: {content[:800]}"
        )
        return llm_answer(prompt) or intent.follow_up_question or "Could you clarify what you want me to do?"
    if intent.intent == "youtube_transcript":
        transcript = fetch_youtube_transcript(message)
        if transcript.warnings:
            return "\n".join(transcript.warnings)
        summary_format = ASSIGNMENT_SUMMARY_FORMAT
        return llm_summarize(transcript.text, summary_format) or summarize(transcript.text, summary_format)
    if intent.intent in {"summarization", "audio_summary"}:
        if not strip_task_instruction(content):
            return "What file or text should I summarize?"
        summary_format = ASSIGNMENT_SUMMARY_FORMAT
        return llm_summarize(content, summary_format) or summarize(content, summary_format)
    if intent.intent == "sentiment_analysis":
        return llm_sentiment(content) or analyze_sentiment(content)
    if intent.intent == "code_explanation":
        return llm_code_explanation(content) or explain_code(content)
    if intent.intent == "action_items":
        return llm_action_items(content) or extract_action_items(content)
    if intent.intent == "text_extraction":
        confidence = "unknown" if extracted.confidence is None else f"{extracted.confidence:.2f}"
        return f"Extracted text:\n{content or '[No text extracted]'}\n\nOCR/parser confidence: {confidence}"
    return llm_answer(message, extracted.text) or answer_question(message, extracted.text)
