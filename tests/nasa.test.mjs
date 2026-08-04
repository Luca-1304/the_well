import assert from "node:assert/strict";
import test from "node:test";

import handler, {
  COURTESY_LIMITS,
  buildEonetUrl,
  checkCourtesyLimit,
  deduplicatedFetch,
  fetchJson,
  isIsoDate,
  resetRuntimeStateForTests,
  scrubApiKeys,
} from "../api/nasa.js";

function fakeResponse() {
  return {
    headers: new Map(),
    statusCode: null,
    payload: null,
    setHeader(name, value) {
      this.headers.set(name.toLowerCase(), String(value));
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

async function withFetch(mock, operation) {
  const original = globalThis.fetch;
  globalThis.fetch = mock;
  try {
    return await operation();
  } finally {
    globalThis.fetch = original;
  }
}

test.beforeEach(() => resetRuntimeStateForTests());

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
  assert.equal(clean.links.self, "https://api.nasa.gov/neo?start=2026-08-03");
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

test("EONET rejects excessive history windows", () => {
  assert.throws(
    () => buildEonetUrl({ status: "open", days: "3651" }),
    /between 1 and 3650/i,
  );
});

test("ISO date validation rejects impossible and malformed dates", () => {
  assert.equal(isIsoDate("2026-08-03"), true);
  assert.equal(isIsoDate("2026-02-30"), false);
  assert.equal(isIsoDate("03-08-2026"), false);
  assert.equal(isIsoDate(""), false);
});

test("health response exposes v1.2 runtime and privacy without a credential", async () => {
  const previous = process.env.NASA_API_KEY;
  process.env.NASA_API_KEY = "private-value";
  const response = fakeResponse();

  try {
    await handler(
      { method: "GET", query: { mode: "health" }, headers: {} },
      response,
    );
  } finally {
    if (previous === undefined) delete process.env.NASA_API_KEY;
    else process.env.NASA_API_KEY = previous;
  }

  assert.equal(response.statusCode, 200);
  assert.equal(response.payload.version, "1.2");
  assert.equal(response.payload.runtime, `node-${process.versions.node.split(".")[0]}`);
  assert.equal(response.payload.using_demo_key, false);
  assert.match(response.payload.privacy, /no account/i);
  assert.equal(JSON.stringify(response.payload).includes("private-value"), false);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("x-app-version"), "1.2");
});

test("invalid NEO windows fail before any network request", async () => {
  let networkCalled = false;
  const response = fakeResponse();

  await withFetch(
    async () => {
      networkCalled = true;
      throw new Error("network should not be called");
    },
    () =>
      handler(
        {
          method: "GET",
          query: {
            mode: "neo",
            start: "2026-08-01",
            end: "2026-08-10",
          },
          headers: { "x-forwarded-for": "192.0.2.1" },
        },
        response,
      ),
  );

  assert.equal(networkCalled, false);
  assert.equal(response.statusCode, 400);
  assert.match(response.payload.error, /seven days/i);
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("successful authenticated route redacts echoed keys", async () => {
  const previous = process.env.NASA_API_KEY;
  process.env.NASA_API_KEY = "private-value";
  const response = fakeResponse();

  try {
    await withFetch(
      async (url) => {
        assert.equal(new URL(url).searchParams.get("api_key"), "private-value");
        return new Response(
          JSON.stringify({
            title: "Example",
            links: {
              self: "https://api.nasa.gov/example?date=2026-08-03&api_key=private-value",
            },
          }),
          {
            status: 200,
            headers: {
              "content-type": "application/json",
              "x-ratelimit-limit": "1000",
              "x-ratelimit-remaining": "999",
            },
          },
        );
      },
      () =>
        handler(
          {
            method: "GET",
            query: { mode: "apod", date: "2026-08-03" },
            headers: { "x-forwarded-for": "192.0.2.2" },
          },
          response,
        ),
    );
  } finally {
    if (previous === undefined) delete process.env.NASA_API_KEY;
    else process.env.NASA_API_KEY = previous;
  }

  assert.equal(response.statusCode, 200);
  assert.equal(JSON.stringify(response.payload).includes("private-value"), false);
  assert.equal(JSON.stringify(response.payload).toLowerCase().includes("api_key"), false);
  assert.equal(response.headers.get("cache-control").includes("s-maxage=300"), true);
});

test("EONET route never receives a NASA key", async () => {
  const response = fakeResponse();
  await withFetch(
    async (url) => {
      const upstream = new URL(url);
      assert.equal(upstream.pathname, "/api/v3/events");
      assert.equal(upstream.searchParams.has("api_key"), false);
      return new Response(JSON.stringify({ events: [] }), { status: 200 });
    },
    () =>
      handler(
        {
          method: "GET",
          query: { mode: "eonet", status: "open", limit: "3" },
          headers: { "x-forwarded-for": "192.0.2.3" },
        },
        response,
      ),
  );

  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.payload.data.events, []);
});

test("fetchJson retries one retryable response", async () => {
  let calls = 0;
  const result = await withFetch(async () => {
    calls += 1;
    if (calls === 1) {
      return new Response(JSON.stringify({ error: "temporary" }), { status: 503 });
    }
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }, () => fetchJson("https://example.com/data"));

  assert.equal(calls, 2);
  assert.deepEqual(result.data, { ok: true });
});

test("fetchJson reports malformed upstream JSON without leaking content", async () => {
  await assert.rejects(
    withFetch(
      async () => new Response("not-json-private-value", { status: 200 }),
      () => fetchJson("https://example.com/data"),
    ),
    /invalid JSON/i,
  );
});

test("deduplicatedFetch shares identical in-flight work", async () => {
  let operations = 0;
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  const operation = async () => {
    operations += 1;
    await gate;
    return { ok: true };
  };

  const first = deduplicatedFetch("same-public-request", operation);
  const second = deduplicatedFetch("same-public-request", operation);
  release();
  const [left, right] = await Promise.all([first, second]);

  assert.equal(operations, 1);
  assert.deepEqual(left, right);
});

test("courtesy limiter is anonymous, temporary and family-specific", () => {
  const request = { headers: { "x-forwarded-for": "192.0.2.9, 10.0.0.1" } };
  const now = 1_000_000;
  for (let count = 0; count < COURTESY_LIMITS.nasa.limit; count += 1) {
    assert.equal(checkCourtesyLimit(request, "apod", now).allowed, true);
  }
  const blocked = checkCourtesyLimit(request, "neo", now);
  assert.equal(blocked.allowed, false);
  assert.equal(blocked.retryAfter, COURTESY_LIMITS.nasa.windowMs / 1000);

  assert.equal(checkCourtesyLimit(request, "eonet", now).allowed, true);
  assert.equal(
    checkCourtesyLimit(request, "apod", now + COURTESY_LIMITS.nasa.windowMs).allowed,
    true,
  );
});
