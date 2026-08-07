"use client";

import { Download, ExternalLink, FileText } from "lucide-react";
import { fileUrl } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Source } from "@/types";

interface SourceCardProps {
  source: Source;
  index: number;
  page: string | null;
}

export function SourceCard({ source, index, page }: SourceCardProps) {
  const { t } = useI18n();
  return (
    <div
      id={`source-${index}`}
      className="flex items-start gap-3 rounded-lg border bg-muted/40 p-3 transition-shadow"
    >
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
        <FileText className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{source.title || source.filename}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {source.document_type.toUpperCase()}
          {page ? ` · ${page}` : ""} · {t("chat.score", { p: (source.relevance_score * 100).toFixed(0) })}
        </p>
      </div>
      <div className="flex shrink-0 gap-1.5">
        <a
          href={fileUrl(source.view_url)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          {t("chat.view")}
        </a>
        <a
          href={fileUrl(source.download_url)}
          download
          className="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <Download className="h-3.5 w-3.5" />
          {t("chat.download")}
        </a>
      </div>
    </div>
  );
}
