"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { toast as sonnerToast } from "sonner";
import { cn } from "@/lib/utils";
import { CheckCircleFillIcon, WarningIcon } from "./icons";

const iconsByType: Record<"success" | "error", ReactNode> = {
  success: <CheckCircleFillIcon />,
  error: <WarningIcon />,
};

function normalizeToastDescription(
  type: "success" | "error",
  description: string
) {
  if (type !== "error") {
    return description;
  }

  const raw = String(description || "");
  const shouldHideInternalError =
    raw.includes("importKey") ||
    raw.includes("Cannot read properties of undefined") ||
    raw.includes("TypeError") ||
    raw.includes("Failed to fetch") ||
    raw.includes("unexpected response") ||
    raw.includes("NetworkError");

  if (!shouldHideInternalError) {
    return raw;
  }

  return "일시적인 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
}

export function toast(props: Omit<ToastProps, "id">) {
  const normalizedDescription = normalizeToastDescription(
    props.type,
    props.description
  );

  return sonnerToast.custom((id) => (
    <Toast description={normalizedDescription} id={id} type={props.type} />
  ));
}

function Toast(props: ToastProps) {
  const { id, type, description } = props;

  const descriptionRef = useRef<HTMLDivElement>(null);
  const [multiLine, setMultiLine] = useState(false);

  useEffect(() => {
    const el = descriptionRef.current;
    if (!el) {
      return;
    }

    const update = () => {
      const lineHeight = Number.parseFloat(getComputedStyle(el).lineHeight);
      const lines = Math.round(el.scrollHeight / lineHeight);
      setMultiLine(lines > 1);
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);

    return () => ro.disconnect();
  }, []);

  return (
    <div className="flex toast-mobile:w-[356px] w-full justify-center">
      <div
        className={cn(
          "flex toast-mobile:w-fit w-full flex-row gap-3 rounded-lg bg-card border border-border/50 shadow-[var(--shadow-float)] p-3",
          multiLine ? "items-start" : "items-center"
        )}
        data-testid="toast"
        key={id}
      >
        <div
          className={cn(
            "data-[type=error]:text-red-600 data-[type=success]:text-green-600",
            { "pt-1": multiLine }
          )}
          data-type={type}
        >
          {iconsByType[type]}
        </div>
        <div className="text-sm text-foreground" ref={descriptionRef}>
          {description}
        </div>
      </div>
    </div>
  );
}

type ToastProps = {
  id: string | number;
  type: "success" | "error";
  description: string;
};
