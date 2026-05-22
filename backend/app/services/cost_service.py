import os

from app.models.schemas import ExtractedContent, IntentResult


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text or "") / 4))


def estimate_cost(message: str, extracted: ExtractedContent, intent: IntentResult) -> dict:
    input_text = "\n".join(part for part in [message, extracted.text] if part)
    input_tokens = estimate_tokens(input_text)
    output_tokens = {
        "summarization": 350,
        "audio_summary": 350,
        "youtube_transcript": 350,
        "sentiment_analysis": 80,
        "code_explanation": 250,
        "action_items": 180,
        "text_extraction": estimate_tokens(extracted.text),
        "conversational_answering": 180,
        "clarification_required": 40,
    }.get(intent.intent, 180)

    total_tokens = input_tokens + output_tokens
    return {
        "provider": "ollama_local",
        "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        "input_tokens_estimate": input_tokens,
        "output_tokens_estimate": output_tokens,
        "total_tokens_estimate": total_tokens,
        "estimated_cost_usd": 0.0,
        "note": "Local Ollama execution has no per-token API charge. Token count is approximate.",
    }
