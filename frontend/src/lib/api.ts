/**
 * Thin typed wrapper around `fetch` for the FlowForge API.
 *
 * The API is a separate origin in development, so every request opts into
 * cookie credentials. Errors are normalised into `ApiError` so UI code can
 * render a useful message instead of a stack trace.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Field level validation problems keyed by a dotted field path. */
export type FieldErrors = Record<string, string[]>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldErrors;
  readonly details: unknown;

  constructor(
    status: number,
    message: string,
    options: { code?: string; fieldErrors?: FieldErrors; details?: unknown } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = options.code ?? "error";
    this.fieldErrors = options.fieldErrors ?? {};
    this.details = options.details;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

type Json = Record<string, unknown>;

function isJsonObject(value: unknown): value is Json {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * FastAPI returns `{"detail": ...}` for HTTPException and a list of problems
 * for request validation failures. Both shapes are collapsed here.
 */
function parseErrorBody(status: number, body: unknown): ApiError {
  if (isJsonObject(body)) {
    const detail = body.detail;

    if (typeof detail === "string") {
      return new ApiError(status, detail, { code: String(body.code ?? "error") });
    }

    if (isJsonObject(detail) && typeof detail.message === "string") {
      return new ApiError(status, detail.message, {
        code: typeof detail.code === "string" ? detail.code : "error",
        details: detail.details,
      });
    }

    if (Array.isArray(detail)) {
      const fieldErrors: FieldErrors = {};
      for (const item of detail) {
        if (!isJsonObject(item)) continue;
        const loc = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "_";
        const message = typeof item.msg === "string" ? item.msg : "Invalid value";
        (fieldErrors[loc] ??= []).push(message);
      }
      const first = Object.values(fieldErrors)[0]?.[0];
      return new ApiError(status, first ?? "The request was rejected.", {
        code: "validation_error",
        fieldErrors,
      });
    }
  }

  return new ApiError(status, `Request failed with status ${status}.`);
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** Serialised as JSON unless it is already a `BodyInit`. */
  body?: unknown;
  /** Appended to the URL, skipping `undefined` and `null` values. */
  query?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, query, headers, ...rest } = options;

  const isRawBody = body instanceof FormData || body instanceof URLSearchParams;
  const response = await fetch(buildUrl(path, query), {
    ...rest,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(body !== undefined && !isRawBody ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : isRawBody ? body : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const parsed: unknown = text ? safeJsonParse(text) : null;

  if (!response.ok) {
    throw parseErrorBody(response.status, parsed);
  }

  return parsed as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};
