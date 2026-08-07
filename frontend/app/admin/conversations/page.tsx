"use client";

import * as React from "react";
import { ChevronLeft, MessageSquare, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import type { ConversationDetail, ConversationSummary } from "@/types";

export default function AdminConversationsPage() {
  const { t } = useI18n();
  const [conversations, setConversations] = React.useState<ConversationSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [detail, setDetail] = React.useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState<string | null>(null);
  const { toast } = useToast();

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<{ items: ConversationSummary[] }>("/api/admin/conversations");
      setConversations(data.items);
    } catch {
      toast(t("conv.toast.loadFailed"), { variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [toast, t]);

  React.useEffect(() => {
    load();
  }, [load]);

  const openDetail = async (sessionId: string) => {
    setDetailLoading(true);
    setDetail(null);
    try {
      const data = await api.get<ConversationDetail>(`/api/admin/conversations/${sessionId}`);
      setDetail(data);
    } catch {
      toast(t("conv.toast.loadDetailFailed"), { variant: "error" });
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    try {
      await api.delete(`/api/admin/conversations/${confirmDelete}`);
      toast(t("conv.toast.deleted"), { variant: "success" });
      setConfirmDelete(null);
      setDetail(null);
      load();
    } catch {
      toast(t("conv.toast.deleteFailed"), { variant: "error" });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("conv.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("conv.subtitle", { count: conversations.length })}</p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{t("conv.noConversations")}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("conv.colTitle")}</TableHead>
                  <TableHead>{t("conv.colSession")}</TableHead>
                  <TableHead>{t("conv.colMessages")}</TableHead>
                  <TableHead>{t("conv.colLast")}</TableHead>
                  <TableHead>{t("conv.colUpdated")}</TableHead>
                  <TableHead className="text-right">{t("conv.colActions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.map((conversation) => (
                  <TableRow key={conversation.session_id} className="cursor-pointer" onClick={() => openDetail(conversation.session_id)}>
                    <TableCell className="font-medium">{conversation.title}</TableCell>
                    <TableCell className="font-mono text-xs">{truncate(conversation.session_id, 16)}</TableCell>
                    <TableCell>{conversation.message_count}</TableCell>
                    <TableCell className="max-w-[240px] truncate text-muted-foreground">{conversation.last_message || "—"}</TableCell>
                    <TableCell className="whitespace-nowrap text-xs">{formatDate(conversation.updated_at)}</TableCell>
                    <TableCell>
                      <div className="flex justify-end">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive"
                          onClick={(event) => {
                            event.stopPropagation();
                            setConfirmDelete(conversation.session_id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!detail || detailLoading} onOpenChange={(open) => !open && setDetail(null)}>
        {detail && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Button size="sm" variant="ghost" onClick={() => setDetail(null)} className="-ml-2">
                  <ChevronLeft className="h-4 w-4" />
                  {t("conv.back")}
                </Button>
                {detail.title}
              </DialogTitle>
              <DialogDescription>
                {t("conv.sessionInfo", { id: detail.session_id, count: detail.messages.length })}
              </DialogDescription>
            </DialogHeader>
            <div className="max-h-[55vh] space-y-3 overflow-y-auto pr-1">
              {detail.messages.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">{t("conv.noMessages")}</p>
              ) : (
                detail.messages.map((message) => (
                  <div key={message.id} className="rounded-lg border p-3">
                    <div className="mb-1 flex items-center gap-2">
                      <Badge variant={message.role === "user" ? "secondary" : "info"}>{message.role}</Badge>
                      <span className="text-xs text-muted-foreground">{formatDate(message.created_at)}</span>
                    </div>
                    <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {message.sources.map((source) => (
                          <Badge key={source.chunk_id} variant="outline">
                            {source.filename}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </>
        )}
        {detailLoading && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}
      </Dialog>

      <Dialog open={!!confirmDelete} onOpenChange={(open) => !open && setConfirmDelete(null)}>
        <DialogHeader>
          <DialogTitle>{t("conv.deleteTitle")}</DialogTitle>
          <DialogDescription>{t("conv.deleteDesc")}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmDelete(null)}>
            {t("common.cancel")}
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            {t("common.delete")}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
