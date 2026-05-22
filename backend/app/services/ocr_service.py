from pathlib import Path

from app.models.schemas import ExtractedContent


WINDOWS_TESSERACT_PATH = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")


def _clean_ocr_text(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)


def ocr_pil_image(image, filename: str = "image") -> tuple[str, float, list[str], dict]:
    import pytesseract

    if WINDOWS_TESSERACT_PATH.exists():
        pytesseract.pytesseract.tesseract_cmd = str(WINDOWS_TESSERACT_PATH)

    try:
        raw_text = pytesseract.image_to_string(image)
    except pytesseract.pytesseract.TesseractNotFoundError:
        return (
            "",
            0.0,
            ["Tesseract OCR is not installed or is not available in PATH."],
            {"filename": filename, "size": image.size, "ocr_engine": "tesseract_missing"},
        )
    except Exception as exc:
        return (
            "",
            0.0,
            [f"OCR failed: {exc}"],
            {"filename": filename, "size": image.size, "ocr_engine": "tesseract_error"},
        )

    text = _clean_ocr_text(raw_text)
    confidence_values: list[float] = []

    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confidence_values = [
            float(value)
            for value in data.get("conf", [])
            if str(value).strip() not in {"", "-1"}
        ]
    except Exception:
        confidence_values = []

    if confidence_values:
        confidence = max(0.0, min(1.0, sum(confidence_values) / len(confidence_values) / 100))
    else:
        confidence = 0.75 if text else 0.2

    warnings = [] if text else ["No readable text was detected in the image."]
    metadata = {"filename": filename, "size": image.size}
    return text, confidence, warnings, metadata


def extract_image_text(path: Path) -> ExtractedContent:
    try:
        from PIL import Image
        import pytesseract  # noqa: F401
    except ImportError:
        return ExtractedContent(
            source_type="image",
            confidence=0.0,
            warnings=[
                "OCR dependencies are not installed. Install pillow, pytesseract, and Tesseract OCR."
            ],
            metadata={"filename": path.name},
        )

    image = Image.open(path)
    text, confidence, warnings, metadata = ocr_pil_image(image, path.name)
    return ExtractedContent(
        source_type="image",
        text=text,
        confidence=confidence,
        warnings=warnings,
        metadata=metadata,
    )
