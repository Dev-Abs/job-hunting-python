const form = document.querySelector("#jobForm");
const textarea = document.querySelector("#jobText");
const message = document.querySelector("#message");
const result = document.querySelector("#result");
const details = document.querySelector("#details");
const score = document.querySelector("#score");
const subject = document.querySelector("#subject");
const emailBody = document.querySelector("#emailBody");
const button = form.querySelector("button");

const detailKeys = [
  "Company",
  "Job Title",
  "Location",
  "Remote Type",
  "Salary",
  "Job URL",
  "Required Skills",
  "Why Good Fit",
  "Missing Skills",
  "Next Action",
  "Contact Email",
  "Cover Letter Angle"
];

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
  message.hidden = false;
}

function renderResult(data) {
  const analysis = data.analysis;
  score.textContent = `${analysis["Match Score"]}/100`;
  details.innerHTML = "";

  for (const key of detailKeys) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = analysis[key] || "Not specified";
    details.append(dt, dd);
  }

  subject.textContent = data.email_draft.subject;
  emailBody.innerHTML = data.email_draft.body;
  result.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const jobText = textarea.value.trim();
  if (jobText.length < 40) {
    showMessage("Paste a fuller job description first.", true);
    return;
  }

  button.disabled = true;
  showMessage("Analyzing with DeepSeek and saving to Google Sheets...");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_text: jobText })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Something went wrong.");
    }
    showMessage("Saved to Google Sheets. Draft generated below.");
    renderResult(data);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
});
