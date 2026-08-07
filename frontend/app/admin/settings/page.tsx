"use client";

import * as React from "react";
import { FileSearch, KeyRound, Save, Settings2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useI18n } from "@/lib/i18n";
import type { Settings } from "@/types";

function serializeMetadata(meta: Settings["metadata"]) {
  return {
    categoriesText: meta.categories
      .map((c) => (c.keywords.length ? `${c.name}: ${c.keywords.join(", ")}` : c.name))
      .join("\n"),
    departmentsText: meta.departments.join("\n"),
    programsText: meta.programs.join("\n"),
  };
}

export default function AdminSettingsPage() {
  const { t } = useI18n();
  const [settings, setSettings] = React.useState<Settings | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [savingGeneral, setSavingGeneral] = React.useState(false);
  const [savingSecurity, setSavingSecurity] = React.useState(false);
  const [savingMetadata, setSavingMetadata] = React.useState(false);
  const [metadataDraft, setMetadataDraft] = React.useState({ categoriesText: "", departmentsText: "", programsText: "" });
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [changingPassword, setChangingPassword] = React.useState(false);
  const { toast } = useToast();

  React.useEffect(() => {
    async function load() {
      try {
        const data = await api.get<Settings>("/api/admin/settings");
        setSettings(data);
        setMetadataDraft(serializeMetadata(data.metadata));
      } catch {
        toast(t("settings.loadFailed"), { variant: "error" });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [toast, t]);

  const setGeneral = <K extends keyof Settings["general"]>(key: K, value: Settings["general"][K]) => {
    setSettings((prev) => (prev ? { ...prev, general: { ...prev.general, [key]: value } } : prev));
  };

  const setSecurity = <K extends keyof Settings["security"]>(key: K, value: Settings["security"][K]) => {
    setSettings((prev) => (prev ? { ...prev, security: { ...prev.security, [key]: value } } : prev));
  };

  const handleSaveGeneral = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!settings) return;
    setSavingGeneral(true);
    try {
      const data = await api.put<Settings>("/api/admin/settings", { general: settings.general });
      setSettings(data);
      toast(t("settings.toast.generalSaved"), { variant: "success" });
    } catch (error) {
      toast(t("settings.toast.saveFailed"), {
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    } finally {
      setSavingGeneral(false);
    }
  };

  const handleSaveSecurity = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!settings) return;
    setSavingSecurity(true);
    try {
      const data = await api.put<Settings>("/api/admin/settings", { security: settings.security });
      setSettings(data);
      toast(t("settings.toast.securitySaved"), { variant: "success" });
    } catch (error) {
      toast(t("settings.toast.saveFailed"), {
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    } finally {
      setSavingSecurity(false);
    }
  };

  const handleSaveMetadata = async (event: React.FormEvent) => {
    event.preventDefault();
    setSavingMetadata(true);
    try {
      const categories = metadataDraft.categoriesText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const idx = line.indexOf(":");
          if (idx > 0) {
            return {
              name: line.slice(0, idx).trim(),
              keywords: line
                .slice(idx + 1)
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            };
          }
          return { name: line, keywords: [] };
        });
      const departments = metadataDraft.departmentsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const programs = metadataDraft.programsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const data = await api.put<Settings>("/api/admin/settings", {
        metadata: { categories, departments, programs },
      });
      setSettings(data);
      setMetadataDraft(serializeMetadata(data.metadata));
      toast(t("settings.toast.metadataSaved"), { variant: "success" });
    } catch (error) {
      toast(t("settings.toast.saveFailed"), {
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    } finally {
      setSavingMetadata(false);
    }
  };

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setChangingPassword(true);
    try {
      await api.post("/api/admin/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast(t("settings.toast.passwordChanged"), { variant: "success" });
      setCurrentPassword("");
      setNewPassword("");
    } catch (error) {
      toast(t("settings.toast.passwordChangeFailed"), {
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    } finally {
      setChangingPassword(false);
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

  if (!settings) {
    return <p className="text-sm text-muted-foreground">{t("settings.couldNotLoad")}</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("settings.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("settings.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Settings2 className="h-4 w-4" />
            {t("settings.general")}
          </CardTitle>
          <CardDescription>{t("settings.generalDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveGeneral} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>{t("settings.siteName")}</Label>
                <Input value={settings.general.site_name} onChange={(e) => setGeneral("site_name", e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>{t("settings.chatbotName")}</Label>
                <Input value={settings.general.chatbot_name} onChange={(e) => setGeneral("chatbot_name", e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t("settings.welcomeMessage")}</Label>
              <Textarea
                rows={3}
                value={settings.general.welcome_message}
                onChange={(e) => setGeneral("welcome_message", e.target.value)}
              />
            </div>
            <Button type="submit" disabled={savingGeneral}>
              <Save className="h-4 w-4" />
              {savingGeneral ? t("common.saving") : t("settings.saveGeneral")}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4" />
            {t("settings.security")}
          </CardTitle>
          <CardDescription>{t("settings.securityDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={handleSaveSecurity} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>{t("settings.chatRateLimit")}</Label>
                <Input
                  type="number"
                  min="1"
                  value={settings.security.chat_rate_limit_per_minute}
                  onChange={(e) => setSecurity("chat_rate_limit_per_minute", parseInt(e.target.value, 10) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("settings.maxUploadSize")}</Label>
                <Input
                  type="number"
                  min="1"
                  value={settings.security.max_upload_size_mb}
                  onChange={(e) => setSecurity("max_upload_size_mb", parseInt(e.target.value, 10) || 0)}
                />
              </div>
            </div>
            <Button type="submit" disabled={savingSecurity}>
              <Save className="h-4 w-4" />
              {savingSecurity ? t("common.saving") : t("settings.saveSecurity")}
            </Button>
          </form>

          <div className="border-t pt-6">
            <h3 className="mb-1 text-sm font-medium">{t("settings.changePassword")}</h3>
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t("settings.currentPassword")}</Label>
                  <Input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("settings.newPassword")}</Label>
                  <Input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={8}
                  />
                </div>
              </div>
              <Button type="submit" variant="outline" disabled={changingPassword}>
                {changingPassword ? t("common.saving") : t("settings.changePasswordBtn")}
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileSearch className="h-4 w-4" />
            {t("settings.metadataExtraction")}
          </CardTitle>
          <CardDescription>{t("settings.metadataDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveMetadata} className="space-y-4">
            <div className="space-y-2">
              <Label>{t("settings.categories")}</Label>
              <p className="text-xs text-muted-foreground">
                {t("settings.categoriesHint")}
              </p>
              <Textarea
                rows={8}
                value={metadataDraft.categoriesText}
                onChange={(e) => setMetadataDraft({ ...metadataDraft, categoriesText: e.target.value })}
                spellCheck={false}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>{t("settings.departments")}</Label>
                <p className="text-xs text-muted-foreground">{t("settings.onePerLine")}</p>
                <Textarea
                  rows={5}
                  value={metadataDraft.departmentsText}
                  onChange={(e) => setMetadataDraft({ ...metadataDraft, departmentsText: e.target.value })}
                  spellCheck={false}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("settings.programs")}</Label>
                <p className="text-xs text-muted-foreground">{t("settings.onePerLine")}</p>
                <Textarea
                  rows={5}
                  value={metadataDraft.programsText}
                  onChange={(e) => setMetadataDraft({ ...metadataDraft, programsText: e.target.value })}
                  spellCheck={false}
                />
              </div>
            </div>
            <Button type="submit" disabled={savingMetadata}>
              <Save className="h-4 w-4" />
              {savingMetadata ? t("common.saving") : t("settings.saveMetadata")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
