import { z } from "zod";

const textPartSchema = z.object({
  type: z.enum(["text"]),
  // n8n 워크플로우 JSON을 채팅창에 직접 붙여넣는 수동 폴백 경로를 지원하려면
  // 넉넉한 상한이 필요함 (복잡한 워크플로우는 수만 자에 달함).
  text: z.string().min(1).max(100_000),
});

const filePartSchema = z.object({
  type: z.enum(["file"]),
  mediaType: z.enum(["image/jpeg", "image/png"]),
  name: z.string().min(1).max(100),
  url: z.string().url(),
});

const partSchema = z.union([textPartSchema, filePartSchema]);

const userMessageSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(["user"]),
  parts: z.array(partSchema),
});

const toolApprovalMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  parts: z.array(z.record(z.unknown())),
});

export const postRequestBodySchema = z.object({
  id: z.string().uuid(),
  message: userMessageSchema.optional(),
  messages: z.array(toolApprovalMessageSchema).optional(),
  selectedChatModel: z.string().optional(),
  selectedVisibilityType: z.enum(["public", "private"]).default("private"),
  raw_json: z.string().optional(),
  needs_canvas: z.boolean().optional(),
  openai_api_key: z.string().optional(),
  n8n_url: z.string().optional(),
  n8n_api_key: z.string().optional(),
});

export type PostRequestBody = z.infer<typeof postRequestBodySchema>;
