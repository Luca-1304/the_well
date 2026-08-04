import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  formatLocalInputDate,
  parseResponseText,
  RequestCoordinator,
  shiftIsoDate,
} from "../features/common.js";
import { assertAssetParity } from "../scripts/production-smoke.mjs";

const source = (relativePath) =>
  readFile(new URL(relativePath, import.meta.url), "utf8");

test("local date input formatting uses calendar fields rather than UTC serialisation", () => {
  const fakeDate = {
    getFullYear: () => 2026,
    getMonth: () => 7,
    getDate: () => 3,
  };
  assert.equal(formatLocalInputDate(fakeDate), "2026-08-03");
});

test("ISO date shifting supports the seven-day NEO window", () => {
  assert.equal(shiftIsoDate("2026-08-03", 7), "2026-08-10");
  assert.equal(shiftIsoDate("2026-12-29", 7), "2027-01-05");
  assert.throws(() => shiftIsoDate("not-a-date", 7), /valid ISO date/i);
});

test("response parsing returns JSON and rejects unreadable upstream bodies cleanly", () => {
  assert.deepEqual(parseResponseText('{"ok":true}', "NASA API"), { ok: true });
  assert.throws(
    () => parseResponseText("<html>gateway failure</html>", "NASA API"),
    /unreadable response/i,
  );
});

test("request coordinator aborts the previous request and prevents stale completion", () => {
  const coordinator = new RequestCoordinator();
  const target = {};
  const first = coordinator.begin(target);
  const second = coordinator.begin(target);

  assert.equal(first.signal.aborted, true);
  assert.equal(first.isCurrent(), false);
  assert.equal(second.signal.aborted, false);
  assert.equal(second.isCurrent(), true);
  second.finish();
  assert.equal(second.isCurrent(), false);
});

test("asset parity normalises line endings but rejects real deployment drift", () => {
  assert.doesNotThrow(() => assertAssetParity("app.js", "a\r\nb\r\n", "a\nb\n"));
  assert.throws(() => assertAssetParity("app.js", "old", "new"), /does not match GitHub/i);
});

test("v1.2 source pins the runtime and exposes correct date constraints", async () => {
  const packageJson = JSON.parse(await source("../package.json"));
  const app = await source("../app.js");
  const stabilityCss = await source("../stability.css");

  assert.equal(packageJson.version, "1.2.0");
  assert.equal(packageJson.engines.node, "22.x");
  assert.match(app, /apodInput\.max = today/);
  assert.match(app, /donkiStartInput\.max = today/);
  assert.match(app, /neoEndInput\.max = shiftIsoDate\(neoStartInput\.value, 7\)/);
  assert.match(stabilityCss, /object-fit:\s*contain/);
});
