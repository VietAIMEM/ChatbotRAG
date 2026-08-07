"use client";

import * as React from "react";
import { Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import type { RAGConfig } from "@/types";

interface ModelOption {
  value: string;
  label: string;
}

export default function AdminRagPage() {
  const { t } = useI18n();
  const [config, setConfig] = React.useState<RAGConfig | null>(null);
  const [embeddingModels, setEmbeddingModels] = React.useState<ModelOption[]>([]);
  const [rerankerModels, setRerankerModels] = React.useState<ModelOption[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const { toast } = useToast();

  React.useEffect(() => {
    async function load() {
      try {
        const [rag, emb, rerank] = await Promise.all([
          api.get<RAGConfig>("/api/admin/rag/config"),
          api.get<ModelOption[]>("/api/admin/rag/embedding-models"),
          api.get<ModelOption[]>("/api/admin/rag/reranker-models"),
        ]);
        setConfig(rag);
        setEmbeddingModels(emb);
        setRerankerModels(rerank);
      } catch {
        toast(t("rag.toast.loadFailed"), { variant: "error" });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [toast, t]);

  const set = <K extends keyof RAGConfig>(key: K, value: RAGConfig[K]) => {
    setConfig((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!config) return;
    setSaving(true);
    try {
      await api.put("/api/admin/rag/config", config);
      toast(t("rag.toast.saved"), {
        description: t("rag.toast.savedDesc"),
        variant: "success",
      });
    } catch (error) {
      toast(t("rag.toast.saveFailed"), {
        description: error instanceof ApiError ? error.message : t("rag.toast.checkFields"),
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (!config) {
    return <p className="text-sm text-muted-foreground">{t("rag.couldNotLoad")}</p>;
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("rag.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("rag.subtitle")}</p>
        </div>
        <Button type="submit" disabled={saving}>
          <Save className="h-4 w-4" />
          {saving ? t("common.saving") : t("rag.saveSettings")}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("rag.embedding")}</CardTitle>
          <CardDescription>{t("rag.embeddingDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>{t("rag.embeddingProvider")}</Label>
            <Select
              value={config.embedding_provider}
              onChange={(e) => set("embedding_provider", e.target.value)}
            >
              <option value="local">{t("rag.localEmbedding")}</option>
              <option value="openai_compatible">{t("rag.openAIEmbedding")}</option>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t("rag.embeddingModel")}</Label>
            <Select value={config.embedding_model} onChange={(e) => set("embedding_model", e.target.value)}>
              {embeddingModels.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </Select>
          </div>
          {config.embedding_provider !== "local" && (
            <>
              <div className="space-y-2">
                <Label>{t("rag.embeddingApiUrl")}</Label>
                <Input
                  value={config.embedding_base_url}
                  onChange={(e) => set("embedding_base_url", e.target.value)}
                  placeholder="https://api.openai.com/v1"
                />
              </div>
              <div className="space-y-2">
                <Label>{t("rag.embeddingApiKey")}</Label>
                <Input
                  type="password"
                  value={config.embedding_api_key}
                  onChange={(e) => set("embedding_api_key", e.target.value)}
                  placeholder="sk-..."
                />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("rag.reranking")}</CardTitle>
          <CardDescription>{t("rag.rerankingDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>{t("rag.rerankerProvider")}</Label>
            <Select value={config.reranker_provider} onChange={(e) => set("reranker_provider", e.target.value)}>
              <option value="local">{t("rag.localReranker")}</option>
              <option value="cross_encoder">{t("rag.crossEncoder")}</option>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t("rag.rerankerModel")}</Label>
            <Select value={config.reranker_model} onChange={(e) => set("reranker_model", e.target.value)}>
              {rerankerModels.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={config.enable_reranker} onCheckedChange={(checked) => set("enable_reranker", checked)} />
            <Label>{t("rag.enableReranker")}</Label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("rag.chunking")}</CardTitle>
          <CardDescription>{t("rag.chunkingDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>{t("rag.chunkSize")}</Label>
            <Input type="number" value={config.chunk_size} onChange={(e) => set("chunk_size", parseInt(e.target.value, 10) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>{t("rag.chunkOverlap")}</Label>
            <Input type="number" value={config.chunk_overlap} onChange={(e) => set("chunk_overlap", parseInt(e.target.value, 10) || 0)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("rag.retrieval")}</CardTitle>
          <CardDescription>{t("rag.retrievalDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label>{t("rag.initialTopK")}</Label>
            <Input type="number" value={config.top_k} onChange={(e) => set("top_k", parseInt(e.target.value, 10) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>{t("rag.finalTopK")}</Label>
            <Input type="number" value={config.final_k} onChange={(e) => set("final_k", parseInt(e.target.value, 10) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>{t("rag.similarityThreshold")}</Label>
            <Input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={config.similarity_threshold}
              onChange={(e) => set("similarity_threshold", parseFloat(e.target.value) || 0)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={config.enable_query_rewrite} onCheckedChange={(checked) => set("enable_query_rewrite", checked)} />
            <Label>{t("rag.enableQueryRewrite")}</Label>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}
