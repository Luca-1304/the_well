import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { buildShareUrl, safeHttpUrl } from "../features/common.js";

const FRONTEND_FILES = [
  "../app.js",
  "../features/common.js",
  "../features/apod.js",
  "../features/neo.js",
  "../features/donki.js",
  "../features/eonet.js",
];

async function source(relativePath) {
  return readFile(new URL(relativePath, import.meta.url), "utf8");
}

test("share URLs preserve only public allow-listed filters", () => {
  const url = buildShareUrl(
    "neo",
    {
      start: "2026-08-03",
      end: "2026-08-04",
      sort: "closest",
      unknown: "should-not-survive",
      api_key: "private-value",
    },
    "https://nasa-data-hub.vercel.app/?utm_source=test&token=private#old",
  );
  const parsed = new URL(url);

  assert.equal(parsed.origin, "https://nasa-data-hub.vercel.app");
  assert.equal(parsed.searchParams.get("view"), "neo");
  assert.equal(parsed.searchParams.get("start"), "2026-08-03");
  assert.equal(parsed.searchParams.get("end"), "2026-08-04");
  assert.equal(parsed.searchParams.get("sort"), "closest");
  assert.equal(parsed.searchParams.has("utm_source"), false);
  assert.equal(parsed.searchParams.has("unknown"), false);
  assert.equal(parsed.searchParams.has("api_key"), false);
  assert.equal(parsed.searchParams.has("token"), false);
  assert.equal(parsed.hash, "#neo");
});

test("share URLs discard credential-shaped values", () => {
  const url = buildShareUrl(
    "eonet",
    { status: "open", category: "api_key=private-value" },
    "https://nasa-data-hub.vercel.app/",
  );
  const parsed = new URL(url);
  assert.equal(parsed.searchParams.get("status"), "open");
  assert.equal(parsed.searchParams.has("category"), false);
});

test("safe URL handling accepts only HTTP and HTTPS", () => {
  assert.equal(safeHttpUrl("https://nasa.gov/"), "https://nasa.gov/");
  assert.equal(safeHttpUrl("http://example.com/path"), "http://example.com/path");
  assert.equal(safeHttpUrl("javascript:alert(1)"), null);
  assert.equal(safeHttpUrl("data:text/html,unsafe"), null);
  assert.equal(safeHttpUrl("not a url"), null);
});

test("frontend modules contain no credential access or unsafe HTML sinks", async () => {
  for (const file of FRONTEND_FILES) {
    const text = await source(file);
    assert.equal(text.includes("process.env"), false, file);
    assert.equal(text.includes("NASA_API_KEY"), false, file);
    assert.equal(/api_key\s*=/i.test(text), false, file);
    assert.equal(text.includes("innerHTML"), false, file);
    assert.equal(text.includes("outerHTML"), false, file);
    assert.equal(text.includes("insertAdjacentHTML"), false, file);
    assert.equal(text.includes("eval("), false, file);
  }
});

test("document exposes credibility, privacy and source information", async () => {
  const html = await source("../index.html");

  assert.match(html, /not an official NASA service/i);
  assert.match(html, /No advertising trackers/i);
  assert.match(html, /Shared links contain public filters only/i);
  assert.match(html, /NASA Open APIs/i);
  assert.match(html, /Inspect public-safe code/i);
  assert.match(html, /<link rel="stylesheet" href="\/styles\.css">/);
  assert.match(html, /<script type="module" src="\/app\.js"><\/script>/);
  assert.equal(/<style[\s>]/i.test(html), false);
  assert.equal(/<script(?![^>]*\bsrc=)[^>]*>/i.test(html), false);
});
