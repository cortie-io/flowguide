"use client";

import { useCallback, useEffect, useState } from "react";

export interface N8nConnection {
  url: string;
  apiKey: string;
}

const STORAGE_KEY = "naito_n8n_connection";

export function useN8nConnection() {
  const [connection, setConnection] = useState<N8nConnection | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setConnection(JSON.parse(raw));
    } catch {}
    setLoaded(true);
  }, []);

  const save = useCallback((conn: N8nConnection) => {
    const trimmed: N8nConnection = {
      url: conn.url.trim().replace(/\/$/, ""),
      apiKey: conn.apiKey.trim(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    setConnection(trimmed);
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setConnection(null);
  }, []);

  const inject = useCallback(
    async (workflowJson: Record<string, unknown>): Promise<{ ok: boolean; message: string; workflowId?: string }> => {
      if (!connection?.url) {
        return { ok: false, message: "n8n URL이 설정되지 않았습니다." };
      }
      try {
        const resp = await fetch("/api/n8n-inject", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            n8nUrl: connection.url,
            apiKey: connection.apiKey || undefined,
            workflowJson,
          }),
        });
        const data = await resp.json();
        if (!resp.ok) {
          return { ok: false, message: data?.detail ?? "n8n API 오류" };
        }
        return { ok: true, message: data.message, workflowId: data.workflow_id };
      } catch (err) {
        return { ok: false, message: String(err) };
      }
    },
    [connection]
  );

  return { connection, loaded, save, clear, inject };
}
