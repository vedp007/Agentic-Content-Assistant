from pathlib import Path
import os
import subprocess
import wave

from app.models.schemas import ExtractedContent

_WHISPER_MODEL = None


def _ensure_ffmpeg_path() -> None:
    candidates = list(
        Path.home()
        .joinpath("AppData/Local/Microsoft/WinGet/Packages")
        .glob("Gyan.FFmpeg_*/ffmpeg-*-full_build/bin")
    )
    for candidate in candidates:
        if candidate.joinpath("ffmpeg.exe").exists():
            os.environ["PATH"] = f"{candidate}{os.pathsep}{os.environ.get('PATH', '')}"
            return


def _clean_transcript(text: str) -> str:
    return " ".join((text or "").split())


def _wav_duration_seconds(path: Path) -> float | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            return round(frames / float(rate), 2) if rate else None
    except (wave.Error, OSError, EOFError):
        return None


def _load_whisper_model(whisper):
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
    return _WHISPER_MODEL


def transcribe_audio(path: Path) -> ExtractedContent:
    try:
        import whisper
    except ImportError:
        return ExtractedContent(
            source_type="audio",
            confidence=0.0,
            warnings=[
                "Whisper is not installed. Install openai-whisper and ffmpeg for audio transcription."
            ],
            metadata={"filename": path.name},
        )

    _ensure_ffmpeg_path()
    try:
        model = _load_whisper_model(whisper)
        result = model.transcribe(str(path))
    except FileNotFoundError:
        duration = _wav_duration_seconds(path)
        metadata = {"filename": path.name}
        if duration is not None:
            metadata["duration_seconds"] = duration
        return ExtractedContent(
            source_type="audio",
            confidence=0.0,
            warnings=["ffmpeg is not installed or is not available in PATH. Whisper requires ffmpeg for audio transcription."],
            metadata=metadata,
        )
    except subprocess.CalledProcessError as exc:
        return ExtractedContent(
            source_type="audio",
            confidence=0.0,
            warnings=[f"ffmpeg could not read this audio file: {exc}"],
            metadata={"filename": path.name},
        )
    except Exception as exc:
        return ExtractedContent(
            source_type="audio",
            confidence=0.0,
            warnings=[f"Audio transcription failed: {exc}"],
            metadata={"filename": path.name},
        )
    text = _clean_transcript(result.get("text") or "")
    segments = result.get("segments") or []
    duration = None
    if segments:
        duration = round(max(float(segment.get("end", 0) or 0) for segment in segments), 2)
    duration = duration or _wav_duration_seconds(path)

    metadata = {
        "filename": path.name,
        "language": result.get("language"),
        "segments": len(segments),
    }
    if duration is not None:
        metadata["duration_seconds"] = duration

    return ExtractedContent(
        source_type="audio",
        text=text,
        confidence=0.8 if text else 0.2,
        warnings=[] if text else ["Audio was processed but no transcript was produced."],
        metadata=metadata,
    )
