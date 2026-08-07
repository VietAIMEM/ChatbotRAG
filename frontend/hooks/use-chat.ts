"use client";

import * as React from "react";
import { api, ApiError, streamChat } from "@/lib/api";
import {
  getClientId,
  getCurrentConversationId,
  setCurrentConversationId,
} from "@/lib/storage";
import { useI18n } from "@/lib/i18n";
import type { ChatMessageData, ConversationSummary, Source, SSEEvent } from "@/types";

export interface ChatState {
  messages: ChatMessageData[];
  conversationId: string | null;
  isStreaming: boolean;
  conversations: ConversationSummary[];
}

export function useChat() {
  const { t } = useI18n();
  const [messages, setMessages] = React.useState<ChatMessageData[]>([]);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [conversations, setConversations] = React.useState<ConversationSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [chatbotName, setChatbotName] = React.useState("Postgraduate Information Assistant");
  const abortRef = React.useRef<AbortController | null>(null);

  const refreshConversations = React.useCallback(async () => {
    try {
      const clientId = getClientId();
      const result = await api.get<{ items: ConversationSummary[] }>(`/api/conversations?client_id=${encodeURIComponent(clientId)}`);
      setConversations(result.items);
    } catch {
      /* ignore */
    }
  }, []);

  const loadConversation = React.useCallback(
    async (sessionId: string) => {
      try {
        const clientId = getClientId();
        const detail = await api.get<{ messages: ChatMessageData[] }>(
          `/api/conversations/${encodeURIComponent(sessionId)}?client_id=${encodeURIComponent(clientId)}`,
        );
        setMessages(detail.messages);
        setConversationId(sessionId);
        setCurrentConversationId(sessionId);
      } catch {
        setCurrentConversationId(null);
        setConversationId(null);
        setMessages([]);
      }
    },
    [],
  );

  React.useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const settings = await api.get<{ site_name: string; chatbot_name: string; welcome_message: string }>(
          "/api/public-settings",
        );
        if (!cancelled) setChatbotName(settings.chatbot_name);
      } catch {
        /* ignore */
      }
      const saved = getCurrentConversationId();
      if (saved) {
        await loadConversation(saved);
      }
      await refreshConversations();
      if (!cancelled) setLoading(false);
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [loadConversation, refreshConversations]);

  const stopGeneration = React.useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const send = React.useCallback(
    async (question: string) => {
      if (isStreaming) return;
      const clientId = getClientId();
      const text = question.trim();
      if (!text) return;

      const userMessage: ChatMessageData = {
        id: `local-${Date.now()}`,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      };
      const assistantMessage: ChatMessageData = {
        id: `local-${Date.now() + 1}`,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(
          { client_id: clientId, conversation_id: conversationId, question: text },
          (event: SSEEvent) => {
            if (event.type === "delta" && event.content !== undefined) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = { ...last, content: last.content + event.content };
                }
                return next;
              });
            }
            if (event.type === "done") {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = {
                    ...last,
                    content: last.content,
                    sources: event.sources ?? [],
                  };
                }
                return next;
              });
              if (event.conversation_id) {
                setConversationId(event.conversation_id);
                setCurrentConversationId(event.conversation_id);
              }
            }
            if (event.type === "error") {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = {
                    ...last,
                    content: event.message || t("chat.errors.generic"),
                  };
                }
                return next;
              });
            }
          },
          controller.signal,
        );
      } catch (error) {
        if (error instanceof ApiError && error.status === 429) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = {
                ...last,
                content: `⚠️ ${error.message}`,
              };
            }
            return next;
          });
        } else if ((error as Error).name !== "AbortError") {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = {
                ...last,
                content: t("chat.errors.network"),
              };
            }
            return next;
          });
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
        await refreshConversations();
      }
    },
    [conversationId, isStreaming, refreshConversations, t],
  );

  const newConversation = React.useCallback(() => {
    abortRef.current?.abort();
    setConversationId(null);
    setCurrentConversationId(null);
    setMessages([]);
    setIsStreaming(false);
  }, []);

  const selectConversation = React.useCallback(
    async (sessionId: string) => {
      if (isStreaming) abortRef.current?.abort();
      setIsStreaming(false);
      await loadConversation(sessionId);
    },
    [isStreaming, loadConversation],
  );

  const deleteConversation = React.useCallback(
    async (sessionId: string) => {
      try {
        const clientId = getClientId();
        await api.delete(`/api/conversations/${encodeURIComponent(sessionId)}?client_id=${encodeURIComponent(clientId)}`);
        if (conversationId === sessionId) {
          newConversation();
        }
        await refreshConversations();
      } catch {
        /* ignore */
      }
    },
    [conversationId, newConversation, refreshConversations],
  );

  return {
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
  };
}
