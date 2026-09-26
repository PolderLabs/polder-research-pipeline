const state = { overview: null, config: null, revision: null, savedYaml: "", editorDirty: false, reviewDraft: { reviewer: "", values: {} }, expandedReviews: new Set(), reviewDecisionDraft: false, downloadTimer: null };
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

function queuePreview(items, emptyLabel) {
  if (!items.length) return `<span>${safe(emptyLabel)}</span>`;
  return `<div class="queue-preview">${items.slice(0, 6).map((item) => {
    if (typeof item === "string") return `<div><code>${safe(item)}</code></div>`;
    const fields = Object.entries(item.field_decisions || {}).slice(0, 8).map(([field, decision]) => {
      const probability = Number.isFinite(decision?.probability) ? ` · ${Math.round(decision.probability * 100)}%` : "";
      const value = typeof decision?.value === "string" ? ` = ${decision.value}` : decision?.value === true ? " = yes" : decision?.value === false ? " = no" : "";
      const optionValue = (option) => option === null ? "__null__" : String(option);
      const optionLabel = (option) => option === null ? "No value" : option === true ? "Yes" : option === false ? "No" : String(option);
      const options = (decision?.options || []).map((option) => `<option value="${safe(optionValue(option))}"${option === decision?.value ? " selected" : ""}>${safe(optionLabel(option))}</option>`).join("");
      const proposedValue = optionValue(decision?.value ?? null);
      return `<div class="review-field"><span>${safe(field)}: ${safe(decision?.status || "unknown")}${safe(value)}${safe(probability)}</span><div class="review-actions"><select aria-label="Reviewed value for ${safe(field)}" data-review-value="${safe(item.id)}:${safe(field)}" data-proposed-value="${safe(proposedValue)}">${options}</select><button class="button button-secondary" type="button" data-review-action="accept" data-classification-id="${safe(item.id)}" data-field="${safe(field)}">Accept</button><button class="button button-quiet" type="button" data-review-action="reject" data-classification-id="${safe(item.id)}" data-field="${safe(field)}">Reject</button><button class="button button-primary" type="button" data-review-action="edit" data-classification-id="${safe(item.id)}" data-field="${safe(field)}" disabled>Save edit</button></div></div>`;
    }).join("");
    const preview = item.preview || {};
    const fieldCount = Object.keys(item.field_decisions || {}).length;
    return `<details class="review-candidate" data-review-candidate="${safe(item.id)}"><summary><code>${safe(item.id)}</code><strong>${safe(preview.title || "Evidence preview unavailable")}</strong><span class="review-meta">${safe(item.target_kind)} · ${fieldCount} fields</span></summary><div class="review-content"><p>${safe(preview.text || "No stored text preview. Follow the target ID to inspect its source record.")}</p><small>${safe(preview.sensitivity || "unspecified sensitivity")}${preview.personal_data ? " · marked as personal data" : ""} · ${safe(item.target_id)}</small>${fields || ""}</div></details>`;
  }).join("")}</div>`;
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
  const uncertain = classifications.confidence_bands?.near_threshold || 0;
  const issueCount = research.malformed_count + (research.operational_health.issues || []).length;
  $("#overview-metrics").innerHTML = [
    metric("Registered sources", corpus.sources || 0, `${corpus.segments || 0} source passages`),
    metric("Structured claims", corpus.claims || 0, `${corpus.entities || 0} named entities`),
    metric("Classification decisions", corpus.classifications || 0, `${accepted} accepted · ${review} review · ${failed} failed${uncertain ? ` · ${uncertain} near threshold` : ""}`),
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
  document.querySelectorAll("[data-review-candidate][open]").forEach((item) => state.expandedReviews.add(item.dataset.reviewCandidate));
  const c = research.corpus;
  const acquisition = research.acquisition_statuses || {};
  $("#research-metrics").innerHTML = [
    metric("Sources", c.sources || 0, `${acquisition.acquired || 0} acquired · ${acquisition.unacquired || 0} references`),
    metric("Segments", c.segments || 0, "Pinned source passages"),
    metric("Claims", c.claims || 0, `${c.edges || 0} evidence links`),
    metric("Entities", c.entities || 0, `${c.gaps || 0} open research gaps recorded`),
  ].join("");
  $("#source-types").innerHTML = bars(research.source_types, "clay");
  const byDisposition = research.classifications.by_disposition;
  const byProvider = research.classifications.by_provider;
  const queues = research.classifications.queues || {};
  const review = queues.review_required || research.classifications.review_required || [];
  const failed = queues.failed || research.classifications.failed || [];
  const reviewCount = queues.review_required_count ?? review.length;
  const failedCount = queues.failed_count ?? failed.length;
  const queueIds = (items) => items.map((item) => safe(typeof item === "string" ? item : item.id)).join(", ");
  const fieldStatus = research.classifications.field_status || {};
  const bands = research.classifications.confidence_bands || {};
  const latency = research.classifications.latency_ms || {};
  const humanReviews = research.classifications.human_reviews || {};
  const byField = research.classifications.by_field_status || {};
  const fieldSummary = Object.entries(byField).map(([field, statuses]) => `${safe(field)}: ${safe(Object.entries(statuses).map(([status, count]) => `${status} ${count}`).join(", "))}`).join(" · ");
  const runtime = latency.count ? `${latency.p50_ms} ms p50 · ${latency.p95_ms} ms p95 · ${latency.max_ms} ms max` : "No completed classification timings yet";
  $("#classification-quality").innerHTML = total(byDisposition) ? `<div class="distribution-columns quality-columns"><div><h3>Category outcomes</h3>${bars(fieldStatus.category, "amber")}</div><div><h3>Tag outcomes</h3>${bars(fieldStatus.tags)}</div><div><h3>Dimension outcomes</h3>${bars(fieldStatus.dimensions, "clay")}</div><div><h3>Confidence position</h3>${bars(bands)}</div></div><div class="panel-footnote">Latency: ${safe(runtime)}. Field decision status: ${fieldSummary || "no typed field decisions stored"}. “Near threshold” means a score within 0.05 of the decision threshold; it identifies decisions most likely to benefit from review. These signals do not measure provider accuracy or calibration.</div>` : empty("No classification quality signals yet", "Field outcomes, confidence position, and latency appear after classification records are stored.");
  $("#classification-breakdown").innerHTML = total(byDisposition) ? `<div class="distribution-columns"><div><h3>Disposition</h3>${bars(byDisposition, "amber")}</div><div><h3>Provider</h3>${bars(byProvider)}</div></div><div class="panel-footnote">Review queue: ${safe(reviewCount)} record(s)${review.length ? ` · ${queueIds(review)}` : ""}<br>Failed queue: ${safe(failedCount)} record(s)${failed.length ? ` · ${queueIds(failed)}` : ""}<br>Human review records: ${safe(humanReviews.record_count || 0)} · resolved fields: ${safe(humanReviews.resolved_field_count || 0)}</div><div class="queue-detail"><h3>Review candidates</h3><label class="reviewer-field"><span>Reviewer identity <small>Self-reported; this local dashboard does not authenticate reviewers.</small></span><input id="reviewer-name" maxlength="120" autocomplete="name" placeholder="Name or stable reviewer ID"></label>${queuePreview(review, "No records currently need classification review.")}</div>` : empty("No classification records yet", "Register a source or other evidence record to create a classification decision.");
  const reviewerInput = $("#reviewer-name");
  if (reviewerInput) reviewerInput.value = state.reviewDraft.reviewer;
  document.querySelectorAll("[data-review-candidate]").forEach((item) => {
    item.open = state.expandedReviews.has(item.dataset.reviewCandidate);
  });
  document.querySelectorAll("[data-review-value]").forEach((select) => {
    const draft = state.reviewDraft.values[select.dataset.reviewValue];
    if (draft !== undefined) select.value = draft;
    const edit = select.closest(".review-field")?.querySelector('[data-review-action="edit"]');
    if (edit) edit.disabled = select.value === select.dataset.proposedValue;
  });
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
  const queues = payload.research.classifications.queues || {};
  const humanReviews = payload.research.classifications.human_reviews || {};
  const replay = p.replay || {};
  const replayJobs = operational.classification_jobs || {};
  const reviewIntegrity = operational.classification_reviews || {};
  $("#classification-operations").innerHTML = detailRows([["Routing", p.routing?.mode || "single-provider"], ["Routing detail", p.routing?.detail || "No routing policy status available"], ["Review queue", `${queues.review_required_count ?? 0} record(s)`], ["Human reviews", `${humanReviews.record_count ?? 0} immutable record(s)`], ["Review integrity errors", reviewIntegrity.malformed_count ?? 0], ["Failed queue", `${queues.failed_count ?? 0} record(s)`], ["Replay jobs", replayJobs.job_count ?? 0], ["Replay job integrity errors", replayJobs.malformed_count ?? 0], ["Replay", replay.available ? "Available" : "Integration needed"], ["Replay detail", replay.detail || "No replay status available"]]);
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

function setView(name, moveFocus = false) {
  const view = ["overview", "research", "health", "settings"].includes(name) ? name : "overview";
  document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  document.querySelectorAll(".nav-link").forEach((link) => {
    const active = link.dataset.view === view;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  $("#current-section").textContent = ({ overview: "Overview", research: "Research data", health: "System health", settings: "Configuration" })[view];
  document.title = `${$("#current-section").textContent} · Polder Research`;
  if (moveFocus) $(`#${view}-title`)?.focus({ preventScroll: true });
  if (view === "settings" && !state.editorDirty) loadSettings().catch((error) => showError(error.message));
  if (view === "health") refresh();
}

async function loadSettings() {
  const data = await api("/api/config");
  state.config = data.config || {};
  state.revision = data.revision;
  state.savedYaml = data.config_yaml;
  state.editorDirty = false;
  $("#config-editor").value = data.config_yaml;
  $("#save-basics").disabled = Boolean(data.validation_error);
  if (data.validation_error) {
    $("#config-message").textContent = `Current configuration is invalid: ${data.validation_error}. Edit the YAML below and save a valid complete configuration.`;
    $("#settings-saved").textContent = "Configuration needs repair";
    $("#taxonomy-summary").textContent = "Taxonomy details are unavailable until the configuration is valid.";
    $("#typesafe-card").hidden = true;
    $("#laya-card").hidden = true;
    return;
  }
  $("#config-message").textContent = "";
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
  pill.textContent = !status.installed ? "Dependency missing" : status.inference_verified ? "Inference verified" : status.cached ? "Checkpoint cached · not loaded" : "Model not downloaded";
  pill.className = `credential-status${status.installed && status.inference_verified ? " ready" : ""}`;
  const messages = [];
  if (!status.installed) messages.push("Install the optional Laya dependency: pip install 'polder-research-pipeline[laya]'. Then restart this local server.");
  else if (status.job.status === "downloading") messages.push(`Preparing the ${status.job.model} checkpoint. The model downloads to the local Hugging Face cache and loads into this process.`);
  else if (status.job.status === "failed") messages.push(`Model setup failed: ${status.job.error || "No error details returned."}`);
  else if (status.inference_verified) messages.push(`${status.model} completed a successful local inference in this server process.`);
  else if (status.cached) messages.push(`${status.model} checkpoint is already cached${status.cache_path ? ` at ${status.cache_path}` : " locally"}, but this process has not verified inference. Select load to prepare it.`);
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
  const resultNode = $("#provider-test-result");
  resultNode.textContent = "Checking provider connectivity and a sample response…";
  resultNode.classList.remove("error");
  try {
    const result = await api("/api/providers/test", { method: "POST", body: JSON.stringify({ provider }) });
    resultNode.textContent = result.message;
    resultNode.classList.toggle("error", !result.ok);
    toast(result.message, !result.ok);
  } catch (error) { resultNode.textContent = error.message; resultNode.classList.add("error"); toast(error.message, true); }
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

function queuedDecision(classificationId, field) {
  const items = state.overview?.research?.classifications?.queues?.review_required || [];
  const item = items.find((candidate) => candidate.id === classificationId);
  return item?.field_decisions?.[field] ? { item, decision: item.field_decisions[field] } : null;
}

function selectedReviewValue(classificationId, field) {
  const select = document.querySelector(`[data-review-value="${CSS.escape(`${classificationId}:${field}`)}"]`);
  if (!select) return undefined;
  if (field.startsWith("tag_")) return select.value === "true";
  return select.value === "__null__" ? null : select.value;
}

async function saveReview(button) {
  const classificationId = button.dataset.classificationId;
  const field = button.dataset.field;
  const action = button.dataset.reviewAction;
  const reviewer = $("#reviewer-name")?.value.trim();
  const proposal = queuedDecision(classificationId, field);
  if (!reviewer) { toast("Enter your self-reported reviewer identity before recording a decision.", true); return; }
  if (!proposal) { toast("This proposal is no longer in the review queue. Refresh the dashboard.", true); return; }
  let value;
  if (action === "accept") value = proposal.decision.value;
  else if (action === "reject") value = field.startsWith("tag_") ? false : null;
  else value = selectedReviewValue(classificationId, field);
  button.disabled = true;
  try {
    const result = await api("/api/classifications/review", {
      method: "POST",
      body: JSON.stringify({ classification_id: classificationId, reviewer, resolutions: { [field]: { action, value } } }),
    });
    toast(`Saved immutable review ${result.review_id}.`);
    delete state.reviewDraft.values[`${classificationId}:${field}`];
    state.reviewDecisionDraft = Object.keys(state.reviewDraft.values).length > 0;
    await refresh();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

document.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", (event) => {
  event.preventDefault(); location.hash = link.dataset.view;
}));
window.addEventListener("hashchange", () => setView(location.hash.slice(1), true));
$("#refresh-button").addEventListener("click", refresh);
$("#health-refresh").addEventListener("click", refresh);
$("#provider-select").addEventListener("change", updateProviderCopy);
$("#save-basics").addEventListener("click", saveBasics);
$("#save-config").addEventListener("click", saveConfig);
$("#reload-config").addEventListener("click", () => {
  state.editorDirty = false;
  loadSettings().catch((error) => toast(error.message, true));
});
$("#save-key").addEventListener("click", () => saveSecret($("#typesafe-key").value));
$("#remove-key").addEventListener("click", () => saveSecret(null));
$("#test-jev").addEventListener("click", () => testProvider("jev"));
$("#test-laya").addEventListener("click", () => testProvider("laya"));
$("#download-laya").addEventListener("click", startDownload);
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-review-action]");
  if (button) saveReview(button);
});
$("#config-editor").addEventListener("input", () => {
  state.editorDirty = $("#config-editor").value !== state.savedYaml;
  $("#settings-saved").textContent = state.editorDirty ? "Unsaved YAML edits" : "Saved configuration";
  $("#save-basics").disabled = state.editorDirty;
});
document.addEventListener("input", (event) => {
  if (event.target.id === "reviewer-name") state.reviewDraft.reviewer = event.target.value;
});
document.addEventListener("change", (event) => {
  if (event.target.matches("[data-review-value]")) {
    state.reviewDraft.values[event.target.dataset.reviewValue] = event.target.value;
    state.reviewDecisionDraft = true;
    const edit = event.target.closest(".review-field")?.querySelector('[data-review-action="edit"]');
    if (edit) edit.disabled = event.target.value === event.target.dataset.proposedValue;
  }
});
document.addEventListener("toggle", (event) => {
  const candidate = event.target;
  if (!(candidate instanceof HTMLDetailsElement) || !candidate.matches("[data-review-candidate]")) return;
  if (candidate.open) state.expandedReviews.add(candidate.dataset.reviewCandidate);
  else state.expandedReviews.delete(candidate.dataset.reviewCandidate);
}, true);
window.addEventListener("beforeunload", (event) => {
  if (state.editorDirty || state.reviewDecisionDraft) {
    event.preventDefault();
    event.returnValue = "";
  }
});
setView(location.hash.slice(1) || "overview");
refresh();
setInterval(() => { if (document.visibilityState === "visible") refresh(); }, 30_000);
