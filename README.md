# Job Hunting Assistant Web App

This is a deployable Python replacement for the n8n job hunting workflow.

You paste a job description or a public job listing URL into the web chat-style form. The app:

1. Reads the pasted job description, or fetches a public job listing URL.
2. Sends the real job content to DeepSeek.
3. Analyzes the role against Abdullah's resume profile.
4. Appends the result to Google Sheets through a free Google Apps Script webhook.
5. Generates a tailored application email draft.
6. Lets you copy the draft or open a Gmail compose window.
7. Can discover ranked jobs from public sources.
8. Manual discovery shows a dashboard with Save buttons.
9. Scheduled discovery auto-saves the best matches.

The app validates input before saving. If the text or URL does not contain enough real job detail, it will not save a row or generate a draft.

URL note: LinkedIn and some job boards block automated public reads. If a URL cannot be read, paste the job description text instead.

Auto-discovery looks for remote/worldwide jobs, relocation-friendly roles where visible, and Pakistan onsite roles when available from public sources.

Manual behavior:

```text
Find Matching Jobs Now
→ returns a dashboard of ranked jobs
→ you choose which jobs to save
```

Scheduled behavior:

```text
Vercel Cron
→ ranks jobs automatically
→ saves the best matches automatically
```

## Google Sheet Columns

Create a Google Sheet with a tab named `Sheet1`. The Apps Script below can create/update the header row automatically.

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
GOOGLE_SCRIPT_WEBHOOK_URL
```

Optional auto-discovery settings:

```text
DISCOVERY_MIN_SCORE=55
DISCOVERY_SAVE_LIMIT=8
DISCOVERY_FALLBACK_SAVE_COUNT=5
DISCOVERY_MAX_CANDIDATES=30
DISCOVERY_QUERIES=ai automation,ai agent,python automation,junior software engineer,mern developer,react node,flutter developer,machine learning intern,digital transformation
```

## Google Apps Script Setup

This avoids Google Cloud service accounts and billing setup.

1. Open your Google Sheet.
2. Go to **Extensions > Apps Script**.
3. Paste this code:

```javascript
const SHEET_NAME = "Sheet1";

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    const columns = payload.columns || [];
    const rows = payload.rows || (payload.row ? [payload.row] : []);
    const dedupeColumn = payload.dedupeColumn || "Job URL";

    const existingHeader = sheet.getRange(1, 1, 1, columns.length).getValues()[0];
    const headerMissing = existingHeader.join("") === "" || existingHeader.join("|") !== columns.join("|");

    if (headerMissing) {
      sheet.getRange(1, 1, 1, columns.length).setValues([columns]);
      sheet.setFrozenRows(1);
    }

    const dedupeIndex = columns.indexOf(dedupeColumn);
    const existingValues = new Set();

    if (dedupeIndex >= 0 && sheet.getLastRow() > 1) {
      const values = sheet
        .getRange(2, dedupeIndex + 1, sheet.getLastRow() - 1, 1)
        .getValues()
        .flat()
        .filter(Boolean)
        .map(String);

      values.forEach((value) => existingValues.add(value));
    }

    const valuesToAppend = [];
    let skipped = 0;

    rows.forEach((rowObject) => {
      const dedupeValue = dedupeIndex >= 0 ? String(rowObject[dedupeColumn] || "") : "";
      if (dedupeValue && existingValues.has(dedupeValue)) {
        skipped += 1;
        return;
      }

      if (dedupeValue) {
        existingValues.add(dedupeValue);
      }

      valuesToAppend.push(columns.map((column) => rowObject[column] || "Not specified"));
    });

    if (valuesToAppend.length) {
      sheet
        .getRange(sheet.getLastRow() + 1, 1, valuesToAppend.length, columns.length)
        .setValues(valuesToAppend);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, inserted: valuesToAppend.length, skipped }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(error) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

4. Click **Deploy > New deployment**.
5. Select type: **Web app**.
6. Set **Execute as**: `Me`.
7. Set **Who has access**: `Anyone`.
8. Click **Deploy**.
9. Copy the Web app URL. This is your `GOOGLE_SCRIPT_WEBHOOK_URL`.

Important: if you already deployed the old script, replace it with this updated script and deploy a **new version**:

```text
Deploy > Manage deployments > Edit > Version > New version > Deploy
```

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
$env:GOOGLE_SCRIPT_WEBHOOK_URL="your_apps_script_web_app_url"
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

Daily auto-discovery is configured in `vercel.json`:

```text
0 4 * * *
```

That means Vercel calls `/api/discover` daily at 04:00 UTC. Cron uses `GET`, so it auto-saves top matches. The web page uses `POST`, so it only shows ranked jobs for review until you click **Save**.

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
- This app does not need a Google Cloud billing account.
- If Google Sheets fails, check that the Apps Script deployment access is set to `Anyone`.
- If DeepSeek fails, check `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`.
- If URL reading fails for LinkedIn or gated job boards, paste the job description text instead.
