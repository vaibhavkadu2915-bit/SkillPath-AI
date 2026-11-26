
import re


SKILL_KEYWORDS = {
    "Python": ["python", "python programming"],
    "SQL": ["sql", "structured query language"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "neural networks"],
    "Statistics": ["statistics", "statistical analysis"],
    "Data Visualization": ["data visualization", "data visualisation", "data viz"],
    "Excel": ["microsoft excel", "excel spreadsheets", "excel"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy", "numerical python"],
    "Scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "Data Cleaning": ["data cleaning", "data cleansing", "data preprocessing"],
    "Git": ["git", "version control"],
    "FastAPI": ["fastapi", "fast api"],
    "REST APIs": ["rest api", "rest apis", "api development"],
    "JavaScript": ["javascript", "ecmascript"],
    "HTML and CSS": ["html", "css", "html and css"],
    "Communication": ["communication skills", "written communication"],
    "Project Management": ["project management", "project planning"],
    "AWS": ["amazon web services", "aws"],
    "Azure": ["microsoft azure", "azure"],
    "Natural Language Processing": ["natural language processing", "nlp"],
    "Exploratory Data Analysis": [
        "exploratory data analysis",
        "eda",
        "data exploration"
    ],
    "Data Analytics": [
        "data analytics",
        "data analysis",
        "data analyst"
    ],
    "Risk Profiling": [
        "risk profiling",
        "risk analysis"
    ],
    "Generative AI": [
        "generative ai",
        "genai",
        "gen ai"
    ],
    "Artificial Intelligence": [
        "artificial intelligence",
        "ai-driven",
        "ai driven",
        "ai-powered",
        "ai powered"
    ],
    "Predictive Modeling": [
        "predictive modeling",
        "predictive modelling",
        "predicting",
        "prediction"
    ],
    "Data Storytelling": [
        "data storytelling",
        "storytelling with data"
    ],
    "Business Reporting": [
        "business report",
        "business reporting"
    ],
    "Collections Strategy": [
        "collections strategy",
        "collections management"
    ],
    "Strategy Development": [
        "strategic planning",
        "strategy development"
    ]
}


def extract_skills(text: str) -> dict:
    """Identify skills using explicit keyword matching."""

    if not text or not text.strip():
        return {
            "skills": [],
            "skill_count": 0,
            "message": "No text provided for skill extraction."
        }

    normalized_text = re.sub(r"\s+", " ", text.lower())
    found_skills = []

    for skill_name, keywords in SKILL_KEYWORDS.items():
        matched_keywords = []

        for keyword in keywords:
            pattern = (
                r"(?<!\w)"
                + re.escape(keyword)
                + r"(?!\w)"
            )

            if re.search(pattern, normalized_text):
                matched_keywords.append(keyword)

        if matched_keywords:
            found_skills.append({
                "skill": skill_name,
                "matched_keywords": matched_keywords,
                "confidence": 0.95,
                "source": "rule",
            })

    return {
        "skills": found_skills,
        "skill_count": len(found_skills),
        "message": "Skill extraction completed using keyword matching."
    }


def normalize_skill_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", (value or "").strip().lower())
    for canonical, aliases in SKILL_KEYWORDS.items():
        candidates = [canonical.lower(), *[alias.lower() for alias in aliases]]
        if normalized in candidates:
            return canonical
    return re.sub(r"\s+", " ", (value or "").strip())[:80]
