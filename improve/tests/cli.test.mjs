import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { tmpDir, writeCodexSession, writeSoul } from "./helpers.mjs";

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "bin", "ca-improve.js");

function cli(args, env = {}) {
  const out = spawnSync(process.execPath, [BIN, ...args], { encoding: "utf8", env: { ...process.env, ...env } });
  return { code: out.status, stdout: out.stdout, stderr: out.stderr };
}

function setup() {
  const root = tmpDir();
  const home = path.join(root, "home");
  writeCodexSession(home, "codex-0");
  writeCodexSession(home, "codex-1");
  return { home, state: path.join(root, "state"), soul: writeSoul(root) };
}

describe("ca-improve CLI", () => {
  it("run --headless prints exactly one JSON proposal on stdout", () => {
    const { home, state, soul } = setup();
    const out = cli(["run", "--headless", "--state-dir", state, "--soul-path", soul, "--home", home, "--analyzer", "mock", "--since", "all"]);
    assert.equal(out.code, 0, out.stderr);
    assert.equal(out.stdout.trim().split("\n").length, 1);
    const proposal = JSON.parse(out.stdout);
    assert.equal(proposal.edits.length, 1);
    assert.equal(proposal.edits[0].annotation.verdict, "keep");
  });

  it("synthesize refuses without a model and leaves the proposal under review alone", () => {
    const { home, state, soul } = setup();
    cli(["run", "--headless", "--state-dir", state, "--soul-path", soul, "--home", home, "--analyzer", "mock", "--since", "all"]);
    const before = fs.readFileSync(path.join(state, "proposal.json"), "utf8");
    const out = cli(["synthesize", "--state-dir", state, "--soul-path", soul], { CA_LLM_BASE_URL: "" });
    assert.notEqual(out.code, 0);
    assert.equal(out.stdout, "");
    assert.match(out.stderr, /CA_LLM_BASE_URL/);
    assert.equal(fs.readFileSync(path.join(state, "proposal.json"), "utf8"), before);
  });

  it("rejects bad invocations with usage on stderr and nothing on stdout", () => {
    const { state, soul } = setup();
    for (const args of [
      ["discover"],
      ["run", "--state-dir", state, "--soul-path", soul],
      ["run", "--headless", "--tui", "--state-dir", state, "--soul-path", soul],
      ["run", "--headless", "--soul-path", soul],
      ["synthesize", "--state-dir", state],
      ["run", "--headless", "--state-dir", state, "--soul-path"],
    ]) {
      const out = cli(args);
      assert.equal(out.code, 2, args.join(" "));
      assert.equal(out.stdout, "");
      assert.match(out.stderr, /usage:/);
    }
  });

  it("a named harness with no store fails the run", () => {
    const { state, soul } = setup();
    const out = cli(["run", "--headless", "--state-dir", state, "--soul-path", soul, "--harness", "hermes", "--analyzer", "mock"], { HERMES_HOME: path.join(tmpDir(), "none") });
    assert.equal(out.code, 1);
    assert.equal(out.stdout, "");
    assert.match(out.stderr, /hermes: store missing/);
  });

  it("resume with no saved state fails naming improve-run", () => {
    const { state, soul } = setup();
    const out = cli(["synthesize", "--state-dir", state, "--soul-path", soul]);
    assert.equal(out.code, 1);
    assert.match(out.stderr, /improve-run/);
  });
});
