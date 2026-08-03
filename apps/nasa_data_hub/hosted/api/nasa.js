const NASA_BASE_URL = "https://api.nasa.gov";
const EONET_BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3";
const RETRYABLE_STATUS = new Set([429, 500, 502, 503, 504]);
const DONKI_ENDPOINTS = new Map(
  [
    "CME",
    "CMEAnalysis",
    "GST",
    "IPS",
    "FLR",
    "SEP",
    "MPC",
    "RBE",
    "HSS",
    "WSAEnlilSimulations",
    "notifications",
  ].map((name) => [name.toLowerCase(), name]),
);

export const COURTESY_LIMITS = Object.freeze({
  nasa: Object.freeze({ limit: 8, windowMs: 10 * 60 * 1000 }),
  eonet: Object.freeze({ limit: 30, windowMs: 10 * 60 * 1000 }),
});

const wait = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

function runtimeState() {
  if (!globalThis.__NASA_DATA_HUB_RUNTIME__) {
    globalThis.__NASA_DATA_HUB_RUNTIME__ = {
      inflight: new Map(),
      limits: new Map(),
    };
  }
  return globalThis.__NASA_DATA_HUB_RUNTIME__;
}

export function resetRuntimeStateForTests() {
  const state = runtimeState();
  state.inflight.clear();
  state.limits.clear();
}

export function single(value) {
  return Array.isArray(value) ? value[0] : value;
}

export function isIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? "")) return false;
  return new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}

function dateDistance(start, end) {
  return (
    (Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) /
    86_400_000
  );
}

function headerValue(request, name) {
  const headers = request?.headers;
  if (!headers) return null;
  if (typeof headers.get === "function") return headers.get(name);
  const match = Object.entries(headers).find(
    ([key]) => key.toLowerCase() === name.toLowerCase(),
  );
  return match ? single(match[1]) : null;
}

function clientIdentifier(request) {
  const forwarded = String(headerValue(request, "x-forwarded-for") || "")
    .split(",")[0]
    .trim();
  return forwarded || String(headerValue(request, "x-real-ip") || "anonymous");
}

export function checkCourtesyLimit(request, mode, now = Date.now()) {
  if (mode === "health") {
    return { allowed: true, remaining: null, retryAfter: 0, limit: null };
  }

  const family = mode === "eonet" ? "eonet" : "nasa";
  const policy = COURTESY_LIMITS[family];
  const key = `${family}:${clientIdentifier(request)}`;
  const state = runtimeState();
  const existing = state.limits.get(key);
  const bucket =
    !existing || now - existing.startedAt >= policy.windowMs
      ? { startedAt: now, count: 0 }
      : existing;

  bucket.count += 1;
  state.limits.set(key, bucket);
  const allowed = bucket.count <= policy.limit;
  return {
    allowed,
    limit: policy.limit,
    remaining: Math.max(0, policy.limit - bucket.count),
    retryAfter: allowed
      ? 0
      : Math.max(1, Math.ceil((bucket.startedAt + policy.windowMs - now) / 1000)),
  };
}

export function scrubApiKeys(value) {
  if (Array.isArray(value)) return value.map(scrubApiKeys);

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, scrubApiKeys(item)]),
    );
  }

  if (typeof value !== "string" || !/api_key=/i.test(value)) return value;

  try {
    const url = new URL(value);
    for (const key of [...url.searchParams.keys()]) {
      if (key.toLowerCase() === "api_key") url.searchParams.delete(key);
    }
    return url.toString();
  } catch {
    return value
      .replace(/([?&])api_key=[^&#]*/gi, "$1")
      .replace(/\?&/, "?")
      .replace(/[?&]$/, "");
  }
}

function upstreamDedupeKey(url) {
  const safe = new URL(url);
  for (const key of [...safe.searchParams.keys()]) {
    if (key.toLowerCase() === "api_key") safe.searchParams.delete(key);
  }
  safe.searchParams.sort();
  return safe.href;
}

export function deduplicatedFetch(key, operation) {
  const state = runtimeState();
  if (state.inflight.has(key)) return state.inflight.get(key);

  const promise = Promise.resolve()
    .then(operation)
    .finally(() => state.inflight.delete(key));
  state.inflight.set(key, promise);
  return promise;
}

export async function fetchJson(url, { authenticated = false } = {}) {
  const requestUrl = new URL(url);
  if (authenticated) {
    requestUrl.searchParams.set(
      "api_key",
      process.env.NASA_API_KEY?.trim() || "DEMO_KEY",
    );
  }

  return deduplicatedFetch(upstreamDedupeKey(requestUrl), async () => {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15_000);

      try {
        const response = await fetch(requestUrl, {
          headers: {
            Accept: "application/json",
            "User-Agent": "luca-nasa-data-hub/1.1",
          },
          signal: controller.signal,
        });
        const text = await response.text();

        let payload;
        try {
          payload = scrubApiKeys(text ? JSON.parse(text) : null);
        } catch {
          throw Object.assign(new Error("NASA service returned invalid JSON"), {
            status: 502,
          });
        }

        if (!response.ok) {
          if (RETRYABLE_STATUS.has(response.status) && attempt < 2) {
            await wait(350 * 2 ** attempt);
            continue;
          }

          const message =
            payload?.error?.message ??
            payload?.error ??
            payload?.msg ??
            payload?.message ??
            `NASA service returned HTTP ${response.status}`;
          throw Object.assign(new Error(String(message)), {
            status: response.status,
          });
        }

        return {
          data: payload,
          rate_limit: {
            limit: response.headers.get("x-ratelimit-limit"),
            remaining: response.headers.get("x-ratelimit-remaining"),
          },
        };
      } catch (error) {
        const networkFailure =
          error?.name === "AbortError" || error instanceof TypeError;
        if (networkFailure && attempt < 2) {
          await wait(350 * 2 ** attempt);
          continue;
        }
        if (networkFailure) {
          throw Object.assign(
            new Error("Could not reach the NASA service. Try again shortly."),
            { status: 502 },
          );
        }
        throw error;
      } finally {
        clearTimeout(timeout);
      }
    }

    throw Object.assign(new Error("NASA request failed after retries"), {
      status: 502,
    });
  });
}

export function buildEonetUrl(query = {}) {
  const status = single(query.status) || "open";
  const limit = Number(single(query.limit) || 30);
  const days = single(query.days) ? Number(single(query.days)) : null;

  if (!["open", "closed", "all"].includes(status)) {
    throw Object.assign(new Error("Invalid EONET status"), { status: 400 });
  }
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw Object.assign(new Error("EONET limit must be between 1 and 100"), {
      status: 400,
    });
  }
  if (
    days !== null &&
    (!Number.isInteger(days) || days < 1 || days > 3650)
  ) {
    throw Object.assign(
      new Error("EONET days must be between 1 and 3650"),
      { status: 400 },
    );
  }

  const url = new URL(`${EONET_BASE_URL}/events`);
  url.searchParams.set("status", status);
  url.searchParams.set("limit", String(limit));
  if (days !== null) url.searchParams.set("days", String(days));

  const categories = Array.isArray(query.category)
    ? query.category
    : query.category
      ? [query.category]
      : [];
  for (const rawCategory of categories) {
    const category = String(rawCategory).trim();
    if (!category || category.length > 80) {
      throw Object.assign(new Error("Invalid EONET category"), { status: 400 });
    }
    url.searchParams.append("category", category);
  }

  return url;
}

function sendJson(response, status, payload, { cache = false, headers = {} } = {}) {
  response.setHeader(
    "Cache-Control",
    cache
      ? "public, s-maxage=300, stale-while-revalidate=3600"
      : "no-store",
  );
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("X-Robots-Tag", "noindex");
  for (const [name, value] of Object.entries(headers)) {
    response.setHeader(name, String(value));
  }
  return response.status(status).json(payload);
}

export default async function handler(request, response) {
  if (request.method !== "GET") {
    response.setHeader("Allow", "GET");
    return sendJson(response, 405, { ok: false, error: "Method not allowed" });
  }

  const query = request.query ?? {};
  const mode = single(query.mode) || "health";
  const usingDemoKey = !(process.env.NASA_API_KEY || "").trim();

  try {
    if (mode === "health") {
      return sendJson(response, 200, {
        ok: true,
        service: "NASA Data Hub",
        version: "1.1",
        key_mode: usingDemoKey ? "demo" : "personal",
        using_demo_key: usingDemoKey,
        privacy: "no account or tracking profile",
      });
    }

    if (!["apod", "neo", "donki", "eonet"].includes(mode)) {
      return sendJson(response, 404, { ok: false, error: "Unknown API route" });
    }

    const courtesy = checkCourtesyLimit(request, mode);
    const courtesyHeaders = {
      "X-Courtesy-Limit": courtesy.limit,
      "X-Courtesy-Remaining": courtesy.remaining,
    };
    if (!courtesy.allowed) {
      return sendJson(
        response,
        429,
        {
          ok: false,
          error: "This browser has reached the temporary public-data courtesy limit.",
        },
        {
          headers: {
            ...courtesyHeaders,
            "Retry-After": courtesy.retryAfter,
          },
        },
      );
    }

    let result;

    if (mode === "apod") {
      const day = single(query.date);
      if (day && !isIsoDate(day)) {
        throw Object.assign(new Error("Use YYYY-MM-DD"), { status: 400 });
      }
      const url = new URL("/planetary/apod", NASA_BASE_URL);
      if (day) url.searchParams.set("date", day);
      url.searchParams.set("thumbs", "true");
      result = await fetchJson(url, { authenticated: true });
    } else if (mode === "neo") {
      const start = single(query.start);
      const end = single(query.end) || start;
      if (!isIsoDate(start) || !isIsoDate(end)) {
        throw Object.assign(
          new Error("start and end must use YYYY-MM-DD"),
          { status: 400 },
        );
      }
      const distance = dateDistance(start, end);
      if (distance < 0 || distance > 7) {
        throw Object.assign(
          new Error(
            distance < 0
              ? "end cannot precede start"
              : "Near-Earth Object windows cannot exceed seven days",
          ),
          { status: 400 },
        );
      }
      const url = new URL("/neo/rest/v1/feed", NASA_BASE_URL);
      url.searchParams.set("start_date", start);
      url.searchParams.set("end_date", end);
      result = await fetchJson(url, { authenticated: true });
    } else if (mode === "donki") {
      const endpoint = DONKI_ENDPOINTS.get(
        String(single(query.type) || "FLR").toLowerCase(),
      );
      const start = single(query.start);
      const end = single(query.end);
      if (!endpoint) {
        throw Object.assign(new Error("Unknown DONKI event type"), {
          status: 400,
        });
      }
      if (
        (start && !isIsoDate(start)) ||
        (end && !isIsoDate(end)) ||
        (start && end && dateDistance(start, end) < 0) ||
        (start && end && dateDistance(start, end) > 365)
      ) {
        throw Object.assign(new Error("Invalid DONKI date range"), {
          status: 400,
        });
      }
      const url = new URL(`/DONKI/${endpoint}`, NASA_BASE_URL);
      if (start) url.searchParams.set("startDate", start);
      if (end) url.searchParams.set("endDate", end);
      result = await fetchJson(url, { authenticated: true });
    } else {
      result = await fetchJson(buildEonetUrl(query));
    }

    return sendJson(
      response,
      200,
      { ok: true, ...result },
      { cache: true, headers: courtesyHeaders },
    );
  } catch (error) {
    const status = Number.isInteger(error?.status) ? error.status : 500;
    return sendJson(response, status, {
      ok: false,
      error: error?.message || "Unexpected server error",
    });
  }
}
