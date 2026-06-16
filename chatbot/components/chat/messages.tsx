import type { UseChatHelpers } from "@ai-sdk/react";
import { ArrowDownIcon } from "lucide-react";
import { useEffect, useRef } from "react";
import type { DataUIPart } from "ai";
import { useMessages } from "@/hooks/use-messages";
import type { Vote } from "@/lib/db/schema";
import type { ChatMessage } from "@/lib/types";
import type { CustomUIDataTypes } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useDataStream } from "./data-stream-provider";
import { Greeting } from "./greeting";
import { PreviewMessage, ThinkingMessage } from "./message";

function renderCellValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function EventPanel({ event }: { event: DataUIPart<CustomUIDataTypes> }) {
  switch (event.type) {
    case "data-intent":
      return null;

    case "data-curriculum":
      return (
        <section className="space-y-4 rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Curriculum
            </div>
            {event.data.description && (
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{event.data.description}</p>
            )}
          </div>
          <div className="space-y-3">
            {event.data.cards.map((card, index) => {
              const level = String(card.level ?? "beginner");
              return (
                <article className="border-l-2 border-border/60 pl-4" key={`curriculum-${index}`}>
                  <div className="mb-1 flex items-center gap-3">
                    <span className="text-sm font-semibold text-foreground">{String(card.title ?? `Card ${index + 1}`)}</span>
                    <span className="rounded-full border border-border/50 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                      {level}
                    </span>
                  </div>
                  <div className="mb-2 text-xs text-muted-foreground">{String(card.week ?? "")}</div>
                  <p className="text-sm leading-6 text-muted-foreground">{String(card.description ?? "")}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {card.duration ? <span>{String(card.duration)}</span> : null}
                    {card.canvas_code_id ? <span>실습 코드: {String(card.canvas_code_id)}</span> : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      );

    case "data-card":
    case "data-node_property_card": {
      const payload = event.data;
      const entries = Object.entries(payload);
      return (
        <section className="space-y-3 rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {event.type === "data-card" ? "Action Card" : "Node Property"}
          </div>
          <dl className="space-y-3">
            {entries.map(([key, value]) => (
              <div className="border-b border-border/40 pb-3 last:border-0 last:pb-0" key={key}>
                <dt className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{key}</dt>
                <dd>
                  <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-foreground/90">{renderCellValue(value)}</pre>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      );
    }

    case "data-error_alert":
      return (
        <section className="rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-300/80">
            Error Alert
          </div>
          <p className="text-sm leading-6 text-foreground">{event.data.message}</p>
          {!!event.data.tokens?.length && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {event.data.tokens.map((token) => (
                <li key={token}>
                  {token}
                </li>
              ))}
            </ul>
          )}
        </section>
      );

    case "data-reg_warning":
      return (
        <section className="rounded-2xl border border-sky-500/20 bg-sky-500/8 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-300/80">
            REG Warning
          </div>
          <p className="text-sm leading-6 text-foreground">{String(event.data.summary ?? "파라미터 보정이 적용되었습니다.")}</p>
          {Array.isArray(event.data.corrections) && event.data.corrections.length > 0 && (
            <div className="mt-3 overflow-x-auto rounded-xl border border-border/40 bg-background/50">
              <table className="w-full min-w-[420px] text-left text-xs">
                <tbody>
                  {event.data.corrections.map((correction, index) => (
                    <tr className="border-t border-border/30 first:border-0" key={`correction-${index}`}>
                      <td className="px-3 py-2 font-medium text-foreground">{renderCellValue(correction.field ?? correction.name ?? `item-${index + 1}`)}</td>
                      <td className="px-3 py-2 text-muted-foreground">{renderCellValue(correction)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      );

    case "data-expression":
      return (
        <section className="rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-300/80">
            Expression
          </div>
          <div className="mb-2 text-sm text-muted-foreground">{String(event.data.node_type ?? "")}</div>
          <pre className="whitespace-pre-wrap break-words rounded-xl border border-border/40 bg-background px-3 py-3 text-xs leading-6 text-foreground">
            {String(event.data.raw_expression ?? "")}
          </pre>
        </section>
      );

    case "data-report": {
      const items = Array.isArray(event.data.items) ? event.data.items : [];
      return (
        <section className="space-y-3 rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {String(event.data.layer ?? "report")}
          </div>
          <h3 className="mb-2 text-base font-semibold text-foreground">{String(event.data.title ?? "분석 리포트")}</h3>
          {event.data.content ? <p className="mb-3 text-sm leading-6 text-muted-foreground">{String(event.data.content)}</p> : null}
          {items.length > 0 && (
            <div className="space-y-3">
              {items.map((item, index) => (
                <div className="border-l-2 border-border/60 pl-4" key={`report-item-${index}`}>
                  {isRecord(item) ? (
                    Object.entries(item).map(([key, value]) => (
                      <div className="mb-1 text-sm leading-6" key={key}>
                        <span className="mr-1 font-semibold text-foreground/90">{key}:</span>
                        <span className="text-muted-foreground">{renderCellValue(value)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm leading-6 text-muted-foreground">{renderCellValue(item)}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      );
    }

    default:
      return null;
  }
}

function StructuredEventFeed({ events }: { events: DataUIPart<CustomUIDataTypes>[] }) {
  const visibleEvents = events.filter(
    (event) =>
      event.type !== "data-chat-title" &&
      event.type !== "data-intent" &&
      event.type !== "data-node_property_card"
  );
  if (visibleEvents.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {visibleEvents.map((event, index) => (
        <EventPanel event={event} key={`${event.type}-${index}`} />
      ))}
    </div>
  );
}

type MessagesProps = {
  addToolApprovalResponse: UseChatHelpers<ChatMessage>["addToolApprovalResponse"];
  chatId: string;
  status: UseChatHelpers<ChatMessage>["status"];
  votes: Vote[] | undefined;
  messages: ChatMessage[];
  setMessages: UseChatHelpers<ChatMessage>["setMessages"];
  regenerate: UseChatHelpers<ChatMessage>["regenerate"];
  isReadonly: boolean;
  isArtifactVisible: boolean;
  isLoading?: boolean;
  selectedModelId: string;
  onEditMessage?: (message: ChatMessage) => void;
};

function PureMessages({
  addToolApprovalResponse,
  chatId,
  status,
  votes,
  messages,
  setMessages,
  regenerate,
  isReadonly,
  isArtifactVisible,
  isLoading,
  selectedModelId: _selectedModelId,
  onEditMessage,
}: MessagesProps) {
  const {
    containerRef: messagesContainerRef,
    endRef: messagesEndRef,
    isAtBottom,
    scrollToBottom,
    hasSentMessage,
    reset,
  } = useMessages({
    status,
  });

  const { uiEvents, setUiEvents } = useDataStream();
  const lastUserMessageIdRef = useRef<string | null>(null);

  const prevChatIdRef = useRef(chatId);
  useEffect(() => {
    if (prevChatIdRef.current !== chatId) {
      prevChatIdRef.current = chatId;
      reset();
      setUiEvents([]);
      lastUserMessageIdRef.current = null;
    }
  }, [chatId, reset, setUiEvents]);

  useEffect(() => {
    const lastUserMessage = [...messages].reverse().find((message) => message.role === "user");
    const lastUserMessageId = lastUserMessage?.id ?? null;

    if (lastUserMessageId && lastUserMessageIdRef.current !== lastUserMessageId) {
      lastUserMessageIdRef.current = lastUserMessageId;
      setUiEvents([]);
    }
  }, [messages, setUiEvents]);

  return (
    <div className="relative flex-1 bg-background">
      {messages.length === 0 && !isLoading && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <Greeting />
        </div>
      )}
      <div
        className={cn(
          "absolute inset-0 touch-pan-y overflow-y-auto",
          messages.length > 0 ? "bg-background" : "bg-transparent"
        )}
        ref={messagesContainerRef}
        style={isArtifactVisible ? { scrollbarWidth: "none" } : undefined}
      >
        <div className="mx-auto flex min-h-full min-w-0 max-w-4xl flex-col gap-5 px-2 py-6 md:gap-7 md:px-4">
          {messages.map((message, index) => (
            <PreviewMessage
              addToolApprovalResponse={addToolApprovalResponse}
              chatId={chatId}
              isLoading={
                status === "streaming" && messages.length - 1 === index
              }
              isReadonly={isReadonly}
              key={message.id}
              message={message}
              onEdit={onEditMessage}
              regenerate={regenerate}
              requiresScrollPadding={
                hasSentMessage && index === messages.length - 1
              }
              setMessages={setMessages}
              vote={
                votes
                  ? votes.find((vote) => vote.messageId === message.id)
                  : undefined
              }
            />
          ))}

          {status === "submitted" && messages.at(-1)?.role !== "assistant" && (
            <ThinkingMessage />
          )}

          <StructuredEventFeed events={uiEvents} />

          <div
            className="min-h-[24px] min-w-[24px] shrink-0"
            ref={messagesEndRef}
          />
        </div>
      </div>

      <button
        aria-label="Scroll to bottom"
        className={`absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 items-center rounded-full border border-border/50 bg-card/90 px-3.5 shadow-[var(--shadow-float)] backdrop-blur-lg transition-all duration-200 h-7 text-[10px] ${
          isAtBottom
            ? "pointer-events-none scale-90 opacity-0"
            : "pointer-events-auto scale-100 opacity-100"
        }`}
        onClick={() => scrollToBottom("smooth")}
        type="button"
      >
        <ArrowDownIcon className="size-3 text-muted-foreground" />
      </button>
    </div>
  );
}

export const Messages = PureMessages;
