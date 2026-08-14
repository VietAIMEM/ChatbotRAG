="use client";

import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import type { ConversationSummary } from "@/types";

interface ChatSidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  open: boolean;
  onNewConversation: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}

export function ChatSidebar({
  conversations,
  activeId,
  open,
  onNewConversation,
  onSelect,
  onDelete,
}: ChatSidebarProps) {
  const { t } = useI18n();
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r bg-card transition-transform duration-200 lg:static lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="border-b p-4">
        <Button onClick={onNewConversation} className="w-full justify-start gap-2">
          <Plus className="h-4 w-4" />
          {t("chat.newConversation")}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <p className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("chat.conversations")}
        </p>
        {conversations.length === 0 ? (
          <p className="px-3 py-2 text-sm text-muted-foreground">{t("chat.noConversations")}</p>
        ) : (
          <div className="space-y-1">
            {conversations.map((conversation) => (
              <div
                key={conversation.session_id}
                className={cn(
                  "group flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent",
                  activeId === conversation.session_id && "bg-accent",
                )}
                onClick={() => onSelect(conversation.session_id)}
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
                <button
                  type="button"
                  className="shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                  aria-label={t("chat.deleteConversation")}
                  onClick={(event) => {
                    event.stopPropagation();
                    onDelete(conversation.session_id);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
