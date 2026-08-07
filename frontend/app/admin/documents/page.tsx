"use client";

import * as React from "react";
import {
  Download,
  Eye,
  FileText,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  Wand2,
} from "lucide-react";
import { api, ApiError, fileUrl } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import type { DocumentOut, MetadataExtractionResult, MetadataField, Settings, UploadResult } from "@/types";

const STATUS_VARIANT: Record<string, "warning" | "success" | "destructive" | "secondary" | "info"> = {
  DRAFT: "secondary",
  UPLOADING: "warning",
  PROCESSING: "warning",
  CHUNKING: "warning",
  EMBEDDING: "warning",
  INDEXING: "warning",
  INDEXED: "success",
  FAILED: "destructive",
};

const STATUS_OPTIONS = [
  "DRAFT",
  "UPLOADING",
  "PROCESSING",
  "CHUNKING",
  "EMBEDDING",
  "INDEXING",
  "INDEXED",
  "FAILED",
];

const TERMINAL_STATUSES = new Set(["INDEXED", "FAILED"]);
const TEXT_PREVIEW_TYPES = new Set(["txt", "md"]);
const PREVIEW_CHAR_LIMIT = 4000;

interface DocumentForm {
  title: string;
  description: string;
  category: string;
  year: string;
  version: string;
  department: string;
  program: string;
  language: string;
}

const EMPTY_FORM: DocumentForm = {
  title: "",
  description: "",
  category: "",
  year: "",
  version: "",
  department: "",
  program: "",
  language: "vi",
};

function ConfidenceTag({ field }: { field?: MetadataField | null }) {
  const { t } = useI18n();
  if (!field || field.value === null || field.value === undefined || field.value === "") {
    return <span className="text-[10px] text-muted-foreground">{t("docs.confidenceNotSet")}</span>;
  }
  const percent = Math.round(field.confidence * 100);
  let label = t("docs.confidenceReview");
  let cls = "bg-amber-100 text-amber-700";
  if (field.confidence >= 0.7) {
    label = t("docs.confidenceHigh");
    cls = "bg-emerald-100 text-emerald-700";
  } else if (field.confidence >= 0.4) {
    label = t("docs.confidenceMedium");
    cls = "bg-sky-100 text-sky-700";
  }
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold ${cls}`}>
      {label} · {percent}%
    </span>
  );
}

function FieldLabel({ children, field }: { children: React.ReactNode; field?: MetadataField | null }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <Label>{children}</Label>
      <ConfidenceTag field={field} />
    </div>
  );
}

function DocumentPreview({ doc }: { doc: DocumentOut }) {
  const { t } = useI18n();
  const [text, setText] = React.useState<string | null>(null);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    if (doc.document_type === "pdf" || !TEXT_PREVIEW_TYPES.has(doc.document_type)) return;
    let cancelled = false;
    setText(null);
    setError(false);
    fetch(fileUrl(doc.view_url ?? ""), { credentials: "include" })
      .then((res) => (res.ok ? res.text() : Promise.reject(new Error("load failed"))))
      .then((content) => {
        if (!cancelled) setText(content);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [doc.document_type, doc.id, doc.view_url]);

  if (doc.document_type === "pdf") {
    return (
      <div className="overflow-hidden rounded-lg border">
        <iframe src={fileUrl(doc.view_url ?? "")} className="h-[45vh] w-full bg-muted/40" title={doc.filename} />
      </div>
    );
  }
  if (!TEXT_PREVIEW_TYPES.has(doc.document_type)) {
    return <p className="text-sm text-muted-foreground">{t("docs.viewNoPreview")}</p>;
  }
  if (error) return <p className="text-sm text-destructive">{t("docs.viewError")}</p>;
  if (text === null) return <p className="text-sm text-muted-foreground">{t("docs.viewLoadingPreview")}</p>;
  const truncated = text.length > PREVIEW_CHAR_LIMIT ? text.slice(0, PREVIEW_CHAR_LIMIT) + "\n\n…" : text;
  return (
    <pre className="max-h-[45vh] overflow-auto whitespace-pre-wrap rounded-lg border bg-muted/40 p-3 text-xs">
      {truncated}
    </pre>
  );
}

export default function AdminDocumentsPage() {
  const { t } = useI18n();
  const [documents, setDocuments] = React.useState<DocumentOut[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [query, setQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("");
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<DocumentOut | null>(null);
  const [viewDoc, setViewDoc] = React.useState<DocumentOut | null>(null);
  const [confirmDelete, setConfirmDelete] = React.useState<DocumentOut | null>(null);
  const [form, setForm] = React.useState<DocumentForm>(EMPTY_FORM);
  const [file, setFile] = React.useState<File | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [extracting, setExtracting] = React.useState(false);
  const [extractResult, setExtractResult] = React.useState<MetadataExtractionResult | null>(null);
  const [extractError, setExtractError] = React.useState("");
  const [useLLM, setUseLLM] = React.useState(false);
  const [categoryOptions, setCategoryOptions] = React.useState<string[]>([]);
  const { toast } = useToast();
  const pollRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current);
    };
  }, []);

  const pollDocument = React.useCallback((id: string) => {
    let attempts = 0;
    const maxAttempts = 60;
    const tick = async () => {
      try {
        const doc = await api.get<DocumentOut>(`/api/admin/documents/${id}`);
        setDocuments((prev) =>
          prev.some((d) => d.id === id) ? prev.map((d) => (d.id === id ? doc : d)) : prev,
        );
        if (TERMINAL_STATUSES.has(doc.status)) return;
      } catch {
        /* keep polling until timeout */
      }
      attempts += 1;
      if (attempts < maxAttempts) {
        pollRef.current = window.setTimeout(tick, 2000);
      }
    };
    tick();
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (statusFilter) params.set("status", statusFilter);
      const data = await api.get<{ items: DocumentOut[]; total: number }>(
        `/api/admin/documents?${params.toString()}`,
      );
      setDocuments(data.items);
      setTotal(data.total);
    } catch (error) {
      toast(t("docs.toast.loadFailed"), { variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [query, statusFilter, toast, t]);

  React.useEffect(() => {
    const timer = setTimeout(load, 300);
    return () => clearTimeout(timer);
  }, [load]);

  React.useEffect(() => {
    api
      .get<Settings>("/api/admin/settings")
      .then((data) => setCategoryOptions(data.metadata.categories.map((c) => c.name)))
      .catch(() => undefined);
  }, []);

  const applyExtraction = (result: MetadataExtractionResult) => {
    setForm({
      title: result.title.value ? String(result.title.value) : "",
      category: result.category.value ? String(result.category.value) : "",
      year: result.year.value !== null && result.year.value !== undefined ? String(result.year.value) : "",
      version: result.version.value ? String(result.version.value) : "",
      department: result.department.value ? String(result.department.value) : "",
      program: result.program.value ? String(result.program.value) : "",
      language: (result.language.value as string) || "vi",
      description: result.description.value ? String(result.description.value) : "",
    });
    setExtractResult(result);
  };

  const runExtraction = async (target: File) => {
    setExtracting(true);
    setExtractError("");
    setExtractResult(null);
    try {
      const formData = new FormData();
      formData.append("file", target);
      const path = useLLM
        ? "/api/admin/documents/extract-metadata?use_llm=true"
        : "/api/admin/documents/extract-metadata";
      const result = await api.upload<MetadataExtractionResult>(path, formData);
      applyExtraction(result);
      toast(t("docs.toast.metadataExtracted"), {
        description: t("docs.toast.metadataExtractedDesc"),
        variant: "success",
      });
    } catch (error) {
      setExtractError(
        error instanceof ApiError ? error.message : t("docs.toast.couldNotAnalyze"),
      );
      toast(t("docs.toast.extractionFailed"), {
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    } finally {
      setExtracting(false);
    }
  };

  const handleFileSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setForm(EMPTY_FORM);
    setExtractResult(null);
    setExtractError("");
    if (selected) {
      void runExtraction(selected);
    }
  };

  const resetUpload = () => {
    setUploadOpen(false);
    setFile(null);
    setForm(EMPTY_FORM);
    setExtractResult(null);
    setExtractError("");
  };

  const handleUpload = async (event: React.FormEvent, autoIndex: boolean) => {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (form.title) formData.append("title", form.title);
      if (form.description) formData.append("description", form.description);
      if (form.category) formData.append("category", form.category);
      if (form.year) formData.append("year", form.year);
      if (form.version) formData.append("version", form.version);
      if (form.department) formData.append("department", form.department);
      if (form.program) formData.append("program", form.program);
      formData.append("language", form.language || "vi");
      formData.append("auto_index", String(autoIndex));

      const data = await api.upload<UploadResult>("/api/admin/documents", formData);
      toast(t("docs.toast.uploaded"), { description: data.message, variant: "success" });
      resetUpload();
      load();
      if (autoIndex) pollDocument(data.document.id);
    } catch (error) {
      toast(t("docs.toast.uploadFailed"), {
        description: error instanceof ApiError ? error.message : t("docs.pleaseTryAgain"),
        variant: "error",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!editing) return;
    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        description: form.description || null,
        category: form.category || null,
        version: form.version || null,
        department: form.department || null,
        program: form.program || null,
        language: form.language || "vi",
      };
      if (form.year) payload.year = parseInt(form.year, 10);
      await api.put(`/api/admin/documents/${editing.id}`, payload);
      toast(t("docs.toast.updated"), { variant: "success" });
      setEditing(null);
      setExtractResult(null);
      load();
    } catch (error) {
      toast(t("docs.toast.updateFailed"), { variant: "error" });
    }
  };

  const openEdit = (doc: DocumentOut) => {
    setEditing(doc);
    setExtractResult(null);
    setExtractError("");
    setForm({
      title: doc.title,
      description: doc.description ?? "",
      category: doc.category ?? "",
      year: doc.year ? String(doc.year) : "",
      version: doc.version ?? "",
      department: doc.department ?? "",
      program: doc.program ?? "",
      language: doc.language ?? "vi",
    });
  };

  const handleReExtract = async () => {
    if (!editing) return;
    setExtracting(true);
    setExtractError("");
    try {
      const path = useLLM
        ? `/api/admin/documents/${editing.id}/re-extract-metadata?use_llm=true`
        : `/api/admin/documents/${editing.id}/re-extract-metadata`;
      const result = await api.post<MetadataExtractionResult>(path);
      applyExtraction(result);
      toast(t("docs.toast.reExtracted"), {
        description: t("docs.toast.reExtractedDesc"),
        variant: "success",
      });
    } catch (error) {
      setExtractError(error instanceof ApiError ? error.message : t("docs.toast.couldNotReExtract"));
      toast(t("docs.toast.reExtractionFailed"), {
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    } finally {
      setExtracting(false);
    }
  };

  const handleReindex = async (doc: DocumentOut) => {
    try {
      const data = await api.post<DocumentOut>(`/api/admin/documents/${doc.id}/reindex`);
      toast(t("docs.toast.reindexStarted"), {
        description: t("docs.toast.reindexStartedDesc", { filename: doc.filename }),
        variant: "success",
      });
      load();
      pollDocument(data.id);
    } catch (error) {
      toast(t("docs.toast.reindexFailed"), { variant: "error" });
    }
  };

  const toggleActive = async (doc: DocumentOut) => {
    try {
      await api.put(`/api/admin/documents/${doc.id}`, { is_active: !doc.is_active });
      toast(doc.is_active ? t("docs.toast.deactivated") : t("docs.toast.activated"), { variant: "success" });
      load();
    } catch (error) {
      toast(t("docs.toast.actionFailed"), { variant: "error" });
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    try {
      await api.delete(`/api/admin/documents/${confirmDelete.id}`);
      toast(t("docs.toast.deleted"), { variant: "success" });
      setConfirmDelete(null);
      load();
    } catch (error) {
      toast(t("docs.toast.deleteFailed"), { variant: "error" });
    }
  };

  const handleReplace = async (doc: DocumentOut, newFile: File) => {
    try {
      const formData = new FormData();
      formData.append("file", newFile);
      const data = await api.upload<DocumentOut>(`/api/admin/documents/${doc.id}/replace`, formData);
      toast(t("docs.toast.replaced"), { description: t("docs.toast.replacedDesc"), variant: "success" });
      load();
      pollDocument(data.id);
    } catch (error) {
      toast(t("docs.toast.replaceFailed"), { variant: "error" });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("docs.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("docs.subtitle", { total })}</p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>
          <Plus className="h-4 w-4" />
          {t("docs.upload")}
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder={t("docs.search")}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="max-w-xs"
            />
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="w-44">
              <option value="">{t("docs.allStatuses")}</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : documents.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {t("docs.empty")}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("docs.colDocument")}</TableHead>
                    <TableHead>{t("docs.colType")}</TableHead>
                    <TableHead>{t("docs.colSize")}</TableHead>
                    <TableHead>{t("docs.colChunks")}</TableHead>
                    <TableHead>{t("docs.colStatus")}</TableHead>
                    <TableHead>{t("docs.colActive")}</TableHead>
                    <TableHead>{t("docs.colUpdated")}</TableHead>
                    <TableHead className="text-right">{t("docs.colActions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                          <div className="min-w-0">
                            <p className="max-w-[260px] truncate font-medium">{doc.title}</p>
                            <p className="max-w-[260px] truncate text-xs text-muted-foreground">{doc.filename}</p>
                          </div>
                        </div>
                        {doc.error_message && <p className="mt-1 text-xs text-destructive">{doc.error_message}</p>}
                      </TableCell>
                      <TableCell className="uppercase">{doc.document_type}</TableCell>
                      <TableCell className="text-xs">{formatBytes(doc.file_size)}</TableCell>
                      <TableCell>{doc.chunk_count}</TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANT[doc.status] ?? "secondary"}>{doc.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => toggleActive(doc)}
                          className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium hover:bg-accent"
                        >
                          {doc.is_active ? t("docs.active") : t("docs.inactive")}
                        </button>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">{formatDate(doc.updated_at)}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setViewDoc(doc)} aria-label={t("docs.view")}>
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => openEdit(doc)} aria-label={t("docs.edit")}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleReindex(doc)} aria-label={t("docs.reindex")}>
                            <RefreshCw className="h-3.5 w-3.5" />
                          </Button>
                          <a
                            href={fileUrl(doc.download_url ?? "")}
                            download
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
                            aria-label={t("docs.download")}
                          >
                            <Download className="h-3.5 w-3.5" />
                          </a>
                          <label className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-accent" aria-label={t("docs.replace")}>
                            <Upload className="h-3.5 w-3.5" />
                            <input
                              type="file"
                              className="hidden"
                              accept=".pdf,.doc,.docx,.txt,.md,.markdown,.text"
                              onChange={(event) => {
                                const selected = event.target.files?.[0];
                                if (selected) handleReplace(doc, selected);
                                event.target.value = "";
                              }}
                            />
                          </label>
                          <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setConfirmDelete(doc)} aria-label={t("docs.delete")}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload dialog */}
      <Dialog open={uploadOpen} onOpenChange={(open) => (open ? setUploadOpen(true) : resetUpload())}>
        <DialogHeader>
          <DialogTitle>{t("docs.uploadTitle")}</DialogTitle>
          <DialogDescription>
            {t("docs.uploadDesc")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => handleUpload(e, true)} className="space-y-4">
          <div className="space-y-2">
            <Label>{t("docs.file")}</Label>
            <input
              type="file"
              required
              accept=".pdf,.doc,.docx,.txt,.md,.markdown,.text"
              onChange={handleFileSelected}
              className="block w-full text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary hover:file:bg-primary/20"
            />
            {file && !extracting && (
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={useLLM} onChange={(event) => setUseLLM(event.target.checked)} />
                  {t("docs.useLLM")}
                </label>
                <Button type="button" size="sm" variant="outline" onClick={() => file && runExtraction(file)}>
                  <Wand2 className="h-3.5 w-3.5" />
                  {t("docs.reanalyze")}
                </Button>
              </div>
            )}
            {extracting && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t("docs.analyzing")}
              </p>
            )}
            {extractError && <p className="text-xs text-destructive">{extractError}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <FieldLabel field={extractResult?.title}>{t("docs.fieldTitle")}</FieldLabel>
              <Input id="title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={t("docs.phTitle")} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.category}>{t("docs.fieldCategory")}</FieldLabel>
              <Input
                id="category"
                list="category-options"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                placeholder={t("docs.phCategory")}
              />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.year}>{t("docs.fieldYear")}</FieldLabel>
              <Input id="year" type="number" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} placeholder={t("docs.phYear")} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.version}>{t("docs.fieldVersion")}</FieldLabel>
              <Input id="version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} placeholder={t("docs.phVersion")} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.department}>{t("docs.fieldDepartment")}</FieldLabel>
              <Input id="department" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.program}>{t("docs.fieldProgram")}</FieldLabel>
              <Input id="program" value={form.program} onChange={(e) => setForm({ ...form, program: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.language}>{t("docs.fieldLanguage")}</FieldLabel>
              <Select id="language" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                <option value="vi">{t("docs.langVi")}</option>
                <option value="en">{t("docs.langEn")}</option>
                <option value="bilingual">{t("docs.langBilingual")}</option>
              </Select>
            </div>
          </div>
          <datalist id="category-options">
            {categoryOptions.map((name) => (
              <option key={name} value={name} />
            ))}
          </datalist>
          <div className="space-y-2">
            <FieldLabel field={extractResult?.description}>{t("docs.fieldDescription")}</FieldLabel>
            <Textarea id="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder={t("docs.phDescription")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={resetUpload}>
              {t("common.cancel")}
            </Button>
            <Button type="button" variant="outline" disabled={uploading || !file} onClick={(e) => handleUpload(e, false)}>
              {t("docs.saveDraft")}
            </Button>
            <Button type="submit" disabled={uploading || extracting || !file}>
              {uploading ? t("docs.uploading") : t("docs.saveIndex")}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogHeader>
          <DialogTitle>{t("docs.editTitle")}</DialogTitle>
          <DialogDescription>{editing?.filename}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          {editing && !extracting && (
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={useLLM} onChange={(event) => setUseLLM(event.target.checked)} />
                {t("docs.useLLM")}
              </label>
              <Button type="button" size="sm" variant="outline" onClick={handleReExtract}>
                <Wand2 className="h-3.5 w-3.5" />
                {t("docs.reExtract")}
              </Button>
            </div>
          )}
          {extracting && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("docs.reanalyzing")}
            </p>
          )}
          {extractError && <p className="text-xs text-destructive">{extractError}</p>}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <FieldLabel field={extractResult?.title}>{t("docs.fieldTitle")}</FieldLabel>
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.category}>{t("docs.fieldCategory")}</FieldLabel>
              <Input list="category-options" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.year}>{t("docs.fieldYear")}</FieldLabel>
              <Input type="number" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.version}>{t("docs.fieldVersion")}</FieldLabel>
              <Input value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.department}>{t("docs.fieldDepartment")}</FieldLabel>
              <Input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.program}>{t("docs.fieldProgram")}</FieldLabel>
              <Input value={form.program} onChange={(e) => setForm({ ...form, program: e.target.value })} />
            </div>
            <div className="space-y-2">
              <FieldLabel field={extractResult?.language}>{t("docs.fieldLanguage")}</FieldLabel>
              <Select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                <option value="vi">{t("docs.langVi")}</option>
                <option value="en">{t("docs.langEn")}</option>
                <option value="bilingual">{t("docs.langBilingual")}</option>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <FieldLabel field={extractResult?.description}>{t("docs.fieldDescription")}</FieldLabel>
            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setEditing(null)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={extracting}>{t("docs.saveChanges")}</Button>
          </DialogFooter>
        </form>
      </Dialog>

      {/* View dialog */}
      <Dialog open={!!viewDoc} onOpenChange={(open) => !open && setViewDoc(null)}>
        {viewDoc && (
          <>
            <DialogHeader>
              <DialogTitle>{t("docs.viewTitle")}</DialogTitle>
              <DialogDescription>{viewDoc.filename}</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <div className="space-y-1">
                  <Label>{t("docs.fieldTitle")}</Label>
                  <p className="text-sm font-medium">{viewDoc.title}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.fieldCategory")}</Label>
                  <p className="text-sm font-medium">{viewDoc.category || "—"}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.fieldYear")}</Label>
                  <p className="text-sm font-medium">{viewDoc.year ?? "—"}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.fieldVersion")}</Label>
                  <p className="text-sm font-medium">{viewDoc.version || "—"}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.fieldDepartment")}</Label>
                  <p className="text-sm font-medium">{viewDoc.department || "—"}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.fieldProgram")}</Label>
                  <p className="text-sm font-medium">{viewDoc.program || "—"}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.fieldLanguage")}</Label>
                  <p className="text-sm font-medium">{viewDoc.language || "—"}</p>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.colStatus")}</Label>
                  <Badge variant={STATUS_VARIANT[viewDoc.status] ?? "secondary"}>{viewDoc.status}</Badge>
                </div>
                <div className="space-y-1">
                  <Label>{t("docs.colType")}</Label>
                  <p className="text-sm font-medium uppercase">{viewDoc.document_type}</p>
                </div>
              </div>
              {viewDoc.description && (
                <div className="space-y-1">
                  <Label>{t("docs.fieldDescription")}</Label>
                  <p className="text-sm text-muted-foreground">{viewDoc.description}</p>
                </div>
              )}
              <div className="space-y-1">
                <Label>{t("docs.viewPreview")}</Label>
                <DocumentPreview doc={viewDoc} />
              </div>
              <div className="flex gap-2">
                <a
                  href={fileUrl(viewDoc.view_url ?? "")}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  {t("docs.viewOpenNewTab")}
                </a>
                <a
                  href={fileUrl(viewDoc.download_url ?? "")}
                  download
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  {t("docs.viewOpenDownload")}
                </a>
              </div>
            </div>
          </>
        )}
      </Dialog>

      {/* Confirm delete */}
      <Dialog open={!!confirmDelete} onOpenChange={(open) => !open && setConfirmDelete(null)}>
        <DialogHeader>
          <DialogTitle>{t("docs.deleteTitle")}</DialogTitle>
          <DialogDescription>
            {t("docs.deleteDesc", { filename: confirmDelete?.filename ?? "" })}
          </DialogDescription>
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
