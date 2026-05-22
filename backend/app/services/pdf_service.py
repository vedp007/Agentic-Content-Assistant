from pathlib import Path

from app.models.schemas import ExtractedContent


def _extract_scanned_pdf_with_ocr(path: Path) -> ExtractedContent:
    try:
        from pdf2image import convert_from_path
        import pytesseract  # noqa: F401

        from app.services.ocr_service import ocr_pil_image
    except ImportError:
        return ExtractedContent(
            source_type="pdf",
            confidence=0.0,
            warnings=[
                "No embedded PDF text found. Install pdf2image, pillow, pytesseract, Tesseract OCR, and Poppler for scanned PDF OCR."
            ],
            metadata={"filename": path.name, "ocr_fallback": "dependencies_missing"},
        )

    try:
        images = convert_from_path(str(path), dpi=200)
    except Exception as exc:
        return ExtractedContent(
            source_type="pdf",
            confidence=0.0,
            warnings=[f"No embedded PDF text found. Scanned PDF OCR could not run: {exc}"],
            metadata={"filename": path.name, "ocr_fallback": "failed"},
        )

    page_text: list[str] = []
    confidences: list[float] = []
    warnings: list[str] = []
    for index, image in enumerate(images, start=1):
        text, confidence, page_warnings, _ = ocr_pil_image(image, f"{path.name} page {index}")
        if text:
            page_text.append(f"[Page {index}]\n{text}")
        confidences.append(confidence)
        warnings.extend(f"Page {index}: {warning}" for warning in page_warnings)

    combined = "\n\n".join(page_text).strip()
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    if not combined and not warnings:
        warnings.append("No readable text was detected by scanned PDF OCR.")

    return ExtractedContent(
        source_type="pdf",
        text=combined,
        confidence=confidence,
        warnings=warnings,
        metadata={
            "filename": path.name,
            "pages": len(images),
            "ocr_fallback": "pdf2image+pytesseract",
        },
    )


def extract_pdf_text(path: Path) -> ExtractedContent:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractedContent(
            source_type="pdf",
            warnings=["pypdf is not installed. Install it to parse text PDFs."],
            metadata={"filename": path.name},
        )

    reader = PdfReader(str(path))
    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {index}]\n{text.strip()}")

    combined = "\n\n".join(pages).strip()
    confidence = 0.9 if combined else 0.15
    if not combined:
        return _extract_scanned_pdf_with_ocr(path)

    return ExtractedContent(
        source_type="pdf",
        text=combined,
        confidence=confidence,
        warnings=[],
        metadata={"filename": path.name, "pages": len(reader.pages)},
    )
