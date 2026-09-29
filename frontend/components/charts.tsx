"use client";

import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { MODEL_COLORS } from "@/lib/colors";

const GRID = "#d8e1ea";

export function SeriesChart({
  rows,
  unit,
  models,
}: {
  rows: Record<string, string | number>[];
  unit: string;
  models: string[];
}) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
          <XAxis dataKey="lead" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={48} unit="" />
          <Tooltip formatter={(value) => `${Number(value).toFixed(1)} ${unit}`} />
          <Legend />
          {models.map((model) => (
            <Line key={model} type="monotone" dataKey={model} stroke={MODEL_COLORS[model] || "#64748b"} strokeWidth={1.6} dot={false} />
          ))}
          <Line type="monotone" dataKey="Blend" stroke={MODEL_COLORS.BLEND} strokeWidth={2.8} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SkillBars({ rows, unit }: { rows: { model: string; mae: number }[]; unit: string }) {
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="model" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip formatter={(value) => `${Number(value).toFixed(2)} ${unit}`} />
          <Bar dataKey="mae" name={`MAE (${unit})`} radius={[4, 4, 0, 0]}>
            {rows.map((row) => (
              <Cell key={row.model} fill={MODEL_COLORS[row.model] || "#0e7490"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LeadLines({
  rows,
  models,
  unit,
}: {
  rows: Record<string, string | number>[];
  models: string[];
  unit: string;
}) {
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
          <XAxis dataKey="lead" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip formatter={(value) => `${Number(value).toFixed(2)} ${unit}`} />
          <Legend />
          {models.map((model) => (
            <Line key={model} type="monotone" dataKey={model} stroke={MODEL_COLORS[model] || "#64748b"} strokeWidth={model === "BLEND" ? 2.8 : 1.6} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HazardLines({ rows }: { rows: Record<string, string | number>[] }) {
  const series = [
    { key: "Heavy rain", color: "#2563eb" },
    { key: "Heat wave", color: "#dc2626" },
    { key: "High wind", color: "#d97706" },
  ];
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
          <XAxis dataKey="lead" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={40} tickFormatter={(value) => `${Math.round(Number(value) * 100)}%`} />
          <Tooltip formatter={(value) => `${Math.round(Number(value) * 100)}%`} />
          <Legend />
          {series.map((item) => (
            <Line key={item.key} type="monotone" dataKey={item.key} stroke={item.color} strokeWidth={2.2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
