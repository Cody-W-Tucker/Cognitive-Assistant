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
      id: "exp-x",
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

describe("synthesis.md durable-record contract (Backpass src/prompts/synthesis.md @ 0268201)", () => {
  it("exists with exact upstream provenance", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(text.includes("Backpass"));
    assert.ok(text.includes("0268201"));
    assert.ok(text.includes("src/prompts/synthesis.md"));
    assert.ok(text.includes("https://github.com/kunchenguid/backpass"));
  });

  it("declares exactly the supported placeholders and nothing else", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    const tokens = [...text.matchAll(/\{\{([A-Za-z0-9_]+)\}\}/g)].map((m) => m[1]);
    assert.deepEqual([...new Set(tokens)].sort(), [
      "EVIDENCE",
      "HARNESS_SUMMARY",
      "REJECTIONS",
      "RUN_NOTE",
      "TRANSCRIPT_COUNT",
    ]);
  });

  it("does not bake in the sentinel", () => {
    assert.ok(!fs.readFileSync(SYNTH_MD, "utf8").includes("ca-improve:self-session"));
  });

  it("contracts title, bounded body, evidence sessions+verbatim quotes, counterevidence, compilerImplication", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(/title/i.test(text));
    assert.ok(/body/i.test(text) && /\b2000\b/.test(text));
    assert.ok(/verbatim/i.test(text) && /quote/i.test(text));
    assert.ok(/counterevidence/i.test(text) && /none observed/i.test(text));
    assert.ok(/compilerImplication/i.test(text));
  });

  it("contracts staged artifact/diff, no live/tracked/SOUL/skills/Hermes changes, proposal not authoritative", () => {
    const text = fs.readFileSync(SYNTH_MD, "utf8");
    assert.ok(/staged artifact/i.test(text) && /diff/i.test(text));
    assert.ok(/never.*(SOUL|tracked|live|Hermes)|no .*SOUL/i.test(text));
    assert.ok(/not authoritative|pre-apply|until.*appl/i.test(text));
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
        }),
      /RUN_NOTE/,
    );
  });

  it("persists rendered synthesis prompt privately with run/stage metadata", () => {
    const stateDir = tmpDir();
    const prompt = buildSynthesisPrompt(ledger(), {
      evidenceIndex: evidenceIndex(),
      runNote: "n",
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

describe("mock deterministic synthesis path (unchanged, reviewable, no real calls)", () => {
  it("synthesizeCandidates still produces reviewable edits with no invoke", () => {
    const edits = synthesizeCandidates(ledger(), { evidenceIndex: evidenceIndex(), soulBaseline: "" });
    assert.equal(edits.length, 1);
    assert.ok(edits[0].record.title.length > 0);
    assert.ok(edits[0].stagedArtifact.includes(edits[0].record.id));
    assert.ok(edits[0].diff.includes(edits[0].record.id));
  });

  it("mock records carry counterevidence and compilerImplication", () => {
    const edits = synthesizeCandidates(ledger(), { evidenceIndex: evidenceIndex() });
    assert.equal(edits[0].record.counterevidence, "none observed");
    assert.ok(typeof edits[0].record.compilerImplication === "string");
    assert.ok(edits[0].record.compilerImplication.length > 0);
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

describe("synthesizeWithAcpx (production only, fail-closed)", () => {
  it("validates acpx candidates and renders staged artifact/diff", () => {
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", candidates: [candidate()] }),
    });
    assert.equal(out.failed, undefined);
    assert.equal(out.edits.length, 1);
    assert.ok(out.edits[0].stagedArtifact.includes(out.edits[0].record.id));
    assert.ok(out.edits[0].diff.includes(out.edits[0].record.id));
  });

  it("drops invalid candidates; fails closed with visible note when none remain", () => {
    const bad = candidate();
    bad.evidence = [{ polarity: "negative", text: "made up", source: "ghost" }];
    bad.record = { ...bad.record, evidence: bad.evidence, sources: ["ghost"] };
    const out = synthesizeWithAcpx(ledger(), {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", candidates: [bad] }),
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
      invoke: () => ({ status: "ok", candidates: [] }),
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
        return { status: "ok", candidates: [] };
      },
    });
    assert.ok(seen.prompt.includes("ca-improve:self-session"));
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

  it("synthesizeWithAcpx suppresses rejected identities but keeps novel ones", () => {
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
    const novel = candidate();
    novel.record = { ...novel.record, title: "Brand new", clusterId: "g-new", sources: ["s1", "s2"] };
    novel.title = "Brand new";
    const out = synthesizeWithAcpx(led, {
      evidenceIndex: evidenceIndex(),
      invoke: () => ({ status: "ok", candidates: [candidate(), novel] }),
      rejections,
    });
    assert.equal(out.edits.length, 1);
    assert.equal(out.edits[0].record.clusterId, "g-new");
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

  it("RED: model {edits:[...]} shape is rejected (strict {candidates:[...]} only)", () => {
    const rec = boundCandidate().record;
    const out = synthesizeWithAcpx(boundLedger(), {
      evidenceIndex: boundIndex(),
      invoke: () => ({ status: "ok", result: { edits: [{ record: rec }] } }),
    });
    assert.deepEqual(out.edits, []);
    assert.ok(out.failed);
  });

  it("RED: malformed model shapes fail closed", () => {
    for (const result of [{}, { candidates: "nope" }, { candidates: [{ record: { title: "" } }] }]) {
      const out = synthesizeWithAcpx(boundLedger(), {
        evidenceIndex: boundIndex(),
        invoke: () => ({ status: "ok", result }),
      });
      assert.deepEqual(out.edits, [], JSON.stringify(result));
      assert.ok(out.failed, JSON.stringify(result));
    }
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
