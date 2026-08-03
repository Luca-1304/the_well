import { pathToFileURL } from "node:url";

const DEFAULT_BASE_URL = "https://nasa-data-hub.vercel.app";
const REQUEST_TIMEOUT_MS = 15_000;
const CREDENTIAL_PATTERN = /(?:api[_-]?key|authorization|bearer\s+[a-z0-9._-]+|(?:access[_-]?)?token=|secret=)/i;

function requireCondition(condition, message) {
  if (!condition) throw new Error(message);
}

function normaliseBaseUrl(value) {
  const url = new URL(value || DEFAULT_BASE_URL);
  requireCondition(url.protocol === "https:", "Smoke target must use HTTPS");
  requireCondition(!url.username && !url.password, "Smoke target cannot contain credentials");
  url.pathname = "/";
  url.search = "";
  url.hash = "";
  return url;
}

function header(headers, name) {
  return String(headers.get(name) || "").trim();
}

export function assertCredentialFree(value) {
  const serialised = JSON.stringify(value);
  requireCondition(
    !CREDENTIAL_PATTERN.test(serialised),
    "Response contains a credential-shaped value",
  );
}

export function assertStructuralPage(html, headers) {
  requireCondition(html.includes("<title>NASA Data Hub</title>"), "Production title is missing");
  requireCondition(
    html.includes("Space and Earth data, made understandable."),
    "Production v1.1 hero copy is missing",
  );
  requireCondition(html.includes("Review source"), "Public source link is missing");

  const csp = header(headers, "content-security-policy");
  requireCondition(csp, "Content-Security-Policy header is missing");
  requireCondition(!csp.includes("'unsafe-inline'"), "CSP contains unsafe-inline");
  requireCondition(csp.includes("script-src 'self'"), "CSP does not restrict scripts to self");
  requireCondition(csp.includes("style-src 'self'"), "CSP does not restrict styles to self");
  requireCondition(csp.includes("frame-ancestors 'none'"), "CSP does not deny framing");
  requireCondition(header(headers, "x-frame-options") === "DENY", "X-Frame-Options is not DENY");
  requireCondition(header(headers, "referrer-policy") === "no-referrer", "Referrer-Policy is not no-referrer");
  requireCondition(header(headers, "x-content-type-options") === "nosniff", "X-Content-Type-Options is not nosniff");
  requireCondition(header(headers, "x-dns-prefetch-control") === "off", "DNS prefetching is not disabled");
  requireCondition(
    header(headers, "permissions-policy").includes("camera=()"),
    "Permissions-Policy is missing camera denial",
  );
}

export function assertHealthPayload(payload) {
  requireCondition(payload?.ok === true, "Health endpoint is not ok");
  requireCondition(payload?.service === "NASA Data Hub", "Unexpected health service name");
  requireCondition(payload?.version === "1.1", "Health endpoint is not version 1.1");
  requireCondition(
    typeof payload?.using_demo_key === "boolean",
    "Health endpoint does not expose a boolean key mode",
  );
  requireCondition(
    payload?.privacy === "no account or tracking profile",
    "Health endpoint privacy contract changed",
  );
  assertCredentialFree(payload);
}

async function request(baseUrl, path, expectedStatus = 200) {
  const url = new URL(path, baseUrl);
  requireCondition(url.origin === baseUrl.origin, "Smoke request escaped the configured origin");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json, text/plain, */*" },
      redirect: "error",
      signal: controller.signal,
    });
    const text = await response.text();
    requireCondition(
      response.status === expectedStatus,
      `${url.pathname} returned HTTP ${response.status}; expected ${expectedStatus}`,
    );
    return { response, text, url };
  } finally {
    clearTimeout(timeout);
  }
}

function parseJson(text, label) {
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} did not return valid JSON`);
  }
}

export async function runStructuralSmoke(base = DEFAULT_BASE_URL) {
  const baseUrl = normaliseBaseUrl(base);
  const root = await request(baseUrl, "/");
  assertStructuralPage(root.text, root.response.headers);

  const health = await request(baseUrl, "/api/health");
  requireCondition(
    header(health.response.headers, "cache-control").includes("no-store"),
    "Health response is cacheable",
  );
  assertHealthPayload(parseJson(health.text, "Health endpoint"));

  const assets = [
    ["/app.js", "application/javascript"],
    ["/styles.css", "text/css"],
    ["/features/common.js", "application/javascript"],
  ];
  for (const [path, contentType] of assets) {
    const asset = await request(baseUrl, path);
    requireCondition(asset.text.length > 200, `${path} is unexpectedly small`);
    requireCondition(
      header(asset.response.headers, "content-type").includes(contentType),
      `${path} has an unexpected content type`,
    );
  }

  return { mode: "structural", baseUrl: baseUrl.href };
}

async function requestJson(baseUrl, path, expectedStatus = 200) {
  const result = await request(baseUrl, path, expectedStatus);
  const payload = parseJson(result.text, result.url.pathname);
  assertCredentialFree(payload);
  return { ...result, payload };
}

export async function runFullSmoke(base = DEFAULT_BASE_URL) {
  const structural = await runStructuralSmoke(base);
  const baseUrl = new URL(structural.baseUrl);

  const apod = await requestJson(baseUrl, "/api/apod?date=2026-08-02");
  requireCondition(apod.payload?.data?.date === "2026-08-02", "APOD returned the wrong date");

  const neo = await requestJson(
    baseUrl,
    "/api/neo?start=2026-08-03&end=2026-08-03",
  );
  requireCondition(
    Number.isInteger(neo.payload?.data?.element_count),
    "NeoWs response is missing element_count",
  );

  const donki = await requestJson(
    baseUrl,
    "/api/donki?type=FLR&start=2026-08-03&end=2026-08-03",
  );
  requireCondition(Array.isArray(donki.payload?.data), "DONKI response is not an array");

  const eonet = await requestJson(baseUrl, "/api/eonet?status=open&limit=1");
  requireCondition(Array.isArray(eonet.payload?.data?.events), "EONET response is missing events");

  const invalid = await requestJson(
    baseUrl,
    "/api/neo?start=2026-08-01&end=2026-08-10",
    400,
  );
  requireCondition(invalid.payload?.ok === false, "Invalid NeoWs request did not fail closed");
  requireCondition(
    header(invalid.response.headers, "cache-control").includes("no-store"),
    "Invalid NeoWs response is cacheable",
  );

  return { mode: "full", baseUrl: baseUrl.href };
}

function readArgument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}

async function main() {
  const mode = readArgument("--mode") || "structural";
  const base = readArgument("--base") || DEFAULT_BASE_URL;
  requireCondition(["structural", "full"].includes(mode), "Mode must be structural or full");

  const result =
    mode === "full"
      ? await runFullSmoke(base)
      : await runStructuralSmoke(base);
  console.log(`NASA Data Hub ${result.mode} production smoke passed: ${result.baseUrl}`);
}

const isCli = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isCli) {
  main().catch((error) => {
    console.error(`NASA Data Hub production smoke failed: ${error?.message || error}`);
    process.exitCode = 1;
  });
}
