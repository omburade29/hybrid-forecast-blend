"use client";

import { useQuery } from "@tanstack/react-query";

import { Explain } from "@/components/explain";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_URL, getHealth } from "@/lib/api";
import { useSettings } from "@/lib/store";
import { REGIONS, type RegionId } from "@/lib/types";
import type { UnitSystem } from "@/lib/units";

export default function SettingsPage() {
  return (
    <Shell>
      <SettingsScreen />
    </Shell>
  );
}

function SettingsScreen() {
  const region = useSettings((state) => state.region);
  const units = useSettings((state) => state.units);
  const theme = useSettings((state) => state.theme);
  const setRegion = useSettings((state) => state.setRegion);
  const setUnits = useSettings((state) => state.setUnits);
  const setTheme = useSettings((state) => state.setTheme);
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth });

  return (
    <>
      <header>
        <p className="font-mono text-xs uppercase tracking-widest text-muted">Preferences</p>
        <h1 className="text-2xl font-semibold">Settings</h1>
      </header>
      <Explain title="What these settings change">
        <p>
          Region filters every map, score, and extreme field to that part of the blending grid. Units change how rainfall, temperature, and wind are labeled on the dashboard.
          Skill tables stay in native units (mm, °C, m/s) so verification numbers are not rescaled. Theme is stored in this browser.
        </p>
      </Explain>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Default region</CardTitle></CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            {REGIONS.map((item) => (
              <button
                key={item.id}
                onClick={() => setRegion(item.id as RegionId)}
                className={`rounded-lg border px-3 py-3 text-left text-sm ${region === item.id ? "border-cyan-700 bg-cyan-50 dark:bg-cyan-950/40" : "border-line"}`}
              >
                {item.label}
              </button>
            ))}
          </CardContent>
        </Card>
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Units</CardTitle></CardHeader>
            <CardContent className="flex gap-2">
              {(["metric", "imperial"] as UnitSystem[]).map((item) => (
                <button
                  key={item}
                  onClick={() => setUnits(item)}
                  className={`rounded-md px-3 py-2 text-sm font-medium capitalize ${units === item ? "bg-brand text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                >
                  {item === "metric" ? "Metric (mm, °C, km/h)" : "Imperial (in, °F, mph)"}
                </button>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Theme</CardTitle></CardHeader>
            <CardContent className="flex gap-2">
              {(["light", "dark"] as const).map((item) => (
                <button
                  key={item}
                  onClick={() => setTheme(item)}
                  className={`rounded-md px-3 py-2 text-sm font-medium capitalize ${theme === item ? "bg-brand text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                >
                  {item}
                </button>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>API</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="font-mono text-xs">{API_URL}</p>
              <p>{health.isError ? "Unreachable" : health.data ? `${health.data.status} · latest init ${health.data.latest_init}` : "Checking…"}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
