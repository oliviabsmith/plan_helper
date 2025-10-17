const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");

if (!API_BASE_URL) {
  // eslint-disable-next-line no-console
  console.warn("VITE_API_BASE_URL is not set. API requests will likely fail.");
}

export const env = {
  apiBaseUrl: API_BASE_URL ?? "",
};
