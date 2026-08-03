import assert from "node:assert/strict";
import test from "node:test";

import {
  assertCredentialFree,
  assertHealthPayload,
  assertStructuralPage,
} from "../scripts/production-smoke.mjs";

const validHtml =
  "<title>NASA Data Hub</title><h1>Space and Earth data, made understandable.</h1><a>Review source</a>";

const secureHeaders = new Headers({
  "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'",
  "permissions-policy": "camera=(), microphone=(), geolocation=()",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-dns-prefetch-control": "off",
  "x-frame-options": "DENY",
});

const validHealth = {
  ok: true,
  service: "NASA Data Hub",
  version: "1.2",
  runtime: "node-22",
  key_mode: "demo",
  using_demo_key: true,
  privacy: "no account or tracking profile",
};

test("structural smoke accepts the deployed v1.2 page and hardened headers", () => {
  assert.doesNotThrow(() => assertStructuralPage(validHtml, secureHeaders));
});

test("structural smoke rejects weakened inline CSP", () => {
  const headers = new Headers(secureHeaders);
  headers.set(
    "content-security-policy",
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'; frame-ancestors 'none'",
  );
  assert.throws(() => assertStructuralPage(validHtml, headers), /unsafe-inline/i);
});

test("health smoke requires v1.2 on Node 22 with no credential disclosure", () => {
  assert.doesNotThrow(() => assertHealthPayload(validHealth));

  assert.throws(
    () => assertHealthPayload({ ...validHealth, version: "1.1" }),
    /version 1\.2/i,
  );
  assert.throws(
    () => assertHealthPayload({ ...validHealth, runtime: "node-24" }),
    /Node 22/i,
  );
});

test("credential scan rejects nested api_key values and accepts public data", () => {
  assert.doesNotThrow(() =>
    assertCredentialFree({ links: { self: "https://api.nasa.gov/neo?start=2026-08-03" } }),
  );
  assert.throws(
    () =>
      assertCredentialFree({
        links: { self: "https://api.nasa.gov/neo?api_key=private-value" },
      }),
    /credential/i,
  );
});
