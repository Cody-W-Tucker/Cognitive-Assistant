// Regression: OpenCode legacy `session` table timestamp repair.
// (1) time_updated preferred / time_created fallback filtered by --since.
// (2) table lacking temporal columns keeps mtimeMs null (cursor fallback).
// (3) session_v2 behavior unchanged.
import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

import { discoverTranscripts } from "../src/discovery.js";

const require = createRequire(import.meta.url);
const sqlite = require("node:sqlite");

const DAY_MS = 86400_000;

function mkHome() {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-legacy-"));
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-state-"));
  const dbDir = path.join(home, ".local", "share", "opencode");
  fs.mkdirSync(dbDir, { recursive: true });
  return { home, stateDir, dbPath: path.join(dbDir, "opencode.db") };
}

function writeDb(dbPath, setupSql) {
  if (fs.existsSync(dbPath)) fs.rmSync(dbPath);
  const db = new sqlite.DatabaseSync(dbPath);
  db.exec(setupSql);
  db.close();
}

// Legacy timestamps in the OpenCode schema are epoch seconds.
function epochSec(ms) {
  return Math.floor(ms / 1000);
}

describe("opencode legacy session timestamps", () => {
  let home;
  let stateDir;
  let dbPath;
  let now;

  beforeEach(() => {
    ({ home, stateDir, dbPath } = mkHome());
    now = Date.now();
  });

  afterEach(() => {
    fs.rmSync(home, { recursive: true, force: true });
    fs.rmSync(stateDir, { recursive: true, force: true });
  });

  it("(1) filters legacy session rows by time_updated preferred over time_created", () => {
    const freshUpdated = epochSec(now - 1 * DAY_MS);
    const staleUpdated = epochSec(now - 40 * DAY_MS);
    const freshCreated = epochSec(now - 2 * DAY_MS);
    writeDb(
      dbPath,
      `CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT, time_created INTEGER, time_updated INTEGER);
       INSERT INTO session VALUES ('fresh', '/tmp/proj-fresh', ${freshCreated}, ${freshUpdated});
       INSERT INTO session VALUES ('stale', '/tmp/proj-stale', ${freshCreated}, ${staleUpdated});`,
    );
    const { transcripts } = discoverTranscripts({
      home,
      stateDir,
      since: "30d",
      harnesses: ["opencode"],
    });
    const ids = transcripts.map((t) => t.id).sort();
    assert.deepEqual(ids, ["fresh"]);
    const fresh = transcripts.find((t) => t.id === "fresh");
    assert.equal(fresh.mtimeMs, freshUpdated * 1000);
  });

  it("(1b) falls back to time_created when time_updated is null", () => {
    const freshCreated = epochSec(now - 5 * DAY_MS);
    const staleCreated = epochSec(now - 60 * DAY_MS);
    writeDb(
      dbPath,
      `CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT, time_created INTEGER, time_updated INTEGER);
       INSERT INTO session VALUES ('fallback-fresh', '/tmp/a', ${freshCreated}, NULL);
       INSERT INTO session VALUES ('fallback-stale', '/tmp/b', ${staleCreated}, NULL);`,
    );
    const { transcripts } = discoverTranscripts({
      home,
      stateDir,
      since: "30d",
      harnesses: ["opencode"],
    });
    const ids = transcripts.map((t) => t.id).sort();
    assert.deepEqual(ids, ["fallback-fresh"]);
    const fresh = transcripts.find((t) => t.id === "fallback-fresh");
    assert.equal(fresh.mtimeMs, freshCreated * 1000);
  });

  it("(2) legacy table without temporal columns keeps cursor fallback (mtimeMs null)", () => {
    writeDb(
      dbPath,
      `CREATE TABLE session (id TEXT PRIMARY KEY, directory TEXT);
       INSERT INTO session VALUES ('no-time', '/tmp/no-time');`,
    );
    // Even with a tight --since window, the row must survive with null mtimeMs
    // so the persistent cursor (not timestamp guessing) owns freshness.
    const { transcripts } = discoverTranscripts({
      home,
      stateDir,
      since: "1d",
      harnesses: ["opencode"],
    });
    assert.equal(transcripts.length, 1);
    assert.equal(transcripts[0].id, "no-time");
    assert.equal(transcripts[0].mtimeMs, null);
  });

  it("(3) session_v2 behavior remains unchanged", () => {
    const freshUpdated = epochSec(now - 1 * DAY_MS);
    const staleCreated = epochSec(now - 60 * DAY_MS);
    writeDb(
      dbPath,
      `CREATE TABLE session_v2 (id TEXT PRIMARY KEY, directory TEXT, title TEXT, time_created INTEGER, time_updated INTEGER);
       INSERT INTO session_v2 VALUES ('v2-fresh', '/tmp/v2-fresh', 't', ${staleCreated}, ${freshUpdated});
       INSERT INTO session_v2 VALUES ('v2-stale', '/tmp/v2-stale', 't', ${staleCreated}, ${staleCreated});`,
    );
    const { transcripts } = discoverTranscripts({
      home,
      stateDir,
      since: "30d",
      harnesses: ["opencode"],
    });
    const ids = transcripts.map((t) => t.id).sort();
    assert.deepEqual(ids, ["v2-fresh"]);
    assert.equal(transcripts[0].mtimeMs, freshUpdated * 1000);
  });
});
