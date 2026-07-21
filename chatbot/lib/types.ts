import type { InferUITool, UIMessage } from "ai";
import { z } from "zod";
import type { ArtifactKind } from "@/components/chat/artifact";
import type { createDocument } from "./ai/tools/create-document";
import type { getWeather } from "./ai/tools/get-weather";
import type { requestSuggestions } from "./ai/tools/request-suggestions";
import type { updateDocument } from "./ai/tools/update-document";
import type { Suggestion } from "./db/schema";

export const messageMetadataSchema = z.object({
  createdAt: z.string(),
});

export type MessageMetadata = z.infer<typeof messageMetadataSchema>;

type weatherTool = InferUITool<typeof getWeather>;
type createDocumentTool = InferUITool<ReturnType<typeof createDocument>>;
type updateDocumentTool = InferUITool<ReturnType<typeof updateDocument>>;
type requestSuggestionsTool = InferUITool<
  ReturnType<typeof requestSuggestions>
>;

export type ChatTools = {
  getWeather: weatherTool;
  createDocument: createDocumentTool;
  updateDocument: updateDocumentTool;
  requestSuggestions: requestSuggestionsTool;
};

export type CustomUIDataTypes = {
  textDelta: string;
  imageDelta: string;
  sheetDelta: string;
  codeDelta: string;
  suggestion: Suggestion;
  appendMessage: string;
  id: string;
  title: string;
  kind: ArtifactKind;
  clear: null;
  finish: null;
  "chat-title": string;
  intent: {
    intent: string;
    label: string;
  };
  curriculum: {
    cards: Record<string, unknown>[];
    description?: string;
  };
  expression: {
    raw_expression: string;
    node_type?: string;
  };
  card: Record<string, unknown>;
  error_alert: {
    type?: string;
    tokens?: string[];
    message: string;
  };
  report: {
    title?: string;
    layer?: string;
    content?: string;
    items?: Record<string, unknown>[];
  };
  reg_warning: {
    summary?: string;
    corrections?: Record<string, unknown>[];
  };
  node_property_card: Record<string, unknown>;
  rag_sources: {
    sources: Array<{
      title: string;
      data_type: string;
      source: string;
      preview: string;
    }>;
  };
};

export type ChatMessage = UIMessage<
  MessageMetadata,
  CustomUIDataTypes,
  ChatTools
>;

export type Attachment = {
  name: string;
  url: string;
  contentType: string;
};
