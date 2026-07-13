# Job Hunting Assistant Web App

This is a deployable Python replacement for the n8n job hunting workflow.

You paste a job description into the web chat-style form. The app:

1. Sends the job description to DeepSeek.
2. Analyzes the role against Abdullah's resume profile.
3. Appends the result to Google Sheets.
4. Generates a tailored application email draft.

## Google Sheet Columns

Create a Google Sheet with a tab named `Sheet1`. The app can create/update the header row automatically.

Columns:

```text
Date Added
Company
Job Title
Location
Remote Type
Salary
Job URL
Required Skills
Match Score
Why Good Fit
Missing Skills
Status
Next Action
Contact Email
Cover Letter Angle
Notes
```

## Environment Variables

Set these in your deployment platform:

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
GOOGLE_SHEET_ID
GOOGLE_WORKSHEET_NAME=Sheet1
GOOGLE_SERVICE_ACCOUNT_JSON
```

`GOOGLE_SERVICE_ACCOUNT_JSON` must be the full service account JSON pasted as one environment variable.

Important: share your Google Sheet with the service account email, usually something like:

```text
name@project-id.iam.gserviceaccount.com
```

Give it Editor access.

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

PowerShell env var example:

```powershell
$env:DEEPSEEK_API_KEY="your_key"
$env:GOOGLE_SHEET_ID="your_sheet_id"
$env:GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account", "...":"..."}'
python app.py
```

Open:

```text
http://localhost:5000
```

## Deploy On Vercel

1. Push this folder to GitHub.
2. In Vercel, choose **Add New Project**.
3. Import the GitHub repository.
4. Framework preset can stay as **Other**.
5. Add the environment variables listed above.
6. Deploy.

This project includes:

```text
api/index.py
vercel.json
```

Those files route Vercel requests into the Flask app.

## Deploy On Render

1. Push this folder to GitHub.
2. Create a new Render Web Service.
3. Runtime: Python.
4. Build command:

```text
pip install -r requirements.txt
```

5. Start command:

```text
gunicorn app:app
```

6. Add the environment variables listed above.
7. Deploy.

The included `render.yaml` can also be used as a Render Blueprint.

## Notes

- This app does not store your DeepSeek key in code.
- This app does not store your Google service account in code.
- If Google Sheets fails, check that the sheet is shared with the service account email.
- If DeepSeek fails, check `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`.
