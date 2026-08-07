"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { AdminUser } from "@/types";

interface AdminAuthState {
  admin: AdminUser | null;
  loading: boolean;
  isAuthed: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export function useAdminAuth(redirectOnUnauthed = true, recheckSignal?: unknown): AdminAuthState {
  const router = useRouter();
  const [admin, setAdmin] = React.useState<AdminUser | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    async function check() {
      try {
        const me = await api.get<AdminUser>("/api/admin/auth/me");
        if (!cancelled) setAdmin(me);
      } catch (error) {
        if (!cancelled && redirectOnUnauthed) {
          router.replace("/admin/login");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    check();
    return () => {
      cancelled = true;
    };
  }, [router, redirectOnUnauthed, recheckSignal]);

  const login = React.useCallback(
    async (username: string, password: string) => {
      const response = await api.post<{ admin: AdminUser }>("/api/admin/auth/login", {
        username,
        password,
      });
      setAdmin(response.admin);
      router.replace("/admin");
    },
    [router],
  );

  const logout = React.useCallback(async () => {
    try {
      await api.post("/api/admin/auth/logout");
    } catch (error) {
      // ignore
    }
    setAdmin(null);
    router.replace("/admin/login");
  }, [router]);

  return { admin, loading, isAuthed: !!admin, login, logout };
}
