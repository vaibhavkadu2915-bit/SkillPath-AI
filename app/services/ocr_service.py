
from pathlib import Path

import pymupdf as fitz
import pytesseract
from PIL import Image, ImageOps


# Change this path if Tesseract is installed elsewhere.
TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if TESSERACT_PATH.is_file():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)


def extract_image_text(image_path: str) -> str:
    """Extract printed text from a JPG or PNG certificate."""

    path = Path(image_path)

    if not path.is_file():
        raise FileNotFoundError("Certificate image not found.")

    with Image.open(path) as image:
        # Improve contrast and convert to grayscale.
        processed_image = ImageOps.grayscale(image)
        processed_image = ImageOps.autocontrast(processed_image)

        text = pytesseract.image_to_string(
            processed_image,
            lang="eng"
        )

    return text.strip()


def extract_scanned_pdf_text(pdf_path: str) -> dict:
    """Convert scanned PDF pages into images and read their text."""

    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError("Certificate PDF not found.")

    extracted_pages = []

    with fitz.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            # Render the page at a higher resolution for OCR.
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False
            )

            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples
            )

            processed_image = ImageOps.grayscale(image)
            processed_image = ImageOps.autocontrast(processed_image)

            page_text = pytesseract.image_to_string(
                processed_image,
                lang="eng"
            ).strip()

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
        "extraction_method": "ocr"
    }
