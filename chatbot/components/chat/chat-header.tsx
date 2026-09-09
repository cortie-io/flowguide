"use client";

import { PanelLeftIcon } from "lucide-react";
import Link from "next/link";
import { memo } from "react";
import { Button } from "@/components/ui/button";
import { useSidebar } from "@/components/ui/sidebar";
import { N9NIcon } from "./icons";
import { VisibilitySelector, type VisibilityType } from "./visibility-selector";
import { N8nConnectButton } from "./n8n-connect-button";

function PureChatHeader({
  chatId,
  selectedVisibilityType,
  isReadonly,
}: {
  chatId: string;
  selectedVisibilityType: VisibilityType;
  isReadonly: boolean;
}) {
  const { toggleSidebar } = useSidebar();

  return (
    <header className="sticky top-0 flex h-14 items-center gap-2 bg-sidebar px-3">
      <Button
        className="md:hidden"
        onClick={toggleSidebar}
        size="icon-sm"
        variant="ghost"
      >
        <PanelLeftIcon className="size-4" />
      </Button>

      <Link
        className="flex size-9 items-center justify-center rounded-xl md:hidden"
        href="/"
      >
        <N9NIcon size={19} />
      </Link>

      {!isReadonly && (
        <VisibilitySelector
          chatId={chatId}
          selectedVisibilityType={selectedVisibilityType}
        />
      )}

      <div className="ml-auto hidden items-center gap-2.5 md:flex">
        <N8nConnectButton />
        <div className="flex size-8 items-center justify-center rounded-lg bg-muted/40 ring-1 ring-border/50">
          <N9NIcon size={17} />
        </div>
        <span className="text-[13px] font-semibold tracking-tight text-sidebar-foreground/70">
          Naito <span className="font-normal opacity-60">Tutor Agent</span>
        </span>
      </div>
    </header>
  );
}

export const ChatHeader = memo(PureChatHeader, (prevProps, nextProps) => {
  return (
    prevProps.chatId === nextProps.chatId &&
    prevProps.selectedVisibilityType === nextProps.selectedVisibilityType &&
    prevProps.isReadonly === nextProps.isReadonly
  );
});
