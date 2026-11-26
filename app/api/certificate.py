from io import BytesIO
import json
from pathlib import Path
import uuid

import pymupdf as fitz
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pytesseract import TesseractNotFoundError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_optional_user
from app.core.settings import MAX_UPLOAD_BYTES, UPLOAD_DIR
from app.models.certificate import Certificate
from app.models.user import User
from app.services.certificate_processing import process_certificate

router = APIRouter(prefix="/certificates", tags=["Certificates"])
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def _same_path(left: str, right: Path) -> bool:
    try:
        return Path(left).resolve() == right.resolve()
    except (OSError, RuntimeError):
        return False


def _record_for_filename(db: Session, filename: str) -> Certificate | None:
    target = (UPLOAD_DIR / filename).resolve()
    for row in db.query(Certificate).all():
        if _same_path(row.file_path, target):
            return row
    return None


def _ensure_legacy_records(db: Session) -> None:
    """Index old uploaded files that predate database-backed upload history."""
    rows = db.query(Certificate).all()
    known = {Path(row.file_path).resolve() for row in rows}
    changed = False
    for path in UPLOAD_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        resolved = path.resolve()
        if resolved in known:
            continue
        db.add(Certificate(
            user_id=None, file_path=str(resolved), original_filename=path.name,
            file_type=path.suffix.lower(), status="uploaded",
        ))
        known.add(resolved)
        changed = True
    if changed:
        db.commit()


def _certificate_payload(item: Certificate) -> dict:
    try:
        skills = json.loads(item.detected_skills or "[]")
    except (ValueError, TypeError):
        skills = []
    return {
        "id": item.id, "filename": Path(item.file_path).name,
        "original_filename": item.original_filename, "file_type": item.file_type,
        "status": item.status or "uploaded", "title": item.title or "",
        "issuer": item.issuer or "", "issue_date": item.issue_date or "",
        "cert_type": item.cert_type or "other", "credential_id": item.credential_id or "",
        "extraction_method": item.extraction_method or "",
        "skills": skills,
    }


def _validate_content(filename: str, content: bytes) -> None:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        if b"%PDF-" not in content[:1024]:
            raise HTTPException(status_code=400, detail="The selected file is not a readable PDF.")
    else:
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(status_code=400, detail="The selected image could not be read.")


async def _save_upload(file: UploadFile, user: User | None) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please select a file.")
    original_filename = Path(file.filename.replace("\\", "/")).name
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, JPEG and PNG files are allowed.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Certificate files must be 5 MB or smaller.")
    _validate_content(original_filename, content)

    stored_name = f"{uuid.uuid4().hex}{extension}"
    file_path = (UPLOAD_DIR / stored_name).resolve()
    try:
        with file_path.open("xb") as destination:
            destination.write(content)
        db = SessionLocal()
        try:
            certificate = Certificate(
                user_id=user.id if user else None, file_path=str(file_path),
                original_filename=original_filename, file_type=extension, status="uploaded",
            )
            db.add(certificate)
            db.commit()
            db.refresh(certificate)
            return {
                "message": "Certificate uploaded and saved to history.",
                "certificate_id": certificate.id, "filename": stored_name,
                "original_filename": original_filename, "file_type": extension,
                "status": certificate.status,
            }
        finally:
            db.close()
    except Exception:
        file_path.unlink(missing_ok=True)
        raise


@router.post("/upload")
async def upload_certificate(
    file: UploadFile = File(...),
    user: User | None = Depends(get_optional_user),
):
    try:
        return await _save_upload(file, user)
    finally:
        await file.close()


@router.post("/upload-many")
async def upload_certificates(
    files: list[UploadFile] = File(...),
    user: User | None = Depends(get_optional_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one certificate.")
    results = []
    try:
        for file in files:
            results.append(await _save_upload(file, user))
    finally:
        for file in files:
            await file.close()
    return {"certificates": results}


@router.get("")
@router.get("/history")
def certificate_history(user: User | None = Depends(get_optional_user)):
    db = SessionLocal()
    try:
        _ensure_legacy_records(db)
        query = db.query(Certificate)
        if user is not None:
            query = query.filter((Certificate.user_id == user.id) | (Certificate.user_id.is_(None)))
        records = query.order_by(Certificate.id.desc()).all()
        return {"certificates": [_certificate_payload(item) for item in records], "count": len(records)}
    finally:
        db.close()


@router.post("/extract/{filename}")
def extract_certificate_text(
    filename: str,
    user: User | None = Depends(get_optional_user),
):
    if Path(filename).name != filename or Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Please provide a valid certificate filename.")
    file_path = (UPLOAD_DIR / filename).resolve()
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Certificate not found. Upload it first.")
    db = SessionLocal()
    try:
        certificate = _record_for_filename(db, filename)
        if certificate is None:
            certificate = Certificate(
                user_id=user.id if user else None, file_path=str(file_path),
                original_filename=filename, file_type=file_path.suffix.lower(), status="uploaded",
            )
            db.add(certificate)
            db.flush()
        elif user and certificate.user_id not in (None, user.id):
            raise HTTPException(status_code=404, detail="Certificate not found.")
        elif user and certificate.user_id is None:
            certificate.user_id = user.id
        result = process_certificate(file_path)
        metadata = result["metadata"]
        certificate.extracted_text = result["text"]
        certificate.extraction_method = result["extraction_method"]
        certificate.detected_skills = json.dumps(result["skills"], ensure_ascii=False)
        certificate.status = "processed"
        for key, value in metadata.items():
            setattr(certificate, key, value)
        db.commit()
        return {
            "message": "Certificate text extracted and saved to history.",
            "filename": filename, "certificate_id": certificate.id,
            **result,
        }
    except HTTPException:
        db.rollback()
        raise
    except TesseractNotFoundError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Tesseract OCR is not installed or is not on PATH.")
    except (fitz.FileDataError, RuntimeError, ValueError) as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not read the certificate: {error}")
    finally:
        db.close()
