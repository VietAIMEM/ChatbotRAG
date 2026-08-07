"use client";

import * as React from "react";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import type { LLMProvider } from "@/types";

interface ProviderForm {
  name: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  model: string;
  temperature: string;
  max_tokens: string;
  timeout: string;
  enabled: boolean;
  priority: string;
}

const EMPTY_FORM: ProviderForm = {
  name: "",
  provider_type: "openrouter",
  base_url: "",
  api_key: "",
  model: "",
  temperature: "0.2",
  max_tokens: "1024",
  timeout: "120",
  enabled: true,
  priority: "100",
};

export default function AdminLlmPage() {
  const { t } = useI18n();
  const PROVIDER_TYPES = [
    { value: "openrouter", label: t("llm.typeOpenRouter") },
    { value: "openai_compatible", label: t("llm.typeOpenAI") },
    { value: "opencode", label: t("llm.typeOpenCode") },
    { value: "custom", label: t("llm.typeCustom") },
  ];

  const TYPE_DEFAULTS: Record<string, Partial<ProviderForm>> = {
    openrouter: { base_url: "https://openrouter.ai/api/v1", model: "anthropic/claude-3.5-sonnet" },
    openai_compatible: { base_url: "https://api.openai.com/v1", model: "gpt-4o-mini" },
    opencode: { base_url: "http://localhost:8090/v1", model: "" },
    custom: { base_url: "", model: "" },
  };

  const [providers, setProviders] = React.useState<LLMProvider[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<LLMProvider | null>(null);
  const [form, setForm] = React.useState<ProviderForm>(EMPTY_FORM);
  const [testing, setTesting] = React.useState<string | null>(null);
  const [testResults, setTestResults] = React.useState<Record<string, { success: boolean; message: string }>>({});
  const { toast } = useToast();

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<LLMProvider[]>("/api/admin/llm-providers");
      setProviders(data);
    } catch {
      toast(t("llm.toast.loadFailed"), { variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [toast, t]);

  React.useEffect(() => {
    load();
  }, [load]);

  const applyTypeDefaults = (type: string) => {
    setForm((prev) => ({ ...prev, ...TYPE_DEFAULTS[type] }));
  };

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, ...TYPE_DEFAULTS.openrouter });
    setDialogOpen(true);
  };

  const openEdit = (provider: LLMProvider) => {
    setEditing(provider);
    setForm({
      name: provider.name,
      provider_type: provider.provider_type,
      base_url: provider.base_url,
      api_key: "",
      model: provider.model,
      temperature: String(provider.temperature),
      max_tokens: String(provider.max_tokens),
      timeout: String(provider.timeout),
      enabled: provider.enabled,
      priority: String(provider.priority),
    });
    setDialogOpen(true);
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    const payload: Record<string, unknown> = {
      name: form.name,
      provider_type: form.provider_type,
      base_url: form.base_url,
      api_key: form.api_key || undefined,
      model: form.model,
      temperature: parseFloat(form.temperature),
      max_tokens: parseInt(form.max_tokens, 10),
      timeout: parseInt(form.timeout, 10),
      enabled: form.enabled,
      priority: parseInt(form.priority, 10),
    };
    try {
      if (editing) {
        await api.put(`/api/admin/llm-providers/${editing.id}`, payload);
        toast(t("llm.toast.updated"), { variant: "success" });
      } else {
        await api.post("/api/admin/llm-providers", payload);
        toast(t("llm.toast.added"), { variant: "success" });
      }
      setDialogOpen(false);
      load();
    } catch (error) {
      toast(t("llm.toast.saveFailed"), {
        description: error instanceof ApiError ? error.message : t("llm.toast.checkFields"),
        variant: "error",
      });
    }
  };

  const handleDelete = async (provider: LLMProvider) => {
    try {
      await api.delete(`/api/admin/llm-providers/${provider.id}`);
      toast(t("llm.toast.deleted"), { variant: "success" });
      load();
    } catch {
      toast(t("llm.toast.deleteFailed"), { variant: "error" });
    }
  };

  const toggleEnabled = async (provider: LLMProvider) => {
    try {
      await api.put(`/api/admin/llm-providers/${provider.id}`, { enabled: !provider.enabled });
      load();
    } catch {
      toast(t("llm.toast.updateFailed"), { variant: "error" });
    }
  };

  const testConnection = async (provider: LLMProvider) => {
    setTesting(provider.id);
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/api/admin/llm-providers/${provider.id}/test`,
      );
      setTestResults((prev) => ({ ...prev, [provider.id]: result }));
      toast(result.success ? t("llm.toast.connectionSuccess") : t("llm.toast.connectionFailed"), {
        description: result.message,
        variant: result.success ? "success" : "error",
      });
    } catch {
      setTestResults((prev) => ({ ...prev, [provider.id]: { success: false, message: t("llm.toast.couldNotReach") } }));
    } finally {
      setTesting(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("llm.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("llm.subtitle")}</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          {t("llm.add")}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("llm.providers")}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : providers.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {t("llm.empty")}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("llm.colName")}</TableHead>
                    <TableHead>{t("llm.colType")}</TableHead>
                    <TableHead>{t("llm.colModel")}</TableHead>
                    <TableHead>{t("llm.colApiKey")}</TableHead>
                    <TableHead>{t("llm.colPriority")}</TableHead>
                    <TableHead>{t("llm.colEnabled")}</TableHead>
                    <TableHead className="text-right">{t("llm.colActions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {providers.map((provider) => (
                    <TableRow key={provider.id}>
                      <TableCell>
                        <p className="font-medium">{provider.name}</p>
                        <p className="text-xs text-muted-foreground">{provider.base_url}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{provider.provider_type}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">{provider.model || "—"}</TableCell>
                      <TableCell className="text-xs">{provider.api_key_masked || t("llm.notSet")}</TableCell>
                      <TableCell>{provider.priority}</TableCell>
                      <TableCell>
                        <Switch checked={provider.enabled} onCheckedChange={() => toggleEnabled(provider)} />
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" onClick={() => testConnection(provider)} disabled={testing === provider.id}>
                            <RefreshCw className={`h-3.5 w-3.5 ${testing === provider.id ? "animate-spin" : ""}`} />
                            {t("llm.test")}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => openEdit(provider)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" className="text-destructive" onClick={() => handleDelete(provider)}>
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogHeader>
          <DialogTitle>{editing ? t("llm.editTitle") : t("llm.addTitle")}</DialogTitle>
          <DialogDescription>{t("llm.dialogDesc")}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>{t("llm.name")}</Label>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.providerType")}</Label>
              <Select
                value={form.provider_type}
                onChange={(e) => {
                  setForm({ ...form, provider_type: e.target.value });
                  if (!editing) applyTypeDefaults(e.target.value);
                }}
              >
                {PROVIDER_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2 col-span-2">
              <Label>{t("llm.baseUrl")}</Label>
              <Input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder={t("llm.phBaseUrl")} />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.apiKey")}</Label>
              <Input
                type="password"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                placeholder={editing ? t("llm.phApiKeyEdit") : t("llm.phApiKey")}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.model")}</Label>
              <Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder={t("llm.phModel")} />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.temperature")}</Label>
              <Input type="number" step="0.1" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.maxTokens")}</Label>
              <Input type="number" value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.timeout")}</Label>
              <Input type="number" value={form.timeout} onChange={(e) => setForm({ ...form, timeout: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("llm.priority")}</Label>
              <Input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={form.enabled} onCheckedChange={(checked) => setForm({ ...form, enabled: checked })} />
            <Label>{t("llm.enabled")}</Label>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit">{editing ? t("docs.saveChanges") : t("llm.add")}</Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  );
}
