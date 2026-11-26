from pathlib import Path

from pytesseract import TesseractNotFoundError

from app.services.certificate_parser import parse_certificate_metadata
from app.services.ocr_service import extract_image_text, extract_scanned_pdf_text
from app.services.pdf_extractor import extract_pdf_text
from app.services.skill_extractor import extract_skills


def process_certificate(file_path: Path) -> dict:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        extracted = extract_pdf_text(str(file_path))
        if extracted["needs_ocr"]:
            extracted = extract_scanned_pdf_text(str(file_path))
    else:
        text = extract_image_text(str(file_path))
        extracted = {
            "filename": file_path.name, "total_pages": 1, "text": text,
            "character_count": len(text), "needs_ocr": len(text.strip()) < 30,
            "extraction_method": "ocr",
        }
    text = extracted["text"]
    skills = extract_skills(text)
    return {
        **extracted,
        "metadata": parse_certificate_metadata(text, file_path.name),
        "skills": skills["skills"], "skill_count": skills["skill_count"],
        "needs_ocr": len(text.strip()) < 30,
    }
