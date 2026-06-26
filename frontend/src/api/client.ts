const RAW_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  "http://localhost:8000";
const BASE_URL = RAW_BASE.replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      ...init,
    });
  } catch (error) {
    throw new Error(
      `Network error reaching ${url}. ${error instanceof Error ? error.message : ""}`.trim(),
    );
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response, url), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(
      `Expected JSON from ${url} but got ${contentType || "unknown content-type"}.`,
    );
  }

  return (await response.json()) as T;
}

export const isApiConfigured = () => Boolean(BASE_URL);

async function fetchSameOriginJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      ...init,
    });
  } catch (error) {
    throw new Error(
      `Network error reaching ${path}. ${error instanceof Error ? error.message : ""}`.trim(),
    );
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response, path), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(
      `Expected JSON from ${path} but got ${contentType || "unknown content-type"}.`,
    );
  }

  return (await response.json()) as T;
}

async function errorMessage(response: Response, url: string) {
  let detail = "";
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const body = (await response.clone().json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = `: ${body.detail}`;
      }
    } catch {
      detail = "";
    }
  }
  return `Request failed: ${response.status} ${response.statusText} from ${url}${detail}`;
}

export const api = {
  portfolio: () => fetchJson<import("../types/api").Portfolio>("/portfolio"),
  markets: () => fetchJson<import("../types/api").Market[]>("/markets/active"),
  signals: () => fetchJson<import("../types/api").Signal[]>("/signals"),
  trades: () => fetchJson<import("../types/api").Trade[]>("/trades"),
  postmortems: () => fetchJson<import("../types/api").Postmortem[]>("/postmortems"),
  settings: () => fetchJson<import("../types/api").RiskSettings>("/settings"),
  analysis: () => fetchJson<import("../types/api").AnalysisResult>("/analysis/all"),
  exportCsv: () => `${BASE_URL}/analysis/export-csv`,
  runCycle: () =>
    import.meta.env.PROD
      ? fetchSameOriginJson<{ status?: string; message?: string; notes?: string[] } | null>(
          "/api/run-cycle",
          { method: "POST" },
        )
      : fetchJson<{ status?: string; message?: string; notes?: string[] } | null>(
          "/engine/run-cycle",
          { method: "POST" },
        ),
};
