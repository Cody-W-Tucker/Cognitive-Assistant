import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { prepareExperienceWorkspace, measureExperienceWorkspace } from "../src/experience-workspace.js";

it("measures a synthesis-authored staged record as an anchored add diff", () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-workspace-"));
  const workspace = prepareExperienceWorkspace({ stateDir, records: [] });
  fs.writeFileSync(path.join(workspace.root, "exp-reserve-calls.md"), "---\nid: exp-reserve-calls\nsources: s1, s2\n---\n\n# Reserve calls\n", "utf8");
  const measured = measureExperienceWorkspace(workspace);
  assert.equal(measured.length, 1);
  assert.equal(measured[0].kind, "created");
  assert.equal(measured[0].recordId, "exp-reserve-calls");
  assert.match(measured[0].text, /Reserve calls/);
});
