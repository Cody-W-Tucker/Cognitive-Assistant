import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { setup } from "./helpers.mjs";

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "bin", "ca-improve.js");

/** Run the CLI without blocking, so an in-process fake Langfuse can answer it. */
function cli(args, env = {}) {
  return new Promise((resolve) => {
    execFile(process.execPath, [BIN, ...args], { encoding: "utf8", env: { ...process.env, ...env } }, (err, stdout, stderr) => {
      resolve({ code: err ? err.code : 0, stdout, stderr });
    });
  });
}

/** Two substantial sessions behind a fake Langfuse server; `close` stops it. */
async function serve() {
  const env = setup(2);
  const server = await env.langfuse.serve();
  return { state: env.stateDir, soul: env.soulPath, env: server.env, close: server.close };
}

describe("ca-improve CLI", () => {
  it("run --headless prints exactly one JSON proposal on stdout", async () => {
    const { state, soul, env, close } = await serve();
    try {
      const out = await cli(["run", "--headless", "--state-dir", state, "--soul-path", soul, "--analyzer", "mock", "--since", "all"], env);
      assert.equal(out.code, 0, out.stderr);
      assert.equal(out.stdout.trim().split("\n").length, 1);
      const proposal = JSON.parse(out.stdout);
      assert.equal(proposal.edits.length, 1);
      assert.equal(proposal.edits[0].annotation.verdict, "keep");
    } finally {
      await close();
    }
  });

  it("synthesize refuses without a model and leaves the proposal under review alone", async () => {
    const { state, soul, env, close } = await serve();
    try {
      await cli(["run", "--headless", "--state-dir", state, "--soul-path", soul, "--analyzer", "mock", "--since", "all"], env);
    } finally {
      await close();
    }
    const before = fs.readFileSync(path.join(state, "proposal.json"), "utf8");
    const out = await cli(["synthesize", "--state-dir", state, "--soul-path", soul], { CA_LLM_BASE_URL: "" });
    assert.notEqual(out.code, 0);
    assert.equal(out.stdout, "");
    assert.match(out.stderr, /CA_LLM_BASE_URL/);
    assert.equal(fs.readFileSync(path.join(state, "proposal.json"), "utf8"), before);
  });

  it("rejects bad invocations with usage on stderr and nothing on stdout", async () => {
    const { stateDir: state, soulPath: soul } = setup(0);
    for (const args of [
      ["discover"],
      ["run", "--state-dir", state, "--soul-path", soul],
      ["run", "--headless", "--tui", "--state-dir", state, "--soul-path", soul],
      ["run", "--headless", "--soul-path", soul],
      ["synthesize", "--state-dir", state],
      ["run", "--headless", "--state-dir", state, "--soul-path"],
      ["run", "--headless", "--state-dir", state, "--soul-path", soul, "--home", state],
    ]) {
      const out = await cli(args);
      assert.equal(out.code, 2, args.join(" "));
      assert.equal(out.stdout, "");
      assert.match(out.stderr, /usage:/);
    }
  });

  it("fails naming the variables when Langfuse is not configured", async () => {
    const { stateDir: state, soulPath: soul } = setup(0);
    const out = await cli(["run", "--headless", "--state-dir", state, "--soul-path", soul, "--analyzer", "mock"], { LANGFUSE_PUBLIC_KEY: "", LANGFUSE_SECRET_KEY: "", LANGFUSE_BASE_URL: "" });
    assert.equal(out.code, 1);
    assert.equal(out.stdout, "");
    assert.match(out.stderr, /LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL not set/);
  });

  it("resume with no saved state fails naming improve-run", async () => {
    const { stateDir: state, soulPath: soul } = setup(0);
    const out = await cli(["synthesize", "--state-dir", state, "--soul-path", soul]);
    assert.equal(out.code, 1);
    assert.match(out.stderr, /improve-run/);
  });
});
