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
const modeTabs = document.querySelectorAll(".mode-tab");
const jobTextLabel = document.querySelector("#jobTextLabel");
const discoverJobs = document.querySelector("#discoverJobs");
const discoveryResult = document.querySelector("#discoveryResult");
const discoveryCount = document.querySelector("#discoveryCount");
const discoveryList = document.querySelector("#discoveryList");
const submitButton = form.querySelector("button[type='submit']");
let currentDraft = null;
let inputMode = "description";
let discoveredJobs = [];

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

function setInputMode(mode) {
  inputMode = mode;
  modeTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === mode));
  if (mode === "url") {
    jobTextLabel.textContent = "Enter job listing URL";
    textarea.placeholder = "Paste a public job listing URL. If LinkedIn or another site blocks reading, paste the full description instead.";
    textarea.value = "";
    textarea.style.minHeight = "88px";
  } else {
    jobTextLabel.textContent = "Paste job description";
    textarea.placeholder = "Paste the full job post here. Include company, role, responsibilities, requirements, location, salary, contact email, and URL if available.";
    textarea.value = "";
    textarea.style.minHeight = "";
  }
  result.hidden = true;
  discoveryResult.hidden = true;
}

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => setInputMode(tab.dataset.mode));
});

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
  if (inputMode === "url" && !/^https?:\/\/\S+$/i.test(jobText)) {
    showMessage("Enter a valid public job listing URL.", true);
    return;
  }
  if (jobText.length < 12) {
    showMessage("Add a job description or a job listing URL first.", true);
    return;
  }

  submitButton.disabled = true;
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
    submitButton.disabled = false;
  }
});

function renderDiscovery(data) {
  const jobs = data.jobs || [];
  discoveredJobs = jobs;
  discoveryCount.textContent = data.auto_saved ? `${data.saved || 0} saved` : `${jobs.length} ranked`;
  discoveryList.innerHTML = "";

  if (!jobs.length) {
    discoveryList.innerHTML = `
      <p>No jobs were saved this time.</p>
      <p class="muted">Checked ${data.candidates_checked || 0} candidates, analyzed ${data.analyzed || 0}, threshold ${data.threshold || "--"}.</p>
    `;
  }

  const summary = document.createElement("div");
  summary.className = "discovery-summary";
  summary.innerHTML = `
    <span>Checked: ${data.candidates_checked || 0}</span>
    <span>Analyzed: ${data.analyzed || 0}</span>
    <span>DeepSeek: ${data.deepseek_success || 0}</span>
    <span>Fallback: ${data.fallback_used || 0}</span>
    <span>Skipped duplicates: ${data.skipped || 0}</span>
    <span>${data.auto_saved ? "Auto-saved" : "Review mode"}</span>
  `;
  discoveryList.appendChild(summary);

  jobs.forEach((job, index) => {
    const item = document.createElement("div");
    item.className = "job-item";
    const link = job["Job URL"] && job["Job URL"] !== "Not specified";
    item.innerHTML = `
      <div class="job-main">
        <div class="job-title-row">
          <strong></strong>
          <span class="score-badge"></span>
        </div>
        <span class="job-subtitle"></span>
        <p class="job-fit"></p>
        <div class="job-tags"></div>
      </div>
      <div class="job-meta">
        <span class="status-chip"></span>
        ${link ? `<a class="open-link" target="_blank" rel="noopener noreferrer">Open listing</a>` : ""}
        <button class="secondary save-job" type="button" data-index="${index}">Save</button>
      </div>
    `;
    item.querySelector("strong").textContent = job["Job Title"] || "Not specified";
    item.querySelector(".score-badge").textContent = `${job["Match Score"] || "--"}/100`;
    item.querySelector(".job-subtitle").textContent = `${job["Company"] || "Not specified"} · ${job["Location"] || "Not specified"} · ${job["Remote Type"] || "Not specified"}`;
    item.querySelector(".job-fit").textContent = job["Why Good Fit"] || "No summary available.";
    item.querySelector(".job-tags").textContent = job["Required Skills"] || "Skills not specified";
    item.querySelector(".status-chip").textContent = job["Status"] || "Discovered";
    if (link) {
      item.querySelector(".open-link").href = job["Job URL"];
    }
    discoveryList.appendChild(item);
  });

  discoveryResult.hidden = false;
}

discoveryList.addEventListener("click", async (event) => {
  const button = event.target.closest(".save-job");
  if (!button) return;

  const index = Number(button.dataset.index);
  const job = discoveredJobs[index];
  if (!job) return;

  button.disabled = true;
  button.textContent = "Saving...";
  try {
    const response = await fetch("/api/save-job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Save failed.");
    }
    button.textContent = data.skipped ? "Already saved" : "Saved";
    showMessage(data.message || "Saved to Google Sheets.");
  } catch (error) {
    button.disabled = false;
    button.textContent = "Save";
    showMessage(error.message, true);
  }
});

discoverJobs.addEventListener("click", async () => {
  discoverJobs.disabled = true;
  showMessage("Searching remote/worldwide/Pakistan jobs and ranking matches for review...");
  try {
    const response = await fetch("/api/discover", { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Discovery failed.");
    }
    showMessage(`Discovery complete. Found ${data.jobs?.length || 0} ranked jobs from ${data.candidates_checked || 0} candidates. Click Save on the ones you want.`);
    renderDiscovery(data);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    discoverJobs.disabled = false;
  }
});
