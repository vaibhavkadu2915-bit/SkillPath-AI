import os
from pathlib import Path


UPLOAD_DIR = Path(os.getenv("SKILLPATH_UPLOAD_DIR", "uploads/certificates"))
GENERATED_DIR = Path(os.getenv("SKILLPATH_GENERATED_DIR", "generated/resumes"))
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
