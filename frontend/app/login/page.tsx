"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { login, register } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("analyst@example.com");
  const [password, setPassword] = useState("Forecast#2026");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, fullName);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-brand px-10 py-12 text-white lg:flex">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-cyan-200">Operational meteorology</p>
          <h1 className="mt-4 max-w-md text-4xl font-semibold leading-tight">Hybrid AI–NWP forecast blending</h1>
          <p className="mt-4 max-w-md text-cyan-50/80">
            Weights shift with region, season, and lead time so the consensus uses whichever source is actually skillful — GFS, ECMWF, AI models, or the ensemble mean.
          </p>
        </div>
        <p className="text-sm text-cyan-100/70">Synthetic archive included. Plug in ERA5, GFS, and ECMWF when you are ready.</p>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <form onSubmit={onSubmit} className="w-full max-w-md space-y-4">
          <div>
            <h2 className="text-2xl font-semibold">{mode === "login" ? "Sign in" : "Create an account"}</h2>
            <p className="mt-1 text-sm text-muted">Duty desk access for the blending workspace.</p>
          </div>
          {mode === "register" ? (
            <label className="block text-sm font-medium">
              Name
              <input
                className="mt-1 w-full rounded-md border border-line bg-panel px-3 py-2"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </label>
          ) : null}
          <label className="block text-sm font-medium">
            Email
            <input
              type="email"
              required
              className="mt-1 w-full rounded-md border border-line bg-panel px-3 py-2"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input
              type="password"
              required
              minLength={8}
              className="mt-1 w-full rounded-md border border-line bg-panel px-3 py-2"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={pending}>
            {pending ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </Button>
          <button
            type="button"
            className="text-sm text-cyan-800 dark:text-cyan-300"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Need an account? Register" : "Already registered? Sign in"}
          </button>
          <div className="rounded-lg border border-dashed border-line bg-panel p-3 text-sm text-muted">
            Demo desk: <span className="font-mono text-ink">analyst@example.com</span> / <span className="font-mono text-ink">Forecast#2026</span>
          </div>
        </form>
      </section>
    </div>
  );
}
