"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  FileText,
  GraduationCap,
  LayoutDashboard,
  MessageSquare,
  Settings,
  SlidersHorizontal,
  Sparkles,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { LanguageToggle } from "@/components/language-toggle";
import { useI18n } from "@/lib/i18n";

export function AdminSidebar({ onLogout }: { onLogout: () => void }) {
  const pathname = usePathname();
  const { t } = useI18n();

  const NAV_ITEMS = [
    { href: "/admin", label: t("admin.dashboard"), icon: LayoutDashboard, exact: true },
    { href: "/admin/documents", label: t("admin.documents"), icon: FileText },
    { href: "/admin/llm", label: t("admin.llmProviders"), icon: Sparkles },
    { href: "/admin/rag", label: t("admin.ragSettings"), icon: SlidersHorizontal },
    { href: "/admin/conversations", label: t("admin.conversations"), icon: MessageSquare },
    { href: "/admin/logs", label: t("admin.systemLogs"), icon: Activity },
    { href: "/admin/settings", label: t("admin.settings"), icon: Settings },
  ];

  return (
    <aside className="sticky top-0 flex h-dvh w-60 shrink-0 flex-col border-r bg-card">
      <div className="flex items-center gap-2 border-b p-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <GraduationCap className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">{t("admin.brandTitle")}</p>
          <p className="text-[11px] text-muted-foreground">{t("admin.brandSubtitle")}</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {NAV_ITEMS.map((item) => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent",
                active ? "bg-accent text-foreground" : "text-muted-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-3">
        <Link
          href="/"
          className="mb-1 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent"
        >
          <BarChart3 className="h-4 w-4" />
          {t("admin.openChat")}
        </Link>
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground" onClick={onLogout}>
          <LogOut className="h-4 w-4" />
          {t("admin.logout")}
        </Button>
        <div className="mt-2 flex justify-center border-t pt-3">
          <LanguageToggle />
        </div>
      </div>
    </aside>
  );
}
