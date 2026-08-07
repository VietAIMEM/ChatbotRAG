"use client";

import * as React from "react";
import { Activity, AlertTriangle, CheckCircle2, FileText, MessageSquare, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { StatCard } from "@/components/admin/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { DashboardStats } from "@/types";

export default function AdminDashboardPage() {
  const { t } = useI18n();
  const [stats, setStats] = React.useState<DashboardStats | null>(null);
  const [loading, setLoading] = React.useState(true);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<DashboardStats>("/api/admin/dashboard/stats");
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("dash.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("dash.subtitle")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="h-3.5 w-3.5" />
          {t("dash.refresh")}
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t("dash.totalDocuments")} value={stats?.total_documents ?? 0} icon={<FileText className="h-4 w-4" />} loading={loading} />
        <StatCard label={t("dash.indexed")} value={stats?.indexed_documents ?? 0} icon={<CheckCircle2 className="h-4 w-4" />} accent="bg-emerald-500/10 text-emerald-600" loading={loading} />
        <StatCard label={t("dash.processing")} value={stats?.processing_documents ?? 0} icon={<RefreshCw className="h-4 w-4" />} accent="bg-amber-500/10 text-amber-600" loading={loading} />
        <StatCard label={t("dash.failed")} value={stats?.failed_documents ?? 0} icon={<AlertTriangle className="h-4 w-4" />} accent="bg-red-500/10 text-red-600" loading={loading} />
        <StatCard label={t("dash.conversations")} value={stats?.total_conversations ?? 0} icon={<MessageSquare className="h-4 w-4" />} accent="bg-sky-500/10 text-sky-600" loading={loading} />
        <StatCard label={t("dash.totalMessages")} value={stats?.total_messages ?? 0} icon={<MessageSquare className="h-4 w-4" />} loading={loading} />
        <StatCard label={t("dash.ragQueries")} value={stats?.rag_queries ?? 0} icon={<Activity className="h-4 w-4" />} loading={loading} />
        <StatCard label={t("dash.llmRequests")} value={stats?.llm_requests ?? 0} icon={<Activity className="h-4 w-4" />} loading={loading} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("dash.recentActivity")}</CardTitle>
        </CardHeader>
        <CardContent>
          {stats && stats.recent_activity.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">{t("dash.noActivity")}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("dash.colTime")}</TableHead>
                  <TableHead>{t("dash.colEvent")}</TableHead>
                  <TableHead>{t("dash.colQuestion")}</TableHead>
                  <TableHead>{t("dash.colLlm")}</TableHead>
                  <TableHead>{t("dash.colLatency")}</TableHead>
                  <TableHead>{t("dash.colStatus")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(stats?.recent_activity ?? []).map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-xs">{formatDate(log.timestamp)}</TableCell>
                    <TableCell>
                      <Badge variant={log.level === "ERROR" ? "destructive" : "secondary"}>{log.event_type}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[240px] truncate">{log.question || "—"}</TableCell>
                    <TableCell className="text-xs">
                      {log.llm_provider ? `${log.llm_provider} / ${log.llm_model ?? ""}` : "—"}
                    </TableCell>
                    <TableCell className="text-xs">{log.latency_ms ? `${log.latency_ms.toFixed(0)} ms` : "—"}</TableCell>
                    <TableCell>
                      <Badge variant={log.status === "ok" ? "success" : "destructive"}>{log.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
