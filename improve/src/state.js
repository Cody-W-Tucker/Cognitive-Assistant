// XDG private state for the CA improvement runtime. Everything the
// runtime persists (cursor/run state, evidence, folded ledger, proposal,
// rejections) lives here — never in the CA repo.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

export function defaultStateDir() {
  const base = process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
  return path.join(base, "cognitive-assistant", "improve");
}

export function initStateDir(stateDir) {
  fs.mkdirSync(stateDir, { recursive: true });
  fs.mkdirSync(path.join(stateDir, "evidence"), { recursive: true });
  fs.mkdirSync(path.join(stateDir, "prompts"), { recursive: true });
  fs.mkdirSync(path.join(stateDir, "staging"), { recursive: true });
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}
