import { initApod } from "./features/apod.js";
import { initDonki } from "./features/donki.js";
import { initEonet } from "./features/eonet.js";
import {
  formatLocalInputDate,
  parseResponseText,
  readShareState,
} from "./features/common.js";
import { initNeo } from "./features/neo.js";

const stabilityStyles = document.createElement("link");
stabilityStyles.rel = "stylesheet";
stabilityStyles.href = "/stability.css";
document.head.append(stabilityStyles);

const today = formatLocalInputDate();
for (const id of ["apod-date", "neo-start", "neo-end", "donki-start", "donki-end"]) {
  const input = document.getElementById(id);
  if (input) {
    input.value = today;
    input.max = today;
  }
}

const statusText = document.getElementById("service-status");
const refreshText = document.getElementById("last-refresh");
const sharedState = readShareState();

function recordSuccess(label) {
  const now = new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date());
  refreshText.textContent = `${label} refreshed ${now}`;
}

async function loadHealth() {
  const state = statusText.closest(".service-state");
  try {
    const response = await fetch("/api/health", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const payload = parseResponseText(await response.text(), "Health check");
    if (!response.ok || !payload.ok) throw new Error("Health check failed");
    statusText.textContent = payload.using_demo_key
      ? "Service live · public NASA quota"
      : "Service live · private server quota";
    state?.classList.remove("is-warning");
    state?.classList.add("is-live");
  } catch {
    statusText.textContent = "Service status unavailable";
    state?.classList.remove("is-live");
    state?.classList.add("is-warning");
  }
}

const context = { onSuccess: recordSuccess, sharedState };
initApod(context);
initNeo(context);
initDonki(context);
initEonet(context);
loadHealth();

if (sharedState) {
  const section = document.getElementById(sharedState.view);
  section?.scrollIntoView({ block: "start" });
}

const navLinks = [...document.querySelectorAll(".section-nav a")];
const sections = navLinks
  .map((link) => document.querySelector(link.getAttribute("href")))
  .filter(Boolean);

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (!visible) return;
      for (const link of navLinks) {
        const active = link.getAttribute("href") === `#${visible.target.id}`;
        link.toggleAttribute("aria-current", active);
      }
    },
    { rootMargin: "-25% 0px -60%", threshold: [0.05, 0.25, 0.5] },
  );
  sections.forEach((section) => observer.observe(section));
}
