import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

import { renderPrompt, SELF_SESSION_SENTINEL } from "../src/prompts.js";
import {
  synthesizeCandidates,
  buildSynthesisPrompt,
  validateCandidate,
  validateChangePlan,
  synthesizeWithAcpx,
  renderRejectionsForPrompt,
  isSuppressedByRejection,
  BODY_MAX_CHARS,
} from "../src/synthesize.js";
import { persistPrompt } from "../src/analyze.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SYNTH_MD = path.join(HERE, "..", "prompts", "synthesis.md");
const NOTICE = path.join(HERE, "..", "LICENSE.NOTICE");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-"));
}

function ledger() {
  return {
    version: 1,
    minGapEvidence: 2,
    clusters: [
      {
        id: "g-aaa",
        proposedInstruction: "Bootstrap context once",
        representativeQuote: "sessions re-derive project context from scratch",
        mistake: "sessions re-derive project context from scratch",
        sources: ["s1", "s2"],
        count: 2,
        eligible: true,
        perSource: {
          s1: { quote: "sessions re-derive project context from scratch", mistake: "m" },
          s2: { quote: "sessions re-derive project context from scratch", mistake: "m" },
        },
      },
    ],
  };
}

function evidenceIndex() {
  return new Map([
    ["s1", [{ quote: "sessions re-derive project context from scratch", effect: "e1" }]],
    ["s2", [{ quote: "sessions re-derive project context from scratch", effect: "e2" }]],
  ]);
}

function candidate(overrides = {}) {
  return {
    id: "e1",
    kind: "add",
    title: "Bootstrap context once",
    rationale: "sessions re-derive project context from scratch",
    instructions: ["Bootstrap context once"],
    record: {
      id: "exp-x-a1b2c3d4e5f6",
      title: "Bootstrap context once",
      body: "Recurring gap seen in 2 session(s): sessions re-derive project context from scratch",
      sources: ["s1", "s2"],
      clusterId: "g-aaa",
      evidence: [
        { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s1", effect: "m" },
        { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s2", effect: "m" },
      ],
      counterevidence: "none observed",
      compilerImplication: "compiler appends this record to the experience block",
    },
    evidence: [
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s1", effect: "m" },
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s2", effect: "m" },
    ],
    counterevidence: "none observed",
    compilerImplication: "compiler appends this record to the experience block",
    stagedArtifact: "artifact",
    diff: "diff",
    ...overrides,
  };
}

describe("synthesis.md narrow-plan contract (Backpass src/prompts/synthesis.md @ 0268201)", () => {
  it("maps exact upstream provenance in LICENSE.NOTICE (prompt carries no license comments)", () => {
    const notice = fs.readFileSync(NOTICE, "utf8");
    assert.ok(notice.includes("Backpass"));
    assert.ok(notice.includes("0268201"));
    assert.ok(notice.includes("improve/prompts/synthesis.md"));
    assert.ok(notice.includes("src/prompts/synthesis.md"));
    assert.ok(notice.includes("src/prompts/annotate.md"));
    assert.ok(notice.includes("https://github.com/kunchenguid/backpass"));
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(!text.includes("Backpass"), "prompt body carries no license comments");
    assert.ok(!text.includes("0268201"), "prompt body carries no pinned commit");
  });

  it("declares exactly the supported placeholders and nothing else", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    const tokens = [...text.matchAll(/\{\{([A-Za-z0-9_]+)\}\}/g)].map((m) => m[1]);
    assert.deepEqual([...new Set(tokens)].sort(), [
      "EVIDENCE",
      "HARNESS_SUMMARY",
      "REJECTIONS",
      "RUN_NOTE",
      "SOUL_SHA256",
      "SOUL_SNAPSHOT",
      "TRANSCRIPT_COUNT",
    ]);
  });

  it("does not bake in the sentinel", () => {
    assert.ok(!fs.readFileSync(SYNTH_MD, "utf8").includes("ca-improve:self-session"));
  });

  it("contracts edit-only workspace edits; no JSON plan contract, annotation owns durable fields", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(/edit-only|edit only/i.test(text), "synthesis prompt must declare edit-only workspace edits");
    assert.ok(/workspace/i.test(text), "synthesis prompt must mention workspace");
    assert.ok(!/change plan/i.test(text), "synthesis prompt must not contract a JSON change plan");
    assert.ok(!/"plans"/.test(text) && !/\bplans\s*:/i.test(text), "synthesis prompt must not contract a plans JSON key");
    // Mandated provenance YAML frontmatter contract: workspace files carry
    // ONLY clusterId + provisionalSources as structured frontmatter (not JSON).
    assert.ok(/clusterId/.test(text), "synthesis prompt must mandate clusterId frontmatter provenance");
    assert.ok(/provisionalSources/.test(text), "synthesis prompt must mandate provisionalSources frontmatter provenance");
    assert.ok(/frontmatter[\s\S]{0,400}ONLY\s+`?clusterId`?\s+and\s+`?provisionalSources`?/i.test(text), "synthesis prompt must restrict frontmatter to ONLY the two provenance keys");
    assert.ok(!/provisionalIntent/.test(text), "synthesis prompt must not contract provisionalIntent (only the two mandated frontmatter keys)");
    // Edit turn still requires structured frontmatter per record and keeps
    // annotation as the sole full-record origin.
    assert.ok(/frontmatter/i.test(text), "synthesis prompt must require structured YAML frontmatter");
    assert.ok(/at least 2 distinct session/i.test(text), "synthesis prompt must require >=2 distinct session ids");
    // Synthesis never authors final durable fields; annotation does.
    assert.ok(/never.*(record|final)|annotation.*(sole|origin)/is.test(text));
    assert.ok(/counterevidence/i.test(text) || /compilerImplication/i.test(text));
  });

  it("contracts staged artifact/diff from annotated finals, workspace-only edits, apply as sole writer", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(/staged artifact/i.test(text) && /diff/i.test(text));
    assert.ok(/synthesis-workspace/i.test(text), "synthesis prompt must confine edits to synthesis-workspace");
    assert.ok(/never.*(SOUL|tracked|live|Hermes)|no .*SOUL/i.test(text));
    assert.ok(/apply.*sole|sole.*writer|not authoritative|pre-apply|until.*appl/i.test(text));
  });
});

describe("synthesis render + persistence (exact)", () => {
  it("renderPrompt keeps sentinel FIRST", () => {
    const out = renderPrompt("synthesis", {
      EVIDENCE: "ev",
      REJECTIONS: "(none)",
      TRANSCRIPT_COUNT: "2",
      HARNESS_SUMMARY: "pi 2",
      RUN_NOTE: "note",
      SOUL_SNAPSHOT: "soul snapshot",
      SOUL_SHA256: "abc123",
    });
    assert.ok(out.startsWith(`${SELF_SESSION_SENTINEL}\n`));
    assert.ok(out.includes("ev"));
  });

  it("fails strict on missing/unused placeholders", () => {
    assert.throws(
      () =>
        renderPrompt("synthesis", {
          EVIDENCE: "e",
          REJECTIONS: "r",
          TRANSCRIPT_COUNT: "1",
          HARNESS_SUMMARY: "h",
          SOUL_SNAPSHOT: "soul snapshot",
          SOUL_SHA256: "abc123",
        }),
      /RUN_NOTE/,
    );
  });

  it("persists rendered synthesis prompt privately with run/stage metadata", () => {
    const stateDir = tmpDir();
    const prompt = buildSynthesisPrompt(ledger(), {
      evidenceIndex: evidenceIndex(),
      runNote: "n",
      soulSnapshot: "soul snapshot",
      soulSha256: "abc123",
    });
    const file = persistPrompt(stateDir, {
      runId: "run-SY1",
      transcriptId: "synthesis",
      harness: "stage",
      prompt,
      stage: "synthesis",
    });
    assert.ok(file.endsWith("run-SY1__synthesis.md"));
    assert.ok(fs.readFileSync(file, "utf8").startsWith(`${SELF_SESSION_SENTINEL}\n`));
    const meta = JSON.parse(
      fs.readFileSync(path.join(stateDir, "prompts", "run-SY1__synthesis.json"), "utf8"),
    );
    assert.equal(meta.stage, "synthesis");
    assert.equal(meta.runId, "run-SY1");
    if (process.platform !== "win32") {
      assert.equal(fs.statSync(file).mode & 0o777, 0o600);
    }
  });

  it("prior rejections render into the prompt", () => {
    const text = renderRejectionsForPrompt([
      { edit: "e1", reason: "too-narrow", title: "Old title" },
    ]);
    assert.ok(text.includes("e1"));
    assert.ok(text.includes("too-narrow"));
    const empty = renderRejectionsForPrompt([]);
    assert.ok(/none/i.test(empty));
  });
});

describe("mock deterministic synthesis path (narrow plans, reviewable, no real calls)", () => {
  it("synthesizeCandidates produces narrow plans with no invoke and no final record", () => {
    const plans = synthesizeCandidates(ledger(), { evidenceIndex: evidenceIndex(), soulBaseline: "" });
    assert.equal(plans.length, 1);
    assert.equal(plans[0].clusterId, "g-aaa");
    assert.ok(String(plans[0].provisionalIntent).length > 0);
    assert.deepEqual([...plans[0].provisionalSources].sort(), ["s1", "s2"]);
    for (const forbidden of ["record", "evidence", "title", "body", "counterevidence", "compilerImplication", "stagedArtifact", "diff"]) {
      assert.equal(plans[0][forbidden], undefined, `plan must not carry ${forbidden}`);
    }
  });

  it("narrow plans validate as plans; final fields belong to annotation only", () => {
    const plans = synthesizeCandidates(ledger(), { evidenceIndex: evidenceIndex() });
    assert.equal(validateChangePlan(plans[0], { ledger: ledger() }).ok, true);
    // A plan carrying a final record is invalid.
    assert.equal(validateChangePlan({ ...plans[0], record: { title: "x" } }, { ledger: ledger() }).ok, false);
  });
});

describe("strict candidate validation (production acpx)", () => {
  it("accepts a fully-evidenced candidate", () => {
    const res = validateCandidate(candidate(), { ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.equal(res.ok, true);
  });

  it("rejects unknown evidence source ids", () => {
    const bad = candidate({
      evidence: [{ polarity: "negative", text: "sessions re-derive project context from scratch", source: "ghost" }],
    });
    bad.record = { ...bad.record, sources: ["ghost"], evidence: bad.evidence };
    const res = validateCandidate(bad, { ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.equal(res.ok, false);
  });

  it("rejects paraphrased (non-exact) quotes", () => {
    const bad = candidate({
      evidence: [{ polarity: "negative", text: "sessions rederive context", source: "s1" }],
    });
    bad.record = { ...bad.record, evidence: bad.evidence };
    const res = validateCandidate(bad, { ledger: ledger(), evidenceIndex: evidenceIndex() });
    assert.equal(res.ok, false);
  });

  it("rejects missing title/counterevidence/compilerImplication and overlong body", () => {
    assert.equal(
      validateCandidate(candidate({ record: { ...candidate().record, title: "" } }), {
        ledger: ledger(),
        evidenceIndex: evidenceIndex(),
      }).ok,
      false,
    );
    assert.equal(
      validateCandidate(candidate({ record: { ...candidate().record, counterevidence: "" } }), {
        ledger: ledger(),
        evidenceIndex: evidenceIndex(),
      }).ok,
      false,
    );
    assert.equal(
      validateCandidate(candidate({ record: { ...candidate().record, compilerImplication: "" } }), {
        ledger: ledger(),
        evidenceIndex: evidenceIndex(),
      }).ok,
      false,
    );
    const long = candidate();
    long.record = { ...long.record, body: "x".repeat(BODY_MAX_CHARS + 1) };
    assert.equal(
      validateCandidate(long, { ledger: ledger(), evidenceIndex: evidenceIndex() }).ok,
      false,
    );
  });
});

describe("synthesizeWithAcpx (production only, narrow plans, fail-closed)", () => {
  function plan(overrides = {}) {
    return {
      clusterId: "g-aaa",
      provisionalIntent: "Bootstrap context once",
      provisionalSources: ["s1", "s2"],
      ...overrides,
    };
  }
  function validWorkspaceBody() {
    return `---\nclusterId: g-aaa\nprovisionalSources:\n  - s1\n  - s2\n---\n# Bootstrap context once\n\nsessions re-derive project context from scratch\n`;
  }
  it("validates acpx plans and returns narrow plans only (no final record)", () => {
    // EDIT-ONLY: durable plans come from measured workspace files, never JSON alone.
    const stateDir = tmpDir();
    const ws = `${stateDir}/synthesis-workspace`;
    fs.mkdirSync(ws, { recursive: true });
    fs.writeFileSync(`${ws}/e1.md`, validWorkspaceBody(), "utf8");
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [{ ...plan(), id: "e1" }] }),
      workspace: ws,
      stateDir,
    });
    assert.equal(out.failed, undefined);
    assert.equal(out.edits.length, 1);
    assert.equal(out.edits[0].id, "e1");
    assert.equal(out.edits[0].clusterId, "g-aaa");
    for (const forbidden of ["record", "evidence", "title", "body", "counterevidence", "compilerImplication", "stagedArtifact", "diff"]) {
      assert.equal(out.edits[0][forbidden], undefined, `synth plan must not carry ${forbidden}`);
    }
  });

  it("JSON-only plans with no workspace changes fail closed (never durable)", () => {
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [plan()] }),
    });
    assert.deepEqual(out.edits, []);
    assert.ok(out.failed);
  });

  it("workspace edits with no JSON plan still proceed via measured IDs", () => {
    const stateDir = tmpDir();
    const ws = `${stateDir}/synthesis-workspace`;
    fs.mkdirSync(ws, { recursive: true });
    fs.writeFileSync(`${ws}/e9.md`, validWorkspaceBody(), "utf8");
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", result: { plans: [] } }),
    });
    // No workspace passed -> cannot observe the file; fail closed.
    assert.deepEqual(out.edits, []);
    const out2 = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", result: { plans: [] } }),
      workspace: ws,
      stateDir,
    });
    assert.equal(out2.edits.length, 1);
    assert.equal(out2.edits[0].id, "e9");
  });

  it("drops plans carrying authoritative final fields; fails closed when none remain", () => {
    const leaked = { ...plan(), record: { title: "leaked" } };
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [leaked] }),
    });
    assert.deepEqual(out.edits, []);
    assert.ok(out.failed);
    assert.ok(typeof out.note === "string" && /no valid|fail/i.test(out.note));
  });

  it("drops invalid plans (unknown cluster); fails closed with visible note", () => {
    const bad = plan({ clusterId: "g-ghost" });
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [bad] }),
    });
    assert.deepEqual(out.edits, []);
    assert.ok(out.failed);
    assert.ok(typeof out.note === "string" && /no valid|fail/i.test(out.note));
  });

  it("fails closed with visible note and no edits on acpx failure", () => {
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "failed", error: "boom" }),
    });
    assert.deepEqual(out.edits, []);
    assert.ok(out.failed);
    assert.ok(/fail/i.test(out.note));
  });

  it("persists the synthesis prompt with run/stage metadata", () => {
    const stateDir = tmpDir();
    synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [] }),
      stateDir,
      runId: "run-SY2",
    });
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-SY2__synthesis.md")));
  });

  it("makes no real acpx calls (injectable invoke only)", () => {
    let seen = null;
    synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: (args) => {
        seen = args;
        return { status: "ok", plans: [] };
      },
    });
    assert.ok(seen.prompt.includes("ca-improve:self-session"));
  });

  it("does not suppress at synthesis; suppression operates on annotated finals downstream", () => {
    const rejections = [{ edit: "e9", title: "Bootstrap context once", clusterId: "g-aaa", sources: ["s1", "s2"] }];
    const stateDir = tmpDir();
    const ws = `${stateDir}/synthesis-workspace`;
    fs.mkdirSync(ws, { recursive: true });
    fs.writeFileSync(`${ws}/e1.md`, validWorkspaceBody(), "utf8");
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [{ ...plan(), id: "e1" }] }),
      rejections,
      workspace: ws,
      stateDir,
    });
    assert.equal(out.edits.length, 1);
  });
});

describe("rejected-identity suppression", () => {
  const rejections = [{ edit: "e9", title: "Bootstrap context once", clusterId: "g-aaa", sources: ["s1", "s2"] }];

  it("suppresses the same identity on equal evidence", () => {
    assert.equal(
      isSuppressedByRejection(candidate(), rejections, { evidenceIndex: evidenceIndex() }),
      true,
    );
  });

  it("allows higher evidence (more sessions) through", () => {
    const higher = candidate();
    higher.record = { ...higher.record, sources: ["s1", "s2", "s3"] };
    higher.evidence = [
      ...higher.evidence,
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s3", effect: "m" },
    ];
    const idx = new Map([
      ...evidenceIndex(),
      ["s3", [{ quote: "sessions re-derive project context from scratch", effect: "e3" }]],
    ]);
    assert.equal(isSuppressedByRejection(higher, rejections, { evidenceIndex: idx }), false);
  });

  it("allows new evidence (unseen source) through", () => {
    const idx = new Map([
      ["s1", [{ quote: "sessions re-derive project context from scratch", effect: "e1" }]],
      ["s9", [{ quote: "sessions re-derive project context from scratch", effect: "e9" }]],
    ]);
    const novel = candidate();
    novel.record = { ...novel.record, sources: ["s1", "s9"] };
    novel.evidence = [
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s1", effect: "m" },
      { polarity: "negative", text: "sessions re-derive project context from scratch", source: "s9", effect: "m" },
    ];
    assert.equal(isSuppressedByRejection(novel, rejections, { evidenceIndex: idx }), false);
  });

  it("annotation finals suppress rejected identities but keep novel ones (suppression on finals only)", async () => {
    const { applyRejectionSuppression } = await import("../src/annotate.js");
    const led = ledger();
    led.clusters.push({
      id: "g-new",
      proposedInstruction: "Brand new",
      representativeQuote: "sessions re-derive project context from scratch",
      mistake: "sessions re-derive project context from scratch",
      sources: ["s1", "s2"],
      count: 2,
      eligible: true,
      perSource: {
        s1: { quote: "sessions re-derive project context from scratch", mistake: "m" },
        s2: { quote: "sessions re-derive project context from scratch", mistake: "m" },
      },
    });
    const same = { ...candidate(), annotation: { verdict: "keep", record: candidate().record } };
    const novel = candidate();
    novel.record = { ...novel.record, title: "Brand new", clusterId: "g-new", sources: ["s1", "s2"] };
    const novelFinal = { ...novel, annotation: { verdict: "keep", record: novel.record } };
    assert.equal(applyRejectionSuppression([same], rejections).length, 0);
    assert.equal(applyRejectionSuppression([novelFinal], rejections).length, 1);
  });
});

describe("review findings: quote/session binding + cluster linkage + suppression + strict output", () => {
  function boundLedger() {
    return {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-aaa",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: "alpha quote one",
          mistake: "m-aaa",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: {
            s1: { quote: "alpha quote one", mistake: "m-aaa" },
            s2: { quote: "beta quote two", mistake: "m-aaa" },
          },
        },
        {
          id: "g-inelig",
          proposedInstruction: "Ineligible thing",
          representativeQuote: "zzz quote",
          mistake: "m-zzz",
          sources: ["sx"],
          count: 1,
          eligible: false,
          perSource: { sx: { quote: "zzz quote", mistake: "m-zzz" } },
        },
      ],
    };
  }
  function boundIndex() {
    return new Map([
      ["s1", [{ quote: "alpha quote one", effect: "e1" }]],
      ["s2", [{ quote: "beta quote two", effect: "e2" }]],
      ["s9", [{ quote: "outsider quote nine", effect: "e9" }]],
    ]);
  }
  function boundCandidate(overrides = {}) {
    const base = {
      id: "e1",
      kind: "add",
      title: "Bootstrap context once",
      rationale: "m-aaa",
      instructions: ["Bootstrap context once"],
      record: {
        id: "exp-x",
        title: "Bootstrap context once",
        body: "Recurring gap seen in 2 session(s): m-aaa",
        sources: ["s1", "s2"],
        clusterId: "g-aaa",
        evidence: [
          { polarity: "negative", text: "alpha quote one", source: "s1", effect: "m-aaa" },
          { polarity: "negative", text: "beta quote two", source: "s2", effect: "m-aaa" },
        ],
        counterevidence: "none observed",
        compilerImplication: "compiler appends this record to the experience block",
      },
      evidence: [
        { polarity: "negative", text: "alpha quote one", source: "s1", effect: "m-aaa" },
        { polarity: "negative", text: "beta quote two", source: "s2", effect: "m-aaa" },
      ],
      counterevidence: "none observed",
      compilerImplication: "compiler appends this record to the experience block",
      ...overrides,
    };
    return base;
  }

  it("RED: swapped quote/source binding fails (exact quote must belong to cited source)", () => {
    const bad = boundCandidate();
    bad.evidence = [
      { polarity: "negative", text: "beta quote two", source: "s1", effect: "m-aaa" },
      { polarity: "negative", text: "alpha quote one", source: "s2", effect: "m-aaa" },
    ];
    bad.record = { ...bad.record, evidence: bad.evidence };
    assert.equal(validateCandidate(bad, { ledger: boundLedger(), evidenceIndex: boundIndex() }).ok, false);
  });

  it("RED: record sources must exactly match evidence sources", () => {
    const bad = boundCandidate();
    bad.record = { ...bad.record, sources: ["s1", "s2"] };
    bad.evidence = [
      { polarity: "negative", text: "alpha quote one", source: "s1", effect: "m-aaa" },
      { polarity: "negative", text: "alpha quote one", source: "s1", effect: "m-aaa" },
    ];
    bad.record = { ...bad.record, evidence: bad.evidence };
    assert.equal(validateCandidate(bad, { ledger: boundLedger(), evidenceIndex: boundIndex() }).ok, false);
  });

  it("RED: unknown clusterId fails", () => {
    const bad = boundCandidate();
    bad.record = { ...bad.record, clusterId: "g-ghost" };
    assert.equal(validateCandidate(bad, { ledger: boundLedger(), evidenceIndex: boundIndex() }).ok, false);
  });

  it("RED: ineligible cluster cannot satisfy the floor", () => {
    const bad = boundCandidate();
    bad.record = {
      ...bad.record,
      clusterId: "g-inelig",
      sources: ["sx", "s1"],
      evidence: [
        { polarity: "negative", text: "zzz quote", source: "sx", effect: "m-zzz" },
        { polarity: "negative", text: "alpha quote one", source: "s1", effect: "e1" },
      ],
    };
    bad.evidence = bad.record.evidence;
    assert.equal(validateCandidate(bad, { ledger: boundLedger(), evidenceIndex: boundIndex() }).ok, false);
  });

  it("RED: global evidenceIndex source outside the cluster cannot satisfy the floor", () => {
    const bad = boundCandidate();
    bad.record = {
      ...bad.record,
      sources: ["s1", "s9"],
      evidence: [
        { polarity: "negative", text: "alpha quote one", source: "s1", effect: "m-aaa" },
        { polarity: "negative", text: "outsider quote nine", source: "s9", effect: "e9" },
      ],
    };
    bad.evidence = bad.record.evidence;
    assert.equal(validateCandidate(bad, { ledger: boundLedger(), evidenceIndex: boundIndex() }).ok, false);
  });

  it("RED: legacy rejection rows without identity never suppress", () => {
    assert.equal(isSuppressedByRejection(boundCandidate(), [{ edit: "e9", reason: "too-narrow" }]), false);
  });

  it("RED: rejection rows with empty sources never suppress (but still render)", () => {
    const rej = [{ edit: "e9", title: "Bootstrap context once", clusterId: "g-aaa", sources: [] }];
    assert.equal(isSuppressedByRejection(boundCandidate(), rej), false);
    assert.ok(renderRejectionsForPrompt(rej).includes("g-aaa"));
  });

  it("RED: model {edits:[...]}/{candidates:[...]} full-record shapes are rejected (strict {plans:[...]} only)", () => {
    const rec = boundCandidate().record;
    for (const result of [{ edits: [{ record: rec }] }, { candidates: [{ record: rec }] }]) {
      const out = synthesizeWithAcpx(boundLedger(), {
        evidenceIndex: boundIndex(),
        invoke: () => ({ status: "ok", result }),
      });
      assert.deepEqual(out.edits, []);
      assert.ok(out.failed);
    }
  });

  it("RED: malformed model shapes fail closed", () => {
    for (const result of [{}, { plans: "nope" }, { plans: [{ clusterId: "" }] }, { candidates: [{ record: { title: "" } }] }]) {
      const out = synthesizeWithAcpx(boundLedger(), {
        evidenceIndex: boundIndex(),
        invoke: () => ({ status: "ok", result }),
      });
      assert.deepEqual(out.edits, [], JSON.stringify(result));
      assert.ok(out.failed, JSON.stringify(result));
    }
  });
});

describe("synthesis invocation/write containment + mock workspace author", () => {
  it("rejects a workspace outside the expected stateDir/private root fail-closed", async () => {
    const { synthesizeWithAcpx, assertContainedSynthesisWorkspace } = await import("../src/synthesize.js");
    const stateDir = tmpDir();
    assert.throws(() => assertContainedSynthesisWorkspace("/tmp/evil-workspace", stateDir), /denied|outside|private/);
    assert.throws(() => assertContainedSynthesisWorkspace("/tmp/evil-workspace/synthesis-workspace-evil", null), /denied|outside|private/);
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", plans: [{ clusterId: "g-aaa", provisionalIntent: "x", provisionalSources: ["s1", "s2"] }] }),
      stateDir,
      runId: "run-DENY1",
      workspace: "/tmp/evil-workspace",
      cwd: "/tmp/evil-workspace",
    });
    assert.deepEqual(out.edits, []);
    assert.ok(out.failed, "escape must fail closed with no plans");
    assert.ok(/denied|refused|outside/i.test(out.note || out.failed || ""));
  });

  it("mock synthesis authors the private workspace before measurement (deterministic created)", async () => {
    const { synthesizeCandidates, applyMockSynthesisWorkspace } = await import("../src/synthesize.js");
    const { prepareExperienceWorkspace, measureExperienceWorkspace } = await import("../src/experience-workspace.js");
    const stateDir = tmpDir();
    // True created/modified/deleted fixture owned by the test itself (no pipeline synthetic records):
    // two baseline records, then mock synthesis authors the created plan alongside a real modify + delete.
    const ws = prepareExperienceWorkspace({ stateDir, records: [
      { id: "base-keep", text: "baseline" },
      { id: "base-gone", text: "bye" },
    ] });
    const plans = synthesizeCandidates(ledger(), { evidenceIndex: evidenceIndex(), workspace: ws.root, stateDir });
    assert.equal(plans.length, 1);
    // Mock path is the workspace author: apply the plan record so measurement observes a real change.
    applyMockSynthesisWorkspace(plans, ws.root, { stateDir });
    fs.writeFileSync(path.join(ws.root, "base-keep.md"), "baseline\namended\n", "utf8");
    fs.rmSync(path.join(ws.root, "base-gone.md"), { force: true });
    const measured = measureExperienceWorkspace(ws);
    const kinds = new Set(measured.map((m) => m.kind));
    assert.ok(kinds.has("created"), "mock author must create the plan record");
    assert.ok(kinds.has("modified"), "fixture must observe a real modified diff");
    assert.ok(kinds.has("deleted"), "fixture must observe a real deleted diff");
    assert.ok(measured.some((m) => m.file === "e1.md"), "plan e1 must author e1.md");
    assert.ok(!measured.some((m) => String(m.file || "").includes("seed-")), "synthetic seed records do not exist");
    // Direct helper is containment-guarded too.
    assert.throws(() => applyMockSynthesisWorkspace(plans, "/tmp/evil-workspace", { stateDir }), /denied|outside/);
  });

  it("measuredIdsForPlan binds specific changes only, never blanket all", async () => {
    const { measuredIdsForPlan } = await import("../src/synthesize.js");
    const changes = [{ id: "m-e1" }, { id: "m-e2" }, { id: "m-other" }];
    assert.deepEqual(measuredIdsForPlan("e1", changes), ["m-e1"]);
    assert.deepEqual(measuredIdsForPlan("e2", changes), ["m-e2"]);
    assert.deepEqual(measuredIdsForPlan("e9", changes), []);
  });
});

describe("upstream mappings + docs (3-stage contract)", () => {
  it("LICENSE.NOTICE maps both prompt files with source URLs", () => {
    const text = fs.readFileSync(NOTICE, "utf8");
    for (const f of ["improve/prompts/consolidate.md", "improve/prompts/synthesis.md"]) {
      assert.ok(text.includes(f), `NOTICE must map ${f}`);
    }
    assert.ok(text.includes("src/prompts/consolidate.md"));
    assert.ok(text.includes("src/prompts/synthesis.md"));
    assert.ok(text.includes("https://github.com/kunchenguid/backpass"));
  });
});
