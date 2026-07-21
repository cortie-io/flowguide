const N9N_API = process.env.N9N_API ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  let body: { message?: string; session_id?: string; model?: string; n8n_url?: string; openai_api_key?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ intent: "GENERAL", needs_canvas: false });
  }

  try {
    const upstream = await fetch(`${N9N_API}/api/workspace/check-intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: body.message ?? "",
        session_id: body.session_id,
        model: body.model ?? "",
        n8n_url: body.n8n_url ?? null,
        openai_api_key: body.openai_api_key ?? null,
      }),
    });
    if (!upstream.ok) return Response.json({ intent: "GENERAL", needs_canvas: false });
    return upstream;
  } catch {
    return Response.json({ intent: "GENERAL", needs_canvas: false });
  }
}
