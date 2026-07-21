import { NextResponse } from "next/server";

const N9N_API = process.env.N9N_API ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { n8nUrl, apiKey, workflowJson } = body as {
      n8nUrl: string;
      apiKey?: string;
      workflowJson: Record<string, unknown>;
    };

    if (!n8nUrl || !workflowJson) {
      return NextResponse.json(
        { error: "n8nUrl과 workflowJson이 필요합니다." },
        { status: 400 }
      );
    }

    const resp = await fetch(`${N9N_API}/api/workflow/remote-inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        n8n_url: n8nUrl,
        api_key: apiKey ?? null,
        workflow_json: workflowJson,
      }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      return NextResponse.json(data, { status: resp.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: String(err) },
      { status: 500 }
    );
  }
}
