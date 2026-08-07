"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import type { SystemLog } from "@/types";

const levelVariant: Record<string, "default" | "secondary" | "warning" | "destructive" | "info"> = {
  DEBUG: "secondary",
  INFO: "info",
  WARNING: "warning",
  ERROR: "destructive",
  CRITICAL: "destructive",
};

export default function AdminLogsPage() {
  const { t } = useI18n();
  const [logs, setLogs] = React.useState<SystemLog[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [offset, setOffset] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(false);
  const { toast } = useToast();

  const LIMIT = 50;

  const load = React.useCallback(
    async (reset = true) => {
      setLoading(true);
      try {
        const nextOffset = reset ? 0 : offset + LIMIT;
        const data = await api.get<{ items: SystemLog[]; total: number }>(
          `/api/admin/logs?limit=${LIMIT}&offset=${nextOffset}`
        );
        setLogs((prev) => (reset ? data.items : [...prev, ...data.items]));
        setOffset(nextOffset);
        setHasMore(nextOffset + data.items.length < data.total);
      } catch {
        toast(t("logs.toast.loadFailed"), { variant: "error" });
      } finally {
        setLoading(false);
      }
    },
    [offset, toast, t]
  );

  React.useEffect(() => {
    load(true);
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("logs.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("logs.subtitle")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => load(true)}>
          <RefreshCw className="h-4 w-4" />
          {t("logs.refresh")}
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading && logs.length === 0 ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : logs.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{t("logs.empty")}</p>
          ) : (
            <>
              <div className="divide-y">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3 py-3">
                    <Badge variant={levelVariant[log.level] ?? "secondary"} className="mt-0.5 w-20 justify-center">
                      {log.level}
                    </Badge>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <span>{formatDate(log.timestamp)}</span>
                        <span className="font-mono">{log.event_type}</span>
                        {log.latency_ms != null && <span>{log.latency_ms.toFixed(0)} ms</span>}
                      </div>
                      <p className="mt-0.5 break-words text-sm">
                        {log.question || log.error || (log.details ? JSON.stringify(log.details) : "—")}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              {hasMore && (
                <div className="mt-4 flex justify-center">
                  <Button variant="outline" size="sm" onClick={() => load(false)} disabled={loading}>
                    {loading ? t("logs.loading") : t("logs.loadMore")}
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
