
from app.services.skill_extractor import extract_skills

sample_text = """
GenAl Powered Data Analytics Job Simulation
Exploratory data analysis and risk profiling
Predicting delinquency with Al
Business report and data storytelling for collections strategy
Implementing an Al-driven collections strategy
"""

result = extract_skills(sample_text)

print("Skills found:", result["skill_count"])

for item in result["skills"]:
    print("-", item["skill"])
    print("  Matched keywords:", ", ".join(item["matched_keywords"]))
