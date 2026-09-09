"use client";

import type { UIMessage } from "ai";
import type { ComponentProps, HTMLAttributes, ReactElement } from "react";

import { Button } from "@/components/ui/button";
import {
  ButtonGroup,
  ButtonGroupText,
} from "@/components/ui/button-group";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { math } from "@streamdown/math";
import { mermaid } from "@streamdown/mermaid";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import {
  createContext,
  memo,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Streamdown } from "streamdown";
import { findNodeIconInText } from "@/lib/node-icons";

// Lucide icon SVG paths — 외부 API 없이 인라인으로 렌더링
const LUCIDE_PATHS: Record<string, string> = {
  lightbulb:
    "<path d='M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5'/><path d='M9 18h6'/><path d='M10 22h4'/>",
  "book-open":
    "<path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/>",
  zap: "<polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'/>",
  "alert-circle":
    "<circle cx='12' cy='12' r='10'/><line x1='12' y1='8' x2='12' y2='12'/><line x1='12' y1='16' x2='12.01' y2='16'/>",
  code: "<polyline points='16 18 22 12 16 6'/><polyline points='8 6 2 12 8 18'/>",
  play: "<polygon points='5 3 19 12 5 21 5 3'/>",
  layout:
    "<rect x='3' y='3' width='18' height='18' rx='2' ry='2'/><line x1='3' y1='9' x2='21' y2='9'/><line x1='9' y1='21' x2='9' y2='9'/>",
  "git-branch":
    "<line x1='6' y1='3' x2='6' y2='15'/><circle cx='18' cy='6' r='3'/><circle cx='6' cy='18' r='3'/><path d='M18 9a9 9 0 0 1-9 9'/>",
  layers:
    "<polygon points='12 2 2 7 12 12 22 7 12 2'/><polyline points='2 17 12 22 22 17'/><polyline points='2 12 12 17 22 12'/>",
  "trending-up":
    "<polyline points='23 6 13 16 8 11 1 18'/><polyline points='17 6 23 6 23 12'/>",
  search:
    "<circle cx='11' cy='11' r='8'/><line x1='21' y1='21' x2='16.65' y2='16.65'/>",
  wrench:
    "<path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z'/>",
  "alert-triangle":
    "<path d='M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'/><line x1='12' y1='9' x2='12' y2='13'/><line x1='12' y1='17' x2='12.01' y2='17'/>",
  sliders:
    "<line x1='4' y1='21' x2='4' y2='14'/><line x1='4' y1='10' x2='4' y2='3'/><line x1='12' y1='21' x2='12' y2='12'/><line x1='12' y1='8' x2='12' y2='3'/><line x1='20' y1='21' x2='20' y2='16'/><line x1='20' y1='12' x2='20' y2='3'/><line x1='1' y1='14' x2='7' y2='14'/><line x1='9' y1='8' x2='15' y2='8'/><line x1='17' y1='16' x2='23' y2='16'/>",
  sparkles:
    "<path d='M12 3l1.88 5.79L20 10.5l-5.12 4.21L16.7 21 12 17.77 7.3 21l1.82-6.29L4 10.5l6.12-1.71z'/>",
  info: "<circle cx='12' cy='12' r='10'/><line x1='12' y1='16' x2='12' y2='12'/><line x1='12' y1='8' x2='12.01' y2='8'/>",
  "check-circle":
    "<path d='M22 11.08V12a10 10 0 1 1-5.93-9.14'/><polyline points='22 4 12 14.01 9 11.01'/>",
  target:
    "<circle cx='12' cy='12' r='10'/><circle cx='12' cy='12' r='6'/><circle cx='12' cy='12' r='2'/>",
  list: "<line x1='8' y1='6' x2='21' y2='6'/><line x1='8' y1='12' x2='21' y2='12'/><line x1='8' y1='18' x2='21' y2='18'/><line x1='3' y1='6' x2='3.01' y2='6'/><line x1='3' y1='12' x2='3.01' y2='12'/><line x1='3' y1='18' x2='3.01' y2='18'/>",
  settings:
    "<circle cx='12' cy='12' r='3'/><path d='M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'/>",
  "file-text":
    "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='16' y1='13' x2='8' y2='13'/><line x1='16' y1='17' x2='8' y2='17'/>",
  globe:
    "<circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/>",
  "arrow-right":
    "<line x1='5' y1='12' x2='19' y2='12'/><polyline points='12 5 19 12 12 19'/>",
  star: "<polygon points='12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2'/>",
  activity:
    "<polyline points='22 12 18 12 15 21 9 3 6 12 2 12'/>",
  shield:
    "<path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/>",
  cpu: "<rect x='4' y='4' width='16' height='16' rx='2' ry='2'/><rect x='9' y='9' width='6' height='6'/><line x1='9' y1='1' x2='9' y2='4'/><line x1='15' y1='1' x2='15' y2='4'/><line x1='9' y1='20' x2='9' y2='23'/><line x1='15' y1='20' x2='15' y2='23'/><line x1='20' y1='9' x2='23' y2='9'/><line x1='20' y1='14' x2='23' y2='14'/><line x1='1' y1='9' x2='4' y2='9'/><line x1='1' y1='14' x2='4' y2='14'/>",
};

function makeSvgUri(iconName: string, hexColor: string): string {
  const paths = LUCIDE_PATHS[iconName] ?? LUCIDE_PATHS.sparkles;
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='${hexColor}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>${paths}</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

const HEADER_ICON_MAP: Record<string, { name: string; color: string }> = {
  "핵심 요약": { name: "lightbulb", color: "#f59e0b" },
  "상세 설명": { name: "book-open", color: "#3b82f6" },
  "실전 활용법": { name: "zap", color: "#ec4899" },
  "주의사항": { name: "alert-circle", color: "#ef4444" },
  "생성된 표현식": { name: "code", color: "#06b6d4" },
  "사용 방법": { name: "play", color: "#10b981" },
  "워크플로우 설계": { name: "layout", color: "#3b82f6" },
  "전체 흐름": { name: "git-branch", color: "#0ea5e9" },
  "노드별 설명": { name: "layers", color: "#8b5cf6" },
  "최적화 권고": { name: "trending-up", color: "#10b981" },
  "원인 분석": { name: "search", color: "#f59e0b" },
  "해결 방법": { name: "wrench", color: "#06b6d4" },
  "에러 진단": { name: "alert-triangle", color: "#f59e0b" },
  "주요 속성": { name: "sliders", color: "#3b82f6" },
  "노드란": { name: "cpu", color: "#8b5cf6" },
  "언제 사용": { name: "target", color: "#10b981" },
  "동작 방식": { name: "activity", color: "#0ea5e9" },
  "유사 노드": { name: "git-branch", color: "#6366f1" },
  "배포 체크": { name: "check-circle", color: "#10b981" },
  "재발 방지": { name: "shield", color: "#ef4444" },
  "패치 코드": { name: "code", color: "#06b6d4" },
  "n8n JSON": { name: "file-text", color: "#94a3b8" },
  "표현식": { name: "code", color: "#06b6d4" },
  "요약": { name: "list", color: "#94a3b8" },
  "설명": { name: "info", color: "#3b82f6" },
  "속성": { name: "sliders", color: "#3b82f6" },
};

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage["role"];
};

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full max-w-[95%] flex-col gap-2",
      from === "user" ? "is-user ml-auto justify-end" : "is-assistant",
      className
    )}
    {...props}
  />
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      "flex min-w-0 max-w-full flex-col gap-2 overflow-hidden text-sm text-foreground",
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export type MessageActionsProps = ComponentProps<"div">;

export const MessageActions = ({
  className,
  children,
  ...props
}: MessageActionsProps) => (
  <div className={cn("flex items-center gap-1", className)} {...props}>
    {children}
  </div>
);

export type MessageActionProps = ComponentProps<typeof Button> & {
  tooltip?: string;
  label?: string;
};

export const MessageAction = ({
  tooltip,
  children,
  label,
  variant = "ghost",
  size = "icon-sm",
  ...props
}: MessageActionProps) => {
  const button = (
    <Button size={size} type="button" variant={variant} {...props}>
      {children}
      <span className="sr-only">{label || tooltip}</span>
    </Button>
  );

  if (tooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent>
            <p>{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
};

interface MessageBranchContextType {
  currentBranch: number;
  totalBranches: number;
  goToPrevious: () => void;
  goToNext: () => void;
  branches: ReactElement[];
  setBranches: (branches: ReactElement[]) => void;
}

const MessageBranchContext = createContext<MessageBranchContextType | null>(
  null
);

const useMessageBranch = () => {
  const context = useContext(MessageBranchContext);

  if (!context) {
    throw new Error(
      "MessageBranch components must be used within MessageBranch"
    );
  }

  return context;
};

export type MessageBranchProps = HTMLAttributes<HTMLDivElement> & {
  defaultBranch?: number;
  onBranchChange?: (branchIndex: number) => void;
};

export const MessageBranch = ({
  defaultBranch = 0,
  onBranchChange,
  className,
  ...props
}: MessageBranchProps) => {
  const [currentBranch, setCurrentBranch] = useState(defaultBranch);
  const [branches, setBranches] = useState<ReactElement[]>([]);

  const handleBranchChange = useCallback(
    (newBranch: number) => {
      setCurrentBranch(newBranch);
      onBranchChange?.(newBranch);
    },
    [onBranchChange]
  );

  const goToPrevious = useCallback(() => {
    const newBranch =
      currentBranch > 0 ? currentBranch - 1 : branches.length - 1;
    handleBranchChange(newBranch);
  }, [currentBranch, branches.length, handleBranchChange]);

  const goToNext = useCallback(() => {
    const newBranch =
      currentBranch < branches.length - 1 ? currentBranch + 1 : 0;
    handleBranchChange(newBranch);
  }, [currentBranch, branches.length, handleBranchChange]);

  const contextValue = useMemo<MessageBranchContextType>(
    () => ({
      branches,
      currentBranch,
      goToNext,
      goToPrevious,
      setBranches,
      totalBranches: branches.length,
    }),
    [branches, currentBranch, goToNext, goToPrevious]
  );

  return (
    <MessageBranchContext.Provider value={contextValue}>
      <div
        className={cn("grid w-full gap-2 [&>div]:pb-0", className)}
        {...props}
      />
    </MessageBranchContext.Provider>
  );
};

export type MessageBranchContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageBranchContent = ({
  children,
  ...props
}: MessageBranchContentProps) => {
  const { currentBranch, setBranches, branches } = useMessageBranch();
  const childrenArray = useMemo(
    () => (Array.isArray(children) ? children : [children]),
    [children]
  );

  // Use useEffect to update branches when they change
  useEffect(() => {
    if (branches.length !== childrenArray.length) {
      setBranches(childrenArray);
    }
  }, [childrenArray, branches, setBranches]);

  return childrenArray.map((branch, index) => (
    <div
      className={cn(
        "grid gap-2 overflow-hidden [&>div]:pb-0",
        index === currentBranch ? "block" : "hidden"
      )}
      key={branch.key}
      {...props}
    >
      {branch}
    </div>
  ));
};

export type MessageBranchSelectorProps = ComponentProps<typeof ButtonGroup>;

export const MessageBranchSelector = ({
  className,
  ...props
}: MessageBranchSelectorProps) => {
  const { totalBranches } = useMessageBranch();

  // Don't render if there's only one branch
  if (totalBranches <= 1) {
    return null;
  }

  return (
    <ButtonGroup
      className={cn(
        "[&>*:not(:first-child)]:rounded-l-md [&>*:not(:last-child)]:rounded-r-md",
        className
      )}
      orientation="horizontal"
      {...props}
    />
  );
};

export type MessageBranchPreviousProps = ComponentProps<typeof Button>;

export const MessageBranchPrevious = ({
  children,
  ...props
}: MessageBranchPreviousProps) => {
  const { goToPrevious, totalBranches } = useMessageBranch();

  return (
    <Button
      aria-label="Previous branch"
      disabled={totalBranches <= 1}
      onClick={goToPrevious}
      size="icon-sm"
      type="button"
      variant="ghost"
      {...props}
    >
      {children ?? <ChevronLeftIcon size={14} />}
    </Button>
  );
};

export type MessageBranchNextProps = ComponentProps<typeof Button>;

export const MessageBranchNext = ({
  children,
  ...props
}: MessageBranchNextProps) => {
  const { goToNext, totalBranches } = useMessageBranch();

  return (
    <Button
      aria-label="Next branch"
      disabled={totalBranches <= 1}
      onClick={goToNext}
      size="icon-sm"
      type="button"
      variant="ghost"
      {...props}
    >
      {children ?? <ChevronRightIcon size={14} />}
    </Button>
  );
};

export type MessageBranchPageProps = HTMLAttributes<HTMLSpanElement>;

export const MessageBranchPage = ({
  className,
  ...props
}: MessageBranchPageProps) => {
  const { currentBranch, totalBranches } = useMessageBranch();

  return (
    <ButtonGroupText
      className={cn(
        "border-none bg-transparent text-muted-foreground shadow-none",
        className
      )}
      {...props}
    >
      {currentBranch + 1} of {totalBranches}
    </ButtonGroupText>
  );
};

export type MessageResponseProps = ComponentProps<typeof Streamdown>;

const streamdownPlugins = { cjk, code, math, mermaid };

export const MessageResponse = memo(
  ({ className, children, ...props }: MessageResponseProps) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (!containerRef.current) return;

      const headers = containerRef.current.querySelectorAll("h2, h3");
      headers.forEach((header) => {
        if (header.querySelector(":scope > .n9n-heading-icon, :scope > .n9n-node-icon")) {
          return;
        }

        const text = (header.textContent ?? "").trim();
        const nodeMatch = findNodeIconInText(text);
        if (nodeMatch) {
          const img = document.createElement("img");
          img.className = "n9n-node-icon";
          img.src = nodeMatch.icon;
          img.alt = "";
          img.setAttribute("aria-hidden", "true");
          header.prepend(img);
          return;
        }

        const matched = Object.entries(HEADER_ICON_MAP).find(([key]) =>
          text.includes(key)
        )?.[1] ?? { name: "sparkles", color: "#94a3b8" };

        const icon = document.createElement("span");
        icon.className = "n9n-heading-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.style.backgroundImage = `url("${makeSvgUri(matched.name, matched.color)}")`;
        header.prepend(icon);
      });

      // 굵은 글씨(**노드 이름**)로 언급된 n8n 노드에도 아이콘을 붙인다.
      // 같은 노드가 메시지 안에서 여러 번 언급될 수 있으므로, 각 노드 이름당
      // 처음 등장하는 곳에만 아이콘을 붙여 시각적으로 과하지 않게 한다.
      const seenNodeNames = new Set<string>();
      const strongEls = containerRef.current.querySelectorAll("strong");
      strongEls.forEach((strong) => {
        if (strong.querySelector(":scope > .n9n-node-icon")) return;
        const text = (strong.textContent ?? "").trim();
        if (!text) return;
        const nodeMatch = findNodeIconInText(text);
        if (!nodeMatch || seenNodeNames.has(nodeMatch.name)) return;
        seenNodeNames.add(nodeMatch.name);

        const img = document.createElement("img");
        img.className = "n9n-node-icon n9n-node-icon--inline";
        img.src = nodeMatch.icon;
        img.alt = "";
        img.setAttribute("aria-hidden", "true");
        strong.prepend(img);
      });
    }, [children]);

    return (
      <>
        <style jsx global>{`
          .message-markdown h2,
          .message-markdown h3 {
            display: flex;
            align-items: center;
            gap: 0.55rem;
          }

          .message-markdown .n9n-heading-icon {
            display: inline-block;
            flex: 0 0 auto;
            width: 1.05rem;
            height: 1.05rem;
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            opacity: 0.9;
          }

          .message-markdown h3 .n9n-heading-icon {
            width: 0.92rem;
            height: 0.92rem;
          }

          .message-markdown .n9n-node-icon {
            display: inline-block;
            flex: 0 0 auto;
            width: 1.05rem;
            height: 1.05rem;
            border-radius: 0.2rem;
            object-fit: contain;
            vertical-align: -0.2rem;
          }

          .message-markdown h3 .n9n-node-icon {
            width: 0.92rem;
            height: 0.92rem;
          }

          .message-markdown .n9n-node-icon--inline {
            width: 0.95rem;
            height: 0.95rem;
            margin-right: 0.3rem;
          }
        `}</style>
        <div ref={containerRef}>
          <Streamdown
            className={cn(
              "message-markdown size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
              className
            )}
            plugins={streamdownPlugins}
            {...props}
          >
            {children}
          </Streamdown>
        </div>
      </>
    );
  },
  (prevProps, nextProps) => prevProps.children === nextProps.children
);

MessageResponse.displayName = "MessageResponse";

export type MessageToolbarProps = ComponentProps<"div">;

export const MessageToolbar = ({
  className,
  children,
  ...props
}: MessageToolbarProps) => (
  <div
    className={cn(
      "mt-4 flex w-full items-center justify-between gap-4",
      className
    )}
    {...props}
  >
    {children}
  </div>
);
