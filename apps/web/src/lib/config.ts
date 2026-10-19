import "server-only";

const DEFAULT_API_URL = "http://localhost:8000";

export function apiBaseUrl(): string {
  return process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? DEFAULT_API_URL;
}
