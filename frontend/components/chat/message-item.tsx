"use client";

import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { Markdown } from "@/components/chat/markdown";
import { SourceCard } from "@/components/chat/source-card";
import { useI18n } from "@/lib/i18n";
import type { ChatMessageData, Source } from "@/types";

interface MessageItemProps {
  message: ChatMessageData;
  isStreaming: boolean;
}

function dedupeSources(sources: Source[]): Source[] {
  const seen = new Map<string, Source>();
  for (const source of sources) {
    const key = `${source.document_id}-${source.page_number ?? ""}`;
    if (!seen.has(key) || source.relevance_score > (seen.get(key)?.relevance_score ?? 0)) {
      seen.set(key, source);
    }
  }
  return Array.from(seen.values());
}

export function MessageItem({ message, isStreaming }: MessageItemProps) {
  const { t } = useI18n();
  const isUser = message.role === "user";
  const sources = message.sources && message.sources.length > 0 ? dedupeSources(message.sources) : [];
  const pageText = (source: Source) => (source.page_number ? t("chat.page", { n: source.page_number }) : null);

  return (
    <div className={cn("flex w-full gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div className={cn("flex max-w-[85%] flex-col gap-2", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-7",
            isUser
              ? "bg-primary text-primary-foreground"
              : "border bg-card text-foreground shadow-sm",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <Markdown content={message.content} />
          )}
          {isStreaming && !isUser && message.content === "" && (
            <div className="flex gap-1 py-1">
              <span className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-pulse-dot" />
              <span className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-pulse-dot [animation-delay:0.2s]" />
              <span className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-pulse-dot [animation-delay:0.4s]" />
            </div>
          )}
        </div>

        {!isUser && sources.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="px-1 text-xs font-medium text-muted-foreground">{t("chat.relatedDocuments")}</p>
            {sources.map((source, index) => (
              <SourceCard key={`${source.document_id}-${index}`} source={source} index={index + 1} page={pageText(source)} />
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
