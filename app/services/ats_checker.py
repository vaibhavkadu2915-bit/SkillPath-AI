import re

from app.services.skill_extractor import SKILL_KEYWORDS, extract_skills


SECTION_NAMES = ("summary", "skills", "education", "projects", "experience", "certifications")
STOPWORDS = {
    "with", "from", "that", "this", "will", "your", "have", "been", "were", "their",
    "about", "into", "across", "using", "used", "work", "team", "role", "years",
    "ability", "strong", "including", "required", "preferred", "skills", "experience",
}


def _find_phrases(text: str, phrases: list[str]) -> tuple[list[str], list[str]]:
    lower = (text or "").lower()
    matched, missing = [], []
    for phrase in dict.fromkeys(phrases):
        pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
        (matched if re.search(pattern, lower) else missing).append(phrase)
    return matched, missing


def _job_keywords(description: str, custom: list[str] | None = None) -> list[str]:
    extracted = extract_skills(description)
    keywords = [item["skill"] for item in extracted["skills"]]
    # Keep a small set of repeated, meaningful words from a supplied job description.
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{3,}", description or "")
    lowered = {word.lower() for word in words}
    for word in words:
        low = word.lower()
        if low not in STOPWORDS and len(low) > 4 and sum(1 for value in words if value.lower() == low) > 1:
            keywords.append(word)
    if custom:
        keywords.extend(value.strip() for value in custom if value.strip())
    return list(dict.fromkeys(keywords))[:40]


def check_ats(resume_text: str, job_description: str = "", custom_keywords: list[str] | None = None) -> dict:
    text = (resume_text or "").strip()
    tips = []
    headings = [name for name in SECTION_NAMES if re.search(rf"(?im)^\s*{name}\s*$", text)]
    if not headings:
        tips.append("Add standard section headings such as Summary, Skills, Education, Projects, Experience, and Certifications.")
    if not re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.I):
        tips.append("Add a plain-text email address near the top of the resume.")
    if len(text.split()) < 120:
        tips.append("Add relevant detail to your experience, projects, and education sections.")
    if len(text.split()) > 900:
        tips.append("Trim the resume to the most relevant evidence and keywords.")
    if not re.search(r"(?m)^\s*[-•*]\s+", text):
        tips.append("Use simple bullet points for project and experience achievements.")
    if re.search(r"\b(?:responsible for|worked on|helped with)\b", text, flags=re.I):
        tips.append("Replace passive phrases with action verbs and measurable results where accurate.")

    if job_description.strip():
        expected = _job_keywords(job_description, custom_keywords)
        matched, missing = _find_phrases(text, expected)
        keyword_score = round(100 * len(matched) / max(len(expected), 1), 1)
        if missing:
            tips.append("Add relevant missing job-description keywords only when they accurately describe your experience.")
        score = round(0.75 * keyword_score + 0.25 * (100 * len(headings) / len(SECTION_NAMES)), 1)
        return {
            "score": score, "keyword_match_score": keyword_score,
            "matched_keywords": matched, "missing_keywords": missing,
            "detected_sections": [name.title() for name in headings], "suggestions": tips,
            "note": "This is a transparent prototype heuristic, not a score from a commercial ATS.",
        }

    score = 100.0
    if not headings:
        score -= 25
    else:
        score -= (len(SECTION_NAMES) - len(headings)) * 4
    if not re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.I):
        score -= 15
    if len(text.split()) < 120:
        score -= 15
    if not re.search(r"(?m)^\s*[-•*]\s+", text):
        score -= 5
    return {
        "score": max(0, round(score, 1)), "keyword_match_score": None,
        "matched_keywords": [], "missing_keywords": [],
        "detected_sections": [name.title() for name in headings], "suggestions": tips,
        "note": "This is a transparent prototype heuristic, not a score from a commercial ATS.",
    }
