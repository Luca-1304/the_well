import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import handler, {
  buildEonetUrl,
  isIsoDate,
  scrubApiKeys,
} from "../api/nasa.js";

function fakeResponse() {
  return {
    headers: new Map(),
    statusCode: null,
    payload: null,
    setHeader(name, value) {
      this.headers.set(name.toLowerCase(), value);
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.payload = payload;
      return this;
    },
  };
}

test("scrubApiKeys removes nested mixed-case credentials", () => {
  const payload = {
    links: {
      self: "https://api.nasa.gov/neo?api_key=private-value&start=2026-08-03",
    },
    nested: [
      "https://api.nasa.gov/neo?start=2026-08-03&API_KEY=private-value#result",
    ],
  };

  const clean = scrubApiKeys(payload);
  const serialised = JSON.stringify(clean);

  assert.equal(serialised.includes("private-value"), false);
  assert.equal(serialised.toLowerCase().includes("api_key"), false);
  assert.equal(
    clean.links.self,
    "https://api.nasa.gov/neo?start=2026-08-03",
  );
  assert.equal(
    clean.nested[0],
    "https://api.nasa.gov/neo?start=2026-08-03#result",
  );
});

test("scrubApiKeys leaves unrelated data unchanged", () => {
  const payload = {
    text: "ordinary response",
    url: "https://example.com/path?value=1",
    number: 3,
  };
  assert.deepEqual(scrubApiKeys(payload), payload);
});

test("buildEonetUrl preserves the required API v3 path", () => {
  const url = buildEonetUrl({
    status: "open",
    limit: "3",
    days: "14",
    category: "wildfires",
  });

  assert.equal(url.origin, "https://eonet.gsfc.nasa.gov");
  assert.equal(url.pathname, "/api/v3/events");
  assert.equal(url.searchParams.get("status"), "open");
  assert.equal(url.searchParams.get("limit"), "3");
  assert.equal(url.searchParams.get("days"), "14");
  assert.equal(url.searchParams.get("category"), "wildfires");
  assert.equal(url.searchParams.has("api_key"), false);
});

test("ISO date validation rejects impossible and malformed dates", () => {
  assert.equal(isIsoDate("2026-08-03"), true);
  assert.equal(isIsoDate("2026-02-30"), false);
  assert.equal(isIsoDate("03-08-2026"), false);
  assert.equal(isIsoDate(""), false);
});

test("health response exposes mode but never a credential", async () => {
  const previous = process.env.NASA_API_KEY;
  process.env.NASA_API_KEY = "private-value";
  const response = fakeResponse();

  try {
    await handler(
      { method: "GET", query: { mode: "health" } },
      response,
    );
  } finally {
    if (previous === undefined) delete process.env.NASA_API_KEY;
    else process.env.NASA_API_KEY = previous;
  }

  assert.equal(response.statusCode, 200);
  assert.equal(response.payload.ok, true);
  assert.equal(response.payload.using_demo_key, false);
  assert.equal(JSON.stringify(response.payload).includes("private-value"), false);
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("invalid NEO windows fail before any network request", async () => {
  const originalFetch = globalThis.fetch;
  let networkCalled = false;
  globalThis.fetch = async () => {
    networkCalled = true;
    throw new Error("network should not be called");
  };
  const response = fakeResponse();

  try {
    await handler(
      {
        method: "GET",
        query: {
          mode: "neo",
          start: "2026-08-01",
          end: "2026-08-10",
        },
      },
      response,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(networkCalled, false);
  assert.equal(response.statusCode, 400);
  assert.match(response.payload.error, /seven days/i);
});

test("frontend source cannot read or append the private key", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");

  assert.equal(html.includes("process.env"), false);
  assert.equal(html.includes("NASA_API_KEY"), false);
  assert.equal(/api_key\s*=/i.test(html), false);
  assert.equal(html.includes("innerHTML"), false);
});
