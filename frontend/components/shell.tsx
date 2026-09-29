"use client";

import { Activity, CloudSun, Gauge, LogOut, Settings, Workflow } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/store";

const LINKS = [
  { href: "/", label: "Dashboard", icon: CloudSun },
  { href: "/models", label: "Models & weights", icon: Gauge },
  { href: "/extremes", label: "Extremes", icon: Activity },
  { href: "/jobs", label: "Operations", icon: Workflow },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const email = useAuth((state) => state.email);
  const token = useAuth((state) => state.accessToken);
  const logout = useAuth((state) => state.logout);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const finish = () => setReady(true);
    const unsub = useAuth.persist.onFinishHydration(finish);
    if (useAuth.persist.hasHydrated()) finish();
    return () => unsub();
  }, []);

  useEffect(() => {
    if (ready && !token) router.replace("/login");
  }, [ready, token, router]);

  if (!ready || !token) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-muted">
        Loading workspace…
      </div>
    );
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="flex flex-col bg-brand text-white lg:min-h-screen">
        <div className="px-5 pb-4 pt-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-cyan-200">Hybrid blend</p>
          <p className="mt-1 text-lg font-semibold leading-tight">AI–NWP Forecast Consensus</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-cyan-50/80 hover:bg-white/10",
                  active && "bg-white/15 text-white",
                )}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden items-center justify-between gap-2 px-4 py-4 lg:flex">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{email}</p>
            <p className="text-xs text-cyan-100/70">Analyst</p>
          </div>
          <button
            className="rounded-md p-2 hover:bg-white/10"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>
      <div className="min-w-0">
        <div className="flex items-center justify-between border-b border-line px-4 py-2 lg:hidden">
          <p className="truncate text-sm text-muted">{email}</p>
          <button
            className="text-sm font-medium text-cyan-800 dark:text-cyan-300"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
        </div>
        <main className="mx-auto max-w-[1400px] space-y-4 px-4 py-4 lg:px-6 lg:py-6">{children}</main>
      </div>
    </div>
  );
}
