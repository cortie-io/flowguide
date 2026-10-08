import { NextResponse } from "next/server";
import { auth } from "@/app/(auth)/auth";

const N9N_API = process.env.N9N_API ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  // 로그인한 사용자만 — 이 요청은 서버가 대신 외부(사용자 n8n)로 보낸다
  const session = await auth();
  if (!session?.user) return Response.json({ error: "로그인이 필요합니다." }, { status: 401 });
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
