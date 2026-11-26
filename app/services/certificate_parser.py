import re


ISSUERS = [
    "Coursera", "Udemy", "NPTEL", "Google", "Microsoft", "IBM",
    "Amazon Web Services", "AWS", "Great Learning", "Infosys", "LinkedIn Learning",
    "freeCodeCamp", "Cisco", "Oracle", "Meta", "Simplilearn", "edX",
]


def parse_certificate_metadata(text: str, filename: str = "") -> dict:
    clean = re.sub(r"[ \t]+", " ", text or "").strip()
    lines = [re.sub(r"\s+", " ", line).strip(" :-") for line in clean.splitlines()]
    lines = [line for line in lines if line]

    title = ""
    title_markers = (
        "certificate of completion", "certificate of achievement",
        "successfully completed", "has completed", "course completion",
    )
    for index, line in enumerate(lines):
        lower = line.lower()
        if any(marker in lower for marker in title_markers):
            if index + 1 < len(lines) and len(lines[index + 1]) > 2:
                title = lines[index + 1]
                break
            title = line
            break
    if not title:
        title = next((line for line in lines if 4 <= len(line) <= 100), "")
    if not title:
        title = re.sub(r"[_-]+", " ", filename.rsplit(".", 1)[0]).strip()

    issuer = ""
    issuer_match = re.search(
        r"(?:issued|offered|provided|presented|authorized)\s+by\s+([A-Z][\w &.,'-]{1,60})",
        clean,
        flags=re.IGNORECASE,
    )
    if issuer_match:
        issuer = issuer_match.group(1).strip(" .,:;")[:80]
    else:
        lower = clean.lower()
        issuer = next((name for name in ISSUERS if name.lower() in lower), "")

    date_pattern = re.compile(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2}\b|"
        r"\b\d{1,2}[/-]\d{1,2}[/-]20\d{2}\b|\b20\d{2}-\d{2}-\d{2}\b",
        flags=re.IGNORECASE,
    )
    date_match = date_pattern.search(clean)
    issue_date = date_match.group(0) if date_match else ""

    credential_match = re.search(
        r"(?:credential\s*(?:id|code)|certificate\s*(?:id|no\.?|number)|"
        r"verification\s*id)\s*[:#]?\s*([A-Z0-9-]{4,40})",
        clean,
        flags=re.IGNORECASE,
    )
    credential_id = credential_match.group(1) if credential_match else ""

    lower = clean.lower()
    if any(word in lower for word in ("internship", "intern")):
        cert_type = "internship"
    elif any(word in lower for word in ("hackathon", "competition")):
        cert_type = "hackathon"
    elif any(word in lower for word in ("workshop", "bootcamp")):
        cert_type = "workshop"
    elif any(word in lower for word in ("course", "specialization", "training")):
        cert_type = "course"
    else:
        cert_type = "other"

    return {
        "title": title[:120], "issuer": issuer, "issue_date": issue_date,
        "cert_type": cert_type, "credential_id": credential_id,
    }
