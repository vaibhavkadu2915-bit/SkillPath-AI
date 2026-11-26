
from pathlib import Path
import pymupdf


def extract_pdf_text(file_path: str) -> dict:
    """Extract selectable text from a PDF certificate."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError("Certificate file not found.")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Text extraction currently supports PDF files only.")

    extracted_pages = []

    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text("text").strip()

            extracted_pages.append({
                "page": page_number,
                "text": page_text
            })

    full_text = "\n\n".join(
        page["text"]
        for page in extracted_pages
        if page["text"]
    )

    return {
        "filename": path.name,
        "total_pages": len(extracted_pages),
        "text": full_text,
        "character_count": len(full_text),
        "needs_ocr": len(full_text.strip()) < 30,
        "extraction_method": "pdf_text"
    }
