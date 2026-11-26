import os
import requests
import streamlit as st


API_URL = os.getenv("SKILLPATH_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="SkillPath AI", page_icon="🎓", layout="wide")


def api(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=30, **kwargs)
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            st.error(f"{detail}")
            return None
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response
    except requests.RequestException as error:
        st.error(f"Could not reach SkillPath API at {API_URL}: {error}")
        return None


def signed_in_user():
    value = st.session_state.get("user")
    if value:
        return value
    return {"name": "Guest", "email": ""}


st.title("SkillPath AI")
st.caption("Turn certificates into confirmed skills, an ATS-ready resume, and a practical career plan.")

with st.sidebar:
    st.subheader("Account")
    if st.session_state.get("access_token"):
        user = signed_in_user()
        st.write(f"Signed in as **{user.get('name', 'User')}**")
        if st.button("Log out"):
            for key in ("access_token", "user", "profile"):
                st.session_state.pop(key, None)
            st.rerun()
    else:
        mode = st.radio("Choose an option", ["Log in", "Create account"], horizontal=True)
        with st.form("account_form"):
            name = st.text_input("Name") if mode == "Create account" else None
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(mode)
        if submitted:
            body = {"email": email, "password": password}
            if mode == "Create account":
                body["name"] = name
            result = api("POST", "/auth/register" if mode == "Create account" else "/auth/login", json=body)
            if result:
                st.session_state.access_token = result["access_token"]
                st.session_state.user = result["user"]
                st.success("Account ready.")
                st.rerun()
        st.caption("You can also explore as a guest. Guest data stays on this computer and is not tied to an account.")

    if st.button("Continue as guest", disabled=bool(st.session_state.get("access_token"))):
        st.session_state.user = {"name": "Guest", "email": ""}
        st.rerun()
    st.divider()
    st.caption(f"API: {API_URL}")

tabs = st.tabs(["Certificates", "Skills", "Profile & Resume", "ATS Check", "Career Plan"])

with tabs[0]:
    st.header("Certificates")
    uploaded = st.file_uploader("Upload a certificate", type=["pdf", "jpg", "jpeg", "png"])
    if uploaded and st.button("Upload and extract skills", type="primary"):
        response = api("POST", "/certificates/upload", files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)})
        if response:
            result = api("POST", f"/skills/extract/{response['filename']}")
            if result:
                st.session_state.latest_detected_skills = result.get("skills", [])
                st.session_state.latest_certificate_id = result.get("certificate_id")
                st.success(f"Saved {uploaded.name}. Review detected skills in the Skills tab.")
                if result.get("metadata"):
                    st.json(result["metadata"])
                st.caption(f"Text extraction: {result.get('extraction_method', 'unknown')} · {result.get('character_count', 0)} characters")
    st.subheader("Upload history")
    history = api("GET", "/certificates/history")
    if history and history.get("certificates"):
        st.dataframe(history["certificates"], use_container_width=True, hide_index=True)
    elif history:
        st.info("Your certificates will appear here after upload.")

with tabs[1]:
    st.header("Review and confirm skills")
    response = api("GET", "/skills/extracted")
    existing = set(response.get("confirmed_skills", [])) if response else set()
    detected = []
    if response:
        for certificate in response.get("certificates", []):
            for item in certificate.get("skills", []):
                name = item.get("skill") if isinstance(item, dict) else str(item)
                if name and name not in detected:
                    detected.append(name)
    manual = st.text_input("Add a skill you want to confirm", placeholder="e.g. Python")
    if manual.strip():
        detected = sorted(set(detected + [manual.strip()]))
    if detected:
        with st.form("skill_confirmation"):
            selected = []
            for index, skill in enumerate(sorted(detected)):
                if st.checkbox(skill, value=skill in existing, key=f"skill_{index}_{skill}"):
                    selected.append(skill)
            confirm = st.form_submit_button("Save confirmed skills", type="primary")
        if confirm:
            result = api("POST", "/skills/confirm", json={"skills": selected, "certificate_id": st.session_state.get("latest_certificate_id")})
            if result:
                st.session_state.confirmed_skills = result.get("confirmed_skills", [])
                st.success(f"Saved {len(result.get('confirmed_skills', []))} confirmed skills.")
    else:
        st.info("Upload a certificate first, or add skills in the profile and resume form.")
    if existing:
        st.write("Current confirmed skills:", ", ".join(sorted(existing)))

with tabs[2]:
    st.header("Profile and ATS resume")
    saved_profile = api("GET", "/profile")
    profile = (saved_profile or {}).get("profile") or st.session_state.get("profile", {})
    with st.form("profile_form"):
        name = st.text_input("Full name", value=profile.get("name", signed_in_user().get("name", "")))
        email = st.text_input("Email", value=profile.get("email", signed_in_user().get("email", "")))
        phone = st.text_input("Phone", value=profile.get("phone", ""))
        education = st.text_area("Education", value=profile.get("education", ""), placeholder="Degree, institution, year")
        linkedin = st.text_input("LinkedIn", value=profile.get("linkedin", ""))
        github = st.text_input("GitHub", value=profile.get("github", ""))
        portfolio = st.text_input("Portfolio", value=profile.get("portfolio", ""))
        summary = st.text_area("Professional summary", placeholder="A concise, accurate 2–3 sentence summary")
        projects = st.text_area("Projects", placeholder="One project per line; include tools and outcomes")
        experience = st.text_area("Experience", placeholder="Internships, work, volunteering or leadership")
        certifications = st.text_area("Additional certifications", placeholder="Optional certificates not uploaded above")
        save_profile = st.form_submit_button("Save profile")
    profile_payload = {
        "name": name, "email": email, "phone": phone, "education": education,
        "linkedin": linkedin, "github": github, "portfolio": portfolio,
        "summary": summary, "projects": projects, "experience": experience,
        "certifications": certifications,
    }
    if save_profile:
        st.session_state.profile = profile_payload
        if st.session_state.get("access_token"):
            saved = api("PUT", "/profile", json={key: profile_payload[key] for key in ("name", "phone", "education", "linkedin", "github", "portfolio")})
            if saved:
                st.success("Profile saved.")
        else:
            st.info("Profile saved for this browser session. Create an account to save it permanently.")
    if st.button("Generate ATS-friendly DOCX and PDF", type="primary"):
        skills_data = api("GET", "/skills/extracted") or {}
        profile_payload["skills"] = skills_data.get("confirmed_skills", [])
        result = api("POST", "/resume/generate", json=profile_payload)
        if result:
            st.session_state.resume_text = result["resume_text"]
            st.session_state.resume_id = result["resume_id"]
            st.success(f"Resume generated. Prototype ATS structure score: {result['ats_score']} / 100")
            col1, col2 = st.columns(2)
            for col, file_format, label in ((col1, "docx", "Download DOCX"), (col2, "pdf", "Download PDF")):
                with col:
                    file_response = api("GET", f"/resume/{result['resume_id']}/download", params={"format": file_format})
                    if file_response:
                        st.download_button(label, file_response.content, file_name=f"skillpath-resume.{file_format}", mime=file_response.headers.get("content-type"), key=f"download_{file_format}")
            st.text_area("Resume text", result["resume_text"], height=300)

with tabs[3]:
    st.header("Resume keyword check")
    resume_text = st.text_area("Resume text", value=st.session_state.get("resume_text", ""), height=240)
    job_description = st.text_area("Job description (optional)", height=180)
    if st.button("Check ATS keywords"):
        result = api("POST", "/resume/check-ats", json={"resume_text": resume_text, "job_description": job_description})
        if result:
            st.metric("Prototype score", f"{result['score']} / 100")
            col1, col2 = st.columns(2)
            col1.write("**Matched keywords**")
            col1.write(", ".join(result["matched_keywords"]) or "None detected")
            col2.write("**Missing keywords**")
            col2.write(", ".join(result["missing_keywords"]) or "None detected")
            for tip in result["suggestions"]:
                st.write(f"• {tip}")
            st.caption(result["note"])

with tabs[4]:
    st.header("Job matches and skill roadmap")
    recommendations = api("GET", "/jobs/recommend")
    if recommendations:
        st.caption(recommendations["data_source"])
        rows = recommendations.get("recommendations", [])
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            selected_role = st.selectbox("Choose a role for your skill-gap plan", rows, format_func=lambda item: item["title"])
            if selected_role:
                gap = api("GET", "/skill-gap", params={"role_id": selected_role["role_id"]})
                if gap:
                    st.metric(f"Readiness for {gap['role']}", f"{gap['readiness_percentage']}%")
                    left, right = st.columns(2)
                    left.write("**Skills you have**")
                    left.write(", ".join(gap["have"]) or "Confirm skills to see matches")
                    right.write("**Must-have skills to learn**")
                    right.write(", ".join(gap["missing_must"]) or "All must-have skills are covered")
                    for item in gap["roadmap"]:
                        st.markdown(f"**{item['priority']}. {item['skill']}** · {item['importance']}")
                        for resource in item["resources"]:
                            st.markdown(f"[{resource['title']}]({resource['url']}) — {resource['provider']}, about {resource['duration']}")
                    if gap["roles_unlocked"]:
                        st.write("Roles you could unlock with a few more skills:", ", ".join(item["title"] for item in gap["roles_unlocked"]))
    st.caption("Recommendations use a small curated role dataset and confirmed skill overlap. They are not live job listings or hiring predictions.")
