const form = document.querySelector("#jobForm");
const textarea = document.querySelector("#jobText");
const message = document.querySelector("#message");
const result = document.querySelector("#result");
const details = document.querySelector("#details");
const score = document.querySelector("#score");
const subject = document.querySelector("#subject");
const emailBody = document.querySelector("#emailBody");
const copyDraft = document.querySelector("#copyDraft");
const openGmail = document.querySelector("#openGmail");
const button = form.querySelector("button");
let currentDraft = null;

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
  currentDraft = data.email_draft;
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

function draftText() {
  if (!currentDraft) return "";
  return `Subject: ${currentDraft.subject}\n\n${currentDraft.plain_body}`;
}

copyDraft.addEventListener("click", async () => {
  if (!currentDraft) return;
  await navigator.clipboard.writeText(draftText());
  showMessage("Draft copied to clipboard.");
});

openGmail.addEventListener("click", () => {
  if (!currentDraft) return;
  const params = new URLSearchParams({
    view: "cm",
    fs: "1",
    su: currentDraft.subject,
    body: currentDraft.plain_body
  });
  window.open(`https://mail.google.com/mail/?${params.toString()}`, "_blank", "noopener,noreferrer");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const jobText = textarea.value.trim();
  if (jobText.length < 12) {
    showMessage("Paste a job description or a job listing URL first.", true);
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
    const sourceLabel = data.source_type === "url" ? "URL read, analyzed, and saved." : "Job description analyzed and saved.";
    showMessage(`${sourceLabel} Draft generated below.`);
    renderResult(data);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
});
