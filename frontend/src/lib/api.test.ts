import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "@/lib/api";

/** Await a request that is expected to reject, and return its ApiError. */
async function expectApiError(request: Promise<unknown>): Promise<ApiError> {
  try {
    await request;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("Expected the request to fail.");
}

function mockResponse(status: number, body: unknown, ok = status < 400) {
  return {
    ok,
    status,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  } as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe("apiFetch", () => {
  it("returns the parsed body on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => mockResponse(200, { id: "1", name: "Nightly sync" })),
    );

    await expect(apiFetch("/api/workflows/1")).resolves.toEqual({ id: "1", name: "Nightly sync" });
  });

  it("sends credentials so the session cookie is included", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => mockResponse(200, {}));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/auth/me");

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "include" });
  });

  it("omits empty query parameters from the URL", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => mockResponse(200, {}));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/workflows", { query: { search: "", status: "active", limit: 20 } });

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("status=active");
    expect(url).toContain("limit=20");
    expect(url).not.toContain("search=");
  });

  it("returns undefined for a 204 without parsing a body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, status: 204 }) as Response),
    );

    await expect(apiFetch("/api/auth/logout")).resolves.toBeUndefined();
  });

  it("turns the API error envelope into an ApiError with its code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        mockResponse(404, { detail: { code: "not_found", message: "Workflow not found." } }),
      ),
    );

    const error = await expectApiError(apiFetch("/api/workflows/missing"));

    expect(error.status).toBe(404);
    expect(error.code).toBe("not_found");
    expect(error.message).toBe("Workflow not found.");
    expect(error.isNotFound).toBe(true);
  });

  it("collapses request validation problems into field errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        mockResponse(422, {
          detail: [
            { loc: ["body", "name"], msg: "String should have at least 1 character" },
            { loc: ["body", "description"], msg: "Too long" },
          ],
        }),
      ),
    );

    const error = await expectApiError(apiFetch("/api/workflows", { method: "POST" }));

    expect(error.code).toBe("validation_error");
    expect(error.fieldErrors.name).toEqual(["String should have at least 1 character"]);
    expect(error.fieldErrors.description).toEqual(["Too long"]);
  });

  it("flags a 401 so the client can send the visitor to sign in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        mockResponse(401, { detail: { code: "unauthenticated", message: "Sign in to continue." } }),
      ),
    );

    const error = await expectApiError(apiFetch("/api/auth/me"));

    expect(error.isUnauthorized).toBe(true);
  });
});
