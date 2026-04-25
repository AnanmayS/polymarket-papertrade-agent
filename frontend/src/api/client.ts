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
    throw new ApiError(
      `Request failed: ${response.status} ${response.statusText}`,
      response.status,
    );
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

export const api = {
  portfolio: () => fetchJson<import("../types/api").Portfolio>("/portfolio"),
  markets: () => fetchJson<import("../types/api").Market[]>("/markets/active"),
  signals: () => fetchJson<import("../types/api").Signal[]>("/signals"),
  trades: () => fetchJson<import("../types/api").Trade[]>("/trades"),
  postmortems: () => fetchJson<import("../types/api").Postmortem[]>("/postmortems"),
  settings: () => fetchJson<import("../types/api").RiskSettings>("/settings"),
  runCycle: () =>
    fetchJson<{ status?: string; message?: string; notes?: string[] } | null>(
      "/engine/run-cycle",
      { method: "POST" },
    ),
};
