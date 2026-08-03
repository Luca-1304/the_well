import {
  clearOutput,
  copyShareLink,
  element,
  externalLink,
  officialApodUrl,
  rawDisclosure,
  requestJson,
  safeHttpUrl,
} from "./common.js";

export function initApod({ onSuccess, sharedState }) {
  const form = document.getElementById("apod-form");
  const output = document.getElementById("apod-output");
  const dateInput = document.getElementById("apod-date");
  const shareButton = document.getElementById("apod-share");

  async function load() {
    const date = dateInput.value;
    const payload = await requestJson(`/api/apod?date=${encodeURIComponent(date)}`, output);
    if (!payload) return;

    clearOutput(output);
    const data = payload.data;
    const layout = element("article", { className: "apod-layout" });
    const media = element("div", { className: "media-frame" });
    const mediaUrl = safeHttpUrl(data.url);

    if (data.media_type === "image" && mediaUrl) {
      media.append(
        element("img", {
          src: mediaUrl,
          alt: data.title || "NASA Astronomy Picture of the Day",
          loading: "eager",
          decoding: "async",
        }),
      );
    } else if (mediaUrl) {
      media.append(
        element("div", { className: "video-fallback" }, [
          element("strong", { text: "This APOD is a video." }),
          externalLink("Open official media", mediaUrl, "button-link"),
        ]),
      );
    } else {
      media.append(element("div", { className: "message", text: "No media URL was returned." }));
    }

    const copy = element("div", { className: "apod-copy" }, [
      element("p", { className: "eyebrow", text: data.date || date }),
      element("h3", { text: data.title || "Untitled astronomy image" }),
      element("p", { className: "explanation", text: data.explanation || "No explanation was returned." }),
    ]);

    const attribution = [];
    if (data.copyright) attribution.push(element("span", { text: `Credit: ${data.copyright}` }));
    attribution.push(externalLink("Official APOD page", officialApodUrl(data.date || date)));
    if (safeHttpUrl(data.hdurl)) attribution.push(externalLink("High-resolution media", data.hdurl));
    copy.append(element("div", { className: "source-row" }, attribution.filter(Boolean)));

    layout.append(media, copy);
    output.append(layout, rawDisclosure(payload));
    onSuccess("APOD");
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    load();
  });
  shareButton.addEventListener("click", () =>
    copyShareLink("apod", { date: dateInput.value }, shareButton),
  );

  if (sharedState?.view === "apod") {
    if (sharedState.params.date) dateInput.value = sharedState.params.date;
    load();
  }
}
