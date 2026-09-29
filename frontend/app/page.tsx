"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { SeriesChart } from "@/components/charts";
import { Explain } from "@/components/explain";
import { FieldLegend } from "@/components/legend";
import { Shell } from "@/components/shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { getBlended, getSeries, getSkill } from "@/lib/api";
import { MODEL_COLORS } from "@/lib/colors";
import { REGIONS, VARIABLES, type CellProperties } from "@/lib/types";
import { useSettings } from "@/lib/store";
import { compass } from "@/lib/utils";
import { displayMeasure, formatMeasure, type Variable } from "@/lib/units";

const ForecastMap = dynamic(() => import("@/components/forecast-map"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center text-sm text-muted">Loading map…</div>,
});

const LEADS = [0, 24, 48, 72, 96, 120, 144, 168];

export default function DashboardPage() {
  return (
    <Shell>
      <Dashboard />
    </Shell>
  );
}

function Dashboard() {
  const region = useSettings((state) => state.region);
  const units = useSettings((state) => state.units);
  const theme = useSettings((state) => state.theme);
  const [variable, setVariable] = useState<Variable>("rainfall");
  const [lead, setLead] = useState(24);
  const [overlay, setOverlay] = useState(false);
  const [initTime, setInitTime] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<CellProperties | null>(null);

  const forecast = useQuery({
    queryKey: ["blended", variable, lead, region, initTime],
    queryFn: () => getBlended({ variable, lead_hour: lead, region, init_time: initTime }),
  });
  const skill = useQuery({
    queryKey: ["skill", variable, region],
    queryFn: () => getSkill(variable, region),
  });
  const series = useQuery({
    queryKey: ["series", variable, selected?.lat, selected?.lon, forecast.data?.init_time],
    enabled: Boolean(selected && forecast.data),
    queryFn: () => getSeries({ variable, lat: selected!.lat, lon: selected!.lon, init_time: forecast.data!.init_time }),
  });

  const data = forecast.data;
  const recentInits = (data?.available_inits ?? []).slice(0, 12);
  const improvement = skill.data?.improvement_pct_vs_best_corrected;

  const chartRows =
    series.data?.leads.map((hour, index) => {
      const row: Record<string, string | number> = { lead: hour === 0 ? "T+0" : `+${hour}h` };
      row.Blend = displayMeasure(variable, series.data!.blend[index], units).value;
      for (const [model, values] of Object.entries(series.data!.models)) {
        row[model] = displayMeasure(variable, values[index], units).value;
      }
      return row;
    }) ?? [];

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Blended forecast</p>
          <h1 className="text-2xl font-semibold">Consensus field</h1>
        </div>
        {data ? (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge>Init {data.init_time} 00Z</Badge>
            <Badge>Valid {data.valid_time}</Badge>
            <Badge>{data.season}</Badge>
            <Badge className="capitalize">{data.regime.replace(/_/g, " ")}</Badge>
          </div>
        ) : null}
      </header>

      <Explain title="What adaptive blending means">
        <p>
          Each source — GFS, ECMWF IFS, two AI models, and an ensemble mean — is bias-corrected using its recent error, then combined with weights that change by grid cell, season, and lead time.
          A model that has been more accurate for monsoon rainfall at day 3 over the west coast gets more of the vote there, and less of it for next-day temperature over the northern plains.
        </p>
        <p>
          Weights come from historical mean absolute error (softer models get less weight) mixed with a small gating network that sees lead time, location, season, and variable. The map can show either the blended value or which model currently holds the highest weight.
        </p>
      </Explain>

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Domain mean</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {data?.summary.domain_mean != null ? formatMeasure(variable, data.summary.domain_mean, units) : "—"}
            <p className="mt-1 text-sm font-normal text-muted">{data?.region_label ?? "Region"} · T+{lead}h</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Domain maximum</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {data?.summary.domain_max != null ? formatMeasure(variable, data.summary.domain_max, units) : "—"}
            <p className="mt-1 text-sm font-normal text-muted">Highest cell in view</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Skill vs best corrected model</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {improvement == null ? "—" : `${Math.abs(improvement).toFixed(1)}% ${improvement >= 0 ? "lower" : "higher"} MAE`}
            <p className="mt-1 text-sm font-normal text-muted">
              {skill.data ? `Best single model after bias correction: ${skill.data.best_model}` : "Held-out window"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="space-y-3 pt-4">
          <div className="flex flex-wrap items-center gap-2">
            {VARIABLES.map((item) => (
              <button
                key={item.id}
                onClick={() => setVariable(item.id)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${variable === item.id ? "bg-brand text-white" : "bg-slate-100 dark:bg-slate-800"}`}
              >
                {item.label}
              </button>
            ))}
            <label className="ml-auto flex items-center gap-2 text-sm">
              <span>Weight overlay</span>
              <Switch checked={overlay} onCheckedChange={setOverlay} />
            </label>
          </div>
          <div className="flex flex-wrap gap-1">
            {LEADS.map((hour) => (
              <button
                key={hour}
                onClick={() => setLead(hour)}
                className={`rounded-md px-2.5 py-1 font-mono text-xs ${lead === hour ? "bg-cyan-800 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
              >
                {hour === 0 ? "T+0" : `T+${hour}h`}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <label>
              Cycle
              <select
                className="ml-2 rounded-md border border-line bg-panel px-2 py-1"
                value={data?.init_time ?? ""}
                onChange={(event) => setInitTime(event.target.value)}
              >
                {recentInits.map((day) => (
                  <option key={day} value={day}>
                    {day}
                  </option>
                ))}
              </select>
            </label>
            <p className="self-end text-muted">Region follows Settings · {REGIONS.find((item) => item.id === region)?.label}</p>
          </div>
        </CardContent>
      </Card>

      {forecast.isError ? <p className="text-sm text-rose-600">{(forecast.error as Error).message}</p> : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="overflow-hidden">
          <div className="h-[540px]">
            {data ? (
              <ForecastMap
                features={data.features}
                mode={overlay ? "dominant" : "field"}
                variable={variable}
                units={units}
                theme={theme}
                regionKey={region}
                selected={selected}
                onSelect={setSelected}
              />
            ) : (
              <div className="grid h-full place-items-center text-sm text-muted">{forecast.isLoading ? "Preparing the cycle…" : "No field"}</div>
            )}
          </div>
          <div className="space-y-2 px-4 py-3">
            {overlay ? (
              <div className="flex flex-wrap gap-3 text-xs">
                {Object.entries(MODEL_COLORS)
                  .filter(([name]) => name !== "BLEND")
                  .map(([name, color]) => (
                    <span key={name} className="inline-flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
                      {name}
                      {data?.summary.dominant_counts?.[name] != null ? ` · ${data.summary.dominant_counts[name]} cells` : ""}
                    </span>
                  ))}
              </div>
            ) : (
              <FieldLegend variable={variable} units={units} />
            )}
            <p className="text-xs text-muted">Click a cell for the lead-time trace. Polygons are the blending grid, not a station network.</p>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{selected ? `${selected.lat.toFixed(1)}°N, ${selected.lon.toFixed(1)}°E` : "Select a cell"}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {selected ? (
                <>
                  <p className="text-lg font-semibold">
                    {selected.blended != null ? formatMeasure(variable, selected.blended, units) : "—"}
                    {selected.dominant_model ? (
                      <span className="ml-2 text-sm font-normal text-muted">
                        led by {selected.dominant_model} ({Math.round((selected.dominant_weight ?? 0) * 100)}%)
                      </span>
                    ) : null}
                  </p>
                  {variable === "wind_speed" && selected.wind_direction != null ? (
                    <p className="text-muted">
                      Blended direction {Math.round(selected.wind_direction)}° ({compass(selected.wind_direction)}), vector mean of the members.
                    </p>
                  ) : null}
                  <div className="space-y-1">
                    {selected.weights
                      ? Object.entries(selected.weights)
                          .sort((a, b) => b[1] - a[1])
                          .map(([model, weight]) => (
                            <div key={model}>
                              <div className="flex justify-between text-xs">
                                <span>{model}</span>
                                <span className="font-mono">
                                  {Math.round(weight * 100)}%
                                  {selected.corrected?.[model] != null ? ` · ${formatMeasure(variable, selected.corrected[model], units)}` : ""}
                                </span>
                              </div>
                              <div className="mt-0.5 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
                                <div className="h-1.5 rounded-full" style={{ width: `${weight * 100}%`, background: MODEL_COLORS[model] }} />
                              </div>
                            </div>
                          ))
                      : null}
                  </div>
                </>
              ) : (
                <p className="text-muted">Choose a grid cell to compare bias-corrected members with the blend across 0–168 h.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Lead time at the selected cell</CardTitle>
            </CardHeader>
            <CardContent>
              {chartRows.length ? (
                <SeriesChart rows={chartRows} unit={displayMeasure(variable, 0, units).unit} models={Object.keys(series.data?.models ?? {})} />
              ) : (
                <p className="text-sm text-muted">The trace appears after you pick a cell.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
