"use client";

import { Languages } from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n, type Language } from "@/lib/i18n";

export function LanguageToggle({ className }: { className?: string }) {
  const { language, setLanguage } = useI18n();
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <Languages className="h-4 w-4 shrink-0 text-muted-foreground" />
      <select
        aria-label="Language"
        value={language}
        onChange={(event) => setLanguage(event.target.value as Language)}
        className="h-8 rounded-md border border-input bg-background px-2 text-xs font-medium shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        <option value="en">English</option>
        <option value="vi">Tiếng Việt</option>
      </select>
    </div>
  );
}
