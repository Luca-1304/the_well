import { initApod } from "./features/apod.js";
import { initDonki } from "./features/donki.js";
import { initEonet } from "./features/eonet.js";
import { readShareState } from "./features/common.js";
import { initNeo } from "./features/neo.js";

const today = new Date().toISOString().slice(0, 10);
for (const id of ["apod-date", "neo-start", "neo-end", "donki-start", "donki-end"]) {
  const input = document.getElementById(id);
  if (input) input.value = today;
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
  try {
    const response = await fetch("/api/health", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error("Health check failed");
    statusText.textContent = payload.using_demo_key
      ? "Service live · public NASA quota"
      : "Service live · private server quota";
    statusText.closest(".service-state")?.classList.add("is-live");
  } catch {
    statusText.textContent = "Service status unavailable";
    statusText.closest(".service-state")?.classList.add("is-warning");
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
