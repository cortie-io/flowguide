import { auth } from "@/app/(auth)/auth";
import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import {
  deleteChatById,
  getChatById,
  getMessagesByChatId,
  saveChat,
  saveMessages,
} from "@/lib/db/queries";
import { ChatbotError } from "@/lib/errors";
import { generateUUID } from "@/lib/utils";
import { type PostRequestBody, postRequestBodySchema } from "./schema";
import { generateTitleFromUserMessage } from "../../actions";

const N9N_API = process.env.N9N_API ?? "http://localhost:8000";

export const maxDuration = 60;

type LegacyStructuredPart = {
  type: string;
  [key: string]: unknown;
};

// ── 메시지 파트에서 텍스트만 추출 ─────────────────────────────
function extractText(parts: Array<Record<string, unknown>>): string {
  return parts
    .filter((p) => p.type === "text")
    .map((p) => String(p.text ?? ""))
    .join("\n");
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

  const { id, message, selectedVisibilityType } = requestBody;

  const session = await auth();
  if (!session?.user) {
    return new ChatbotError("unauthorized:chat").toResponse();
  }

  // ── DB: 채팅 로드 / 생성 ───────────────────────────────────
  const chat = await getChatById({ id });

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
    content: extractText(m.parts as Array<Record<string, unknown>>),
  }));

  // ── nodi FastAPI 백엔드에 스트리밍 프록시 ──────────────────
  let upstream: Response;
  try {
    upstream = await fetch(`${N9N_API}/api/workspace/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: aiMessages,
        session_id: id,
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
            if (done) break;

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
                    writer.write({ type: "text-delta", id: textPartId, delta: token });
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
          if (textPartStarted) {
            writer.write({ type: "text-end", id: textPartId });
          }

          writer.write({ type: "finish-step" });
          writer.write({ type: "finish" });

          // 구조화 데이터를 마크다운으로 변환
          const formatStructuredPayloads = (payloads: unknown[]): string => {
            let output = "";
            for (const payload of payloads) {
              if (!payload || typeof payload !== "object") continue;
              const entry = payload as Record<string, unknown>;
              
              if (entry.type === "curriculum" && Array.isArray(entry.cards)) {
                output += "## CURRICULUM\n\n";
                const cards = entry.cards as Array<Record<string, unknown>>;
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

          if (fullText || fallbackStructuredText) {
            const assistantId = generateUUID();
            await saveMessages({
              messages: [
                {
                  chatId: id,
                  id: assistantId,
                  role: "assistant",
                  parts: [{ type: "text", text: fullText || fallbackStructuredText }],
                  attachments: [],
                  createdAt: new Date(),
                },
              ],
            });

            if (dbMessages.length === 0 && message?.role === "user") {
              try {
                const title = await generateTitleFromUserMessage({ message });
                const { updateChatTitleById } = await import("@/lib/db/queries");
                await updateChatTitleById({ chatId: id, title });
              } catch {
                /* non-fatal */
              }
            }
          }
        }
      },
    }),
    headers: {
      "Cache-Control": "no-cache",
    },
  });

  return response;
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) return new ChatbotError("bad_request:api").toResponse();

  const session = await auth();
  if (!session?.user) return new ChatbotError("unauthorized:chat").toResponse();

  const chat = await getChatById({ id });
  if (chat?.userId !== session.user.id) {
    return new ChatbotError("forbidden:chat").toResponse();
  }

  const deletedChat = await deleteChatById({ id });
  return Response.json(deletedChat, { status: 200 });
}
