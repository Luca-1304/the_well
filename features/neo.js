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

function flattenObjects(data) {
  return Object.values(data?.near_earth_objects || {}).flat().map((object) => {
    const approach = object.close_approach_data?.[0] || {};
    return {
      id: object.id,
      name: object.name,
      hazardous: Boolean(object.is_potentially_hazardous_asteroid),
      minDiameter: Number(object.estimated_diameter?.meters?.estimated_diameter_min),
      maxDiameter: Number(object.estimated_diameter?.meters?.estimated_diameter_max),
      speed: Number(approach.relative_velocity?.kilometers_per_hour),
      missKm: Number(approach.miss_distance?.kilometers),
      missLunar: Number(approach.miss_distance?.lunar),
      approachTime: approach.close_approach_date_full
        ? `${approach.close_approach_date_full.replace("-", " ")} UTC`
        : approach.close_approach_date,
      source: object.nasa_jpl_url,
      raw: object,
    };
  });
}

function sortObjects(objects, sort) {
  const copy = [...objects];
  const accessors = {
    closest: (item) => item.missKm,
    largest: (item) => -item.maxDiameter,
    fastest: (item) => -item.speed,
    hazardous: (item) => (item.hazardous ? 0 : 1),
  };
  return copy.sort((left, right) => accessors[sort](left) - accessors[sort](right));
}

function metric(label, value) {
  return element("div", { className: "summary-metric" }, [
    element("span", { text: label }),
    element("strong", { text: value }),
  ]);
}

export function initNeo({ onSuccess, sharedState }) {
  const form = document.getElementById("neo-form");
  const output = document.getElementById("neo-output");
  const startInput = document.getElementById("neo-start");
  const endInput = document.getElementById("neo-end");
  const sortInput = document.getElementById("neo-sort");
  const shareButton = document.getElementById("neo-share");
  let lastPayload = null;

  function render(payload) {
    const objects = sortObjects(flattenObjects(payload.data), sortInput.value);
    if (!objects.length) {
      showEmpty(output, "NASA returned no close approaches for this window.");
      return;
    }

    clearOutput(output);
    const hazardousCount = objects.filter((item) => item.hazardous).length;
    const closest = Math.min(...objects.map((item) => item.missLunar));
    output.append(
      element("div", { className: "summary-strip" }, [
        metric("Objects", formatNumber(objects.length, 0)),
        metric("Flagged potentially hazardous", formatNumber(hazardousCount, 0)),
        metric("Closest approach", `${formatNumber(closest, 2)} lunar distances`),
      ]),
      element("p", {
        className: "context-note",
        text: "NASA's potentially hazardous classification reflects size and orbital proximity criteria; it does not mean an impact is predicted.",
      }),
    );

    const table = element("table", { className: "data-table" });
    table.append(
      element("thead", {}, [
        element("tr", {}, [
          element("th", { text: "Object", scope: "col" }),
          element("th", { text: "Estimated diameter", scope: "col" }),
          element("th", { text: "Relative speed", scope: "col" }),
          element("th", { text: "Miss distance", scope: "col" }),
          element("th", { text: "Closest approach", scope: "col" }),
          element("th", { text: "Status", scope: "col" }),
        ]),
      ]),
    );
    const body = element("tbody");

    for (const object of objects) {
      const nameCell = element("td");
      nameCell.append(
        externalLink(object.name || `Object ${object.id}`, object.source, "object-link") ||
          element("span", { text: object.name || `Object ${object.id}` }),
      );
      body.append(
        element("tr", {}, [
          nameCell,
          element("td", { text: `${formatNumber(object.minDiameter)}–${formatNumber(object.maxDiameter)} m` }),
          element("td", { text: `${formatNumber(object.speed, 0)} km/h` }),
          element("td", {}, [
            element("strong", { text: `${formatNumber(object.missLunar, 2)} LD` }),
            element("small", { text: `${formatNumber(object.missKm, 0)} km` }),
          ]),
          element("td", { text: object.approachTime || "—" }),
          element("td", {}, [
            element("span", {
              className: object.hazardous ? "status-badge status-watch" : "status-badge status-clear",
              text: object.hazardous ? "Potentially hazardous" : "No hazard flag",
            }),
          ]),
        ]),
      );
    }
    table.append(body);
    output.append(element("div", { className: "table-scroll" }, [table]), rawDisclosure(payload));
    onSuccess("Near-Earth Objects");
  }

  async function load() {
    const start = startInput.value;
    const end = endInput.value || start;
    const payload = await requestJson(
      `/api/neo?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      output,
    );
    if (!payload) return;
    lastPayload = payload;
    render(payload);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });
  sortInput.addEventListener("change", () => {
    if (lastPayload) render(lastPayload);
  });
  shareButton.addEventListener("click", () =>
    copyShareLink(
      "neo",
      { start: startInput.value, end: endInput.value, sort: sortInput.value },
      shareButton,
    ),
  );

  if (sharedState?.view === "neo") {
    if (sharedState.params.start) startInput.value = sharedState.params.start;
    if (sharedState.params.end) endInput.value = sharedState.params.end;
    if (["closest", "largest", "fastest", "hazardous"].includes(sharedState.params.sort)) {
      sortInput.value = sharedState.params.sort;
    }
    load();
  }
}
