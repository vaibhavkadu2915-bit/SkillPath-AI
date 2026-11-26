from app.services.skill_extractor import normalize_skill_name


ROLES = [
    {"id": "data_analyst", "title": "Data Analyst", "must": ["SQL", "Excel", "Data Visualization"], "good": ["Python", "Statistics", "Power BI", "Tableau", "Data Cleaning"]},
    {"id": "bi_analyst", "title": "Business Intelligence Analyst", "must": ["SQL", "Power BI", "Data Visualization"], "good": ["Excel", "Tableau", "Python", "Communication"]},
    {"id": "data_scientist", "title": "Junior Data Scientist", "must": ["Python", "Statistics", "Machine Learning"], "good": ["SQL", "Pandas", "Scikit-learn", "Data Visualization"]},
    {"id": "ml_engineer", "title": "Machine Learning Engineer", "must": ["Python", "Machine Learning", "Scikit-learn"], "good": ["SQL", "Deep Learning", "Git", "REST APIs"]},
    {"id": "python_developer", "title": "Python Developer", "must": ["Python", "Git", "REST APIs"], "good": ["FastAPI", "SQL", "Project Management"]},
    {"id": "backend_developer", "title": "Backend API Developer", "must": ["Python", "REST APIs", "SQL"], "good": ["FastAPI", "Git", "AWS"]},
    {"id": "ai_engineer", "title": "Applied AI Engineer", "must": ["Python", "Machine Learning", "Natural Language Processing"], "good": ["Deep Learning", "REST APIs", "AWS", "Git"]},
    {"id": "data_engineer", "title": "Junior Data Engineer", "must": ["Python", "SQL", "Data Cleaning"], "good": ["AWS", "Git", "Statistics"]},
    {"id": "business_analyst", "title": "Business Analyst", "must": ["Excel", "Communication", "Data Visualization"], "good": ["SQL", "Power BI", "Project Management", "Statistics"]},
    {"id": "product_analyst", "title": "Product Analyst", "must": ["SQL", "Statistics", "Data Visualization"], "good": ["Python", "Excel", "Communication"]},
    {"id": "cloud_support", "title": "Cloud Support Associate", "must": ["AWS", "Communication", "Python"], "good": ["Azure", "SQL", "Git"]},
    {"id": "frontend_developer", "title": "Frontend Developer", "must": ["JavaScript", "HTML and CSS", "Git"], "good": ["REST APIs", "Communication"]},
]

RESOURCES = {
    "Python": [("Python for Everybody", "https://www.freecodecamp.org/learn/scientific-computing-with-python/", "freeCodeCamp", "8 weeks")],
    "SQL": [("SQLBolt interactive lessons", "https://sqlbolt.com/", "SQLBolt", "2 weeks")],
    "Machine Learning": [("Machine Learning Specialization", "https://www.coursera.org/specializations/machine-learning-introduction", "DeepLearning.AI", "10 weeks")],
    "Statistics": [("Introductory Statistics", "https://www.khanacademy.org/math/statistics-probability", "Khan Academy", "4 weeks")],
    "Data Visualization": [("Data Visualization with Python", "https://www.freecodecamp.org/learn/data-visualization/", "freeCodeCamp", "3 weeks")],
    "Excel": [("Excel training", "https://support.microsoft.com/excel", "Microsoft Learn", "2 weeks")],
    "Power BI": [("Get started with Power BI", "https://learn.microsoft.com/training/powerplatform/power-bi/", "Microsoft Learn", "3 weeks")],
    "Tableau": [("Tableau free training", "https://www.tableau.com/learn/training", "Tableau", "3 weeks")],
    "Pandas": [("10 minutes to pandas", "https://pandas.pydata.org/docs/user_guide/10min.html", "pandas", "1 week")],
    "NumPy": [("NumPy quickstart", "https://numpy.org/doc/stable/user/quickstart.html", "NumPy", "1 week")],
    "Scikit-learn": [("scikit-learn tutorials", "https://scikit-learn.org/stable/tutorial/index.html", "scikit-learn", "3 weeks")],
    "Data Cleaning": [("Data cleaning overview", "https://pandas.pydata.org/docs/user_guide/missing_data.html", "pandas", "1 week")],
    "Git": [("Git book", "https://git-scm.com/book/en/v2", "Git", "1 week")],
    "FastAPI": [("FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/", "FastAPI", "2 weeks")],
    "REST APIs": [("APIs and HTTP", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview", "MDN", "1 week")],
    "JavaScript": [("JavaScript guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "MDN", "4 weeks")],
    "HTML and CSS": [("Responsive Web Design", "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "freeCodeCamp", "4 weeks")],
    "AWS": [("AWS Cloud Practitioner learning plan", "https://skillbuilder.aws/", "AWS Skill Builder", "4 weeks")],
    "Azure": [("Azure fundamentals", "https://learn.microsoft.com/training/azure/", "Microsoft Learn", "4 weeks")],
    "Natural Language Processing": [("NLP course", "https://huggingface.co/learn/nlp-course/", "Hugging Face", "4 weeks")],
    "Deep Learning": [("Neural Networks and Deep Learning", "https://www.coursera.org/learn/neural-networks-deep-learning", "DeepLearning.AI", "4 weeks")],
    "Communication": [("Improve communication skills", "https://www.coursera.org/learn/wharton-communication-skills", "Coursera", "2 weeks")],
    "Project Management": [("Project management basics", "https://www.pmi.org/learning/training-development", "PMI", "2 weeks")],
}


def normalized_set(skills):
    return {normalize_skill_name(skill) for skill in skills if str(skill).strip()}


def role_recommendations(skills, limit=8):
    owned = normalized_set(skills)
    results = []
    for role in ROLES:
        weights = {skill: 2 for skill in role["must"]}
        weights.update({skill: 1 for skill in role["good"]})
        total = sum(weights.values()) or 1
        matched = sorted(skill for skill in weights if skill in owned)
        score = round(100 * sum(weights[s] for s in matched) / total, 1)
        results.append({
            "role_id": role["id"], "title": role["title"], "match_percentage": score,
            "matching_skills": matched,
            "missing_must_have": sorted(set(role["must"]) - owned),
        })
    return sorted(results, key=lambda item: (-item["match_percentage"], item["title"]))[:limit]


def analyze_gap(skills, role_id):
    role = next((item for item in ROLES if item["id"] == role_id), None)
    if role is None:
        return None
    owned = normalized_set(skills)
    must, good = set(role["must"]), set(role["good"])
    missing_must = sorted(must - owned)
    missing_good = sorted(good - owned)
    roadmap = []
    for priority, skill in enumerate(missing_must + missing_good, start=1):
        resources = RESOURCES.get(skill, [])
        roadmap.append({
            "priority": priority, "skill": skill,
            "importance": "must-have" if skill in missing_must else "good-to-have",
            "resources": [
                {"title": title, "url": url, "provider": provider, "duration": duration}
                for title, url, provider, duration in resources
            ],
        })

    unlocks = []
    unlock_counts = {}
    for candidate in ROLES:
        candidate_missing = set(candidate["must"]) - owned
        if candidate["id"] != role_id and len(candidate_missing) <= 3:
            unlocks.append({"role_id": candidate["id"], "title": candidate["title"], "missing_skills": sorted(candidate_missing)})
            for skill in candidate_missing:
                unlock_counts[skill] = unlock_counts.get(skill, 0) + 1
    return {
        "role_id": role["id"], "role": role["title"],
        "have": sorted(owned & (must | good)),
        "missing_must": missing_must, "missing_good": missing_good,
        "readiness_percentage": round(100 * len(must & owned) / max(len(must), 1), 1),
        "roadmap": roadmap, "roles_unlocked": unlocks,
        "skills_that_unlock_roles": sorted(
            ({"skill": skill, "additional_roles": count} for skill, count in unlock_counts.items()),
            key=lambda item: (-item["additional_roles"], item["skill"]),
        ),
    }
