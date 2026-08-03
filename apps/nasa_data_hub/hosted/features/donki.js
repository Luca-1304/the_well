import {
  clearOutput,
  copyShareLink,
  element,
  externalLink,
  formatDateTime,
  rawDisclosure,
  requestJson,
  showEmpty,
} from "./common.js";

const TYPE_NAMES = {
  FLR: "Solar flare",
  CME: "Coronal mass ejection",
  GST: "Geomagnetic storm",
  HSS: "High-speed stream",
  SEP: "Solar energetic particle event",
  notifications: "Space-weather notification",
};

function firstValue(event, keys) {
  for (const key of keys) {
    if (event?.[key] !== null && event?.[key] !== undefined && event[key] !== "") return event[key];
  }
  return null;
}

function eventTime(event) {
  return firstValue(event, [
    "beginTime",
    "startTime",
    "eventTime",
    "peakTime",
    "messageIssueTime",
    "submissionTime",
  ]);
}

function eventIdentifier(event) {
  return firstValue(event, [
    "flrID",
    "activityID",
    "gstID",
    "hssID",
    "sepID",
    "messageID",
  ]);
}

function eventSummary(event) {
  const parts = [];
  const flareClass = firstValue(event, ["classType"]);
  const location = firstValue(event, ["sourceLocation"]);
  const activeRegion = firstValue(event, ["activeRegionNum"]);
  const kp = event?.allKpIndex?.[0]?.kpIndex;
  const note = firstValue(event, ["note", "messageBody"]);

  if (flareClass) parts.push(`Class ${flareClass}`);
  if (location) parts.push(`Source ${location}`);
  if (activeRegion) parts.push(`Active region ${activeRegion}`);
  if (kp !== null && kp !== undefined) parts.push(`Kp index ${kp}`);
  if (note) parts.push(String(note).replace(/\s+/g, " ").trim().slice(0, 320));
  return parts;
}

export function initDonki({ onSuccess, sharedState }) {
  const form = document.getElementById("donki-form");
  const output = document.getElementById("donki-output");
  const typeInput = document.getElementById("donki-type");
  const startInput = document.getElementById("donki-start");
  const endInput = document.getElementById("donki-end");
  const shareButton = document.getElementById("donki-share");

  async function load() {
    const query = new URLSearchParams({
      type: typeInput.value,
      start: startInput.value,
      end: endInput.value,
    });
    const payload = await requestJson(`/api/donki?${query}`, output);
    if (!payload) return;
    if (!payload.data.length) {
      showEmpty(output, "No DONKI events were returned for this event type and date range.");
      return;
    }

    clearOutput(output);
    const label = TYPE_NAMES[typeInput.value] || typeInput.value;
    output.append(
      element("div", { className: "summary-strip" }, [
        element("div", { className: "summary-metric" }, [
          element("span", { text: "Event family" }),
          element("strong", { text: label }),
        ]),
        element("div", { className: "summary-metric" }, [
          element("span", { text: "Events returned" }),
          element("strong", { text: String(payload.data.length) }),
        ]),
      ]),
      element("p", {
        className: "context-note",
        text: "DONKI records observations and linked analyses of space-weather activity. Event presence alone does not imply an Earth impact or operational warning.",
      }),
    );

    const timeline = element("ol", { className: "timeline" });
    const sorted = [...payload.data].sort(
      (left, right) => new Date(eventTime(right) || 0) - new Date(eventTime(left) || 0),
    );

    for (const event of sorted) {
      const summaries = eventSummary(event);
      const header = element("div", { className: "timeline-header" }, [
        element("div", {}, [
          element("span", { className: "eyebrow", text: formatDateTime(eventTime(event)) }),
          element("h3", { text: eventIdentifier(event) ? `${label} · ${eventIdentifier(event)}` : label }),
        ]),
      ]);
      const link = externalLink("NASA DONKI source", event.link);
      if (link) header.append(link);

      const item = element("li", { className: "timeline-item" }, [header]);
      if (summaries.length) {
        item.append(
          element(
            "ul",
            { className: "inline-facts" },
            summaries.map((summary) => element("li", { text: summary })),
          ),
        );
      }
      timeline.append(item);
    }

    output.append(timeline, rawDisclosure(payload));
    onSuccess("Space Weather");
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });
  shareButton.addEventListener("click", () =>
    copyShareLink(
      "donki",
      { type: typeInput.value, start: startInput.value, end: endInput.value },
      shareButton,
    ),
  );

  if (sharedState?.view === "donki") {
    if (Object.hasOwn(TYPE_NAMES, sharedState.params.type)) typeInput.value = sharedState.params.type;
    if (sharedState.params.start) startInput.value = sharedState.params.start;
    if (sharedState.params.end) endInput.value = sharedState.params.end;
    load();
  }
}
