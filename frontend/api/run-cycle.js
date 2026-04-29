export default async function handler(request, response) {
  if (process.env.ENABLE_PUBLIC_ENGINE_CONTROLS !== "true") {
    return response.status(404).json({ detail: "Not found" });
  }

  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return response.status(405).json({ detail: "Method not allowed" });
  }

  const backendBaseUrl = (
    process.env.BACKEND_API_BASE_URL ||
    process.env.VITE_API_BASE_URL ||
    ""
  ).replace(/\/$/, "");
  const engineControlToken = process.env.ENGINE_CONTROL_TOKEN;

  if (!backendBaseUrl || !engineControlToken) {
    return response.status(500).json({
      detail:
        "Vercel is missing BACKEND_API_BASE_URL or ENGINE_CONTROL_TOKEN for the run-cycle proxy.",
    });
  }

  try {
    const upstream = await fetch(`${backendBaseUrl}/engine/run-cycle`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${engineControlToken}`,
      },
    });

    const body = await upstream.text();
    const contentType = upstream.headers.get("content-type");
    if (contentType) {
      response.setHeader("Content-Type", contentType);
    }

    return response.status(upstream.status).send(body);
  } catch (error) {
    return response.status(502).json({
      detail:
        error instanceof Error
          ? `Backend request failed: ${error.message}`
          : "Backend request failed.",
    });
  }
}
