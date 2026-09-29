"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { HazardLines } from "@/components/charts";
import { Explain } from "@/components/explain";
import { ProbabilityLegend } from "@/components/legend";
import { Shell } from "@/components/shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getExtremeOverview, getExtremes } from "@/lib/api";
import { useSettings } from "@/lib/store";
import type { CellProperties, Hazard } from "@/lib/types";
import { formatMeasure, type Variable } from "@/lib/units";

const ForecastMap = dynamic(() => import("@/components/forecast-map"), { ssr: false });

const HAZARDS: { id: Hazard; label: string }[] = [
  { id: "heavy_rain", label: "Heavy rain" },
  { id: "heat_wave", label: "Heat wave" },
  { id: "high_wind", label: "High wind" },
];
const LEADS = [0, 24, 48, 72, 96, 120, 144, 168];

export default function ExtremesPage() {
  return (
    <Shell>
      <Extremes />
    </Shell>
  );
}

function Extremes() {
  const region = useSettings((state) => state.region);
  const units = useSettings((state) => state.units);
  const theme = useSettings((state) => state.theme);
  const [hazard, setHazard] = useState<Hazard>("heavy_rain");
  const [lead, setLead] = useState(48);
  const [selected, setSelected] = useState<CellProperties | null>(null);

  const overview = useQuery({ queryKey: ["extreme-overview", region], queryFn: () => getExtremeOverview(region) });
  const field = useQuery({
    queryKey: ["extremes", hazard, lead, region],
    queryFn: () => getExtremes({ hazard, lead_hour: lead, region }),
  });

  const rows =
    overview.data?.leads.map((hour, index) => ({
      lead: `+${hour}h`,
      "Heavy rain": overview.data!.hazards.heavy_rain.mean_probability[index],
      "Heat wave": overview.data!.hazards.heat_wave.mean_probability[index],
      "High wind": overview.data!.hazards.high_wind.mean_probability[index],
    })) ?? [];

  const ranked = [...(field.data?.features ?? [])].sort((a, b) => (b.properties.probability ?? 0) - (a.properties.probability ?? 0)).slice(0, 6);
  const variable = (field.data?.variable ?? "rainfall") as Variable;

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Guidance</p>
          <h1 className="text-2xl font-semibold">Extreme weather</h1>
        </div>
        {overview.data ? <Badge>Regime {overview.data.regime.replace(/_/g, " ")}</Badge> : null}
      </header>

      <Explain title="How to read the probabilities">
        <p>
          Each bias-corrected model is treated as the center of a bell curve whose width is that model&apos;s historical error at this lead time and place.
          The chance of crossing the threshold is averaged with the same adaptive weights used for the deterministic forecast. Confidence is higher when the models agree.
        </p>
        <p>
          Heavy rain uses 64.5 mm/day, the IMD heavy-rain threshold. Heat uses 40 °C as a simplified plains screen — official heat-wave declarations also look at how unusual the temperature is and whether it lasts.
          High wind uses 15 m/s (about 54 km/h) as a damaging-wind screen. These are guidance fields on a synthetic archive, not issued warnings.
        </p>
      </Explain>

      <Card>
        <CardHeader><CardTitle>Mean probability by lead time</CardTitle></CardHeader>
        <CardContent>
          <HazardLines rows={rows} />
          <p className="text-xs text-muted">Fraction is the average probability over grid cells in the selected region, not the fraction of cells already over the threshold.</p>
        </CardContent>
      </Card>

      <Tabs value={hazard} onValueChange={(value) => setHazard(value as Hazard)}>
        <TabsList>
          {HAZARDS.map((item) => (
            <TabsTrigger key={item.id} value={item.id}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {field.data ? (
        <div className="grid gap-3 md:grid-cols-4">
          <Stat label="Threshold" value={`${field.data.comparator} ${field.data.threshold} ${field.data.unit}`} />
          <Stat label="Elevated cells (p ≥ 50%)" value={String(field.data.summary.elevated)} />
          <Stat label="High cells (p ≥ 75%)" value={String(field.data.summary.high)} />
          <Stat label="Peak probability" value={`${Math.round(field.data.summary.max_probability * 100)}%`} />
        </div>
      ) : null}

      <div className="flex flex-wrap gap-1">
        {LEADS.map((hour) => (
          <button key={hour} onClick={() => setLead(hour)} className={`rounded-md px-2.5 py-1 font-mono text-xs ${lead === hour ? "bg-cyan-800 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>
            T+{hour}h
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="overflow-hidden">
          <div className="h-[520px]">
            {field.data ? (
              <ForecastMap
                features={field.data.features}
                mode="probability"
                variable={variable}
                units={units}
                theme={theme}
                regionKey={`${region}-${hazard}`}
                selected={selected}
                onSelect={setSelected}
              />
            ) : (
              <div className="grid h-full place-items-center text-sm text-muted">Loading guidance…</div>
            )}
          </div>
          <div className="px-4 py-3">
            <ProbabilityLegend />
            <p className="mt-2 text-xs text-muted">{field.data?.caveat}</p>
          </div>
        </Card>
        <Card>
          <CardHeader><CardTitle>Highest probabilities</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {selected ? (
              <p>
                Selected cell {selected.lat.toFixed(1)}°N, {selected.lon.toFixed(1)}°E · {Math.round((selected.probability ?? 0) * 100)}% probability, {Math.round((selected.confidence ?? 0) * 100)}% agreement.
                {selected.blended_value != null ? ` Blended value ${formatMeasure(variable, selected.blended_value, units)}.` : ""}
              </p>
            ) : (
              <p className="text-muted">Click the map or a row. Agreement falls when members disagree about crossing the threshold.</p>
            )}
            <ul className="space-y-2">
              {ranked.map((feature) => (
                <li key={`${feature.properties.lat}-${feature.properties.lon}`}>
                  <button className="w-full rounded-md border border-line px-2 py-1.5 text-left hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => setSelected(feature.properties)}>
                    <span className="font-medium">{Math.round((feature.properties.probability ?? 0) * 100)}%</span>
                    <span className="ml-2 text-muted">
                      {feature.properties.lat.toFixed(1)}°N, {feature.properties.lon.toFixed(1)}°E
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardHeader><CardTitle>{label}</CardTitle></CardHeader>
      <CardContent className="text-2xl font-semibold">{value}</CardContent>
    </Card>
  );
}
