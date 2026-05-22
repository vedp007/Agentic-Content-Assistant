import re
from collections import Counter


POSITIVE = {"good", "great", "excellent", "love", "happy", "success", "useful", "clear"}
NEGATIVE = {"bad", "poor", "hate", "angry", "fail", "issue", "bug", "broken", "unclear"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "must",
    "of",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(text))
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def strip_task_instruction(text: str) -> str:
    cleaned = re.sub(
        r"^\s*(please\s+)?(can you\s+)?(summari[sz]e|brief|tl;dr)\s*(this|the following|it)?\s*"
        r"(in\s+)?(all\s+)?(\d+|one|three|five)?\s*[-\s]?"
        r"(formats?|bullets?|sentences?|lines?)?\s*:?\s*",
        "",
        text or "",
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^\s*(give|provide|create)\s+(me\s+)?(a\s+)?summary\s+(of\s+)?(this\s+)?(file|document|text)?\s*:?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def detect_summary_format(message: str) -> str:
    text = (message or "").lower()
    wants_all = any(
        phrase in text
        for phrase in (
            "all formats",
            "all 3 formats",
            "all 3",
            "all three",
            "1-line summary",
            "one-line summary",
        )
    )
    if wants_all:
        return "all_formats"
    if re.search(r"\b(1|one)[-\s]?line\b", text):
        return "one_line"
    if "bullet" in text:
        return "bullets"
    if re.search(r"\b(5|five)[-\s]?sentence", text):
        return "five_sentences"
    return "paragraph"


def keywords(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z'-]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 2]


def ranked_sentences(sentences: list[str]) -> list[str]:
    frequency = Counter(word for sentence in sentences for word in keywords(sentence))
    scored = []
    for index, sentence in enumerate(sentences):
        score = sum(frequency[word] for word in keywords(sentence))
        score += 2 if any(mark in sentence.lower() for mark in ("must", "goal", "output", "extract", "understand")) else 0
        scored.append((score, -index, sentence))
    return [sentence for _, _, sentence in sorted(scored, reverse=True)]


def make_bullet(sentence: str) -> str:
    sentence = re.sub(r"^(the\s+)?(system|application|app|agent)\s+", "", sentence, flags=re.IGNORECASE)
    sentence = sentence.strip().rstrip(".")
    if not sentence:
        return "Key point unavailable"
    return sentence[0].upper() + sentence[1:]


def summarize(text: str, summary_format: str = "paragraph") -> str:
    text = strip_task_instruction(text)
    sentences = split_sentences(text)
    if not sentences:
        return "No content was available to summarize."

    ranked = ranked_sentences(sentences)
    top_sentence = ranked[0]
    if len(sentences) == 1:
        one_line = top_sentence[:240]
    else:
        one_line = clean_text(top_sentence)[:240]

    bullets = []
    for sentence in ranked:
        bullet = make_bullet(sentence)
        if bullet not in bullets:
            bullets.append(bullet)
        if len(bullets) == 3:
            break
    while len(bullets) < 3:
        bullets.append("No additional key point was available in the source.")

    five = sentences[:5]
    while len(five) < 5:
        five.append("No additional distinct detail was available in the source.")

    bullet_text = "\n".join(f"- {item}" for item in bullets)
    five_text = " ".join(five)
    paragraph = " ".join(ranked[:3] if len(sentences) > 3 else sentences)

    if summary_format == "one_line":
        return one_line
    if summary_format == "bullets":
        return bullet_text
    if summary_format == "five_sentences":
        return five_text
    if summary_format == "all_formats":
        return (
            f"1-line summary:\n{one_line}\n\n"
            f"3 bullets:\n{bullet_text}\n\n"
            f"5-sentence summary:\n{five_text}"
        )
    return paragraph


def analyze_sentiment(text: str) -> str:
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return "Label: neutral\nConfidence: 0.50\nJustification: No meaningful text was provided."

    counts = Counter(tokens)
    positive = sum(counts[word] for word in POSITIVE)
    negative = sum(counts[word] for word in NEGATIVE)
    total = positive + negative
    if positive > negative:
        label = "positive"
    elif negative > positive:
        label = "negative"
    else:
        label = "neutral"
    confidence = 0.55 if total == 0 else min(0.95, 0.55 + abs(positive - negative) / max(total, 1) * 0.4)
    return (
        f"Label: {label}\n"
        f"Confidence: {confidence:.2f}\n"
        f"Justification: Found {positive} positive and {negative} negative signal words."
    )


def extract_action_items(text: str) -> str:
    cleaned = re.sub(r"(?i)\bwhat\s+are\s+the\s+action\s+items\??", "", text or "")
    cleaned = re.sub(r"(?i)\bextract\s+action\s+items\??", "", cleaned)
    lines = [line.strip(" -\t") for line in cleaned.splitlines() if line.strip()]
    keywords = ("action", "todo", "owner", "due", "deadline", "assigned", "next step", "follow up")
    matches = []
    for line in lines:
        candidates = split_sentences(line) or [line]
        matches.extend(
            candidate
            for candidate in candidates
            if any(keyword in candidate.lower() for keyword in keywords)
            and not candidate.strip().endswith("?")
        )

    if not matches:
        sentences = split_sentences(cleaned)
        matches = [
            sentence
            for sentence in sentences
            if any(word in sentence.lower() for word in ("must", "should", "need to", "will", "by "))
            and not sentence.strip().endswith("?")
        ][:6]

    if not matches:
        return "No explicit action items were found in the provided content."

    return "Action items:\n" + "\n".join(f"- {item}" for item in matches[:10])


def explain_code(code: str) -> str:
    lines = [line for line in code.splitlines() if line.strip()]
    language = "python" if any("def " in line or "import " in line for line in lines) else "unknown"
    bugs: list[str] = []
    if any("while True" in line for line in lines):
        bugs.append("Possible infinite loop: `while True` needs a clear break condition.")
    if any("/ 0" in line or "/0" in line for line in lines):
        bugs.append("Possible division by zero.")
    if language == "python" and any("except:" in line for line in lines):
        bugs.append("Bare except can hide real errors.")

    bug_text = "\n".join(f"- {bug}" for bug in bugs) if bugs else "- No obvious bugs detected by the heuristic reviewer."
    return (
        f"Detected language: {language}\n\n"
        "What it does:\n"
        f"The snippet has {len(lines)} non-empty lines. It appears to define or execute procedural logic based on the visible tokens.\n\n"
        "Potential bugs:\n"
        f"{bug_text}\n\n"
        "Time complexity:\n"
        "Likely O(n) if it loops over one collection; review nested loops for O(n^2) behavior."
    )


def answer_question(message: str, context: str = "") -> str:
    if context:
        compact = clean_text(context)
        return f"Based on the provided content: {compact[:900]}"
    return (
        "I can help with summaries, sentiment analysis, code explanation, extraction, "
        "audio transcription, or general questions. Share text or upload a file and tell me the goal."
    )
