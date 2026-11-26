"""Black-box end-to-end smoke check; all persistent test data lives in a temp folder."""
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile

import pymupdf as fitz
import requests


def make_certificate() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Certificate of Completion\nData Analytics with Python\nIssued by Coursera\nCompleted on October 22, 2026\nCredential ID: AB12345\nPython SQL data analysis data visualization")
    result = document.tobytes()
    document.close()
    return result


def run() -> None:
    project_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="skillpath-e2e-") as temporary:
        temp = Path(temporary)
        uploads = temp / "uploads"
        generated = temp / "generated"
        uploads.mkdir()
        legacy_pdf = uploads / "legacy.pdf"
        legacy_pdf.write_bytes(make_certificate())
        (uploads / "owned-legacy.pdf").write_bytes(make_certificate())
        legacy_db = temp / "skillpath.db"
        with sqlite3.connect(legacy_db) as connection:
            connection.executescript("""
                CREATE TABLE users (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    email VARCHAR NOT NULL UNIQUE
                );
                CREATE TABLE certificates (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER,
                    file_path VARCHAR NOT NULL,
                    original_filename VARCHAR NOT NULL,
                    file_type VARCHAR NOT NULL,
                    status VARCHAR,
                    extracted_text TEXT,
                    extraction_method VARCHAR,
                    detected_skills TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                INSERT INTO users (id, name, email) VALUES (41, 'Existing User', 'existing@example.com');
            """)
            connection.execute(
                "INSERT INTO certificates (id,user_id,file_path,original_filename,file_type,status) VALUES (73,41,?,?,?,?)",
                (str((uploads / "owned-legacy.pdf").resolve()), "owned-legacy.pdf", ".pdf", "uploaded"),
            )
        connection.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(project_root),
            "SKILLPATH_UPLOAD_DIR": str(uploads),
            "SKILLPATH_GENERATED_DIR": str(generated),
            "SKILLPATH_SECRET_KEY": "end-to-end-test-only-secret",
        })
        log_path = temp / "server.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=temp, env=environment, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(80):
                    if process.poll() is not None:
                        raise AssertionError(f"API exited early. Server output: {log_path.read_text(encoding='utf-8')}")
                    try:
                        if requests.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                            break
                    except requests.RequestException:
                        time.sleep(0.25)
                else:
                    raise AssertionError(f"API did not become ready. Server output: {log_path.read_text(encoding='utf-8')}")

                registered = requests.post(f"{base_url}/auth/register", json={
                    "name": "Prototype User", "email": "prototype@example.com", "password": "local-test-password",
                }, timeout=10)
                assert registered.status_code == 200, registered.text
                token = registered.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                profile = requests.put(f"{base_url}/profile", headers=headers, json={
                    "phone": "555-0100", "education": "BSc Computer Science",
                    "linkedin": "https://example.com/in/profile",
                }, timeout=10)
                assert profile.status_code == 200, profile.text

                certificate = make_certificate()
                uploaded = requests.post(
                    f"{base_url}/certificates/upload", headers=headers,
                    files={"file": ("data-analytics.pdf", certificate, "application/pdf")}, timeout=10,
                )
                assert uploaded.status_code == 200, uploaded.text
                upload_data = uploaded.json()
                assert upload_data["certificate_id"] and upload_data["status"] == "uploaded"

                extracted = requests.post(
                    f"{base_url}/skills/extract/{upload_data['filename']}", headers=headers, timeout=20,
                )
                assert extracted.status_code == 200, extracted.text
                extracted_data = extracted.json()
                detected = {item["skill"] for item in extracted_data["skills"]}
                assert {"Python", "SQL", "Data Visualization"}.issubset(detected), detected
                assert extracted_data["metadata"]["issuer"] == "Coursera", extracted_data["metadata"]
                assert extracted_data["metadata"]["title"] == "Data Analytics with Python", extracted_data["metadata"]

                history = requests.get(f"{base_url}/certificates/history", headers=headers, timeout=10)
                assert history.status_code == 200, history.text
                assert history.json()["count"] == 2, history.json()
                assert {item["original_filename"] for item in history.json()["certificates"]} >= {"data-analytics.pdf", "legacy.pdf"}

                confirmed = requests.post(
                    f"{base_url}/skills/confirm", headers=headers,
                    json={"certificate_id": upload_data["certificate_id"], "skills": sorted(detected)}, timeout=10,
                )
                assert confirmed.status_code == 200, confirmed.text
                assert "Python" in confirmed.json()["confirmed_skills"]

                roles = requests.get(f"{base_url}/jobs/recommend", headers=headers, timeout=10)
                assert roles.status_code == 200 and roles.json()["recommendations"], roles.text
                gap = requests.get(f"{base_url}/skill-gap", headers=headers, params={"role_id": "data_analyst"}, timeout=10)
                assert gap.status_code == 200 and gap.json()["readiness_percentage"] > 0, gap.text
                assert gap.json()["roadmap"], gap.json()

                resume = requests.post(f"{base_url}/resume/generate", headers=headers, json={
                    "name": "Prototype User", "email": "prototype@example.com",
                    "education": "BSc Computer Science", "projects": "Built a data analytics portfolio project.",
                    "experience": "Completed a practical data analytics project.",
                }, timeout=10)
                assert resume.status_code == 200, resume.text
                resume_data = resume.json()
                assert "Python" in resume_data["resume_text"]
                assert "Data Analytics with Python" in resume_data["resume_text"]
                docx = requests.get(f"{base_url}{resume_data['docx_download']}", headers=headers, timeout=10)
                pdf = requests.get(f"{base_url}{resume_data['pdf_download']}", headers=headers, timeout=10)
                assert docx.status_code == pdf.status_code == 200
                with zipfile.ZipFile(__import__("io").BytesIO(docx.content)) as archive:
                    assert "word/document.xml" in archive.namelist()
                    assert "Python" in archive.read("word/document.xml").decode("utf-8")
                parsed_pdf = fitz.open(stream=pdf.content, filetype="pdf")
                assert "Prototype User" in parsed_pdf[0].get_text()
                parsed_pdf.close()

                ats = requests.post(f"{base_url}/resume/check-ats", json={
                    "resume_text": resume_data["resume_text"],
                    "job_description": "Python SQL data visualization and machine learning",
                }, timeout=10)
                assert ats.status_code == 200, ats.text
                assert {"Python", "SQL"}.issubset(set(ats.json()["matched_keywords"])), ats.json()
                with sqlite3.connect(legacy_db) as connection:
                    assert connection.execute("SELECT name,email FROM users WHERE id=41").fetchone() == ("Existing User", "existing@example.com")
                    assert connection.execute("SELECT count(*) FROM certificates WHERE id=73").fetchone()[0] == 1
                    user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
                    cert_columns = {row[1] for row in connection.execute("PRAGMA table_info(certificates)")}
                    assert {"password_hash", "phone", "education", "links"}.issubset(user_columns)
                    assert {"title", "issuer", "issue_date", "cert_type", "credential_id"}.issubset(cert_columns)
                connection.close()
                print("PASS: legacy schema migration/data preservation, account/profile, upload/history, extraction/confirmation, recommendations, skill gap, DOCX/PDF, and ATS check")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    run()
