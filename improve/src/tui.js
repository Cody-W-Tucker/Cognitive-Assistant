// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Live progress view adapted from Backpass's stderr-only TUI. CA keeps the
// terminal contract: JSON remains the sole stdout payload and a non-TTY run is
// byte-for-byte headless.

const MIN_COLUMNS = 60;
const SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏";
const INTERVAL_MS = 80;
const STAGES = [
  ["discover", "collect samples"],
  ["analyze", "calculate loss"],
  ["fold", "aggregate gradients"],
  ["synthesize", "gradient descent"],
];

export function tuiEligible({ env = process.env, stderr = process.stderr } = {}) {
  return Boolean(
    stderr.isTTY &&
      !env.CI &&
      env.NO_COLOR === undefined &&
      env.TERM !== "dumb" &&
      (stderr.columns || 80) >= MIN_COLUMNS,
  );
}

export function initialState(meta = {}) {
  return {
    meta,
    discover: { status: "pending", transcripts: 0, perHarness: {} },
    analyze: { status: "pending", total: 0, pending: 0, done: 0, ok: 0, failed: 0, cached: 0, analyzer: null },
    fold: { status: "pending", clusters: 0, eligible: 0 },
    synthesize: { status: "pending", staged: 0, annotated: 0, edits: 0, note: "" },
  };
}

export function reduceEvent(state, event, data = {}, now = Date.now()) {
  void now;
  if (event === "discover:start") state.discover = { ...state.discover, status: "active", harnesses: data.harnesses || [] };
  if (event === "discover:done") state.discover = { ...state.discover, status: "done", transcripts: data.transcripts || 0, perHarness: data.perHarness || {} };
  if (event === "analyze:start") state.analyze = { ...state.analyze, status: "active", total: data.total || 0, pending: data.pending || 0, cached: data.cached || 0, analyzer: data.analyzer || null };
  if (event === "analyze:tick") state.analyze = { ...state.analyze, done: data.done || 0, ok: data.ok || 0, failed: data.failed || 0 };
  if (event === "analyze:done") state.analyze = { ...state.analyze, status: "done", done: data.done || 0, ok: data.ok || 0, failed: data.failed || 0, cached: data.cached || 0 };
  if (event === "fold:start") state.fold = { ...state.fold, status: "active" };
  if (event === "fold:done") state.fold = { ...state.fold, status: "done", clusters: data.clusters || 0, eligible: data.eligible || 0 };
  if (event === "synthesize:start") state.synthesize = { ...state.synthesize, status: "active" };
  if (event === "synthesize:done") state.synthesize = { ...state.synthesize, status: "done", staged: data.staged || 0, annotated: data.annotated || 0, edits: data.edits || 0, note: data.note || "" };
  return state;
}

function clip(text, width) {
  const chars = [...String(text)];
  return chars.length > width ? `${chars.slice(0, Math.max(0, width - 1)).join("")}…` : chars.join("");
}

function gauge(done, total, cells = 14) {
  const filled = total ? Math.min(cells, Math.round((done / total) * cells)) : 0;
  return `${"▰".repeat(filled)}${"▱".repeat(cells - filled)}`;
}

function stageSummary(key, state) {
  const s = state[key];
  if (key === "discover" && s.status === "done") return `${s.transcripts} transcript(s) · ${Object.entries(s.perHarness).map(([h, n]) => `${h} ${n}`).join(", ") || "no eligible sessions"}`;
  if (key === "analyze" && s.status === "active") return `${gauge(s.done, s.pending)} ${s.done}/${s.pending} · ${s.cached} reused · ${s.analyzer || "analyzer"}`;
  if (key === "analyze" && s.status === "done") return `${s.ok} ok · ${s.failed} failed · ${s.cached} reused`;
  if (key === "fold" && s.status === "done") return `${s.clusters} recurrence cluster(s) · ${s.eligible} eligible`;
  if (key === "synthesize" && s.status === "done") return `${s.edits} candidate edit(s) · ${s.annotated}/${s.staged} annotated`;
  if (s.status === "active") return "working…";
  return "";
}

export function renderFrame(state, { width = 80, now = Date.now(), spin = SPINNER[Math.floor(now / INTERVAL_MS) % SPINNER.length] } = {}) {
  const cols = Math.max(MIN_COLUMNS, Math.min(width, 110));
  const inner = cols - 4;
  const border = "─".repeat(cols - 2);
  const lines = [`╭${border}╮`];
  const title = `∇ cognitive assistant · improvement pass · since ${state.meta.since || "30d"}`;
  lines.push(`│ ${clip(title, inner).padEnd(inner)} │`);
  lines.push(`╰${border}╯`);
  for (const [key, label] of STAGES) {
    const status = state[key].status;
    const mark = status === "done" ? "✓" : status === "active" ? spin : "○";
    lines.push(clip(` ${mark} ${label.padEnd(20)} ${stageSummary(key, state)}`, cols));
  }
  const active = STAGES.find(([key]) => state[key].status === "active");
  if (active) lines.push("", clip(`── ${active[1]} · private state only; stdout remains JSON ${"─".repeat(cols)}`, cols));
  return lines;
}

export function startTui(meta, { stderr = process.stderr } = {}) {
  if (!tuiEligible({ stderr })) return null;
  const state = initialState(meta);
  let painted = 0;
  let stopped = false;
  const paint = () => {
    if (stopped) return;
    const lines = renderFrame(state, { width: stderr.columns || 80 });
    let out = painted ? `\x1b[${painted}A\r` : "";
    for (const line of lines) out += `\x1b[2K${line}\n`;
    if (painted > lines.length) out += "\x1b[0J";
    stderr.write(out);
    painted = lines.length;
  };
  const timer = setInterval(paint, INTERVAL_MS);
  stderr.write("\x1b[?25l");
  paint();
  return {
    event(event, data) { reduceEvent(state, event, data); paint(); },
    stop() {
      if (stopped) return;
      stopped = true;
      clearInterval(timer);
      if (painted) stderr.write(`\x1b[${painted}A\r\x1b[0J`);
      stderr.write("\x1b[?25h");
    },
  };
}
