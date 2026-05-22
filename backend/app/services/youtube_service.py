import re
from urllib.parse import parse_qs, urlparse

from app.models.schemas import ExtractedContent


YOUTUBE_RE = re.compile(
    r"(https?://(?:www\.)?(?:youtube\.com/(?:watch\?[^ ]*v=|shorts/|embed/)|youtu\.be/)[\w\-?=&%./]+)",
    re.IGNORECASE,
)


def find_youtube_url(text: str) -> str | None:
    match = YOUTUBE_RE.search(text or "")
    return match.group(1) if match else None


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/").split("/", 1)[0]
    if parsed.path == "/watch":
        return parse_qs(parsed.query).get("v", [""])[0]
    if parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
        return parsed.path.strip("/").split("/", 1)[1].split("/", 1)[0]
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def fetch_youtube_transcript(text: str) -> ExtractedContent:
    url = find_youtube_url(text)
    if not url:
        return ExtractedContent(source_type="youtube", warnings=["No YouTube URL found."])

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return ExtractedContent(
            source_type="youtube",
            confidence=0.0,
            warnings=[
                "youtube-transcript-api is not installed. Install it to fetch YouTube transcripts."
            ],
            metadata={"url": url},
        )

    video_id = extract_video_id(url)

    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            transcript = YouTubeTranscriptApi().fetch(video_id).to_raw_data()
    except Exception as exc:
        return ExtractedContent(
            source_type="youtube",
            confidence=0.0,
            warnings=[f"Transcript unavailable: {exc}"],
            metadata={"url": url, "video_id": video_id},
        )

    lines = [" ".join((item.get("text", "") or "").split()) for item in transcript]
    duration = 0.0
    for item in transcript:
        start = float(item.get("start", 0) or 0)
        item_duration = float(item.get("duration", 0) or 0)
        duration = max(duration, start + item_duration)

    return ExtractedContent(
        source_type="youtube",
        text=" ".join(lines).strip(),
        confidence=0.85,
        metadata={
            "url": url,
            "video_id": video_id,
            "segments": len(transcript),
            "duration_seconds": round(duration, 2) if duration else None,
        },
    )
