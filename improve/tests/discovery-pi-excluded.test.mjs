// Pi is excluded from discovery (machine/automation work) but stays valid as an ACPX agent option.
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  SUPPORTED_HARNESSES,
  EXCLUDED_HARNESSES,
  discoverTranscripts,
} from "../src/discovery.js";
import { buildAcpxArgs } from "../src/acpx-text.js";

describe("discovery Pi exclusion (default scope + explicit rejection)", () => {
  it("default scope is hermes/claude/codex/opencode only", () => {
    assert.deepEqual([...SUPPORTED_HARNESSES].sort(), ["claude", "codex", "hermes", "opencode"]);
    assert.ok(!SUPPORTED_HARNESSES.includes("pi"));
  });

  it("explicit Pi is excluded with machine/automation reason", () => {
    assert.ok(EXCLUDED_HARNESSES.pi);
    assert.match(EXCLUDED_HARNESSES.pi, /machine\/automation/i);
  });

  it("discoverTranscripts default never returns Pi even with a Pi store present", () => {
    const home = fs.mkdtempSync(path.join(os.tmpdir(), "ca-pi-excl-home-"));
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-pi-excl-state-"));
    try {
      const piDir = path.join(home, ".pi", "agent", "sessions", "-tmp-proj");
      fs.mkdirSync(piDir, { recursive: true });
      fs.writeFileSync(
        path.join(piDir, "2026-10-11T00-00-00_pi-1.jsonl"),
        `${JSON.stringify({ type: "session", cwd: "/tmp/proj", id: "pi-1" })}\n`,
        "utf8",
      );
      const result = discoverTranscripts({ home, stateDir, since: "30d" });
      assert.ok(!result.transcripts.some((t) => t.harness === "pi"));
      assert.ok(!result.transcripts.some((t) => t.id === "pi-1"));
      assert.ok(result.excluded.pi);
    } finally {
      fs.rmSync(home, { recursive: true, force: true });
      fs.rmSync(stateDir, { recursive: true, force: true });
    }
  });

  it("explicit harnesses ['pi'] is rejected fail-closed", () => {
    const home = fs.mkdtempSync(path.join(os.tmpdir(), "ca-pi-rej-home-"));
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-pi-rej-state-"));
    try {
      assert.throws(() => discoverTranscripts({ home, stateDir, harnesses: ["pi"] }), /machine\/automation/);
    } finally {
      fs.rmSync(home, { recursive: true, force: true });
      fs.rmSync(stateDir, { recursive: true, force: true });
    }
  });

  it("Pi stays usable as an ACPX agent option (not affected by discovery exclusion)", () => {
    const prev = process.env.CA_IMPROVE_ACPX_ARGS;
    process.env.CA_IMPROVE_ACPX_ARGS = "--env KEY=value";
    try {
      assert.deepEqual(buildAcpxArgs({ agent: "pi" }), ["--env", "KEY=value", "--format", "quiet", "pi"]);
    } finally {
      if (prev === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
      else process.env.CA_IMPROVE_ACPX_ARGS = prev;
    }
  });
});
