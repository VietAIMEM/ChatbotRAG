"use client";

import * as React from "react";
import Link from "next/link";
import { GraduationCap, Menu, Send, Square, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { MessageItem } from "@/components/chat/message-item";
import { LanguageToggle } from "@/components/language-toggle";
import { useI18n } from "@/lib/i18n";
import { useChat } from "@/hooks/use-chat";

export function ChatInterface() {
  const { t } = useI18n();

  const {
    messages,
    conversationId,
    isStreaming,
    conversations,
    loading,
    chatbotName,
    send,
    stopGeneration,
    newConversation,
    selectConversation,
    deleteConversation,
  } = useChat();

  const [input, setInput] = React.useState("");
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleSubmit = React.useCallback(
    (event?: React.FormEvent) => {
      event?.preventDefault();

      if (!input.trim() || isStreaming) return;

      send(input);
      setInput("");
    },
    [input, isStreaming, send],
  );

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-dvh overflow-hidden">
      <ChatSidebar
        conversations={conversations}
        activeId={conversationId}
        open={sidebarOpen}
        onNewConversation={newConversation}
        onSelect={selectConversation}
        onDelete={deleteConversation}
      />

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center gap-3 border-b bg-background/80 px-4 py-3 backdrop-blur">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label={t("chat.openSidebar")}
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <GraduationCap className="h-5 w-5" />
            </div>

            <div>
              <h1 className="text-sm font-semibold leading-tight">
                {chatbotName}
              </h1>

              <p className="text-xs text-muted-foreground">
                {t("chat.subtitle")}
              </p>
            </div>
          </div>

          {/* Language + Admin */}
          <div className="ml-auto flex items-center gap-2">
            <LanguageToggle />

            <Link href="/admin">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
              >
                <ShieldCheck className="h-4 w-4" />
                Admin
              </Button>
            </Link>
          </div>
        </header>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto"
        >
          <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
            {loading ? (
              <div className="mx-auto mt-12 text-sm text-muted-foreground">
                {t("chat.loadingConversations")}
              </div>
            ) : messages.length === 0 ? (
              <div className="mx-auto mt-16 max-w-xl animate-fade-in-up rounded-2xl border bg-card p-6 text-center shadow-sm">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <GraduationCap className="h-6 w-6" />
                </div>

                <h2 className="text-lg font-semibold">
                  {chatbotName}
                </h2>

                <div className="markdown-body mt-2 whitespace-pre-wrap text-left text-sm text-muted-foreground">
                  {t("chat.welcome")}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <MessageItem
                  key={message.id}
                  message={message}
                  isStreaming={
                    isStreaming &&
                    message.role === "assistant" &&
                    messages[messages.length - 1]?.id === message.id
                  }
                />
              ))
            )}
          </div>
        </div>

        {/* Input */}
        <div className="border-t bg-background/80 px-4 py-3 backdrop-blur">
          <form
            onSubmit={handleSubmit}
            className="mx-auto flex max-w-3xl items-end gap-2"
          >
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder={t("chat.placeholder")}
              className="max-h-40 min-h-[48px] flex-1 resize-none rounded-xl border border-input bg-card px-4 py-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={isStreaming}
            />

            {isStreaming ? (
              <Button
                type="button"
                variant="destructive"
                size="icon"
                className="h-12 w-12 shrink-0"
                onClick={stopGeneration}
                aria-label={t("chat.stopGeneration")}
              >
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                className="h-12 w-12 shrink-0"
                disabled={!input.trim()}
                aria-label={t("chat.send")}
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </form>

          <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
            {t("chat.footer")}
          </p>
        </div>
      </main>
    </div>
  );
}
