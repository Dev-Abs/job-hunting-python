# Job Hunting Assistant Web App

This is a deployable Python replacement for the n8n job hunting workflow.

You paste a job description or a public job listing URL into the web chat-style form. The app:

1. Reads the pasted job description, or fetches a public job listing URL.
2. Sends the real job content to DeepSeek.
3. Analyzes the role against Abdullah's resume profile.
4. Appends the result to Google Sheets through a free Google Apps Script webhook.
5. Generates a tailored application email draft.
6. Lets you copy the draft or open a Gmail compose window.

The app validates input before saving. If the text or URL does not contain enough real job detail, it will not save a row or generate a draft.

URL note: LinkedIn and some job boards block automated public reads. If a URL cannot be read, paste the job description text instead.

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
    const rowObject = payload.row || {};

    const existingHeader = sheet.getRange(1, 1, 1, columns.length).getValues()[0];
    const headerMissing = existingHeader.join("") === "" || existingHeader.join("|") !== columns.join("|");

    if (headerMissing) {
      sheet.getRange(1, 1, 1, columns.length).setValues([columns]);
      sheet.setFrozenRows(1);
    }

    const row = columns.map((column) => rowObject[column] || "Not specified");
    sheet.appendRow(row);

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true }))
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
