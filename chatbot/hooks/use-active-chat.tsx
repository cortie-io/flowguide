"use client";

import type { UseChatHelpers } from "@ai-sdk/react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { usePathname } from "next/navigation";
import {
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import useSWR, { useSWRConfig } from "swr";
import { unstable_serialize } from "swr/infinite";
import { useDataStream } from "@/components/chat/data-stream-provider";
import { getChatHistoryPaginationKey } from "@/components/chat/sidebar-history";
import { toast } from "@/components/chat/toast";
import type { VisibilityType } from "@/components/chat/visibility-selector";
import { useAutoResume } from "@/hooks/use-auto-resume";
import { DEFAULT_CHAT_MODEL } from "@/lib/ai/models";
import type { Vote } from "@/lib/db/schema";
import { ChatbotError } from "@/lib/errors";
import type { ChatMessage } from "@/lib/types";
import { fetcher, fetchWithErrorHandlers, generateUUID } from "@/lib/utils";

type ActiveChatContextValue = {
  chatId: string;
  messages: ChatMessage[];
  setMessages: UseChatHelpers<ChatMessage>["setMessages"];
  sendMessage: UseChatHelpers<ChatMessage>["sendMessage"];
  status: UseChatHelpers<ChatMessage>["status"];
  stop: UseChatHelpers<ChatMessage>["stop"];
  regenerate: UseChatHelpers<ChatMessage>["regenerate"];
  addToolApprovalResponse: UseChatHelpers<ChatMessage>["addToolApprovalResponse"];
  input: string;
  setInput: Dispatch<SetStateAction<string>>;
  visibilityType: VisibilityType;
  isReadonly: boolean;
  isLoading: boolean;
  votes: Vote[] | undefined;
  currentModelId: string;
  setCurrentModelId: (id: string) => void;
  showCreditCardAlert: boolean;
  setShowCreditCardAlert: Dispatch<SetStateAction<boolean>>;
};

const ActiveChatContext = createContext<ActiveChatContextValue | null>(null);

function extractChatId(pathname: string): string | null {
  const match = pathname.match(/\/chat\/([^/]+)/);
  return match ? match[1] : null;
}

export function ActiveChatProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { setDataStream } = useDataStream();
  const { mutate } = useSWRConfig();

  const chatIdFromUrl = extractChatId(pathname);
  const isNewChat = !chatIdFromUrl;
  const newChatIdRef = useRef(generateUUID());
  const prevPathnameRef = useRef(pathname);

  if (isNewChat && prevPathnameRef.current !== pathname) {
    newChatIdRef.current = generateUUID();
  }
  prevPathnameRef.current = pathname;

  const chatId = chatIdFromUrl ?? newChatIdRef.current;

  const [currentModelId, setCurrentModelId] = useState(DEFAULT_CHAT_MODEL);
  const currentModelIdRef = useRef(currentModelId);
  useEffect(() => {
    currentModelIdRef.current = currentModelId;
  }, [currentModelId]);

  const [input, setInput] = useState("");
  const [showCreditCardAlert, setShowCreditCardAlert] = useState(false);

  const { data: chatData, isLoading } = useSWR(
    isNewChat
      ? null
      : `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/messages?chatId=${chatId}`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const initialMessages: ChatMessage[] = isNewChat
    ? []
    : (chatData?.messages ?? []);
  const visibility: VisibilityType = isNewChat
    ? "private"
    : (chatData?.visibility ?? "private");

  const {
    messages,
    setMessages,
    sendMessage,
    status,
    stop,
    regenerate,
    resumeStream,
    addToolApprovalResponse,
  } = useChat<ChatMessage>({
    id: chatId,
    messages: initialMessages,
    generateId: generateUUID,
    sendAutomaticallyWhen: ({ messages: currentMessages }) => {
      const lastMessage = currentMessages.at(-1);
      return (
        lastMessage?.parts?.some(
          (part) =>
            "state" in part &&
            part.state === "approval-responded" &&
            "approval" in part &&
            (part.approval as { approved?: boolean })?.approved === true
        ) ?? false
      );
    },
    transport: new DefaultChatTransport({
      api: `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/chat`,
      fetch: fetchWithErrorHandlers,
      prepareSendMessagesRequest(request) {
        const lastMessage = request.messages.at(-1);
        const isToolApprovalContinuation =
          lastMessage?.role !== "user" ||
          request.messages.some((msg) =>
            msg.parts?.some((part) => {
              const state = (part as { state?: string }).state;
              return (
                state === "approval-responded" || state === "output-denied"
              );
            })
          );

        const openaiApiKey = (() => {
          if (typeof window === "undefined") return "";
          try {
            const raw = localStorage.getItem("openai_api_key");
            if (!raw) return "";
            const parsed = JSON.parse(raw);
            return typeof parsed === "string" ? parsed : "";
          } catch {
            return "";
          }
        })();
        const n8nConnection = (() => {
          if (typeof window === "undefined") return null;
          try {
            const raw = localStorage.getItem("naito_n8n_connection");
            if (!raw) return null;
            return JSON.parse(raw) as { url: string; apiKey: string };
          } catch {
            return null;
          }
        })();

        return {
          body: {
            id: request.id,
            ...(isToolApprovalContinuation
              ? { messages: request.messages }
              : { message: lastMessage }),
            selectedChatModel: currentModelIdRef.current,
            selectedVisibilityType: visibility,
            ...(currentModelIdRef.current.startsWith("openai:") && openaiApiKey
              ? { openai_api_key: openaiApiKey }
              : {}),
            ...(n8nConnection?.url
              ? { n8n_url: n8nConnection.url, n8n_api_key: n8nConnection.apiKey || undefined }
              : {}),
            ...request.body,
          },
        };
      },
    }),
    onData: (dataPart) => {
      setDataStream((ds) => (ds ? [...ds, dataPart] : []));
    },
    onFinish: () => {
      mutate(unstable_serialize(getChatHistoryPaginationKey));
    },
    onError: (error) => {
      if (error.message?.includes("AI Gateway requires a valid credit card")) {
        setShowCreditCardAlert(true);
      } else if (error instanceof ChatbotError) {
        const message = String(error.message || "");
        const shouldHideInternalError =
          message.includes("importKey") ||
          message.includes(
            "An unexpected response was received from the server"
          ) ||
          message.includes("Failed to fetch") ||
          message.includes("Cannot read properties of undefined") ||
          message.includes("TypeError");

        toast({
          type: "error",
          description: shouldHideInternalError
            ? "일시적인 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            : message,
        });
      } else {
        const rawMessage = String(error?.message || "");
        const shouldHideInternalError =
          rawMessage.includes("importKey") ||
          rawMessage.includes(
            "An unexpected response was received from the server"
          ) ||
          rawMessage.includes("Failed to fetch") ||
          rawMessage.includes("Cannot read properties of undefined");

        if (shouldHideInternalError) {
          console.error("[chat] normalized runtime error", error);
        }

        toast({
          type: "error",
          description: shouldHideInternalError
            ? "일시적인 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            : rawMessage || "Oops, an error occurred!",
        });
      }
    },
  });

  // n8n 워크플로우 프리페치 후 sendMessage 호출
  const sendMessageWithN8nPrefetch: UseChatHelpers<ChatMessage>["sendMessage"] = useCallback(
    async (message, options) => {
      const n8nConn = (() => {
        if (typeof window === "undefined") return null;
        try {
          const raw = localStorage.getItem("naito_n8n_connection");
          if (!raw) return null;
          return JSON.parse(raw) as { url: string; apiKey: string };
        } catch { return null; }
      })();

      const messageText = Array.isArray((message as { parts?: unknown[] }).parts)
        ? ((message as { parts: { type: string; text?: string }[] }).parts)
            .filter(p => p.type === "text")
            .map(p => String(p.text ?? ""))
            .join(" ")
        : "";

      let extraBody: Record<string, unknown> = {};

      // n8n 연결 있을 때: LLM에게 intent 먼저 물어보고 REVERSE면 워크플로우 prefetch
      if (n8nConn?.url && messageText) {
        try {
          const apiKey = (() => {
            if (typeof window === "undefined") return null;
            try { return localStorage.getItem("openai_api_key"); } catch { return null; }
          })();

          const checkResp = await fetch(
            `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/intent`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                message: messageText,
                session_id: chatId,
                model: currentModelIdRef.current,
                n8n_url: n8nConn.url,
                ...(apiKey ? { openai_api_key: apiKey } : {}),
              }),
            }
          );

          if (checkResp.ok) {
            const { intent } = await checkResp.json();
            if (intent === "REVERSE") {
              // 익스텐션 브릿지를 통해 fetch (CORS 우회)
              const requestId = Math.random().toString(36).slice(2);
              const { workflow: workflowJson, error: bridgeError, timedOut } = await new Promise<{
                workflow: string | null;
                error?: string;
                timedOut?: boolean;
              }>((resolve) => {
                const handler = (ev: MessageEvent) => {
                  if (ev.data?.type === "NAITO_WORKFLOW_RESPONSE" && ev.data?.requestId === requestId) {
                    window.removeEventListener("message", handler);
                    resolve({ workflow: ev.data.workflow ?? null, error: ev.data.error });
                  }
                };
                window.addEventListener("message", handler);
                window.postMessage({
                  type: "NAITO_GET_WORKFLOW",
                  requestId,
                  n8nUrl: n8nConn.url,
                  apiKey: n8nConn.apiKey || "",
                  messageText,
                }, "*");
                // 익스텐션 없거나 응답 없으면 8초 후 포기
                setTimeout(() => {
                  window.removeEventListener("message", handler);
                  resolve({ workflow: null, timedOut: true });
                }, 8000);
              });
              if (workflowJson) {
                extraBody = { raw_json: workflowJson };
              } else if (bridgeError) {
                toast({
                  type: "error",
                  description: `n8n에서 워크플로우를 가져오지 못했습니다: ${bridgeError}`,
                });
              } else if (timedOut) {
                toast({
                  type: "error",
                  description:
                    "n8n 워크플로우를 가져오지 못했습니다. Naito 확장 프로그램이 설치·활성화되어 있는지 확인해주세요.",
                });
              }
            }
          }
        } catch {
          // prefetch 실패 시 그냥 진행
        }
      }

      return sendMessage(message, {
        ...options,
        body: { ...((options as { body?: Record<string, unknown> })?.body ?? {}), ...extraBody },
      });
    },
    [sendMessage, chatId, currentModelIdRef]
  );

  const loadedChatIds = useRef(new Set<string>());

  if (isNewChat && !loadedChatIds.current.has(newChatIdRef.current)) {
    loadedChatIds.current.add(newChatIdRef.current);
  }

  useEffect(() => {
    if (loadedChatIds.current.has(chatId)) {
      return;
    }
    if (chatData?.messages) {
      loadedChatIds.current.add(chatId);
      setMessages(chatData.messages);
    }
  }, [chatId, chatData?.messages, setMessages]);

  const prevChatIdRef = useRef(chatId);
  useEffect(() => {
    if (prevChatIdRef.current !== chatId) {
      prevChatIdRef.current = chatId;
      if (isNewChat) {
        setMessages([]);
      }
    }
  }, [chatId, isNewChat, setMessages]);

  useEffect(() => {
    if (chatData && !isNewChat) {
      const cookieModel = document.cookie
        .split("; ")
        .find((row) => row.startsWith("chat-model="))
        ?.split("=")[1];
      if (cookieModel) {
        setCurrentModelId(decodeURIComponent(cookieModel));
      }
    }
  }, [chatData, isNewChat]);

  const hasAppendedQueryRef = useRef(false);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("query");
    if (query && !hasAppendedQueryRef.current) {
      hasAppendedQueryRef.current = true;
      window.history.replaceState(
        {},
        "",
        `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/chat/${chatId}`
      );
      sendMessage({
        role: "user" as const,
        parts: [{ type: "text", text: query }],
      });
    }
  }, [sendMessage, chatId]);

  useAutoResume({
    autoResume: !isNewChat && !!chatData,
    initialMessages,
    resumeStream,
    setMessages,
  });

  const isReadonly = isNewChat ? false : (chatData?.isReadonly ?? false);

  const { data: votes } = useSWR<Vote[]>(
    !isReadonly && messages.length >= 2
      ? `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/vote?chatId=${chatId}`
      : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const value = useMemo<ActiveChatContextValue>(
    () => ({
      chatId,
      messages,
      setMessages,
      sendMessage: sendMessageWithN8nPrefetch,
      status,
      stop,
      regenerate,
      addToolApprovalResponse,
      input,
      setInput,
      visibilityType: visibility,
      isReadonly,
      isLoading: !isNewChat && isLoading,
      votes,
      currentModelId,
      setCurrentModelId,
      showCreditCardAlert,
      setShowCreditCardAlert,
    }),
    [
      chatId,
      messages,
      setMessages,
      sendMessageWithN8nPrefetch,
      status,
      stop,
      regenerate,
      addToolApprovalResponse,
      input,
      visibility,
      isReadonly,
      isNewChat,
      isLoading,
      votes,
      currentModelId,
      showCreditCardAlert,
    ]
  );

  return (
    <ActiveChatContext.Provider value={value}>
      {children}
    </ActiveChatContext.Provider>
  );
}

export function useActiveChat() {
  const context = useContext(ActiveChatContext);
  if (!context) {
    throw new Error("useActiveChat must be used within ActiveChatProvider");
  }
  return context;
}
