const state = { overview: null, config: null, revision: null, savedYaml: "", editorDirty: false, downloadTimer: null };
const $ = (selector) => document.querySelector(selector);
const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}

function toast(message, error = false) {
  const node = document.createElement("div");
  node.className = `toast${error ? " error" : ""}`;
  node.textContent = message;
  $("#toasts").append(node);
  setTimeout(() => node.remove(), 4500);
}

function empty(title, detail) {
  return `<div class="empty-state"><strong>${safe(title)}</strong>${safe(detail)}</div>`;
}

function total(map) { return Object.values(map || {}).reduce((sum, value) => sum + Number(value || 0), 0); }

function metric(label, value, foot) {
  return `<div class="metric"><div class="metric-label">${safe(label)}</div><div class="metric-value">${safe(value)}</div><div class="metric-foot">${safe(foot)}</div></div>`;
}

function bars(data, color = "") {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return empty("No records in this collection yet", "Add or register research records to see measured coverage here.");
  const max = Math.max(...entries.map(([, value]) => Number(value)), 1);
  return `<div class="bar-list">${entries.slice(0, 9).map(([label, value]) => `<div class="bar-row"><span class="bar-label" title="${safe(label)}">${safe(label)}</span><span class="bar-track"><span class="bar-fill ${color}" style="display:block;width:${Math.max(2, Number(value) / max * 100)}%"></span></span><span class="bar-value">${safe(value)}</span></div>`).join("")}</div>`;
}

function distributionChips(data) {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return empty("No classification metadata yet", "Automatic classifications appear after structured evidence is registered.");
  return `<div class="bar-list">${entries.slice(0, 10).map(([label, count]) => `<div class="bar-row"><span class="bar-label" title="${safe(label)}">${safe(label)}</span><span class="bar-track"><span class="bar-fill" style="display:block;width:${Math.max(2, Number(count) / Math.max(...entries.map((entry) => Number(entry[1]))) * 100)}%"></span></span><span class="bar-value">${safe(count)}</span></div>`).join("")}</div>`;
}

function renderChart(series) {
  const points = series || [];
  if (!points.some((point) => point.sources || point.classifications)) return empty("No collection activity in the last 30 days", "The chart will reflect saved source and classification dates.");
  const width = 650, height = 180, left = 26, right = 12, top = 14, bottom = 24;
  const values = points.flatMap((point) => [point.sources, point.classifications]);
  const max = Math.max(...values, 1);
  const x = (index) => left + index * (width - left - right) / Math.max(points.length - 1, 1);
  const y = (value) => top + (height - top - bottom) * (1 - value / max);
  const pathFor = (field) => points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point[field]).toFixed(1)}`).join(" ");
  const last = points.length - 1;
  const labels = [0, Math.round(last / 2), last].map((index) => `<text class="chart-label" x="${x(index)}" y="${height - 3}" text-anchor="${index === 0 ? "start" : index === last ? "end" : "middle"}">${safe(points[index].date.slice(5))}</text>`).join("");
  const grid = [0, .5, 1].map((fraction) => `<line class="chart-grid" x1="${left}" y1="${y(max * fraction)}" x2="${width - right}" y2="${y(max * fraction)}"/><text class="chart-label" x="${left - 8}" y="${y(max * fraction) + 3}" text-anchor="end">${Math.round(max * fraction)}</text>`).join("");
  const sourcePoints = points.filter((point) => point.sources).map((point) => `<circle class="chart-source-point" cx="${x(points.indexOf(point))}" cy="${y(point.sources)}" r="3"/>`).join("");
  const classPoints = points.filter((point) => point.classifications).map((point) => `<circle class="chart-class-point" cx="${x(points.indexOf(point))}" cy="${y(point.classifications)}" r="2.7"/>`).join("");
  return `<svg class="activity-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily sources and classifications during the last 30 days">${grid}<line class="chart-axis" x1="${left}" y1="${height-bottom}" x2="${width-right}" y2="${height-bottom}"/><path class="chart-source-line" d="${pathFor("sources")}"/><path class="chart-class-line" d="${pathFor("classifications")}"/>${sourcePoints}${classPoints}${labels}</svg>`;
}

function setHealthBadge(health) {
  const node = $("#overview-health");
  const status = health === "ok" ? "ok" : health === "degraded" ? "degraded" : "attention";
  const label = health === "ok" ? "System operational" : health === "degraded" ? "Needs attention" : "Review recommended";
  node.className = `health-pill ${status}`;
  node.innerHTML = `<span class="status-dot"></span><span>${label}</span>`;
}

function providerSummary(providers) {
  const selected = providers.selected;
  const rows = [
    ["Built-in rules", "Local keyword matching", selected === "rules" ? "Selected" : "Available", ""],
    ["Jev · TypeSafe", providers.typesafe.configured ? `Credential via ${providers.typesafe.source}` : "API key not configured", selected === "jev" ? "Selected" : providers.typesafe.configured ? "Ready" : "Setup needed", providers.typesafe.configured ? "" : "warn"],
    ["Laya · local", providers.laya.installed ? `${providers.laya.model} · ${providers.laya.cached ? "checkpoint cached" : "download required"}` : "Optional dependency not installed", selected === "laya" ? "Selected" : providers.laya.installed ? "Available" : "Setup needed", providers.laya.installed ? "" : "warn"],
  ];
  return rows.map(([name, detail, status, tone]) => `<div class="provider-row"><div><div class="provider-name">${safe(name)}</div><div class="provider-detail">${safe(detail)}</div></div><span class="status-label ${tone}">${safe(status)}</span></div>`).join("");
}

function renderOverview(payload) {
  const research = payload.research, corpus = research.corpus, classifications = research.classifications;
  const disposition = classifications.by_disposition || {};
  const accepted = disposition.accepted || 0;
  const review = disposition.review_required || 0;
  const failed = disposition.failed || 0;
  const issueCount = research.malformed_count + (research.operational_health.issues || []).length;
  $("#overview-metrics").innerHTML = [
    metric("Registered sources", corpus.sources || 0, `${corpus.segments || 0} source passages`),
    metric("Structured claims", corpus.claims || 0, `${corpus.entities || 0} named entities`),
    metric("Classification decisions", corpus.classifications || 0, `${accepted} accepted · ${review} review · ${failed} failed`),
    metric("Open conflicts", corpus.conflicts || 0, `${issueCount} operational or record issues`),
  ].join("");
  $("#activity-chart").innerHTML = renderChart(research.activity_30d);
  $("#provider-summary").innerHTML = providerSummary(payload.providers);
  $("#topic-coverage").innerHTML = distributionChips(research.topics);
  const methods = research.method_records;
  const stages = [["Protocols", methods.protocols], ["Searches", methods.searches], ["Candidates", methods.candidates], ["Screenings", methods.screenings], ["Extractions", methods.extractions], ["Appraisals", methods.appraisals]];
  $("#review-funnel").innerHTML = stages.some(([, count]) => count) ? `<div class="workflow-strip">${stages.map(([label, count]) => `<div class="workflow-stage"><strong>${safe(count)}</strong><span>${safe(label)}</span></div>`).join("")}</div>` : empty("No review method records yet", "Start by creating a protocol before systematic searches or screening.");
  $("#overview-notice").textContent = research.malformed_count ? `${research.malformed_count} stored record(s) failed schema validation and are excluded from research analytics.` : "Counts describe stored records. They do not establish research completeness, screening quality, or systematic-review completion.";
  setHealthBadge(payload.system.health);
}

function renderResearch(research) {
  const c = research.corpus;
  $("#research-metrics").innerHTML = [
    metric("Sources", c.sources || 0, `${total(research.source_statuses)} with recorded status`),
    metric("Segments", c.segments || 0, "Pinned source passages"),
    metric("Claims", c.claims || 0, `${c.edges || 0} evidence links`),
    metric("Entities", c.entities || 0, `${c.gaps || 0} open research gaps recorded`),
  ].join("");
  $("#source-types").innerHTML = bars(research.source_types, "clay");
  const byDisposition = research.classifications.by_disposition;
  const byProvider = research.classifications.by_provider;
  const review = research.classifications.review_required || [];
  const failed = research.classifications.failed || [];
  $("#classification-breakdown").innerHTML = total(byDisposition) ? `<div class="distribution-columns"><div><h3>Disposition</h3>${bars(byDisposition, "amber")}</div><div><h3>Provider</h3>${bars(byProvider)}</div></div><div class="panel-footnote">Review-required IDs: ${review.length ? review.map(safe).join(", ") : "none"}<br>Failed IDs: ${failed.length ? failed.map(safe).join(", ") : "none"}</div>` : empty("No classification records yet", "Register a source or other evidence record to create a classification decision.");
  $("#topic-list").innerHTML = bars(research.topics);
  $("#tag-list").innerHTML = bars(research.tags, "clay");
  const stages = [["Protocols", "protocols"], ["Searches", "searches"], ["Candidates", "candidates"], ["Screenings", "screenings"], ["Extractions", "extractions"], ["Appraisals", "appraisals"]];
  $("#method-counts").innerHTML = `<div class="workflow-strip">${stages.map(([label, key]) => `<div class="workflow-stage"><strong>${safe(research.method_records[key] || 0)}</strong><span>${label}</span></div>`).join("")}</div>`;
}

function detailRows(rows) {
  return `<div class="detail-list">${rows.map(([label, value]) => `<div class="detail-row"><span>${safe(label)}</span><span>${safe(value)}</span></div>`).join("")}</div>`;
}

function renderHealth(payload) {
  const operational = payload.research.operational_health;
  const degraded = payload.system.health === "degraded";
  const label = degraded ? "Action needed" : payload.system.maintenance.due ? "Maintenance recommended" : "No active system alerts";
  $("#health-summary").innerHTML = `<div class="health-summary-main"><span class="health-icon ${degraded ? "degraded" : ""}">${degraded ? "!" : "✓"}</span><div><div class="health-title">${label}</div><div class="health-subtitle">Checked ${new Date(payload.generated_at).toLocaleString()} · live, schema-validated records</div></div></div><span class="status-label ${degraded ? "bad" : payload.system.maintenance.due ? "warn" : ""}">${safe(payload.system.health)}</span>`;
  const disk = `${(payload.system.disk_free_bytes / 1024 ** 3).toFixed(1)} GB free of ${(payload.system.disk_total_bytes / 1024 ** 3).toFixed(1)} GB`;
  $("#runtime-details").innerHTML = detailRows([["Python runtime", payload.system.python], ["Repository disk", disk], ["Config", payload.system.config_valid ? "Valid YAML and provider settings" : "Invalid"], ["Malformed records", payload.research.malformed_count], ["Vault path", payload.repository]]);
  const p = payload.providers;
  $("#health-providers").innerHTML = detailRows([["Selected provider", p.selected], ["Classification", p.enabled ? "Enabled" : "Disabled"], ["Jev credential", p.typesafe.configured ? `Configured in ${p.typesafe.source}` : "Missing"], ["Local Laya package", p.laya.installed ? "Installed" : "Not installed"], ["Configured Laya model", `${p.laya.model} · ${p.laya.cached ? "cached" : "not cached"}`], ["Taxonomy version", p.taxonomy_version]]);
  const issues = [];
  for (const issue of operational.issues || []) issues.push(issue.replaceAll("_", " "));
  for (const row of payload.research.operational_health.malformed_records || []) issues.push(`${row.path}: ${row.error}`);
  for (const id of operational.tasks.failed_ids || []) issues.push(`Failed task ${id}`);
  for (const id of operational.tasks.blocked_ids || []) issues.push(`Blocked task ${id}`);
  for (const id of operational.runs.failed_ids || []) issues.push(`Failed run ${id}`);
  if (payload.research.malformed_count > operational.malformed_records.length) issues.push(`${payload.research.malformed_count - operational.malformed_records.length} invalid evidence record(s) need review`);
  $("#health-issues").innerHTML = issues.length ? `<div class="issue-list">${issues.map((issue) => `<div class="issue-item"><span class="issue-mark">!</span><span>${safe(issue)}</span></div>`).join("")}</div>` : empty("No malformed, failed, or blocked records", "Operational checks found no current exceptions in the local record store.");
  const maintenance = payload.system.maintenance;
  const triggerDetails = (maintenance.triggers || []).map((trigger) => [`${trigger.kind}: ${trigger.name}`, trigger.reason]);
  $("#maintenance-details").innerHTML = detailRows([["Maintenance due", maintenance.due ? "Yes" : "No"], ["Current assessment", maintenance.reason], ["Enabled checks", (maintenance.passes || []).map((item) => item.name).join(", ") || "None"], ...triggerDetails]);
}

function renderAll(payload) {
  state.overview = payload;
  $("#repository-path").textContent = payload.repository;
  $("#last-updated").textContent = `Updated ${new Date(payload.generated_at).toLocaleTimeString()}`;
  $("#footer-time").textContent = `Live local view · ${new Date(payload.generated_at).toLocaleString()}`;
  $("#page-loading").hidden = true;
  $("#page-error").hidden = true;
  renderOverview(payload);
  renderResearch(payload.research);
  renderHealth(payload);
  if (location.hash === "#settings") loadSettings().catch((error) => showError(error.message));
}

async function refresh() {
  $("#refresh-button").disabled = true;
  try { renderAll(await api("/api/overview")); }
  catch (error) { showError(error.message); }
  finally { $("#refresh-button").disabled = false; }
}

function showError(message) {
  const node = $("#page-error");
  node.textContent = `Dashboard data could not be refreshed: ${message}`;
  node.hidden = false;
  $("#page-loading").hidden = true;
}

function setView(name) {
  const view = ["overview", "research", "health", "settings"].includes(name) ? name : "overview";
  document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  document.querySelectorAll(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === view));
  $("#current-section").textContent = ({ overview: "Overview", research: "Research data", health: "System health", settings: "Configuration" })[view];
  if (view === "settings") loadSettings().catch((error) => showError(error.message));
  if (view === "health") refresh();
}

async function loadSettings() {
  const data = await api("/api/config");
  state.config = data.config;
  state.revision = data.revision;
  state.savedYaml = data.config_yaml;
  state.editorDirty = false;
  $("#config-editor").value = data.config_yaml;
  $("#config-message").textContent = "";
  $("#save-basics").disabled = false;
  fillBasicSettings(data.config);
  updateProviderCopy();
  renderCredential(data.provider.typesafe);
  renderLaya(data.provider.laya);
  $("#taxonomy-summary").textContent = `${data.provider.taxonomy_version} · ${Object.keys(data.config.classification?.taxonomy?.categories || {}).length} categories · ${Object.keys(data.config.classification?.taxonomy?.tags || {}).length} tags`;
}

function fillBasicSettings(config) {
  const c = config.classification || {};
  $("#provider-select").value = c.provider || "rules";
  $("#classification-enabled").checked = c.enabled !== false;
  $("#confidence-input").value = c.minimum_confidence ?? 0.75;
  $("#input-limit").value = c.max_input_chars ?? 12000;
  $("#jev-model").value = c.jev?.model || "jev-latest";
  $("#jev-timeout").value = c.jev?.timeout_seconds || 30;
  $("#laya-model").value = c.laya?.model || "multilingual";
  $("#laya-device").value = c.laya?.device || "auto";
  $("#jev-settings").hidden = c.provider !== "jev";
  $("#laya-settings").hidden = c.provider !== "laya";
}

function updateProviderCopy() {
  const provider = $("#provider-select").value;
  const details = {
    rules: "Deterministic keyword rules. No data leaves this machine.",
    jev: "Selected text is sent to the hosted TypeSafe System One API.",
    laya: "Inference runs in this process using locally cached Laya weights.",
  };
  $("#provider-description").textContent = details[provider];
  $("#jev-settings").hidden = provider !== "jev";
  $("#laya-settings").hidden = provider !== "laya";
  $("#typesafe-card").hidden = provider !== "jev" && !(state.overview?.providers.typesafe.configured);
  $("#laya-card").hidden = provider !== "laya" && !(state.overview?.providers.laya.installed || state.overview?.providers.laya.cached);
  $("#privacy-note").textContent = provider === "jev" ? "Jev sends configured input text to TypeSafe's hosted API. The key is stored locally and never returned." : provider === "laya" ? "Laya inference runs locally after its model weights are downloaded. Model download requires a Hugging Face connection." : "Rules run locally. No research text is sent to an external provider.";
}

function renderCredential(status) {
  const pill = $("#credential-status");
  pill.textContent = status.configured ? `Configured · ${status.source}` : "API key needed";
  pill.className = `credential-status${status.configured ? " ready" : ""}`;
  $("#credential-source").textContent = status.source === "environment" ? `${status.key_env} is set in the server environment and takes precedence.` : status.configured ? "A local key is saved. The value cannot be retrieved in the browser." : `Save a key locally for ${status.key_env}.`;
  $("#remove-key").disabled = status.source !== "local vault";
}

function renderLaya(status) {
  const pill = $("#laya-status-pill");
  pill.textContent = !status.installed ? "Dependency missing" : status.job.status === "ready" ? "Loaded in process" : status.cached ? "Checkpoint cached" : "Model not downloaded";
  pill.className = `credential-status${status.installed && (status.cached || status.job.status === "ready") ? " ready" : ""}`;
  const messages = [];
  if (!status.installed) messages.push("Install the optional Laya dependency: pip install 'polder-research-pipeline[laya]'. Then restart this local server.");
  else if (status.job.status === "downloading") messages.push(`Preparing the ${status.job.model} checkpoint. The model downloads to the local Hugging Face cache and loads into this process.`);
  else if (status.job.status === "failed") messages.push(`Model setup failed: ${status.job.error || "No error details returned."}`);
  else if (status.job.status === "ready") messages.push(`${status.job.model} is loaded and ready for local inference.`);
  else if (status.cached) messages.push(`${status.model} checkpoint is already cached${status.cache_path ? ` at ${status.cache_path}` : " locally"}. Select download to load it into this server process.`);
  else messages.push(`The ${status.model} checkpoint will download from Hugging Face. The first download needs network access and available disk/RAM.`);
  $("#laya-model-status").innerHTML = `<span class="model-chip">${safe(status.model)}</span><span class="model-chip">${status.installed ? "Python package installed" : "Package not installed"}</span><span class="model-chip">${status.cached ? "Cached" : "Not cached"}</span>`;
  $("#laya-message").textContent = messages.join(" ");
  $("#laya-model-status").setAttribute("aria-label", messages.join(" "));
  $("#laya-model-status").title = messages.join(" ");
  $("#download-laya").disabled = !status.installed || status.job.status === "downloading";
  $("#download-laya").textContent = status.job.status === "downloading" ? "Preparing model…" : status.cached ? "Load model into server" : "Download and load model";
  const progress = $("#download-progress");
  const busy = status.job.status === "downloading";
  progress.hidden = !busy && status.job.status !== "failed";
  if (busy) progress.innerHTML = `Preparing ${safe(status.job.model)}. Download and model loading can take several minutes; this page will update automatically.<div class="progress-track" role="progressbar" aria-label="Laya model download and loading in progress"><div class="progress-indeterminate"></div></div>`;
  else if (status.job.status === "failed") progress.textContent = status.job.error || "Model preparation failed.";
}

async function saveBasics() {
  if (state.editorDirty) { toast("Save or discard the advanced YAML edits before applying basic settings.", true); return; }
  const updates = {
    "classification.provider": $("#provider-select").value,
    "classification.enabled": $("#classification-enabled").checked,
    "classification.minimum_confidence": Number($("#confidence-input").value),
    "classification.max_input_chars": Number($("#input-limit").value),
    "classification.jev.model": $("#jev-model").value.trim(),
    "classification.jev.timeout_seconds": Number($("#jev-timeout").value),
    "classification.jev.api_key_env": state.config.classification?.jev?.api_key_env || "TYPESAFE_API_KEY",
    "classification.laya.model": $("#laya-model").value,
    "classification.laya.device": $("#laya-device").value,
  };
  const button = $("#save-basics"); button.disabled = true;
  try {
    const result = await api("/api/config/basic", { method: "PATCH", body: JSON.stringify({ revision: state.revision, updates }) });
    state.revision = result.revision;
    $("#basics-message").textContent = "Settings applied.";
    $("#settings-saved").textContent = "Saved";
    await loadSettings(); await refresh(); toast("Classification settings saved.");
  } catch (error) { $("#basics-message").textContent = error.message; toast(error.message, true); }
  finally { button.disabled = false; }
}

async function saveConfig() {
  const button = $("#save-config"); button.disabled = true;
  $("#config-message").textContent = "Validating and saving…";
  try {
    const result = await api("/api/config", { method: "PUT", body: JSON.stringify({ revision: state.revision, config_yaml: $("#config-editor").value }) });
    state.revision = result.revision;
    state.savedYaml = $("#config-editor").value;
    state.editorDirty = false;
    $("#settings-saved").textContent = "Saved configuration";
    $("#config-message").textContent = "Saved and validated.";
    await loadSettings(); await refresh(); toast("Complete configuration saved.");
  } catch (error) { $("#config-message").textContent = error.message; toast(error.message, true); }
  finally { button.disabled = false; }
}

async function saveSecret(secret) {
  try {
    const result = await api("/api/secrets/typesafe", { method: "PUT", body: JSON.stringify({ secret }) });
    $("#typesafe-key").value = "";
    renderCredential(result.status);
    await refresh();
    toast(secret ? "TypeSafe credential saved in the local secret store." : "Saved TypeSafe credential removed.");
  } catch (error) { toast(error.message, true); }
}

async function testProvider(provider) {
  const button = provider === "jev" ? $("#test-jev") : $("#test-laya");
  button.disabled = true; button.textContent = "Checking…";
  try {
    const result = await api("/api/providers/test", { method: "POST", body: JSON.stringify({ provider }) });
    toast(result.message, !result.ok);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = provider === "jev" ? "Test API connection" : "Test local inference"; }
}

async function refreshLayaStatus() {
  try {
    const status = await api("/api/laya/status");
    renderLaya(status);
    if (status.job.status !== "downloading" && state.downloadTimer) { clearInterval(state.downloadTimer); state.downloadTimer = null; }
  } catch (error) { toast(error.message, true); }
}

async function startDownload() {
  const accepted = window.confirm("Download or load the configured Laya checkpoint into this server process? The first download contacts Hugging Face. The model can use substantial memory while the server is running.");
  if (!accepted) return;
  $("#download-laya").disabled = true;
  try {
    await api("/api/laya/download", { method: "POST", body: "{}" });
    await refreshLayaStatus();
    if (!state.downloadTimer) state.downloadTimer = setInterval(refreshLayaStatus, 1400);
  } catch (error) { toast(error.message, true); $("#download-laya").disabled = false; }
}

document.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", (event) => {
  event.preventDefault(); location.hash = link.dataset.view;
}));
window.addEventListener("hashchange", () => setView(location.hash.slice(1)));
$("#refresh-button").addEventListener("click", refresh);
$("#health-refresh").addEventListener("click", refresh);
$("#provider-select").addEventListener("change", updateProviderCopy);
$("#save-basics").addEventListener("click", saveBasics);
$("#save-config").addEventListener("click", saveConfig);
$("#reload-config").addEventListener("click", () => loadSettings().catch((error) => toast(error.message, true)));
$("#save-key").addEventListener("click", () => saveSecret($("#typesafe-key").value));
$("#remove-key").addEventListener("click", () => saveSecret(null));
$("#test-jev").addEventListener("click", () => testProvider("jev"));
$("#test-laya").addEventListener("click", () => testProvider("laya"));
$("#download-laya").addEventListener("click", startDownload);
$("#config-editor").addEventListener("input", () => {
  state.editorDirty = $("#config-editor").value !== state.savedYaml;
  $("#settings-saved").textContent = state.editorDirty ? "Unsaved YAML edits" : "Saved configuration";
  $("#save-basics").disabled = state.editorDirty;
});
setView(location.hash.slice(1) || "overview");
refresh();
setInterval(() => { if (document.visibilityState === "visible") refresh(); }, 30_000);
