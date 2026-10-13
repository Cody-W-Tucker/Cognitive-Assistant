// Centralized workspace record frontmatter parser.
//
// Single source of truth for `clusterId` + `provisionalSources` parsed from
// the actual changed workspace file. Both measurement
// (experience-workspace.js) and synthesis (synthesize.js) share this module so
// behavior cannot drift between duplicated hand-written subset parsers.
//
// Minimal safe YAML subset (no new dependency): supports the normal YAML
// structures expected for these two keys without inventing behavior:
//   clusterId: <plain or single/double-quoted scalar>
//   provisionalSources:
//     - <session id>          # block (YAML sequence) form
//     - "quoted id"
//   provisionalSources: [<a>, <b>]  # flow sequence form (quote-aware)
//   provisionalSources: <single scalar>  # kept as 1-item list (fails >=2 floor downstream)
// Unknown keys are ignored (not provenance). Anything malformed yields
// parseError with null linkage (never auto-assigned, never thrown).

function stripQuotes(value) {
  const v = String(value || "").trim();
  if (v.length >= 2 && ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))) {
    return v.slice(1, -1).trim();
  }
  return v;
}

function stripInlineComment(text) {
  // Remove a trailing ` # comment` outside single/double quotes (normal YAML).
  const s = String(text || "");
  let quote = null;
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    if (quote) {
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === "#" && i > 0 && /\s/.test(s[i - 1])) {
      return s.slice(0, i).trimEnd();
    }
  }
  return s;
}

function parseFlowList(rest) {
  const trimmed = String(rest || "").trim();
  if (!trimmed.startsWith("[")) return null;
  if (!trimmed.endsWith("]")) return { error: "unclosed flow list" };
  const inner = trimmed.slice(1, -1);
  const items = [];
  let current = "";
  let quote = null;
  for (let i = 0; i < inner.length; i += 1) {
    const ch = inner[i];
    if (quote) {
      current += ch;
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
      current += ch;
    } else if (ch === ",") {
      const item = stripQuotes(current.trim());
      if (item) items.push(item);
      current = "";
    } else {
      current += ch;
    }
  }
  if (quote) return { error: "unclosed quote in flow list" };
  const last = stripQuotes(current.trim());
  if (last) items.push(last);
  return { items };
}

/**
 * Parse structured YAML frontmatter from a workspace record.
 * Returns { clusterId, provisionalSources, body, parseError } where
 * clusterId/provisionalSources are null when missing/invalid.
 */
export function parseWorkspaceFrontmatter(text) {
  const raw = String(text || "");
  const lines = raw.split("\n");
  if (lines.length < 3 || lines[0].trim() !== "---") {
    return { clusterId: null, provisionalSources: null, body: raw, parseError: "missing frontmatter" };
  }
  let closeIndex = -1;
  for (let i = 1; i < lines.length; i += 1) {
    if (lines[i].trim() === "---") {
      closeIndex = i;
      break;
    }
  }
  if (closeIndex === -1) {
    return { clusterId: null, provisionalSources: null, body: raw, parseError: "unclosed frontmatter" };
  }
  const head = lines.slice(1, closeIndex);
  const body = lines.slice(closeIndex + 1).join("\n");
  let clusterId = null;
  let sources = null;
  let inList = false;
  for (const line of head) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const itemMatch = line.match(/^\s*-\s+(.*)$/);
    if (inList && itemMatch) {
      const item = stripQuotes(stripInlineComment(itemMatch[1].trim()));
      if (item) (sources || (sources = [])).push(item);
      continue;
    }
    inList = false;
    const kvMatch = trimmed.match(/^([A-Za-z0-9_]+)\s*:\s*(.*)$/);
    if (!kvMatch) {
      return { clusterId: null, provisionalSources: null, body, parseError: `malformed frontmatter line: ${trimmed.slice(0, 80)}` };
    }
    const key = kvMatch[1];
    const rest = stripInlineComment(kvMatch[2] || "").trim();
    if (key === "clusterId") {
      const value = stripQuotes(rest);
      if (!value) {
        clusterId = null;
      } else if (value.includes("[") || value.includes("]")) {
        return { clusterId: null, provisionalSources: null, body, parseError: "malformed clusterId" };
      } else {
        clusterId = value;
      }
    } else if (key === "provisionalSources") {
      if (!rest) {
        sources = [];
        inList = true;
      } else if (rest.startsWith("[")) {
        const parsed = parseFlowList(rest);
        if (parsed?.error) {
          return { clusterId: null, provisionalSources: null, body, parseError: parsed.error };
        }
        sources = [...(parsed?.items || [])];
      } else {
        const value = stripQuotes(rest);
        if (value.includes("[") || value.includes("]")) {
          return { clusterId: null, provisionalSources: null, body, parseError: "malformed sources" };
        }
        sources = value ? [value] : [];
      }
    } else {
      // Unknown frontmatter keys are ignored (not provenance).
    }
  }
  if (!clusterId || !String(clusterId).trim()) {
    return { clusterId: null, provisionalSources: null, body, parseError: "missing cluster id" };
  }
  const distinct = [...new Set((Array.isArray(sources) ? sources : []).map((s) => String(s).trim()).filter(Boolean))];
  if (distinct.length < 2) {
    return { clusterId: null, provisionalSources: null, body, parseError: "needs at least 2 distinct sources" };
  }
  return { clusterId: String(clusterId).trim(), provisionalSources: distinct, body, parseError: null };
}

/**
 * Narrow { clusterId, sources } view for synthesis call sites.
 * Nulls on missing/invalid (never auto-assigned).
 */
export function parseWorkspaceFileProvenance(text) {
  const parsed = parseWorkspaceFrontmatter(text);
  if (parsed.parseError) return { clusterId: null, sources: null };
  return { clusterId: parsed.clusterId, sources: parsed.provisionalSources };
}
