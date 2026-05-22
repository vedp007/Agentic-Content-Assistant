import re

from app.models.schemas import ExtractedContent, IntentResult
from app.services.youtube_service import find_youtube_url


def extract_embedded_goal(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in lines[:12]:
        match = re.match(
            r"(?i)^(task|instruction|instructions|prompt|question|goal|user request)\s*:\s*(.+)$",
            line,
        )
        if match:
            return match.group(2).strip()

    first_text = " ".join(lines[:3])
    if re.match(r"(?i)^(what|why|how|summari[sz]e|analy[sz]e|extract|explain|find)\b", first_text):
        return first_text
    return ""


def looks_like_code(text: str) -> bool:
    code_markers = (
        "def ",
        "class ",
        "import ",
        "return ",
        "for ",
        "while ",
        "if ",
        "function ",
        "const ",
        "let ",
        "var ",
        "=>",
        "{",
        "}",
        ";",
    )
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return bool(lines) and any(marker in text for marker in code_markers)


def detect_intent(message: str, extracted: ExtractedContent) -> IntentResult:
    embedded_goal = "" if message.strip() else extract_embedded_goal(extracted.text)
    goal_text = (message or embedded_goal or "").strip()
    goal_lower = goal_text.lower()
    text = f"{goal_text}\n{extracted.text or ''}".lower()
    constraints = {}
    if "bullet" in text:
        constraints["format"] = "bullets"
    if re.search(r"\b\d+\s*(sentence|line|bullet)", text):
        constraints["length_hint"] = True
    if embedded_goal:
        constraints["goal_source"] = "embedded_in_input"

    if find_youtube_url(message or ""):
        return IntentResult(intent="youtube_transcript", confidence=0.92, constraints=constraints)
    if any(word in goal_lower for word in ["summarize", "summary", "summarise", "brief"]):
        return IntentResult(intent="summarization", confidence=0.9, constraints=constraints)
    if any(word in goal_lower for word in ["sentiment", "positive", "negative", "tone"]):
        return IntentResult(intent="sentiment_analysis", confidence=0.86, constraints=constraints)
    if any(word in goal_lower for word in ["explain code", "explain this code", "bug", "complexity", "rewrite this code"]):
        return IntentResult(intent="code_explanation", confidence=0.87, constraints=constraints)
    if goal_lower in {"explain", "explain this"} and looks_like_code(extracted.text):
        return IntentResult(intent="code_explanation", confidence=0.87, constraints=constraints)
    if any(word in goal_lower for word in ["action item", "todo", "next step", "follow up"]):
        return IntentResult(intent="action_items", confidence=0.84, constraints=constraints)

    if extracted.source_type in {"image", "pdf"} and not goal_text:
        if extracted.text.strip():
            return IntentResult(
                intent="clarification_required",
                confidence=0.45,
                needs_clarification=True,
                follow_up_question="What do you want me to do with this extracted text?",
                constraints=constraints,
            )
        return IntentResult(intent="text_extraction", confidence=0.75, constraints=constraints)
    if extracted.source_type == "audio" and not message.strip():
        return IntentResult(intent="audio_summary", confidence=0.78, constraints=constraints)
    if extracted.text and not goal_text:
        return IntentResult(
            intent="clarification_required",
            confidence=0.45,
            needs_clarification=True,
            follow_up_question="What do you want me to do with this extracted text?",
            constraints=constraints,
        )
    if extracted.text and extracted.source_type == "text" and not any(
        word in goal_lower for word in ["what", "why", "how", "summar", "sentiment", "explain", "find", "extract"]
    ):
        return IntentResult(
            intent="clarification_required",
            confidence=0.48,
            needs_clarification=True,
            follow_up_question="Could you clarify whether you want a summary, sentiment analysis, extraction, or Q&A?",
            constraints=constraints,
        )
    return IntentResult(intent="conversational_answering", confidence=0.7, constraints=constraints)
