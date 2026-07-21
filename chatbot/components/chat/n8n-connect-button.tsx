"use client";

import { useState } from "react";
import { useN8nConnection } from "@/hooks/use-n8n-connection";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function N8nConnectButton() {
  const { connection, loaded, save, clear } = useN8nConnection();
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");

  const isConnected = loaded && !!connection?.url;

  function handleOpen(o: boolean) {
    if (o && connection) {
      setUrl(connection.url);
      setApiKey(connection.apiKey);
    } else if (o) {
      setUrl("http://localhost:5678");
      setApiKey("");
    }
    setOpen(o);
  }

  function handleSave() {
    if (!url.trim()) return;
    save({ url, apiKey });
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={handleOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 rounded-lg px-2.5 text-[12px] font-medium"
        >
          <span
            className={`size-1.5 rounded-full ${
              isConnected ? "bg-emerald-400" : "bg-muted-foreground/40"
            }`}
          />
          <span className="text-muted-foreground">
            {isConnected
              ? new URL(connection!.url).hostname
              : "n8n 연결"}
          </span>
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        className="w-80 p-4"
        sideOffset={8}
      >
        <div className="mb-3">
          <p className="text-[13px] font-semibold text-foreground">
            n8n 인스턴스 연결
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            웹 챗봇에서 워크플로우를 직접 n8n에 생성합니다.
          </p>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-muted-foreground">
              n8n URL
            </label>
            <input
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-[13px] outline-none focus:ring-1 focus:ring-ring"
              placeholder="http://localhost:5678"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
          </div>

          <div>
            <label className="mb-1 block text-[11px] font-medium text-muted-foreground">
              API Key{" "}
              <span className="font-normal opacity-60">(선택 — 자동 주입에 필요)</span>
            </label>
            <input
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-[12px] outline-none focus:ring-1 focus:ring-ring"
              placeholder="n8n_api_..."
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
            <p className="mt-1 text-[10px] text-muted-foreground">
              n8n → Settings → API → Create API Key
            </p>
          </div>

          <div className="flex gap-2 pt-1">
            <Button className="flex-1" size="sm" onClick={handleSave}>
              저장
            </Button>
            {isConnected && (
              <Button
                className="shrink-0"
                size="sm"
                variant="ghost"
                onClick={() => { clear(); setOpen(false); }}
              >
                연결 해제
              </Button>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
