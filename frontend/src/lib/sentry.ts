import * as Sentry from "@sentry/react";

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || "development";
  const isProd = environment === "production";

  Sentry.init({
    dsn,
    environment,
    release: import.meta.env.VITE_APP_VERSION || "procureai-frontend@dev",
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration(),
    ],
    tracesSampleRate: isProd ? 0.3 : 1.0,
    tracePropagationTargets: ["localhost", /^http:\/\/localhost:8000/],
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}
