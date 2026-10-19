import "server-only";

import { apiBaseUrl } from "@/lib/config";

export type BackendHealth =
  | { state: "up"; appName: string }
  | { state: "down"; reason: string };

type HealthBody = { status?: string };

export async function getBackendHealth(): Promise<BackendHealth> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/healthz`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) {
      return { state: "down", reason: `HTTP ${response.status}` };
    }
    const body = (await response.json()) as HealthBody;
    if (body.status !== "ok") {
      return { state: "down", reason: "unexpected response" };
    }
    return { state: "up", appName: "ai-lms" };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "unknown error";
    return { state: "down", reason };
  }
}
