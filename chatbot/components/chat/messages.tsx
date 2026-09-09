import type { UseChatHelpers } from "@ai-sdk/react";
import type { DataUIPart } from "ai";
import { ArrowDownIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useMessages } from "@/hooks/use-messages";
import { useN8nConnection } from "@/hooks/use-n8n-connection";
import type { Vote } from "@/lib/db/schema";
import { getNodeIconByType } from "@/lib/node-icons";
import type { ChatMessage, CustomUIDataTypes } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useDataStream } from "./data-stream-provider";
import { Greeting } from "./greeting";
import { PreviewMessage, ThinkingMessage } from "./message";

function renderCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function WorkflowInjectCard({ payload }: { payload: Record<string, unknown> }) {
  const { connection, inject } = useN8nConnection();
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [msg, setMsg] = useState("");

  const wfJson = payload.workflow_json as Record<string, unknown> | null;
  const hasJson = !!wfJson && typeof wfJson === "object";
  const isConnected = !!connection?.url;

  async function handleInject() {
    if (!hasJson || !isConnected) return;
    setStatus("loading");
    const result = await inject(wfJson!);
    setStatus(result.ok ? "ok" : "error");
    setMsg(result.message);
  }

  return (
    <section className="rounded-2xl border border-indigo-500/20 bg-indigo-950/10 px-4 py-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-indigo-300/80">
          워크플로우 생성 완료
        </span>
        {hasJson && (
          <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-emerald-400">
            JSON 준비됨
          </span>
        )}
      </div>

      {!hasJson && (
        <p className="mb-3 text-[12px] text-muted-foreground">
          워크플로우 JSON을 파싱할 수 없습니다. 위 응답에서 JSON 블록을 확인하세요.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {isConnected ? (
          <button
            onClick={handleInject}
            disabled={!hasJson || status === "loading"}
            className="flex h-8 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "loading" ? "생성 중..." : "n8n에 바로 생성"}
          </button>
        ) : (
          <p className="text-[12px] text-muted-foreground">
            헤더의{" "}
            <span className="font-medium text-foreground">n8n 연결</span>
            {" "}버튼으로 인스턴스를 연결하면 자동으로 워크플로우를 생성할 수 있습니다.
          </p>
        )}

        {status === "ok" && (
          <span className="text-[12px] text-emerald-400">{msg}</span>
        )}
        {status === "error" && (
          <span className="text-[12px] text-red-400">{msg}</span>
        )}
      </div>
    </section>
  );
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
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {event.data.description}
              </p>
            )}
          </div>
          <div className="space-y-3">
            {event.data.cards.map((card, index) => {
              const level = String(card.level ?? "beginner");
              return (
                <article
                  className="border-l-2 border-border/60 pl-4"
                  key={`curriculum-${index}`}
                >
                  <div className="mb-1 flex items-center gap-3">
                    <span className="text-sm font-semibold text-foreground">
                      {String(card.title ?? `Card ${index + 1}`)}
                    </span>
                    <span className="rounded-full border border-border/50 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                      {level}
                    </span>
                  </div>
                  <div className="mb-2 text-xs text-muted-foreground">
                    {String(card.week ?? "")}
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {String(card.description ?? "")}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {card.duration ? (
                      <span>{String(card.duration)}</span>
                    ) : null}
                    {card.canvas_code_id ? (
                      <span>실습 코드: {String(card.canvas_code_id)}</span>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      );

    case "data-card": {
      const payload = event.data;
      // 백엔드는 카드의 서브타입(workflow_inject/error_patch_apply 등)을
      // "kind"로 보낸다 — "type"과 이름이 같으면 최상위 이벤트 종류("card")를
      // 덮어써버려서 여기까지 라우팅되지 못하는 문제가 있었기 때문.
      if (payload.kind === "workflow_inject") {
        return <WorkflowInjectCard payload={payload} />;
      }
      const entries = Object.entries(payload).filter(
        ([k]) =>
          !["type", "kind", "workflow_json", "workflow_payload", "patch_payload", "session_id"].includes(
            k
          )
      );
      return (
        <section className="space-y-3 rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Action Card
          </div>
          <dl className="space-y-3">
            {entries.map(([key, value]) => (
              <div
                className="border-b border-border/40 pb-3 last:border-0 last:pb-0"
                key={key}
              >
                <dt className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  {key}
                </dt>
                <dd>
                  <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-foreground/90">
                    {renderCellValue(value)}
                  </pre>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      );
    }

    case "data-node_property_card": {
      const p = event.data as Record<string, unknown>;
      const TYPE_COLORS: Record<string, string> = {
        string: "text-emerald-400 bg-emerald-400/10 border-emerald-500/30",
        number: "text-sky-400 bg-sky-400/10 border-sky-500/30",
        boolean: "text-violet-400 bg-violet-400/10 border-violet-500/30",
        options: "text-amber-400 bg-amber-400/10 border-amber-500/30",
        collection: "text-rose-400 bg-rose-400/10 border-rose-500/30",
        fixedCollection: "text-orange-400 bg-orange-400/10 border-orange-500/30",
        json: "text-cyan-400 bg-cyan-400/10 border-cyan-500/30",
        notice: "text-slate-400 bg-slate-400/10 border-slate-500/30",
      };
      const rawNodeType = String(p.node_type ?? p.nodeType ?? "");
      const nodeType = rawNodeType.replace(/^n8n-nodes-base\./, "");
      const nodeIcon = getNodeIconByType(rawNodeType);
      const props = Array.isArray(p.properties) ? p.properties as Record<string, unknown>[] : [];
      const badgeFor = (type: string) => {
        const cls = TYPE_COLORS[type] ?? "text-slate-400 bg-slate-400/10 border-slate-500/30";
        return (
          <span className={`inline-block rounded border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${cls}`}>
            {type}
          </span>
        );
      };
      return (
        <section className="rounded-2xl border border-indigo-500/20 bg-indigo-950/20 px-4 py-4">
          <div className="mb-3 flex items-center gap-2">
            {nodeIcon && (
              // biome-ignore lint/performance/noImgElement: 외부 n8n 아이콘 SVG를 그대로 표시
              <img src={nodeIcon} alt="" className="size-4 rounded object-contain" />
            )}
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-indigo-300/80">
              Node Properties
            </span>
            {nodeType && (
              <code className="rounded bg-indigo-500/15 px-1.5 py-0.5 text-[11px] text-indigo-200">
                {nodeType}
              </code>
            )}
          </div>
          {props.length > 0 ? (
            <div className="space-y-2.5">
              {props.map((prop, i) => {
                const name = String(prop.name ?? prop.displayName ?? `prop-${i}`);
                const displayName = String(prop.displayName ?? name);
                const type = String(prop.type ?? "string");
                const desc = String(prop.description ?? "");
                const defaultVal = prop.default !== undefined ? JSON.stringify(prop.default) : null;
                const required = prop.required === true;
                const noDataExpression = prop.noDataExpression === true;
                return (
                  <div
                    className="rounded-xl border border-border/30 bg-background/50 px-3 py-3"
                    key={`prop-${i}-${name}`}
                  >
                    <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-xs font-semibold text-foreground">
                        {name}
                      </span>
                      {badgeFor(type)}
                      {required && (
                        <span className="inline-block rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-red-400">
                          required
                        </span>
                      )}
                      {!noDataExpression && (
                        <span className="inline-block rounded border border-border/30 bg-border/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-muted-foreground">
                          expr
                        </span>
                      )}
                    </div>
                    {displayName !== name && (
                      <p className="mb-1 text-[11px] text-muted-foreground">{displayName}</p>
                    )}
                    {desc && (
                      <p className="mb-1.5 text-xs leading-5 text-muted-foreground/80">{desc}</p>
                    )}
                    {defaultVal !== null && (
                      <code className="block rounded bg-background/80 px-2 py-1 text-[11px] text-foreground/70">
                        default: {defaultVal}
                      </code>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <dl className="space-y-3">
              {Object.entries(p).map(([key, value]) => (
                <div className="border-b border-border/40 pb-3 last:border-0 last:pb-0" key={key}>
                  <dt className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    {key}
                  </dt>
                  <dd>
                    <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-foreground/90">
                      {renderCellValue(value)}
                    </pre>
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      );
    }

    case "data-error_alert":
      return (
        <section className="rounded-2xl border border-amber-500/20 bg-amber-500/8 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-300/80">
            Error Alert
          </div>
          <p className="text-sm leading-6 text-foreground">
            {event.data.message}
          </p>
          {!!event.data.tokens?.length && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {event.data.tokens.map((token) => (
                <li key={token}>{token}</li>
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
          <p className="text-sm leading-6 text-foreground">
            {String(event.data.summary ?? "파라미터 보정이 적용되었습니다.")}
          </p>
          {Array.isArray(event.data.corrections) &&
            event.data.corrections.length > 0 && (
              <div className="mt-3 overflow-x-auto rounded-xl border border-border/40 bg-background/50">
                <table className="w-full min-w-[420px] text-left text-xs">
                  <tbody>
                    {event.data.corrections.map((correction, index) => (
                      <tr
                        className="border-t border-border/30 first:border-0"
                        key={`correction-${index}`}
                      >
                        <td className="px-3 py-2 font-medium text-foreground">
                          {renderCellValue(
                            correction.field ??
                              correction.name ??
                              `item-${index + 1}`
                          )}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {renderCellValue(correction)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </section>
      );

    case "data-validation_report": {
      const d = event.data;
      const issues = Array.isArray(d.issues) ? d.issues : [];
      if (issues.length === 0) return null;
      const SEVERITY_STYLE: Record<string, string> = {
        error: "border-red-500/30 bg-red-500/8 text-red-400",
        warning: "border-amber-500/30 bg-amber-500/8 text-amber-400",
        info: "border-sky-500/30 bg-sky-500/8 text-sky-400",
      };
      return (
        <section className="rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            <span>Validation Report</span>
            {typeof d.error_count === "number" && d.error_count > 0 && (
              <span className="rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 text-[9px] text-red-400">
                오류 {d.error_count}
              </span>
            )}
            {typeof d.warning_count === "number" && d.warning_count > 0 && (
              <span className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[9px] text-amber-400">
                경고 {d.warning_count}
              </span>
            )}
          </div>
          <div className="space-y-2">
            {issues.map((issue, index) => (
              <div
                className={`rounded-xl border px-3 py-2 text-xs leading-5 ${
                  SEVERITY_STYLE[issue.severity] ??
                  "border-border/40 bg-background/50 text-muted-foreground"
                }`}
                key={`issue-${index}`}
              >
                <div className="mb-0.5 flex flex-wrap items-center gap-1.5 font-medium">
                  {issue.node && (
                    <code className="rounded bg-background/60 px-1 py-0.5 text-[10px]">
                      {issue.node}
                    </code>
                  )}
                  {issue.property && (
                    <code className="rounded bg-background/60 px-1 py-0.5 text-[10px]">
                      {issue.property}
                    </code>
                  )}
                </div>
                <p>{issue.message}</p>
                {issue.suggestion && (
                  <p className="mt-1 text-muted-foreground/80">
                    → {issue.suggestion}
                  </p>
                )}
              </div>
            ))}
          </div>
          {Array.isArray(d.best_practices) && d.best_practices.length > 0 && (
            <div className="mt-3 border-t border-border/30 pt-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                모범 사례
              </div>
              <ul className="list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                {d.best_practices.map((bp, i) => (
                  <li key={`bp-${i}`}>{bp}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      );
    }

    case "data-expression": {
      const exprNodeType = event.data.node_type ?? "";
      const exprIcon = getNodeIconByType(exprNodeType);
      return (
        <section className="rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-300/80">
            Expression
          </div>
          <div className="mb-2 flex items-center gap-1.5 text-sm text-muted-foreground">
            {exprIcon && (
              // biome-ignore lint/performance/noImgElement: 외부 n8n 아이콘 SVG를 그대로 표시
              <img src={exprIcon} alt="" className="size-4 rounded object-contain" />
            )}
            {String(exprNodeType)}
          </div>
          <pre className="whitespace-pre-wrap break-words rounded-xl border border-border/40 bg-background px-3 py-3 text-xs leading-6 text-foreground">
            {String(event.data.raw_expression ?? "")}
          </pre>
        </section>
      );
    }

    case "data-report": {
      const items = Array.isArray(event.data.items) ? event.data.items : [];
      return (
        <section className="space-y-3 rounded-2xl border border-border/50 bg-background/70 px-4 py-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {String(event.data.layer ?? "report")}
          </div>
          <h3 className="mb-2 text-base font-semibold text-foreground">
            {String(event.data.title ?? "분석 리포트")}
          </h3>
          {event.data.content ? (
            <p className="mb-3 text-sm leading-6 text-muted-foreground">
              {String(event.data.content)}
            </p>
          ) : null}
          {items.length > 0 && (
            <div className="space-y-3">
              {items.map((item, index) => (
                <div
                  className="border-l-2 border-border/60 pl-4"
                  key={`report-item-${index}`}
                >
                  {isRecord(item) ? (
                    Object.entries(item).map(([key, value]) => (
                      <div className="mb-1 text-sm leading-6" key={key}>
                        <span className="mr-1 font-semibold text-foreground/90">
                          {key}:
                        </span>
                        <span className="text-muted-foreground">
                          {renderCellValue(value)}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm leading-6 text-muted-foreground">
                      {renderCellValue(item)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      );
    }

    case "data-rag_sources": {
      const sources = event.data.sources ?? [];
      if (!sources.length) return null;
      const TYPE_LABEL: Record<string, string> = {
        spec: "스펙",
        official_docs: "공식문서",
        troubleshooting: "트러블슈팅",
        book: "교재",
        api_limits: "API제한",
        cli_spec: "CLI",
        docs: "문서",
      };
      return (
        <details className="group mt-2">
          <summary className="flex cursor-pointer select-none list-none items-center gap-1.5 text-[11px] text-muted-foreground/60 hover:text-muted-foreground transition-colors">
            <svg
              className="size-3 rotate-0 transition-transform group-open:rotate-90"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
            <span>RAG 근거 {sources.length}건</span>
          </summary>
          <div className="mt-2 space-y-1.5 pl-1">
            {sources.map((src, i) => (
              <div
                key={`rag-src-${i}`}
                className="rounded-lg border border-border/30 bg-muted/20 px-3 py-2"
              >
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="rounded border border-border/40 bg-background/60 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted-foreground">
                    {TYPE_LABEL[src.data_type] ?? src.data_type}
                  </span>
                  <span className="text-[11px] font-medium text-foreground/80">
                    {src.title}
                  </span>
                </div>
                {src.preview && (
                  <p className="line-clamp-2 text-[11px] leading-5 text-muted-foreground/70">
                    {src.preview}
                  </p>
                )}
              </div>
            ))}
          </div>
        </details>
      );
    }

    default:
      return null;
  }
}

function StructuredEventFeed({
  events,
}: {
  events: DataUIPart<CustomUIDataTypes>[];
}) {
  const visibleEvents = events.filter(
    (event) =>
      event.type !== "data-chat-title" &&
      event.type !== "data-intent"
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
    const lastUserMessage = [...messages]
      .reverse()
      .find((message) => message.role === "user");
    const lastUserMessageId = lastUserMessage?.id ?? null;

    if (
      lastUserMessageId &&
      lastUserMessageIdRef.current !== lastUserMessageId
    ) {
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
