import "server-only";

import { apiBaseUrl } from "@/lib/config";

export type ApiErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "invalid"
  | "server"
  | "network";

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; kind: ApiErrorKind; message: string };

const REQUEST_TIMEOUT_MS = 10_000;

function classify(status: number): ApiErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 422 || status === 400) return "invalid";
  if (status >= 500) return "server";
  return "network";
}

function defaultMessage(kind: ApiErrorKind): string {
  switch (kind) {
    case "unauthorized":
      return "The API did not authorize this request. Check the API's AUTH_PROVIDER setting (see README).";
    case "forbidden":
      return "You do not have permission to view this resource.";
    case "not_found":
      return "The requested resource could not be found.";
    case "conflict":
      return "The request conflicts with the current state of the resource.";
    case "invalid":
      return "The request was rejected as invalid.";
    case "server":
      return "The API reported an unexpected error.";
    default:
      return "The API is not reachable.";
  }
}

function isFormData(body: unknown): body is FormData {
  return (
    body instanceof FormData ||
    (typeof body === "object" &&
      body !== null &&
      typeof (body as FormData).append === "function" &&
      typeof (body as FormData).get === "function")
  );
}

async function request<T>(
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<ApiResult<T>> {
  const url = `${apiBaseUrl()}/api/v1${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
      headers:
        body === undefined || isFormData(body)
          ? undefined
          : { "content-type": "application/json" },
      body:
        body === undefined
          ? undefined
          : isFormData(body)
            ? body
            : JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 0, kind: "network", message: defaultMessage("network") };
  }

  if (!response.ok) {
    const kind = classify(response.status);
    let message = defaultMessage(kind);
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail.length > 0) {
        message = payload.detail;
      }
    } catch {
      // Non-JSON error bodies fall back to the default message.
    }
    return { ok: false, status: response.status, kind, message };
  }

  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return { ok: true, status: response.status, data: undefined as T };
  }

  try {
    const data = (await response.json()) as T;
    return { ok: true, status: response.status, data };
  } catch {
    return { ok: true, status: response.status, data: undefined as T };
  }
}

export function apiGet<T>(path: string): Promise<ApiResult<T>> {
  return request<T>("GET", path);
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  timeoutMs?: number,
): Promise<ApiResult<T>> {
  return request<T>("POST", path, body, timeoutMs);
}

export function apiPatch<T>(path: string, body?: unknown): Promise<ApiResult<T>> {
  return request<T>("PATCH", path, body);
}

export function apiPut<T>(path: string, body?: unknown): Promise<ApiResult<T>> {
  return request<T>("PUT", path, body);
}

export function apiDelete(path: string): Promise<ApiResult<null>> {
  return request<null>("DELETE", path);
}
