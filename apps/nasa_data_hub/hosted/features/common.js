const SHARE_ALLOWLIST = {
  apod: ["date"],
  neo: ["start", "end", "sort"],
  donki: ["type", "start", "end"],
  eonet: ["status", "days", "category"],
};

const CREDENTIAL_PATTERN = /(api[_-]?key|authorization|bearer\s|token=|secret=)/i;

export function element(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(options)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "className") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("aria")) node.setAttribute(key.replace(/[A-Z]/g, (match) => `-${match.toLowerCase()}`), value);
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child !== null && child !== undefined) node.append(child);
  }
  return node;
}

export function safeHttpUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function externalLink(label, value, className = "source-link") {
  const href = safeHttpUrl(value);
  if (!href) return null;
  return element("a", {
    className,
    text: label,
    href,
    target: "_blank",
    rel: "noopener noreferrer",
  });
}

export function clearOutput(output) {
  output.replaceChildren();
  output.classList.remove("state-error", "state-loading", "state-empty");
}

export function showLoading(output, label = "Loading current data…") {
  clearOutput(output);
  output.classList.add("state-loading");
  output.append(
    element("div", { className: "loading-row" }, [
      element("span", { className: "spinner", ariaHidden: "true" }),
      element("span", { text: label }),
    ]),
  );
}

export function showError(output, message) {
  clearOutput(output);
  output.classList.add("state-error");
  output.append(
    element("div", { className: "message message-error", role: "alert" }, [
      element("strong", { text: "Could not load this view." }),
      element("span", { text: message }),
    ]),
  );
}

export function showEmpty(output, message) {
  clearOutput(output);
  output.classList.add("state-empty");
  output.append(
    element("div", { className: "message" }, [
      element("strong", { text: "No matching events." }),
      element("span", { text: message }),
    ]),
  );
}

export async function requestJson(path, output) {
  const url = new URL(path, window.location.origin);
  if (url.origin !== window.location.origin) {
    showError(output, "Blocked a non-local data request.");
    return null;
  }

  showLoading(output);
  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      const retry = response.headers.get("retry-after");
      const suffix = retry ? ` Try again in about ${retry} seconds.` : "";
      throw new Error(`${payload.error || `HTTP ${response.status}`}${suffix}`);
    }
    return payload;
  } catch (error) {
    showError(output, error?.message || "Unexpected request failure.");
    return null;
  }
}

export function formatNumber(value, maximumFractionDigits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return new Intl.NumberFormat("en-GB", { maximumFractionDigits }).format(number);
}

export function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "—";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date) + " UTC";
}

export function rawDisclosure(value) {
  const details = element("details", { className: "raw-data" });
  details.append(
    element("summary", { text: "View raw public response" }),
    element("pre", { text: JSON.stringify(value, null, 2) }),
  );
  return details;
}

export function buildShareUrl(view, params = {}, base = window.location.href) {
  if (!Object.hasOwn(SHARE_ALLOWLIST, view)) throw new Error("Unknown share view");
  const url = new URL(base);
  url.search = "";
  url.hash = view;
  url.searchParams.set("view", view);

  for (const key of SHARE_ALLOWLIST[view]) {
    const value = String(params[key] ?? "").trim();
    if (!value || value.length > 100 || CREDENTIAL_PATTERN.test(value)) continue;
    url.searchParams.set(key, value);
  }
  return url.href;
}

export function readShareState() {
  const query = new URLSearchParams(window.location.search);
  const view = query.get("view");
  if (!view || !Object.hasOwn(SHARE_ALLOWLIST, view)) return null;
  const params = {};
  for (const key of SHARE_ALLOWLIST[view]) {
    const value = query.get(key);
    if (value && value.length <= 100 && !CREDENTIAL_PATTERN.test(value)) params[key] = value;
  }
  return { view, params };
}

export async function copyShareLink(view, params, button) {
  const url = buildShareUrl(view, params);
  try {
    await navigator.clipboard.writeText(url);
    const previous = button.textContent;
    button.textContent = "Link copied";
    window.setTimeout(() => {
      button.textContent = previous;
    }, 1800);
  } catch {
    window.history.replaceState({}, "", url);
    button.textContent = "Link ready in address bar";
  }
}

export function officialApodUrl(date) {
  const compact = String(date || "").replaceAll("-", "").slice(2);
  return /^\d{6}$/.test(compact)
    ? `https://apod.nasa.gov/apod/ap${compact}.html`
    : "https://apod.nasa.gov/apod/";
}
