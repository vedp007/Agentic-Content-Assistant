import json
import os
import urllib.error
import urllib.request


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def call_ollama(prompt: str, system: str, timeout: int = 120) -> str | None:
    if os.getenv("DISABLE_OLLAMA", "").lower() in {"1", "true", "yes"}:
        return None

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    message = data.get("message") or {}
    content = message.get("content")
    return content.strip() if isinstance(content, str) and content.strip() else None


def llm_summarize(text: str, summary_format: str = "paragraph") -> str | None:
    system = (
        "You are a precise assistant for an interview assignment. "
        "Return text only. Do not mention that you are an AI. "
        "Do not copy the user's instruction words into the summary."
    )
    format_instructions = {
        "one_line": "Return one concise sentence only. Do not use a heading.",
        "bullets": "Return exactly 3 bullet points. Do not use a heading.",
        "five_sentences": "Return exactly 5 complete sentences in one paragraph. Do not use a heading.",
        "all_formats": (
            "Return exactly this structure:\n\n"
            "1-line summary:\n<one concise sentence>\n\n"
            "3 bullets:\n- <important point 1>\n- <important point 2>\n- <important point 3>\n\n"
            "5-sentence summary:\n<exactly five complete sentences>"
        ),
        "paragraph": "Return a natural paragraph summary in 3 to 5 sentences. Do not use headings or bullets.",
    }
    prompt = f"""
Summarize the content below.

Format:
{format_instructions.get(summary_format, format_instructions["paragraph"])}

Content:
{text}
""".strip()
    response = call_ollama(prompt, system)
    if not response:
        return None
    if summary_format == "all_formats":
        required = ("1-line summary:", "3 bullets:", "5-sentence summary:")
        return response if all(section in response for section in required) else None
    return response


def llm_sentiment(text: str) -> str | None:
    system = "You classify sentiment. Return text only and follow the requested format exactly."
    prompt = f"""
Analyze sentiment for this content.

Return exactly:
Label: positive|negative|neutral|mixed
Confidence: <0.00-1.00>
Justification: <one short sentence>

Content:
{text}
""".strip()
    return call_ollama(prompt, system)


def llm_code_explanation(code: str) -> str | None:
    system = "You are a senior code reviewer. Return text only. Be concise and practical."
    prompt = f"""
Explain this code. Include:
Detected language:
What it does:
Potential bugs:
Time complexity:

Code:
{code}
""".strip()
    return call_ollama(prompt, system)


def llm_action_items(text: str) -> str | None:
    system = (
        "You extract concrete action items from text. Return text only. "
        "Do not treat the user's question as an action item."
    )
    prompt = f"""
Extract only concrete action items from the content below.

Rules:
- Ignore questions such as "What are the action items?"
- Include owner and deadline when present.
- Treat commitments with "will", "should", "must", "need to", or "by <date>" as action items.
- If there are no action items, return exactly: No explicit action items were found.
- Otherwise return exactly this format:
Action items:
- <action item 1>
- <action item 2>

Content:
{text}
""".strip()
    response = call_ollama(prompt, system)
    if not response:
        return None
    if "Action items:" in response or "No explicit action items were found" in response:
        return response
    return None


def llm_answer(message: str, context: str = "") -> str | None:
    system = (
        "You are a helpful agentic application assistant. "
        "Use provided context when available. Return text only."
    )
    prompt = f"""
User request:
{message}

Context:
{context or "No extra context provided."}
""".strip()
    return call_ollama(prompt, system)
