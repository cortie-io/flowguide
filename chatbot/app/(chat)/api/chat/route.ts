import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { auth } from "@/app/(auth)/auth";
import {
  deleteChatById,
  getChatById,
  getMessagesByChatId,
  saveChat,
  saveMessages,
  saveRequestLog,
} from "@/lib/db/queries";
import { ChatbotError } from "@/lib/errors";
import { generateUUID } from "@/lib/utils";
import { generateTitleFromUserMessage } from "../../actions";
import { type PostRequestBody, postRequestBodySchema } from "./schema";

const N9N_API = process.env.N9N_API ?? "http://127.0.0.1:8000";

export const maxDuration = 300;

type LegacyStructuredPart = {
  type: string;
  [key: string]: unknown;
};

// ── 메시지 파트에서 텍스트만 추출 ─────────────────────────────
function extractText(parts: Record<string, unknown>[]): string {
  return parts
    .filter((p) => p.type === "text")
    .map((p) => String(p.text ?? ""))
    .join("\n");
}

function extractImageUrls(parts: Record<string, unknown>[]): string[] {
  return parts
    .filter((p) => p.type === "file" && typeof p.url === "string")
    .map((p) => String(p.url));
}

function toStructuredUiChunks(payload: unknown) {
  if (!Array.isArray(payload)) {
    return [];
  }

  return payload.flatMap((entry) => {
    if (!entry || typeof entry !== "object" || !("type" in entry)) {
      return [];
    }

    const structuredEntry = entry as LegacyStructuredPart;
    const { type, ...data } = structuredEntry;
    // thinking/중간 추론 데이터는 최종 답변 UI에서 숨김
    if (
      type === "thinking" ||
      type === "node_property" ||
      type === "node_property_card" ||
      type === "intermediate"
    ) {
      return [];
    }

    return [
      {
        type: `data-${type}` as const,
        data,
      },
    ];
  });
}

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch (_) {
    return new ChatbotError("bad_request:api").toResponse();
  }

  const { id, message, selectedVisibilityType, raw_json, needs_canvas, selectedChatModel, openai_api_key, n8n_url, n8n_api_key } = requestBody;

  const session = await auth();
  if (!session?.user) {
    return new ChatbotError("unauthorized:chat").toResponse();
  }

  // ── DB: 채팅 로드 / 생성 ───────────────────────────────────
  const chat = await getChatById({ id });

  const isFirstMessage = !chat;

  if (chat) {
    if (chat.userId !== session.user.id) {
      return new ChatbotError("forbidden:chat").toResponse();
    }
  } else if (message?.role === "user") {
    await saveChat({
      id,
      userId: session.user.id,
      title: "New chat",
      visibility: selectedVisibilityType,
    });
  }

  // ── DB: 유저 메시지 저장 ──────────────────────────────────
  if (message?.role === "user") {
    await saveMessages({
      messages: [
        {
          chatId: id,
          id: message.id,
          role: "user",
          parts: message.parts,
          attachments: [],
          createdAt: new Date(),
        },
      ],
    });
  }

  // ── 이전 메시지 로드 ──────────────────────────────────────
  const dbMessages = await getMessagesByChatId({ id });

  // AI SDK messages 형식으로 변환
  const aiMessages = dbMessages.map((m) => ({
    role: m.role as "user" | "assistant",
    content: extractText(m.parts as Record<string, unknown>[]),
  }));

  // ── Naito FastAPI 백엔드에 스트리밍 프록시 ──────────────────
  let upstream: Response;
  try {
    const imageUrls = message?.parts
      ? extractImageUrls(message.parts as Record<string, unknown>[])
      : [];

    upstream = await fetch(`${N9N_API}/api/workspace/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: aiMessages,
        session_id: id,
        ...(selectedChatModel ? { model: selectedChatModel } : {}),
        ...(raw_json ? { raw_json } : {}),
        ...(openai_api_key ? { openai_api_key } : {}),
        ...(imageUrls.length > 0 ? { image_urls: imageUrls } : {}),
        ...(n8n_url ? { n8n_url } : {}),
        ...(n8n_api_key ? { n8n_api_key } : {}),
      }),
    });
  } catch {
    return new ChatbotError("offline:chat").toResponse();
  }

  if (!upstream.ok) {
    return new ChatbotError("offline:chat").toResponse();
  }

  if (!upstream.body) {
    return new ChatbotError("offline:chat").toResponse();
  }

  const upstreamBody = upstream.body;
  const requestStartedAt = Date.now();
  const userAgent = request.headers.get("user-agent") ?? undefined;
  const ipAddress =
    (request.headers.get("x-forwarded-for") ?? request.headers.get("x-real-ip"))
      ?.split(",")[0]
      .trim() ?? undefined;

  const response = createUIMessageStreamResponse({
    stream: createUIMessageStream({
      execute: async ({ writer }) => {
        const reader = upstreamBody.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        const structuredPayloads: unknown[] = [];
        let buffer = "";
        let textPartStarted = false;
        let streamFinished = false;
        const textPartId = "text-1";

        writer.write({ type: "start" });
        writer.write({ type: "start-step" });

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const rawLine of lines) {
              const line = rawLine.trimEnd();

              if (!line) {
                continue;
              }

              if (line.startsWith("0:")) {
                try {
                  const token = JSON.parse(line.slice(2));
                  if (typeof token === "string") {
                    if (!textPartStarted) {
                      textPartStarted = true;
                      writer.write({ type: "text-start", id: textPartId });
                    }
                    fullText += token;
                    writer.write({
                      type: "text-delta",
                      id: textPartId,
                      delta: token,
                    });
                  }
                } catch {
                  /* ignore malformed token chunks */
                }
                continue;
              }

              if (line.startsWith("2:")) {
                try {
                  const payload = JSON.parse(line.slice(2));
                  structuredPayloads.push(payload);
                  for (const chunk of toStructuredUiChunks(payload)) {
                    writer.write(chunk);
                  }
                } catch {
                  /* ignore malformed data chunks */
                }
                continue;
              }

              if (line.startsWith("d:")) {
                streamFinished = true;
                break;
              }
            }

            if (streamFinished) {
              break;
            }
          }
        } finally {
          // 구조화 데이터를 마크다운으로 변환
          const formatStructuredPayloads = (payloads: unknown[]): string => {
            let output = "";
            for (const payload of payloads) {
              if (!payload || typeof payload !== "object") {
                continue;
              }
              const entry = payload as Record<string, unknown>;

              if (entry.type === "curriculum" && Array.isArray(entry.cards)) {
                output += "## CURRICULUM\n\n";
                const cards = entry.cards as Record<string, unknown>[];
                for (const card of cards) {
                  output += `### ${card.week} — ${card.title}\n`;
                  output += `**Level:** ${card.level} | **Duration:** ${card.duration}\n\n`;
                  output += `${card.description}\n\n`;
                }
              }
            }
            return output;
          };

          const fallbackStructuredText =
            !fullText && structuredPayloads.length > 0
              ? formatStructuredPayloads(structuredPayloads)
              : "";

          // Intent 추출 (FastAPI 스트림의 첫 번째 구조화 이벤트)
          let detectedIntent: string | undefined;
          let detectedIntentLabel: string | undefined;
          for (const payload of structuredPayloads) {
            if (Array.isArray(payload)) {
              for (const item of payload) {
                if (
                  item &&
                  typeof item === "object" &&
                  (item as Record<string, unknown>).type === "intent"
                ) {
                  const entry = item as Record<string, unknown>;
                  detectedIntent = String(entry.intent ?? "");
                  detectedIntentLabel = String(entry.label ?? "");
                  break;
                }
              }
            }
            if (detectedIntent) break;
          }

          let assistantId: string | undefined;
          if (fullText || fallbackStructuredText) {
            assistantId = generateUUID();
            await saveMessages({
              messages: [
                {
                  chatId: id,
                  id: assistantId,
                  role: "assistant",
                  parts: [
                    { type: "text", text: fullText || fallbackStructuredText },
                  ],
                  attachments: [],
                  createdAt: new Date(),
                },
              ],
            });

            if (isFirstMessage && message?.role === "user") {
              try {
                const title = await generateTitleFromUserMessage({ message });
                const { updateChatTitleById } = await import(
                  "@/lib/db/queries"
                );
                await updateChatTitleById({ chatId: id, title });
              } catch {
                /* non-fatal */
              }
            }
          }

          // 타이틀/메시지 저장 완료 후 스트림 종료 신호 전송
          if (textPartStarted) {
            writer.write({ type: "text-end", id: textPartId });
          }
          writer.write({ type: "finish-step" });
          writer.write({ type: "finish" });

          // RequestLog 저장 (non-fatal)
          await saveRequestLog({
            chatId: id,
            userMessageId: message?.id ?? null,
            assistantMessageId: assistantId ?? null,
            userId: session.user.id!,
            createdAt: new Date(),
            intent: detectedIntent ?? null,
            intentLabel: detectedIntentLabel ?? null,
            needsCanvas: needs_canvas ?? false,
            hasRawJson: !!raw_json,
            rawJson: raw_json ?? null,
            hasNodeData: false,
            nodeData: null,
            hasErrorLog: false,
            errorLog: null,
            model: null,
            selectedVisibility: selectedVisibilityType,
            priorMessageCount: dbMessages.length,
            responseLength: (fullText || fallbackStructuredText).length || null,
            hasStructuredPayload: structuredPayloads.length > 0,
            structuredPayloads: structuredPayloads.length > 0 ? structuredPayloads : null,
            latencyMs: Date.now() - requestStartedAt,
            userAgent: userAgent ?? null,
            ipAddress: ipAddress ?? null,
          });
        }
      },
    }),
    headers: {
      "Cache-Control": "no-cache",
    },
  });

  return response;
}

export async function PATCH(request: Request) {
  const session = await auth();
  if (!session?.user) {
    return new ChatbotError("unauthorized:chat").toResponse();
  }

  let body: { id: string; title: string };
  try {
    body = await request.json();
  } catch {
    return new ChatbotError("bad_request:api").toResponse();
  }

  const { id, title } = body;
  if (!id || !title?.trim()) {
    return new ChatbotError("bad_request:api").toResponse();
  }

  const existingChat = await getChatById({ id });
  if (existingChat?.userId !== session.user.id) {
    return new ChatbotError("forbidden:chat").toResponse();
  }

  const { updateChatTitleById } = await import("@/lib/db/queries");
  await updateChatTitleById({ chatId: id, title: title.trim().slice(0, 100) });
  return Response.json({ success: true }, { status: 200 });
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return new ChatbotError("bad_request:api").toResponse();
  }

  const session = await auth();
  if (!session?.user) {
    return new ChatbotError("unauthorized:chat").toResponse();
  }

  const chat = await getChatById({ id });
  if (chat?.userId !== session.user.id) {
    return new ChatbotError("forbidden:chat").toResponse();
  }

  const deletedChat = await deleteChatById({ id });
  return Response.json(deletedChat, { status: 200 });
}
