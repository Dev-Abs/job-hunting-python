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
const jobSearch = document.querySelector("#jobSearch");
const sourceFilter = document.querySelector("#sourceFilter");
const scoreFilter = document.querySelector("#scoreFilter");
const sortJobs = document.querySelector("#sortJobs");
const submitButton = form.querySelector("button[type='submit']");
let currentDraft = null;
let inputMode = "description";
let discoveredJobs = [];
let discoveryMeta = {};

const detailKeys = ["Company", "Job Title", "Location", "Remote Type", "Salary", "Job URL", "Required Skills", "Why Good Fit", "Missing Skills", "Next Action", "Contact Email", "Cover Letter Angle"];

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
  detailKeys.forEach((key) => {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = analysis[key] || "Not specified";
    details.append(dt, dd);
  });
  subject.textContent = data.email_draft.subject;
  emailBody.innerHTML = data.email_draft.body;
  result.hidden = false;
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setInputMode(mode) {
  inputMode = mode;
  modeTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === mode));
  jobTextLabel.textContent = mode === "url" ? "Enter job listing URL" : "Paste job description";
  textarea.placeholder = mode === "url" ? "Paste a public listing URL. If the site blocks reading, paste the job description instead." : "Paste the full job post here. Include the role, company, location, requirements, and link if available.";
  textarea.value = "";
  textarea.classList.toggle("url-mode", mode === "url");
  result.hidden = true;
}

modeTabs.forEach((tab) => tab.addEventListener("click", () => setInputMode(tab.dataset.mode)));

function draftText() {
  return currentDraft ? `Subject: ${currentDraft.subject}\n\n${currentDraft.plain_body}` : "";
}

copyDraft.addEventListener("click", async () => {
  if (!currentDraft) return;
  await navigator.clipboard.writeText(draftText());
  showMessage("Draft copied to clipboard.");
});

openGmail.addEventListener("click", () => {
  if (!currentDraft) return;
  const params = new URLSearchParams({ view: "cm", fs: "1", su: currentDraft.subject, body: currentDraft.plain_body });
  window.open(`https://mail.google.com/mail/?${params.toString()}`, "_blank", "noopener,noreferrer");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const jobText = textarea.value.trim();
  if (inputMode === "url" && !/^https?:\/\/\S+$/i.test(jobText)) return showMessage("Enter a valid public job listing URL.", true);
  if (jobText.length < 12) return showMessage("Add a job description or a job listing URL first.", true);
  submitButton.disabled = true;
  showMessage("Analyzing with DeepSeek and saving to Google Sheets...");
  try {
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_text: jobText }) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Something went wrong.");
    showMessage(`${data.source_type === "url" ? "Listing read" : "Description analyzed"} and saved. Draft generated below.`);
    renderResult(data);
  } catch (error) { showMessage(error.message, true); }
  finally { submitButton.disabled = false; }
});

function jobScore(job) { return Number.parseInt(job["Match Score"], 10) || 0; }

function populateSources() {
  const selected = sourceFilter.value;
  const sources = [...new Set(discoveredJobs.map((job) => job.Source || job.Notes?.replace("Auto-discovered from ", "").replace(".", "") || "Public source"))].sort();
  sourceFilter.innerHTML = "<option value=\"\">All sources</option>";
  sources.forEach((source) => { const option = document.createElement("option"); option.value = source; option.textContent = source; sourceFilter.appendChild(option); });
  sourceFilter.value = sources.includes(selected) ? selected : "";
}

function filteredJobs() {
  const query = jobSearch.value.trim().toLowerCase();
  const source = sourceFilter.value;
  const minScore = Number.parseInt(scoreFilter.value, 10) || 0;
  return discoveredJobs.filter((job) => {
    const haystack = `${job["Job Title"]} ${job.Company} ${job["Required Skills"]}`.toLowerCase();
    const jobSource = job.Source || "Public source";
    return (!query || haystack.includes(query)) && (!source || jobSource === source) && jobScore(job) >= minScore;
  }).sort((a, b) => sortJobs.value === "company" ? (a.Company || "").localeCompare(b.Company || "") : sortJobs.value === "newest" ? (b["Date Added"] || "").localeCompare(a["Date Added"] || "") : jobScore(b) - jobScore(a));
}

function renderDiscovery() {
  const jobs = filteredJobs();
  discoveryCount.textContent = `${jobs.length} shown · ${discoveredJobs.length} found`;
  discoveryList.innerHTML = "";
  const summary = document.createElement("div");
  summary.className = "discovery-summary";
  summary.innerHTML = `<span>Checked ${discoveryMeta.candidates_checked || 0}</span><span>Analyzed ${discoveryMeta.analyzed || 0}</span><span>${discoveryMeta.deepseek_success || 0} AI ranked</span><span>${discoveryMeta.fallback_used || 0} fallback</span>`;
  discoveryList.appendChild(summary);
  if (!jobs.length) {
    const empty = document.createElement("p"); empty.className = "empty-state"; empty.textContent = "No jobs match these filters."; discoveryList.appendChild(empty); return;
  }
  jobs.forEach((job) => {
    const item = document.createElement("article"); item.className = "job-item";
    const main = document.createElement("div"); main.className = "job-main";
    const titleRow = document.createElement("div"); titleRow.className = "job-title-row";
    const title = document.createElement("h3"); title.textContent = job["Job Title"] || "Untitled role";
    const badge = document.createElement("span"); badge.className = "score-badge"; badge.textContent = `${jobScore(job)}/100`;
    titleRow.append(title, badge);
    const subtitle = document.createElement("p"); subtitle.className = "job-subtitle"; subtitle.textContent = `${job.Company || "Company not specified"} · ${job.Location || "Location not specified"}`;
    const source = document.createElement("span"); source.className = "source-label"; source.textContent = job.Source || "Public source";
    const fit = document.createElement("p"); fit.className = "job-fit"; fit.textContent = job["Why Good Fit"] || "No summary available.";
    const skills = document.createElement("p"); skills.className = "job-tags"; skills.textContent = job["Required Skills"] || "Skills not specified";
    main.append(titleRow, subtitle, source, fit, skills);
    const meta = document.createElement("div"); meta.className = "job-meta";
    const status = document.createElement("span"); status.className = "status-chip"; status.textContent = job.Status || "Discovered";
    meta.appendChild(status);
    if (job["Job URL"] && job["Job URL"] !== "Not specified") { const link = document.createElement("a"); link.className = "open-link"; link.target = "_blank"; link.rel = "noopener noreferrer"; link.href = job["Job URL"]; link.textContent = "Open listing ↗"; meta.appendChild(link); }
    const save = document.createElement("button"); save.className = "secondary save-job"; save.type = "button"; save.textContent = "Save to Sheets"; save.dataset.job = JSON.stringify(job); meta.appendChild(save);
    item.append(main, meta); discoveryList.appendChild(item);
  });
}

[jobSearch, sourceFilter, scoreFilter, sortJobs].forEach((control) => control.addEventListener("input", renderDiscovery));

discoveryList.addEventListener("click", async (event) => {
  const button = event.target.closest(".save-job"); if (!button) return;
  const job = JSON.parse(button.dataset.job); button.disabled = true; button.textContent = "Saving...";
  try {
    const response = await fetch("/api/save-job", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job }) });
    const data = await response.json(); if (!response.ok || !data.ok) throw new Error(data.error || "Save failed.");
    button.textContent = data.skipped ? "Already saved" : "Saved"; showMessage(data.message || "Saved to Google Sheets.");
  } catch (error) { button.disabled = false; button.textContent = "Save to Sheets"; showMessage(error.message, true); }
});

discoverJobs.addEventListener("click", async () => {
  discoverJobs.disabled = true; discoverJobs.classList.add("is-loading"); showMessage("Scanning job sources and ranking every promising match...");
  try {
    const response = await fetch("/api/discover", { method: "POST" }); const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Discovery failed.");
    discoveredJobs = data.jobs || []; discoveryMeta = data; populateSources(); renderDiscovery(); discoveryResult.hidden = false;
    showMessage(`Discovery complete. Found ${discoveredJobs.length} jobs from ${data.candidates_checked || 0} candidates. Review and save the ones you want.`);
    discoveryResult.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) { showMessage(error.message, true); }
  finally { discoverJobs.disabled = false; discoverJobs.classList.remove("is-loading"); }
});
