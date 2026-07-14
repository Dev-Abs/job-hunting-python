import json
import os
import re
from datetime import datetime
from typing import Any, Dict

import requests
from flask import Flask, jsonify, render_template, request


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(APP_DIR, "profile.json")

SHEET_COLUMNS = [
    "Date Added",
    "Company",
    "Job Title",
    "Location",
    "Remote Type",
    "Salary",
    "Job URL",
    "Required Skills",
    "Match Score",
    "Why Good Fit",
    "Missing Skills",
    "Status",
    "Next Action",
    "Contact Email",
    "Cover Letter Angle",
    "Notes",
]

# app
app = Flask(__name__)


def load_profile() -> Dict[str, Any]:
    with open(PROFILE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    if value is None or str(value).strip() == "":
        return "Not specified"
    return str(value).strip()


def normalize_result(raw: Dict[str, Any], job_text: str) -> Dict[str, str]:
    result = {
        "Date Added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Company": raw.get("company", "Not specified"),
        "Job Title": raw.get("job_title", "Not specified"),
        "Location": raw.get("location", "Not specified"),
        "Remote Type": raw.get("remote_type", "Not specified"),
        "Salary": raw.get("salary", "Not specified"),
        "Job URL": raw.get("job_url", "Not specified"),
        "Required Skills": normalize_list(raw.get("required_skills", [])),
        "Match Score": str(raw.get("match_score", "Not specified")),
        "Why Good Fit": raw.get("why_good_fit", "Not specified"),
        "Missing Skills": normalize_list(raw.get("missing_skills", [])),
        "Status": raw.get("status", "Interested"),
        "Next Action": raw.get("next_action", "Not specified"),
        "Contact Email": raw.get("contact_email", "Not specified"),
        "Cover Letter Angle": raw.get("cover_letter_angle", "Not specified"),
        "Notes": raw.get("notes", "Generated from submitted job description."),
    }

    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", job_text)
    if result["Contact Email"] == "Not specified" and email_match:
        result["Contact Email"] = email_match.group(0)

    url_match = re.search(r"https?://[^\s)>\]]+", job_text)
    if result["Job URL"] == "Not specified" and url_match:
        result["Job URL"] = url_match.group(0).rstrip(".,")

    for key, value in result.items():
        if value is None or str(value).strip() == "":
            result[key] = "Not specified"
        else:
            result[key] = str(value).strip()

    return result


def analyze_with_deepseek(job_text: str) -> Dict[str, str]:
    profile = load_profile()
    api_key = env_required("DEEPSEEK_API_KEY")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")

    system_prompt = f"""
You are Abdullah's job hunting assistant.

Analyze job descriptions and return only valid JSON. Do not include markdown.

Abdullah profile:
{json.dumps(profile, ensure_ascii=False, indent=2)}

Return JSON with exactly these keys:
company, job_title, location, remote_type, salary, job_url, required_skills,
match_score, why_good_fit, missing_skills, status, next_action,
contact_email, cover_letter_angle, notes.

Rules:
- match_score must be a number from 0 to 100.
- status defaults to "Interested".
- required_skills and missing_skills must be arrays of short strings.
- If data is missing, use "Not specified".
- Do not invent experience Abdullah does not have.
- Score higher for AI automation, AI agents, n8n, Python, JavaScript, MERN,
  Flutter, healthcare tech, telecom tech, cloud, and digital transformation.
- Score lower for senior-only roles, unrelated sales-only roles, or roles with
  many missing requirements.
""".strip()

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": job_text},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=45,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return normalize_result(extract_json_object(content), job_text)


def append_to_sheet(result: Dict[str, str]) -> None:
    webhook_url = env_required("GOOGLE_SCRIPT_WEBHOOK_URL")
    response = requests.post(
        webhook_url,
        json={
            "columns": SHEET_COLUMNS,
            "row": result,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Google Apps Script returned an error."))


def make_email_draft(result: Dict[str, str]) -> Dict[str, str]:
    company = result["Company"] if result["Company"] != "Not specified" else "your company"
    title = result["Job Title"] if result["Job Title"] != "Not specified" else "the role"
    skills = result["Required Skills"] if result["Required Skills"] != "Not specified" else "software development, automation, and AI-focused problem solving"

    subject = f"Application for {title} - Abdullah"
    body = f"""
<p>Hi Hiring Team,</p>

<p>I hope you are doing well.</p>

<p>I am writing to express my interest in the <strong>{title}</strong> position at <strong>{company}</strong>. The role stood out to me because it aligns with my background in {skills}.</p>

<p>My experience includes software development, AI-driven workflow projects, MERN stack development, Flutter work, and integrating AI agents with tools such as Twilio and ElevenLabs. I am especially interested in roles where I can build practical solutions, automate workflows, and contribute to meaningful digital transformation.</p>

<p>I would appreciate the opportunity to discuss how my experience and projects could fit this role.</p>

<p>
Kind regards,<br>
Muhammad Abdullah Ubaidullah<br>
abdullah.devorbit@gmail.com<br>
linkedin.com/in/muhammadabdullahubaid/
</p>
""".strip()
    return {"subject": subject, "body": body}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    job_text = str(payload.get("job_text", "")).strip()
    if len(job_text) < 40:
        return jsonify({"ok": False, "error": "Please paste a fuller job description."}), 400

    try:
        result = analyze_with_deepseek(job_text)
        append_to_sheet(result)
        email_draft = make_email_draft(result)
        return jsonify({"ok": True, "analysis": result, "email_draft": email_draft})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
