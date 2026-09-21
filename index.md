---
type: moc
status: current
cssclasses:
  - dashboard-layout
tags:
  - knowledge-base
  - polder-research-pipeline
  - navigation
  - moc
---

```dataviewjs
// Polder Research Pipeline — research dashboard
// The repo IS the vault. All documentation lives here.
//
// Link rendering: dv.fileLink() returns a Dataview Link (plain data object),
// never a DOM node. It must go through dv.span(..., { container }) to render.

const container = dv.container.createDiv({ cls: "polder-dashboard animate-in" });

// --- helpers ---
const addLink = (parent, path, label) =>
  dv.span(dv.fileLink(path, false, label), { container: parent });

const tagsOf = (p) => {
  const t = p.tags;
  if (!t) return [];
  if (typeof t.array === "function") return t.array();
  return Array.from(t);
};

// Status → hue, matching the inbox palette so the dot colour reads at a glance.
const STATUS_HUE = {
  current: 160,
  draft: 50,
  stale: 0,
  superseded: 0,
  accepted: 210,
  proposed: 280,
  rejected: 0,
};
const statusHue = (s) => STATUS_HUE[String(s || "").toLowerCase()] ?? 200;

// --- persistence ---
const bannerKey = "polder-banner-title";
let bannerTitle = localStorage.getItem(bannerKey) || "PRP RESEARCH";
localStorage.setItem(bannerKey, bannerTitle);

// --- utils ---
const Utils = {
  _durable: null,

  greeting() {
    const h = new Date().getHours();
    if (h < 5) return "Late-night synthesis 🌙";
    if (h < 12) return "Morning survey ☀️";
    if (h < 18) return "Deep focus ⚡";
    return "End of day 🌌";
  },

  // Cached: several cards derive from the same durable-note universe.
  durablePages() {
    if (this._durable) return this._durable;
    this._durable = dv.pages('""').where(p => {
      const path = p.file.path;
      // Exclude inbox, templates, root readme, and protocol stubs.
      const isStub = path === "AGENTS.md"
                   || path === "CLAUDE.md"
                   || /^(skills)\/README\.md$/.test(path);
      return !path.startsWith("90-inbox/")
          && !path.startsWith("99-templates/")
          && path !== "README.md"
          && !isStub;
    });
    return this._durable;
  },

  inboxCounts() {
    return {
      raw:      Array.from(dv.pages('"90-inbox/raw"'))
                  .filter(p => p.file.name !== "README").length,
      proc:     dv.pages('"90-inbox/processing"').length,
      filed:    dv.pages('"90-inbox/archive/filed"').length,
      rejected: dv.pages('"90-inbox/archive/rejected"').length,
    };
  },

  // Age of the oldest unprocessed item, or null when the inbox is empty.
  inboxOldest() {
    const raw = Array.from(dv.pages('"90-inbox/raw"'))
      .map(p => p.file && p.file.mtime)
      .filter(Boolean);
    if (raw.length === 0) return null;
    return raw.reduce((a, b) => (a.toMillis() <= b.toMillis() ? a : b));
  },

  domains: [
    { code: "01-project",    label: "Project",    hue: 210 },
    { code: "02-research",   label: "Research",   hue: 160 },
    { code: "03-system",     label: "System",     hue: 280 },
    { code: "04-decisions",  label: "Decisions",  hue: 20  },
    { code: "05-operations", label: "Operations", hue: 50  },
    { code: "06-sources",    label: "Sources",    hue: 320 },
  ],

  // One pass over each domain — shared by the domain cards and the index-health card.
  domainStats() {
    return this.domains.map(d => {
      const indexPath = `${d.code}/README`;
      const pages = dv.pages(`"${d.code}"`);
      // The domain README is the MOC: a durable, linkable note in its own right.
      const notes = pages;
      const hasIndex = pages.where(p => p.file.path === `${indexPath}.md`).length > 0;
      const countStatus = (s) => notes.where(p => String(p.status).toLowerCase() === s).length;
      const note = (p) => p.file.name;
      return {
        ...d,
        total: pages.length,
        notes: notes.length,
        current: countStatus("current"),
        draft: countStatus("draft"),
        stale: countStatus("stale") + countStatus("superseded"),
        hasIndex,
        // Always link somewhere real: the MOC when it exists, else the first note.
        indexTarget: hasIndex
          ? indexPath
          : (notes.length ? Array.from(notes.sort(note, "asc"))[0].file.path : null),
      };
    });
  },

  freshest(n = 10) {
    return this.durablePages().sort(p => p.file.mtime, "desc").slice(0, n);
  },

  orphans() {
    // An orphan has no incoming links from any other note.
    // index.md is excluded — it links out, not in.
    return this.durablePages()
      .where(p => p.file.path !== "index.md" && (p.file.inlinks?.length ?? 0) === 0)
      .sort(p => p.file.name, "asc");
  },

  tagBreakdown() {
    const buckets = {};
    this.durablePages().forEach(p => {
      tagsOf(p).forEach(t => {
        const norm = String(t).toLowerCase().trim().replace(/^#/, "");
        if (!norm) return;
        buckets[norm] = (buckets[norm] || 0) + 1;
      });
    });
    return Object.entries(buckets).sort((a, b) => b[1] - a[1]).slice(0, 12);
  },

  staleNotes(thresholdDays = 90) {
    const cutoff = Date.now() - thresholdDays * 86400000;
    return this.durablePages()
      .where(p => p.file.mtime && p.file.mtime.toMillis() < cutoff)
      .sort(p => p.file.mtime, "asc")
      .slice(0, 5);
  },

  // Domain folder health (each numbered folder has a MOC note).
  surfaceHealth() {
    return this.domains.map(d => {
      const pages = dv.pages(`"${d.code}"`);
      return {
        folder: d.code,
        total: pages.length,
        hasReadme: pages.where(p => p.file.name === "README").length > 0,
        notes: pages.where(p => p.file.name !== "README").length,
      };
    });
  },

  // Newest mtime anywhere in the vault.
  lastUpdated() {
    const times = Array.from(dv.pages('""'))
      .map(p => p.file && p.file.mtime)
      .filter(Boolean);
    if (times.length === 0) return null;
    return times.reduce((a, b) => (a.toMillis() >= b.toMillis() ? a : b));
  },

  // Recent decisions (status: accepted, last 30d).
  recentDecisions(days = 30) {
    const cutoff = Date.now() - days * 86400000;
    return dv.pages('"04-decisions"')
      .where(p => p.file.mtime && p.file.mtime.toMillis() >= cutoff)
      .sort(p => p.file.mtime, "desc")
      .slice(0, 5);
  },

  // Research gaps: notes explicitly marked draft.
  researchGaps() {
    return this.durablePages()
      .where(p => String(p.status).toLowerCase() === "draft")
      .sort(p => p.file.name, "asc")
      .slice(0, 8);
  },

  // Manifest rows: read 90-inbox/manifest.md and tail its table.
  recentManifestRows(n = 5) {
    const f = app.vault.getAbstractFileByPath("90-inbox/manifest.md");
    if (!f) return [];
    const content = app.vault.read(f);
    const lines = content.split("\n");
    const rows = [];
    let header = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("|") && lines[i].includes("Item") && lines[i].includes("Status")) {
        header = i;
        break;
      }
    }
    if (header < 0) return [];
    for (let i = header + 2; i < lines.length && rows.length < n * 4; i++) {
      const line = lines[i];
      if (!line.startsWith("|")) break;
      const cells = line.split("|").map(c => c.trim()).filter(Boolean);
      if (cells.length >= 5) rows.push(cells);
    }
    return rows.slice(0, n);
  },

  // Vault-wide frontmatter hole count.
  frontmatterIssues() {
    let missing = 0;
    dv.pages('""').forEach(p => {
      if (!p.type || !p.status || !p.tags) missing++;
    });
    return missing;
  },
};

// ============== HERO ==============
const header = container.createDiv({ cls: "polder-header" });
const hero = header.createDiv({ cls: "polder-hero" });

const bannerText = hero.createDiv({ cls: "polder-banner-text", text: bannerTitle });
const titleRow = hero.createDiv({ cls: "polder-hero-title" });
const titleInput = titleRow.createEl("input", {
  cls: "polder-banner-input",
  attr: { type: "text", value: bannerTitle, "aria-label": "Dashboard banner title" }
});
titleInput.oninput = () => {
  bannerTitle = titleInput.value || "PRP RESEARCH";
  bannerText.textContent = bannerTitle;
  localStorage.setItem(bannerKey, bannerTitle);
};
hero.createDiv({ cls: "polder-greeting", text: Utils.greeting() });

const lastMtime = Utils.lastUpdated();
const stamp = (m) => m.toFormat("yyyy-MM-dd HH:mm");
if (lastMtime) hero.createDiv({ cls: "polder-last-updated", text: `Updated ${stamp(lastMtime)}` });

const stats = header.createDiv({ cls: "polder-hero-stats" });
const inbox = Utils.inboxCounts();
[
  { label: "NOTES",   value: Utils.durablePages().length },
  { label: "INBOX",   value: inbox.raw + inbox.proc },
  { label: "DOMAINS", value: Utils.domains.length },
  { label: "SOURCES", value: dv.pages('"06-sources"').length },
].forEach(({ label, value }) => {
  const cube = stats.createDiv({ cls: "polder-stat-cube" });
  cube.createDiv({
    cls: "polder-stat-value",
    text: String(value)
  });
  cube.createDiv({ cls: "polder-stat-label", text: label });
});

// ============== 12-COLUMN GRID ==============
const grid = container.createDiv({ cls: "polder-grid" });
const domains = Utils.domainStats();

// --- Row 1: domain cards, full width ---
const cardDomains = grid.createDiv({ cls: "span-12 polder-card" });
cardDomains.createDiv({ cls: "polder-card-title", text: "DOMAIN COVERAGE" });
const domainGrid = cardDomains.createDiv({ cls: "polder-domain-grid" });
domains.forEach(d => {
  const card = domainGrid.createDiv({ cls: "polder-domain-card", attr: { style: `--hue:${d.hue}` } });
  const head = card.createDiv({ cls: "polder-domain-head" });
  head.createDiv({ cls: "polder-domain-dot" });
  if (d.indexTarget) addLink(head, d.indexTarget, d.label);
  else head.createDiv({ cls: "polder-domain-name-static", text: d.label });
  card.createDiv({ cls: "polder-domain-code", text: d.code });
  card.createDiv({ cls: "polder-domain-total", text: String(d.total) });
  const parts = [`${d.current} current`, `${d.draft} draft`];
  if (d.stale) parts.push(`${d.stale} stale`);
  card.createDiv({ cls: "polder-domain-status", text: parts.join(" · ") });
});

// --- Row 2: recent activity (8) + inbox (4) ---
const colFresh = grid.createDiv({ cls: "span-8" });
const cardFresh = colFresh.createDiv({ cls: "polder-card" });
cardFresh.createDiv({ cls: "polder-card-title", text: "RECENT ACTIVITY" });
const freshList = cardFresh.createDiv({ cls: "polder-fresh-list" });
const fresh = Utils.freshest(10);
if (fresh.length === 0) {
  freshList.createDiv({ cls: "polder-hint", text: "No notes yet — the vault is freshly empty." });
} else {
  fresh.forEach(p => {
    const row = freshList.createDiv({ cls: "polder-fresh-row" });
    const link = row.createDiv({ cls: "polder-fresh-link" });
    addLink(link, p.file.path, p.file.name);
    const meta = row.createDiv({ cls: "polder-fresh-meta" });
    if (p.status) {
      const tag = meta.createDiv({ cls: "polder-status-tag", attr: { style: `--hue:${statusHue(p.status)}` } });
      tag.createDiv({ cls: "polder-status-dot" });
      tag.createDiv({ text: String(p.status) });
    }
    if (p.type) meta.createDiv({ cls: "polder-type-tag", text: String(p.type) });
    if (p.file.mtime) meta.createDiv({ cls: "polder-fresh-time", text: p.file.mtime.toFormat("yyyy-MM-dd") });
  });
}

const colInbox = grid.createDiv({ cls: "span-4" });
const cardInbox = colInbox.createDiv({ cls: "polder-card" });
cardInbox.createDiv({ cls: "polder-card-title", text: "INBOX STATUS" });
const inboxRow = cardInbox.createDiv({ cls: "polder-inbox-row" });
[
  { value: inbox.raw,      label: "raw",        hue: 200 },
  { value: inbox.proc,     label: "processing", hue: 50  },
  { value: inbox.filed,    label: "filed",      hue: 160 },
  { value: inbox.rejected, label: "rejected",   hue: 0   },
].forEach(({ value, label, hue }) => {
  const cell = inboxRow.createDiv({ cls: "polder-inbox-cell", attr: { style: `--hue:${hue}` } });
  cell.createDiv({ cls: "polder-inbox-value", text: String(value) });
  cell.createDiv({ cls: "polder-inbox-label", text: label });
});
const inboxCta = cardInbox.createDiv({ cls: "polder-inbox-cta" });
addLink(inboxCta, "90-inbox/README", "Open inbox →");
const oldest = Utils.inboxOldest();
if (oldest) {
  cardInbox.createDiv({ cls: "polder-inbox-age", text: `Oldest raw · ${stamp(oldest)}` });
}

// --- Row 3: vault health / top tags / review candidates ---
const orphansList = Utils.orphans();
const fmIssues = Utils.frontmatterIssues();
const cardOrphans = grid.createDiv({
  cls: `span-4 polder-card${orphansList.length > 0 || fmIssues > 0 ? " polder-card-alert" : ""}`
});
cardOrphans.createDiv({ cls: "polder-card-title", text: "VAULT HEALTH" });
const healthEl = cardOrphans.createDiv({ cls: "polder-orphan-list" });
healthEl.createDiv({
  cls: "polder-hint",
  text: `Orphans: ${orphansList.length} · Frontmatter gaps: ${fmIssues}`
});
if (orphansList.length > 0) {
  orphansList.slice(0, 6).forEach(p => {
    const row = healthEl.createDiv({ cls: "polder-orphan-row" });
    addLink(row, p.file.path, p.file.name);
    if (p.status) row.createDiv({ cls: "polder-orphan-status", text: String(p.status) });
  });
}

const cardTags = grid.createDiv({ cls: "span-4 polder-card" });
cardTags.createDiv({ cls: "polder-card-title", text: "TOP TAGS" });
const tagList = cardTags.createDiv({ cls: "polder-tag-list" });
const tags = Utils.tagBreakdown();
if (tags.length === 0) {
  tagList.createDiv({ cls: "polder-hint", text: "No tagged notes yet." });
} else {
  const maxCount = Math.max(...tags.map(t => t[1]));
  tags.forEach(([tag, count]) => {
    const row = tagList.createDiv({ cls: "polder-tag-row" });
    row.createDiv({ cls: "polder-tag-name", text: `#${tag}` });
    const bar = row.createDiv({ cls: "polder-tag-bar" });
    bar.createDiv({ cls: "polder-tag-bar-fill", attr: { style: `width:${Math.round(count / maxCount * 100)}%` } });
    row.createDiv({ cls: "polder-tag-count", text: String(count) });
  });
}

const cardStale = grid.createDiv({ cls: "span-4 polder-card" });
cardStale.createDiv({ cls: "polder-card-title", text: "REVIEW CANDIDATES (90d+)" });
const staleEl = cardStale.createDiv({ cls: "polder-stale-list" });
const stale = Utils.staleNotes();
if (stale.length === 0) {
  staleEl.createDiv({ cls: "polder-hint", text: "All notes are fresh." });
} else {
  stale.forEach(p => {
    const row = staleEl.createDiv({ cls: "polder-stale-row" });
    addLink(row, p.file.path, p.file.name);
    if (p.file.mtime) row.createDiv({ cls: "polder-stale-time", text: p.file.mtime.toFormat("yyyy-MM-dd") });
  });
}

// --- Row 4: self-evolution / research gaps / inbox manifest tail ---
const selfRow = container.createDiv({ cls: "polder-grid polder-grid-surfaces" });

const cardSelf = selfRow.createDiv({ cls: "span-4 polder-card" });
cardSelf.createDiv({ cls: "polder-card-title", text: "SELF-EVOLUTION" });
const selfList = cardSelf.createDiv({ cls: "polder-orphan-list" });
const gaps = Utils.researchGaps();
selfList.createDiv({
  cls: "polder-hint",
  text: `Drafts needing closure: ${gaps.length} · Recent decisions (30d): ${Utils.recentDecisions().length} · Sources: ${dv.pages('"06-sources"').length}`
});
gaps.slice(0, 5).forEach(p => {
  const row = selfList.createDiv({ cls: "polder-orphan-row" });
  addLink(row, p.file.path, p.file.name);
  row.createDiv({ cls: "polder-orphan-status", text: "draft" });
});

const cardRecDec = selfRow.createDiv({ cls: "span-4 polder-card" });
cardRecDec.createDiv({ cls: "polder-card-title", text: "RECENT DECISIONS" });
const decList = cardRecDec.createDiv({ cls: "polder-orphan-list" });
const recDec = Utils.recentDecisions();
if (recDec.length === 0) {
  decList.createDiv({ cls: "polder-hint", text: "No recent decisions yet." });
} else {
  recDec.forEach(p => {
    const row = decList.createDiv({ cls: "polder-orphan-row" });
    addLink(row, p.file.path, p.file.name);
    if (p.file.mtime) row.createDiv({ cls: "polder-orphan-status", text: p.file.mtime.toFormat("yyyy-MM-dd") });
  });
}

const cardManifest = selfRow.createDiv({ cls: "span-4 polder-card" });
cardManifest.createDiv({ cls: "polder-card-title", text: "INBOX MANIFEST TAIL" });
const manifestList = cardManifest.createDiv({ cls: "polder-orphan-list" });
const recManifest = Utils.recentManifestRows(5);
if (recManifest.length === 0) {
  manifestList.createDiv({ cls: "polder-hint", text: "No intake rows yet." });
} else {
  recManifest.forEach(cells => {
    const row = manifestList.createDiv({ cls: "polder-orphan-row" });
    row.createDiv({ cls: "polder-fresh-link", text: cells[0] || "" });
    row.createDiv({ cls: "polder-orphan-status", text: cells[3] || "" });
  });
}

// ============== SURFACE CARDS ==============
const surfaceRow = container.createDiv({ cls: "polder-grid polder-grid-surfaces" });

const implDirs = [
  ["Home",        "00-home/README",      "Navigation hub and operating guides."],
  ["Project",     "01-project/README",   "Goals, requirements, ethics, stable constraints."],
  ["Research",    "02-research/README",  "Distilled research: models, papers, tools, landscape."],
  ["System",      "03-system/README",    "Architecture, performance, transports, deployment."],
  ["Decisions",   "04-decisions/README", "Decision records, comparison matrices, risk assessments."],
  ["Operations",  "05-operations/README","Experiments, benchmarks, roadmaps, runbooks."],
  ["Resources",   "06-sources/README",   "Source catalog and evidence records."],
  ["Inbox",       "90-inbox/README",     "Raw drops, processing, filed/rejected archive."],
  ["Templates",   "99-templates/README", "Canonical note templates."],
];
const cardImpl = surfaceRow.createDiv({ cls: "span-6 polder-card" });
cardImpl.createDiv({ cls: "polder-card-title", text: "VAULT SURFACES" });
implDirs.forEach(([label, path, desc]) => {
  const row = cardImpl.createDiv({ cls: "polder-surface-row" });
  const linkEl = row.createDiv({ cls: "polder-surface-link" });
  addLink(linkEl, path, label);
  row.createDiv({ cls: "polder-surface-desc", text: desc });
});

const agentFiles = [
  ["Agent protocol",     "AGENTS",        "OpenWolf lifecycle, intake process, validators."],
  ["Claude protocol",    "CLAUDE",        "Simplified protocol for Claude sessions."],
  ["Curator skill",      "skills/obsidian-knowledgebase-curator/SKILL",   "Intake, distillation, evidence labels."],
  ["Curator readme",     "skills/obsidian-knowledgebase-curator/README",  "Curator entry point."],
  ["Inbox rules",        "90-inbox/README","Drop zones, manifests, immutability rules."],
  ["Inbox manifest",     "90-inbox/manifest","Queue and lifecycle tracker."],
];
const cardOps = surfaceRow.createDiv({ cls: "span-6 polder-card" });
cardOps.createDiv({ cls: "polder-card-title", text: "OPERATOR SURFACES" });
agentFiles.forEach(([label, path, desc]) => {
  const row = cardOps.createDiv({ cls: "polder-surface-row" });
  const linkEl = row.createDiv({ cls: "polder-surface-link" });
  addLink(linkEl, path, label);
  row.createDiv({ cls: "polder-surface-desc", text: desc });
});

// ============== TEMPLATES ==============
const cardTemplates = container.createDiv({ cls: "polder-card" });
cardTemplates.createDiv({ cls: "polder-card-title", text: "TEMPLATES" });
const tList = cardTemplates.createDiv({ cls: "polder-template-grid" });
dv.pages('"99-templates"').sort(p => p.file.name, "asc").forEach(p => {
  const card = tList.createDiv({ cls: "polder-template-card" });
  addLink(card, p.file.path, p.file.name);
  if (p.topic) card.createDiv({ cls: "polder-template-topic", text: String(p.topic) });
});

// ============== FOOTER ==============
const footer = container.createDiv({ cls: "polder-footer" });
footer.createDiv({
  cls: "polder-footer-text",
  text: `Polder Research Pipeline · ${Utils.durablePages().length} notes tracked`
      + (lastMtime ? ` · updated ${stamp(lastMtime)}` : ""),
});

```

## Operating rules

- The repo IS the Obsidian vault. The dashboard at `index.md` is the single documentation entry point. New durable notes go into `01-project`, `02-research`, `03-system`, `04-decisions`, `05-operations`, or `06-sources`. Raw material lands in `90-inbox/raw` and is processed by the intake guide.
- All in-vault links are wikilinks (`[[path|alias]]`). Cross-tree references use plain Markdown links.
- Required frontmatter: `type`, `status`, `tags`. Optional: `topic`, `created`, `updated`. See [[00-home/knowledge-base-guide|Knowledge base guide]] for the full contract.
- See [[00-home/research-intake-guide|Research intake guide]] for the lifecycle from raw material to durable note.

## Repo surfaces

Everything in this repository is part of the vault. The dashboard above renders live Dataview surfaces; the list below is a static index so these files are real nodes in Obsidian's graph and backlink pane.

### Vault

[[00-home/README|00-home]] · [[01-project/README|01-project]] · [[02-research/README|02-research]] · [[03-system/README|03-system]] · [[04-decisions/README|04-decisions]] · [[05-operations/README|05-operations]] · [[06-sources/README|06-sources]] · [[90-inbox/README|90-inbox]] · [[99-templates/README|99-templates]]

### Operator

[[AGENTS|AGENTS.md]] · [[CLAUDE|CLAUDE.md]] · `skills/obsidian-knowledgebase-curator/SKILL.md` · `skills/obsidian-knowledgebase-curator/README.md` · [[90-inbox/README|inbox rules]] · [[90-inbox/manifest|inbox manifest]]

### Guides and templates

[[00-home/vault-standards|standards]] · [[00-home/knowledge-base-guide|knowledge base guide]] · [[00-home/research-intake-guide|intake guide]] · [[99-templates/intake-record-template|intake record]] · [[99-templates/decision-record-template|decision record]] · [[99-templates/conflict-note-template|conflict note]] · [[99-templates/experiment-template|experiment]] · [[99-templates/source-entry-template|source entry]]
