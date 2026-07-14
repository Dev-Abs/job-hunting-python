import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
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

DEFAULT_DISCOVERY_QUERIES = [
    "ai automation",
    "ai agent",
    "python automation",
    "junior software engineer",
    "mern developer",
    "react node",
    "flutter developer",
    "machine learning intern",
    "digital transformation",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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


def parse_int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def result_score(result: Dict[str, str]) -> int:
    try:
        return int(float(result.get("Match Score", "0")))
    except ValueError:
        return 0


def normalize_score(value: int) -> int:
    return max(0, min(100, value))


def is_url_only(value: str) -> bool:
    return bool(re.fullmatch(r"https?://\S+", value.strip(), flags=re.IGNORECASE))


def fetch_job_page(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise RuntimeError("The URL did not return an HTML job page. Please paste the job description instead.")

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "iframe", "header", "footer", "nav"]):
        element.decompose()

    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()

    body_text = soup.get_text("\n", strip=True)
    body_text = re.sub(r"\n{3,}", "\n\n", body_text)
    extracted = f"Source URL: {url}\nPage title: {page_title}\nMeta description: {meta_description}\n\n{body_text}"

    if len(extracted) > 16000:
        extracted = extracted[:16000]

    if len(extracted.strip()) < 400:
        raise RuntimeError("I could not read enough job details from this URL. Please paste the job description.")

    return extracted


def prepare_job_input(user_input: str) -> Dict[str, str]:
    if is_url_only(user_input):
        try:
            return {
                "source_type": "url",
                "source_input": user_input,
                "analysis_text": fetch_job_page(user_input),
            }
        except requests.HTTPError as error:
            if "linkedin.com" in user_input.lower():
                raise RuntimeError(
                    "LinkedIn often blocks public scraping. Please paste the job description text, "
                    "or use a publicly readable job listing URL."
                ) from error
            raise RuntimeError("Could not fetch this job URL. Please paste the job description text.") from error
    return {
        "source_type": "text",
        "source_input": user_input,
        "analysis_text": user_input,
    }


def is_valid_analysis(raw: Dict[str, Any], result: Dict[str, str]) -> bool:
    if raw.get("is_valid_job_post") is False:
        return False
    has_title = result["Job Title"] != "Not specified"
    has_company = result["Company"] != "Not specified"
    has_skills = result["Required Skills"] != "Not specified"
    has_reason = result["Why Good Fit"] != "Not specified"
    return (has_title or has_company) and (has_skills or has_reason)


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
contact_email, cover_letter_angle, notes, is_valid_job_post, validation_reason.

Rules:
- Only analyze real job descriptions or real job listing pages.
- If the input is vague, unrelated, blocked, or does not contain enough job details,
  set is_valid_job_post to false and explain why in validation_reason.
- Do not invent company, role, skills, salary, or summary details.
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
    raw = extract_json_object(content)
    result = normalize_result(raw, job_text)
    if not is_valid_analysis(raw, result):
        reason = raw.get("validation_reason") or "This does not look like a complete job description."
        raise ValueError(str(reason))
    return result


def append_to_sheet(result: Dict[str, str]) -> Dict[str, Any]:
    webhook_url = env_required("GOOGLE_SCRIPT_WEBHOOK_URL")
    response = requests.post(
        webhook_url,
        json={
            "columns": SHEET_COLUMNS,
            "row": result,
            "dedupeColumn": "Job URL",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Google Apps Script returned an error."))
    return payload


def append_many_to_sheet(results: List[Dict[str, str]]) -> Dict[str, Any]:
    webhook_url = env_required("GOOGLE_SCRIPT_WEBHOOK_URL")
    response = requests.post(
        webhook_url,
        json={
            "columns": SHEET_COLUMNS,
            "rows": results,
            "dedupeColumn": "Job URL",
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Google Apps Script returned an error."))
    return payload


def summarize_text(value: str, limit: int = 1800) -> str:
    value = BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def candidate_from_remotive(job: Dict[str, Any]) -> Dict[str, str]:
    return {
        "source": "Remotive",
        "company": str(job.get("company_name") or "Not specified"),
        "title": str(job.get("title") or "Not specified"),
        "location": str(job.get("candidate_required_location") or "Remote"),
        "url": str(job.get("url") or "Not specified"),
        "salary": str(job.get("salary") or "Not specified"),
        "description": summarize_text(str(job.get("description") or "")),
        "tags": ", ".join(job.get("tags") or []),
    }


def candidate_from_remoteok(job: Dict[str, Any]) -> Dict[str, str]:
    tags = job.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return {
        "source": "RemoteOK",
        "company": str(job.get("company") or "Not specified"),
        "title": str(job.get("position") or job.get("title") or "Not specified"),
        "location": str(job.get("location") or "Remote"),
        "url": str(job.get("url") or job.get("apply_url") or "Not specified"),
        "salary": str(job.get("salary") or "Not specified"),
        "description": summarize_text(str(job.get("description") or "")),
        "tags": ", ".join(tags),
    }


def candidate_from_arbeitnow(job: Dict[str, Any]) -> Dict[str, str]:
    tags = job.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return {
        "source": "Arbeitnow",
        "company": str(job.get("company_name") or "Not specified"),
        "title": str(job.get("title") or "Not specified"),
        "location": str(job.get("location") or "Not specified"),
        "url": str(job.get("url") or "Not specified"),
        "salary": "Not specified",
        "description": summarize_text(str(job.get("description") or "")),
        "tags": ", ".join(tags),
    }


def fetch_remotive_jobs(queries: List[str]) -> List[Dict[str, str]]:
    jobs = []
    for query in queries:
        try:
            response = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": query},
                headers=REQUEST_HEADERS,
                timeout=25,
            )
            response.raise_for_status()
            jobs.extend(candidate_from_remotive(job) for job in response.json().get("jobs", []))
        except Exception:
            continue
    return jobs


def fetch_remoteok_jobs() -> List[Dict[str, str]]:
    try:
        response = requests.get("https://remoteok.com/api", headers=REQUEST_HEADERS, timeout=25)
        response.raise_for_status()
        payload = response.json()
        return [candidate_from_remoteok(job) for job in payload if isinstance(job, dict) and job.get("position")]
    except Exception:
        return []


def fetch_arbeitnow_jobs() -> List[Dict[str, str]]:
    try:
        response = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=REQUEST_HEADERS, timeout=25)
        response.raise_for_status()
        payload = response.json()
        return [candidate_from_arbeitnow(job) for job in payload.get("data", [])]
    except Exception:
        return []


def discovery_queries() -> List[str]:
    raw = os.environ.get("DISCOVERY_QUERIES", "")
    if not raw.strip():
        return DEFAULT_DISCOVERY_QUERIES
    return [query.strip() for query in raw.split(",") if query.strip()]


def candidate_fingerprint(candidate: Dict[str, str]) -> str:
    url = candidate.get("url", "").lower().strip()
    if url and url != "not specified":
        return url
    return f"{candidate.get('company', '').lower()}::{candidate.get('title', '').lower()}"


def candidate_text(candidate: Dict[str, str]) -> str:
    return "\n".join([
        f"Source: {candidate['source']}",
        f"Company: {candidate['company']}",
        f"Job Title: {candidate['title']}",
        f"Location: {candidate['location']}",
        f"Salary: {candidate['salary']}",
        f"Job URL: {candidate['url']}",
        f"Tags: {candidate['tags']}",
        f"Description: {candidate['description']}",
    ])


def is_interesting_candidate(candidate: Dict[str, str], profile: Dict[str, Any]) -> bool:
    combined = candidate_text(candidate).lower()
    preferred = " ".join(profile.get("skills", []) + profile.get("target_roles", [])).lower()
    keywords = set(re.findall(r"[a-z0-9+#.]{3,}", preferred))
    strong_keywords = {
        "ai", "automation", "python", "javascript", "react", "node", "mern",
        "flutter", "machine", "learning", "agent", "agents", "cloud", "api",
        "junior", "intern", "trainee", "remote", "digital", "transformation",
        "healthcare", "telecom", "twilio"
    }
    relocation_terms = {"relocation", "visa", "sponsorship", "worldwide", "global"}
    pakistan_terms = {"pakistan", "islamabad", "lahore", "karachi", "rawalpindi"}
    location_terms = relocation_terms | pakistan_terms | {"remote"}
    keyword_hit = any(keyword in combined for keyword in strong_keywords | set(list(keywords)[:80]))
    location_hit = any(term in combined for term in location_terms)
    return keyword_hit and location_hit


def discover_candidate_pool() -> List[Dict[str, str]]:
    profile = load_profile()
    candidates = fetch_remotive_jobs(discovery_queries()) + fetch_remoteok_jobs() + fetch_arbeitnow_jobs()
    unique: Dict[str, Dict[str, str]] = {}
    for candidate in candidates:
        key = candidate_fingerprint(candidate)
        if key and key not in unique and is_interesting_candidate(candidate, profile):
            unique[key] = candidate
    max_jobs = parse_int_env("DISCOVERY_MAX_CANDIDATES", 30)
    return list(unique.values())[:max_jobs]


def heuristic_result_from_candidate(candidate: Dict[str, str]) -> Dict[str, str]:
    profile = load_profile()
    text = candidate_text(candidate).lower()
    profile_keywords = profile.get("skills", []) + profile.get("target_roles", [])
    hits = []
    for keyword in profile_keywords:
        clean = str(keyword).strip()
        if clean and clean.lower() in text:
            hits.append(clean)

    strong_terms = [
        "ai", "automation", "python", "javascript", "react", "node", "mern",
        "flutter", "machine learning", "ai agent", "api", "cloud", "junior",
        "intern", "trainee", "remote", "worldwide", "relocation", "pakistan"
    ]
    term_hits = [term for term in strong_terms if term in text]
    all_hits = list(dict.fromkeys(hits + term_hits))

    senior_penalty_terms = ["senior", "staff", "principal", "lead ", "8+ years", "10+ years"]
    penalty = 18 if any(term in text for term in senior_penalty_terms) else 0
    score = normalize_score(45 + min(len(all_hits) * 5, 40) - penalty)

    location = candidate.get("location", "Not specified") or "Not specified"
    remote_type = "Remote" if "remote" in text or "worldwide" in text else "Onsite"
    if "hybrid" in text:
        remote_type = "Hybrid"

    return {
        "Date Added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Company": candidate.get("company", "Not specified") or "Not specified",
        "Job Title": candidate.get("title", "Not specified") or "Not specified",
        "Location": location,
        "Remote Type": remote_type,
        "Salary": candidate.get("salary", "Not specified") or "Not specified",
        "Job URL": candidate.get("url", "Not specified") or "Not specified",
        "Required Skills": ", ".join(all_hits[:12]) if all_hits else candidate.get("tags", "Not specified"),
        "Match Score": str(score),
        "Why Good Fit": "This role appears relevant based on public listing keywords and Abdullah's profile.",
        "Missing Skills": "Needs manual review",
        "Status": "Discovered",
        "Next Action": "Review the listing and apply if the role is suitable.",
        "Contact Email": "Not specified",
        "Cover Letter Angle": "Lead with software development, AI automation, and practical project experience.",
        "Notes": f"Auto-discovered from {candidate.get('source', 'public job source')} using fallback scoring.",
    }


def discover_best_jobs(save_matches: bool) -> Dict[str, Any]:
    min_score = parse_int_env("DISCOVERY_MIN_SCORE", 55)
    save_limit = parse_int_env("DISCOVERY_SAVE_LIMIT", 8)
    fallback_save_count = parse_int_env("DISCOVERY_FALLBACK_SAVE_COUNT", 5)
    dashboard_limit = parse_int_env("DISCOVERY_DASHBOARD_LIMIT", 30)
    candidates = discover_candidate_pool()
    analyzed = []
    errors = []
    deepseek_success = 0
    fallback_used = 0

    for candidate in candidates:
        try:
            result = analyze_with_deepseek(candidate_text(candidate))
            if result["Job URL"] == "Not specified":
                result["Job URL"] = candidate["url"]
            result["Status"] = "Discovered"
            result["Notes"] = f"Auto-discovered from {candidate['source']}."
            analyzed.append(result)
            deepseek_success += 1
        except Exception as error:
            fallback = heuristic_result_from_candidate(candidate)
            analyzed.append(fallback)
            fallback_used += 1
            errors.append({"candidate": candidate.get("title", "Unknown"), "error": str(error)})

    analyzed.sort(key=result_score, reverse=True)
    selected = [job for job in analyzed if result_score(job) >= min_score][:save_limit]
    if not selected and analyzed:
        selected = analyzed[:fallback_save_count]
        for job in selected:
            job["Status"] = "Needs Review"
            job["Notes"] = f"{job['Notes']} Saved by fallback because no jobs crossed the configured threshold."

    sheet_result = {"inserted": 0, "skipped": 0}
    if save_matches and selected:
        sheet_result = append_many_to_sheet(selected)

    return {
        "candidates_checked": len(candidates),
        "analyzed": len(analyzed),
        "deepseek_success": deepseek_success,
        "fallback_used": fallback_used,
        "threshold": min_score,
        "selected": len(selected),
        "saved": sheet_result.get("inserted", 0),
        "skipped": sheet_result.get("skipped", 0),
        "auto_saved": save_matches,
        "sheet": sheet_result,
        "jobs": (selected if save_matches else analyzed[:dashboard_limit]),
        "errors": errors[:5],
    }


def make_email_draft(result: Dict[str, str]) -> Dict[str, str]:
    company = result["Company"]
    title = result["Job Title"]
    skills = result["Required Skills"] if result["Required Skills"] != "Not specified" else "software development, automation, and AI-focused problem solving"

    subject = f"Application for {title} - Abdullah"
    plain_body = f"""Hi Hiring Team,

I hope you are doing well.

I am writing to express my interest in the {title} position at {company}. The role stood out to me because it aligns with my background in {skills}.

My experience includes software development, AI-driven workflow projects, MERN stack development, Flutter work, and integrating AI agents with tools such as Twilio and ElevenLabs. I am especially interested in roles where I can build practical solutions, automate workflows, and contribute to meaningful digital transformation.

I would appreciate the opportunity to discuss how my experience and projects could fit this role.

Kind regards,
Muhammad Abdullah Ubaidullah
abdullah.devorbit@gmail.com
linkedin.com/in/muhammadabdullahubaid/
""".strip()

    html_body = f"""
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
    return {"subject": subject, "body": html_body, "plain_body": plain_body}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    user_input = str(payload.get("job_text", "")).strip()
    if len(user_input) < 12:
        return jsonify({"ok": False, "error": "Paste a job description or a job listing URL."}), 400

    try:
        prepared_input = prepare_job_input(user_input)
        result = analyze_with_deepseek(prepared_input["analysis_text"])
        if result["Job URL"] == "Not specified" and prepared_input["source_type"] == "url":
            result["Job URL"] = prepared_input["source_input"]
        sheet_result = append_to_sheet(result)
        email_draft = make_email_draft(result)
        return jsonify({
            "ok": True,
            "analysis": result,
            "email_draft": email_draft,
            "source_type": prepared_input["source_type"],
            "saved": sheet_result.get("inserted", 1) > 0,
            "skipped": sheet_result.get("skipped", 0),
        })
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error), "saved": False}), 422
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 500


@app.route("/api/discover", methods=["GET", "POST"])
def discover():
    try:
        result = discover_best_jobs(save_matches=request.method == "GET")
        return jsonify({"ok": True, **result})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 500


@app.post("/api/save-job")
def save_job():
    payload = request.get_json(silent=True) or {}
    job = payload.get("job") or {}
    if not isinstance(job, dict):
        return jsonify({"ok": False, "error": "Invalid job payload."}), 400

    cleaned_job = {}
    for column in SHEET_COLUMNS:
        value = job.get(column, "Not specified")
        cleaned_job[column] = str(value).strip() if value is not None and str(value).strip() else "Not specified"

    if cleaned_job["Job Title"] == "Not specified" and cleaned_job["Company"] == "Not specified":
        return jsonify({"ok": False, "error": "Cannot save a job without title or company."}), 400

    try:
        sheet_result = append_to_sheet(cleaned_job)
        return jsonify({
            "ok": True,
            "saved": sheet_result.get("inserted", 1) > 0,
            "skipped": sheet_result.get("skipped", 0),
            "message": "Saved to Google Sheets." if not sheet_result.get("skipped") else "Already existed in Google Sheets.",
        })
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
