export const MODEL_COLORS: Record<string, string> = {
  GFS: "#2563eb",
  ECMWF: "#059669",
  "AI-A": "#d97706",
  "AI-B": "#7c3aed",
  ENS: "#0891b2",
  BLEND: "#e11d48",
};

type Stop = { v: number; color: string };

const RAIN: Stop[] = [
  { v: 0, color: "#f8fafc" },
  { v: 2, color: "#dbeafe" },
  { v: 10, color: "#60a5fa" },
  { v: 20, color: "#2563eb" },
  { v: 40, color: "#1e3a8a" },
  { v: 70, color: "#7c3aed" },
  { v: 120, color: "#db2777" },
  { v: 200, color: "#7f1d1d" },
];

const TMAX: Stop[] = [
  { v: 8, color: "#1e3a8a" },
  { v: 18, color: "#38bdf8" },
  { v: 26, color: "#86efac" },
  { v: 32, color: "#fde047" },
  { v: 36, color: "#fb923c" },
  { v: 40, color: "#ef4444" },
  { v: 46, color: "#7f1d1d" },
];

const TMIN: Stop[] = [
  { v: 0, color: "#1e3a8a" },
  { v: 8, color: "#38bdf8" },
  { v: 14, color: "#a7f3d0" },
  { v: 18, color: "#fde68a" },
  { v: 22, color: "#fb923c" },
  { v: 28, color: "#dc2626" },
];

const WIND: Stop[] = [
  { v: 0, color: "#f8fafc" },
  { v: 3, color: "#bae6fd" },
  { v: 6, color: "#22c55e" },
  { v: 10, color: "#eab308" },
  { v: 14, color: "#f97316" },
  { v: 18, color: "#dc2626" },
  { v: 28, color: "#4c1d95" },
];

const PROB: Stop[] = [
  { v: 0, color: "#f8fafc" },
  { v: 0.15, color: "#fef3c7" },
  { v: 0.35, color: "#fdba74" },
  { v: 0.55, color: "#f97316" },
  { v: 0.75, color: "#dc2626" },
  { v: 1, color: "#7f1d1d" },
];

function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace("#", "");
  return [parseInt(value.slice(0, 2), 16), parseInt(value.slice(2, 4), 16), parseInt(value.slice(4, 6), 16)];
}

export function colorAt(stops: Stop[], value: number): string {
  if (value <= stops[0].v) return stops[0].color;
  if (value >= stops[stops.length - 1].v) return stops[stops.length - 1].color;
  let index = 0;
  while (index < stops.length - 1 && value > stops[index + 1].v) index += 1;
  const left = stops[index];
  const right = stops[index + 1];
  const span = right.v - left.v || 1;
  const t = (value - left.v) / span;
  const a = hexToRgb(left.color);
  const b = hexToRgb(right.color);
  const mix = a.map((channel, i) => Math.round(channel + (b[i] - channel) * t));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

export function fieldStops(variable: string): Stop[] {
  if (variable === "rainfall") return RAIN;
  if (variable === "tmin") return TMIN;
  if (variable === "tmax") return TMAX;
  if (variable === "wind_speed") return WIND;
  return PROB;
}

export function fieldColor(variable: string, value: number): string {
  return colorAt(fieldStops(variable), value);
}

export function probabilityColor(value: number): string {
  return colorAt(PROB, value);
}

export { RAIN, TMAX, TMIN, WIND, PROB };
