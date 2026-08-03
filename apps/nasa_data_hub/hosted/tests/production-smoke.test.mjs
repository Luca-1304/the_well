import assert from "node:assert/strict";
import test from "node:test";

import {
  assertCredentialFree,
  assertHealthPayload,
  assertStructuralPage,
} from "../scripts/production-smoke.mjs";

const secureHeaders = new Headers({
  "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'",
  "permissions-policy": "camera=(), microphone=(), geolocation=()",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-dns-prefetch-control": "off",
  "x-frame-options": "DENY",
});

test("structural smoke accepts the deployed v1.1 page and hardened headers", () => {
  assert.doesNotThrow(() =>
    assertStructuralPage(
      "<title>NASA Data Hub</title><h1>Space and Earth data, made understandable.</h1><a>Review source</a>",
      secureHeaders,
    ),
  );
});

test("structural smoke rejects weakened inline CSP", () => {
  const headers = new Headers(secureHeaders);
  headers.set(
    "content-security-policy",
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'",
  );
  assert.throws(
    () => assertStructuralPage("NASA Data Hub Space and Earth data, made understandable. Review source", headers),
    /unsafe-inline/i,
  );
});

test("health smoke requires version 1.1 and no credential disclosure", () => {
  assert.doesNotThrow(() =>
    assertHealthPayload({
      ok: true,
      service: "NASA Data Hub",
      version: "1.1",
      key_mode: "demo",
      using_demo_key: true,
      privacy: "no account or tracking profile",
    }),
  );

  assert.throws(
    () => assertHealthPayload({ ok: true, version: "1.0" }),
    /version 1\.1/i,
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
