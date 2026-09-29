"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { LeadLines, SkillBars } from "@/components/charts";
import { Explain } from "@/components/explain";
import { Shell } from "@/components/shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getModels, getSkill, getWeightMap } from "@/lib/api";
import { MODEL_COLORS } from "@/lib/colors";
import { useSettings } from "@/lib/store";
import { VARIABLES, type CellProperties } from "@/lib/types";
import { nativeUnit, type Variable } from "@/lib/units";

const ForecastMap = dynamic(() => import("@/components/forecast-map"), { ssr: false });

const LEADS = [0, 24, 48, 72, 96, 120, 144, 168];
const SEASONS = ["DJF", "MAM", "JJAS", "ON"];

export default function ModelsPage() {
  return (
    <Shell>
      <Models />
    </Shell>
  );
}

function Models() {
  const region = useSettings((state) => state.region);
  const units = useSettings((state) => state.units);
  const theme = useSettings((state) => state.theme);
  const [variable, setVariable] = useState<Variable>("rainfall");
  const [lead, setLead] = useState(72);
  const [season, setSeason] = useState("JJAS");
  const [selected, setSelected] = useState<CellProperties | null>(null);

  const skill = useQuery({ queryKey: ["skill", variable, region], queryFn: () => getSkill(variable, region) });
  const models = useQuery({ queryKey: ["models"], queryFn: getModels });
  const weights = useQuery({
    queryKey: ["weights", variable, lead, season, region],
    queryFn: () => getWeightMap({ variable, lead_hour: lead, season, region }),
  });

  const unit = nativeUnit(variable);
  const order = ["GFS", "ECMWF", "AI-A", "AI-B", "ENS", "BLEND"];
  const bars =
    skill.data == null
      ? []
      : order.map((model) => ({
          model,
          mae: model === "BLEND" ? skill.data!.by_model[model].mae : (skill.data!.by_model[model].mae_bias_corrected ?? skill.data!.by_model[model].mae),
        }));
  const leadRows =
    skill.data?.by_lead.map((row) => {
      const entry: Record<string, string | number> = { lead: `+${row.lead_hour}h` };
      for (const model of order) {
        const stats = row.models[model];
        entry[model] = model === "BLEND" ? stats.mae : (stats.mae_bias_corrected ?? stats.mae);
      }
      return entry;
    }) ?? [];

  return (
    <>
      <header>
        <p className="font-mono text-xs uppercase tracking-widest text-muted">Verification</p>
        <h1 className="text-2xl font-semibold">Model skill and weight maps</h1>
      </header>
      <Explain title="How weights are computed">
        <p>
          On the training days of each season, every model is scored by mean absolute error at each lead time and grid cell, after a constant bias is removed.
          Those errors are smoothed toward neighbouring cells so one noisy day cannot dominate a tile. A softmax turns lower error into a higher weight.
        </p>
        <p>
          A small linear gating network, trained on lead time, latitude, longitude, season, and variable, is mixed in at 14%. The map shows the model with the largest weight.
          Scores below use the held-out days only. Individual models are shown after the same bias correction as the blend, so the comparison is fair.
        </p>
      </Explain>

      {models.data ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {models.data.models.map((model) => (
            <Card key={model.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: model.color }} />
                  {model.name}
                  <Badge>{model.family}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted">
                <p>{model.description}</p>
                <p className="mt-2 text-ink">
                  Normalized MAE {model.normalized_mae.toFixed(3)} · strongest on {model.strongest_variable.replace(/_/g, " ")}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {VARIABLES.map((item) => (
          <button
            key={item.id}
            onClick={() => setVariable(item.id)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${variable === item.id ? "bg-brand text-white" : "bg-slate-100 dark:bg-slate-800"}`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {skill.data ? (
        <div className="grid gap-3 md:grid-cols-3">
          <Card>
            <CardHeader><CardTitle>Blend MAE</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold">
              {skill.data.blend_mae.toFixed(2)} <span className="text-base font-normal text-muted">{unit}</span>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Best corrected model</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold">
              {skill.data.best_model}
              <p className="text-sm font-normal text-muted">{skill.data.best_model_mae_bias_corrected.toFixed(2)} {unit}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Held-out improvement</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold">
              {skill.data.improvement_pct_vs_best_corrected.toFixed(1)}%
              <p className="text-sm font-normal text-muted">Lower MAE than {skill.data.best_model}. Aggregate normalized gain {skill.data.improvement_pct_vs_best_normalized.toFixed(1)}%.</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Bias-corrected MAE by model</CardTitle></CardHeader>
          <CardContent>
            <SkillBars rows={bars} unit={unit} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>MAE against lead time</CardTitle></CardHeader>
          <CardContent>
            <LeadLines rows={leadRows} models={order} unit={unit} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Scorecard</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="py-2">Model</th>
                <th>MAE raw</th>
                <th>MAE corrected</th>
                <th>RMSE</th>
                <th>Bias</th>
                <th>CRPS</th>
              </tr>
            </thead>
            <tbody>
              {skill.data
                ? order.map((model) => {
                    const row = skill.data!.by_model[model];
                    return (
                      <tr key={model} className={model === "BLEND" ? "bg-rose-50 font-semibold dark:bg-rose-950/30" : "border-t border-line"}>
                        <td className="py-2">
                          <span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: MODEL_COLORS[model] }} />
                          {model}
                        </td>
                        <td>{row.mae.toFixed(2)}</td>
                        <td>{(row.mae_bias_corrected ?? row.mae).toFixed(2)}</td>
                        <td>{row.rmse.toFixed(2)}</td>
                        <td>{row.bias.toFixed(2)}</td>
                        <td>{row.crps.toFixed(2)}</td>
                      </tr>
                    );
                  })
                : null}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-muted">{skill.data?.crps_note}</p>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Where each model is trusted</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {SEASONS.map((item) => (
              <button key={item} onClick={() => setSeason(item)} className={`rounded-md px-2.5 py-1 text-xs font-semibold ${season === item ? "bg-brand text-white" : "bg-slate-100 dark:bg-slate-800"}`}>
                {item}
              </button>
            ))}
            {LEADS.map((hour) => (
              <button key={hour} onClick={() => setLead(hour)} className={`rounded-md px-2.5 py-1 font-mono text-xs ${lead === hour ? "bg-cyan-800 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>
                T+{hour}h
              </button>
            ))}
          </div>
          <div className="h-[480px]">
            {weights.data ? (
              <ForecastMap
                features={weights.data.features}
                mode="dominant"
                variable={variable}
                units={units}
                theme={theme}
                regionKey={`${region}-${season}-${lead}`}
                selected={selected}
                onSelect={setSelected}
              />
            ) : (
              <div className="grid h-full place-items-center text-sm text-muted">Loading weight map…</div>
            )}
          </div>
          <div className="flex flex-wrap gap-3 text-xs">
            {weights.data?.legend.map((item) => (
              <span key={item.model} className="inline-flex items-center gap-1">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: item.color }} />
                {item.name} · {Math.round(item.share * 100)}% of cells
              </span>
            ))}
          </div>
          {selected?.mae ? (
            <p className="text-sm text-muted">
              Training MAE at {selected.lat.toFixed(1)}°N, {selected.lon.toFixed(1)}°E:{" "}
              {Object.entries(selected.mae)
                .map(([model, value]) => `${model} ${value.toFixed(2)}`)
                .join(" · ")}
            </p>
          ) : (
            <p className="text-sm text-muted">Click a cell to read the training MAE that produced its weights.</p>
          )}
        </CardContent>
      </Card>
    </>
  );
}
