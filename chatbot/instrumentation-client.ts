import { initBotId } from "botid/client/core";

const isBotIdEnabled = process.env.NEXT_PUBLIC_ENABLE_BOTID === "1";

if (isBotIdEnabled) {
  initBotId({
    protect: [
      {
        path: "/api/chat",
        method: "POST",
      },
    ],
  });
}

const CJS_NOISE_PATTERN = /\/c\.js\?i=\d+.*h=naito\.chat/i;

if (typeof window !== "undefined") {
  window.addEventListener(
    "error",
    (event) => {
      const source = event.filename || "";
      if (CJS_NOISE_PATTERN.test(source)) {
        event.preventDefault();
      }
    },
    true
  );

  window.addEventListener("unhandledrejection", (event) => {
    const reasonText = String(
      (event.reason as Error | string | undefined) ?? ""
    );
    if (CJS_NOISE_PATTERN.test(reasonText)) {
      event.preventDefault();
    }
  });
}
