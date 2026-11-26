# SkillPath AI

SkillPath AI is a local prototype that turns course certificates into a reviewed skill profile, a simple ATS-oriented resume, role matches, and a learning roadmap. The API is FastAPI, the interface is Streamlit, and the existing SQLite database remains the source of truth.

## Start the app on Windows

Open PowerShell in `C:\Users\HP\Desktop\Skill-Path`.

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SKILLPATH_SECRET_KEY = "replace-this-with-a-long-random-local-secret"
uvicorn app.main:app --reload
```

Keep that window open. Open a second PowerShell window in the same folder, activate the environment, and start the interface:

```powershell
.\venv\Scripts\Activate.ps1
$env:SKILLPATH_API_URL = "http://127.0.0.1:8000"
streamlit run frontend\streamlit_app.py
```

Open the Streamlit URL printed in the second window. The API documentation is at `http://127.0.0.1:8000/docs` and the health check is at `http://127.0.0.1:8000/health`.

On first startup, the app creates any missing tables and adds new nullable columns to the existing `users` and `certificates` tables. It does not drop, replace, or reset `skillpath.db`. Files already in `uploads\certificates` that do not yet have a database row are added to certificate history the first time history is opened.

## Prototype workflow

1. Create an account or continue as a guest.
2. Upload a PDF, JPG, or PNG certificate (up to 5 MB). Upload and history now share one database record.
3. Extract certificate text and review title, issuer, date, credential ID, and detected skills.
4. Confirm the skills that accurately represent your knowledge.
5. Save profile details, generate a single-column DOCX and text PDF, and download either format.
6. Paste a job description to see matched and missing keywords, then review curated role matches and the role-specific skill roadmap.

## Useful API routes

- `POST /auth/register`, `POST /auth/login`, `GET /profile`, `PUT /profile`
- `POST /certificates/upload`, `POST /certificates/upload-many`, `GET /certificates/history`
- `POST /certificates/extract/{filename}`, `POST /skills/extract/{filename}`
- `GET /skills/extracted`, `POST /skills/confirm`
- `POST /resume/generate`, `GET /resume/{id}/download?format=docx|pdf`, `POST /resume/check-ats`
- `GET /jobs/roles`, `GET /jobs/recommend`, `GET /skill-gap?role_id=data_analyst`

## Local requirements

Python 3.10 or later. Text-based PDFs do not need OCR. Scanned PDFs and images use Tesseract OCR through `pytesseract`; install Tesseract separately if it is not installed and on `PATH`. The existing Windows path `C:\Program Files\Tesseract-OCR\tesseract.exe` is used automatically when present.

## Limits to describe honestly

- Skill extraction is a curated keyword and alias matcher. It does not run spaCy, sentence embeddings, an LLM, or a 5,000-skill external taxonomy.
- Certificate fields are parsed with text and regular-expression heuristics. The app does not verify that a certificate is authentic.
- Recommendations come from a small curated list of roles, not live job listings. Scores are weighted skill overlap, not hiring probabilities.
- Learning links and durations are starter suggestions and have not been quality-ranked for every learner.
- The ATS checker looks for section headings, contact details, bullet structure, and job-description keywords. It is a heuristic and is not a score from a commercial ATS.
- The DOCX and text-based PDF are intentionally plain and single-column. Review all generated content for accuracy before applying.
- Authentication is for a local prototype. Passwords are PBKDF2-hashed and access tokens are signed, but the development secret fallback, local file storage, lack of email verification, and lack of account recovery are not production security.
- Guest data is shared in the local database's guest profile. Use an account when separate saved profiles are needed.

## Verification

Run the isolated end-to-end check with the project virtual environment:

```powershell
python tests\test_end_to_end.py
```

The check starts a temporary API process with a temporary SQLite database and temporary upload/output folders. It does not modify the main project database.
