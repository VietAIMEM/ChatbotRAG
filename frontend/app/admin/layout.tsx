"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { useAdminAuth } from "@/hooks/use-admin-auth";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { Skeleton } from "@/components/ui/skeleton";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { admin, loading, logout } = useAdminAuth(true, pathname === "/admin/login");
  const isLoginRoute = pathname === "/admin/login";

  if (isLoginRoute) {
    return <>{children}</>;
  }

  if (loading || !admin) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Skeleton className="h-24 w-64" />
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh bg-background">
      <AdminSidebar onLogout={() => logout()} />
      <main className="flex-1 overflow-x-auto p-6 lg:p-8">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
