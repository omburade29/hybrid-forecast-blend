import type { ReactNode } from "react";

export function Explain({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="rounded-xl border border-line bg-panel px-4 py-3 text-sm text-muted shadow-card">
      <summary className="cursor-pointer font-semibold text-ink">{title}</summary>
      <div className="mt-2 space-y-2 leading-relaxed">{children}</div>
    </details>
  );
}
