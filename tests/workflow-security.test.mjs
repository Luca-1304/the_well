import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function workflow(path) {
  return readFile(new URL(`../${path}`, import.meta.url), "utf8");
}

test("standalone CI keeps checkout credentials ephemeral", async () => {
  for (const path of [
    ".github/workflows/ci.yml",
    ".github/workflows/production-smoke.yml",
  ]) {
    const text = await workflow(path);
    assert.match(text, /uses: actions\/checkout@v7/);
    assert.match(text, /persist-credentials:\s*false/);
    assert.match(text, /uses: actions\/setup-node@v5/);
  }
});

test("standalone source gate validates deployment configuration and secret hygiene", async () => {
  const text = await workflow(".github/workflows/ci.yml");
  assert.match(text, /JSON\.parse/);
  assert.match(text, /vercel\.json/);
  assert.match(text, /git ls-files '\.env\*'/);
  assert.match(text, /npm run check/);
});

test("production smoke is bounded and structural by default", async () => {
  const text = await workflow(".github/workflows/production-smoke.yml");
  assert.match(text, /timeout-minutes:\s*5/);
  assert.match(text, /default:\s*structural/);
  assert.match(text, /options:\s*[\s\S]*- structural[\s\S]*- full/);
  assert.match(text, /node scripts\/production-smoke\.mjs/);
});
