import {
  clearOutput,
  copyShareLink,
  element,
  externalLink,
  formatDateTime,
  formatNumber,
  rawDisclosure,
  requestJson,
  showEmpty,
} from "./common.js";

function latestGeometry(event) {
  const geometries = Array.isArray(event.geometry) ? event.geometry : [];
  return geometries.at(-1) || null;
}

function coordinateText(geometry) {
  const coordinates = geometry?.coordinates;
  if (!Array.isArray(coordinates) || coordinates.length < 2) return null;
  const [longitude, latitude] = coordinates;
  if (!Number.isFinite(Number(longitude)) || !Number.isFinite(Number(latitude))) return null;
  return `${formatNumber(latitude, 3)}, ${formatNumber(longitude, 3)}`;
}

export function initEonet({ onSuccess, sharedState }) {
  const form = document.getElementById("eonet-form");
  const output = document.getElementById("eonet-output");
  const statusInput = document.getElementById("eonet-status");
  const daysInput = document.getElementById("eonet-days");
  const categoryInput = document.getElementById("eonet-category");
  const shareButton = document.getElementById("eonet-share");

  async function load() {
    const query = new URLSearchParams({ status: statusInput.value, limit: "30" });
    if (daysInput.value) query.set("days", daysInput.value);
    if (categoryInput.value.trim()) query.set("category", categoryInput.value.trim());

    const payload = await requestJson(`/api/eonet?${query}`, output);
    if (!payload) return;
    const events = payload.data?.events || [];
    if (!events.length) {
      showEmpty(output, "Try a wider date range or remove the category filter.");
      return;
    }

    clearOutput(output);
    output.append(
      element("div", { className: "summary-strip" }, [
        element("div", { className: "summary-metric" }, [
          element("span", { text: "Events returned" }),
          element("strong", { text: String(events.length) }),
        ]),
        element("div", { className: "summary-metric" }, [
          element("span", { text: "Status filter" }),
          element("strong", { text: statusInput.value }),
        ]),
      ]),
      element("p", {
        className: "context-note",
        text: "EONET aggregates reported natural events from source agencies. Entries may be delayed, revised or incomplete and should not replace local emergency guidance.",
      }),
    );

    const grid = element("div", { className: "event-grid" });
    for (const event of events) {
      const geometry = latestGeometry(event);
      const categories = (event.categories || []).map((category) => category.title).filter(Boolean);
      const facts = [];
      if (categories.length) facts.push(`Category: ${categories.join(", ")}`);
      if (geometry?.date) facts.push(`Latest observation: ${formatDateTime(geometry.date)}`);
      const coordinates = coordinateText(geometry);
      if (coordinates) facts.push(`Coordinates: ${coordinates}`);
      if (geometry?.magnitudeValue !== null && geometry?.magnitudeValue !== undefined) {
        facts.push(`Magnitude: ${formatNumber(geometry.magnitudeValue)} ${geometry.magnitudeUnit || ""}`.trim());
      }

      const card = element("article", { className: "event-card" }, [
        element("div", { className: "event-card-header" }, [
          element("div", {}, [
            element("p", { className: "eyebrow", text: event.closed ? "Closed event" : "Open event" }),
            element("h3", { text: event.title || event.id || "Natural event" }),
          ]),
        ]),
      ]);
      if (event.description) card.append(element("p", { text: event.description }));
      card.append(
        element(
          "ul",
          { className: "fact-list" },
          facts.map((fact) => element("li", { text: fact })),
        ),
      );

      const sourceRow = element("div", { className: "source-row" });
      const eventLink = externalLink("EONET event record", event.link);
      if (eventLink) sourceRow.append(eventLink);
      for (const source of (event.sources || []).slice(0, 3)) {
        const link = externalLink(source.id ? `${source.id} source` : "Source agency", source.url);
        if (link) sourceRow.append(link);
      }
      card.append(sourceRow);
      grid.append(card);
    }

    output.append(grid, rawDisclosure(payload));
    onSuccess("Earth Natural Events");
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });
  shareButton.addEventListener("click", () =>
    copyShareLink(
      "eonet",
      {
        status: statusInput.value,
        days: daysInput.value,
        category: categoryInput.value.trim(),
      },
      shareButton,
    ),
  );

  if (sharedState?.view === "eonet") {
    if (["open", "closed", "all"].includes(sharedState.params.status)) {
      statusInput.value = sharedState.params.status;
    }
    if (/^\d{1,4}$/.test(sharedState.params.days || "")) daysInput.value = sharedState.params.days;
    if (sharedState.params.category) categoryInput.value = sharedState.params.category;
    load();
  }
}
