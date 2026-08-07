import type { Metadata } from "next";
import "@/app/globals.css";
import { ToastProvider } from "@/components/ui/toast";
import { I18nProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "Postgraduate Information Assistant",
  description: "RAG-powered postgraduate information assistant for university applicants.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen font-sans">
        <ToastProvider>
          <I18nProvider>{children}</I18nProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
