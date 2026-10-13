// Isolated repaint loop for ca-improve. The pipeline may block synchronously
// inside ACPX; this process receives its progress as NDJSON over stdin.
import readline from "node:readline";

import { startTui } from "./tui.js";

let tui = null;
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

input.on("line", (line) => {
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    return;
  }
  if (message.type === "start") {
    tui = startTui(message.meta || {});
    return;
  }
  if (message.type === "event") tui?.event(message.event, message.data || {});
});

input.on("close", () => tui?.stop());

// The parent can be interrupted while blocked in spawnSync. stdin may not get
// a graceful close in that path, so restore the cursor on every exit route.
const shutdown = (code = 0) => {
  tui?.stop();
  process.exit(code);
};
process.once("SIGINT", () => shutdown(130));
process.once("SIGTERM", () => shutdown(143));
process.once("exit", () => tui?.stop());
