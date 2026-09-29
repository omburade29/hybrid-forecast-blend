"use client";

import { colorAt, fieldStops, PROB } from "@/lib/colors";
import type { Variable, UnitSystem } from "@/lib/units";
import { displayMeasure } from "@/lib/units";

export function FieldLegend({ variable, units }: { variable: Variable; units: UnitSystem }) {
  const stops = fieldStops(variable);
  const gradient = stops
    .map((stop, index) => {
      const t = (index / (stops.length - 1)) * 100;
      return `${stop.color} ${t}%`;
    })
    .join(", ");
  const labels = [stops[0], stops[Math.floor(stops.length / 2)], stops[stops.length - 1]];
  return (
    <div>
      <div className="h-3 rounded-full" style={{ background: `linear-gradient(90deg, ${gradient})` }} />
      <div className="mt-1 flex justify-between font-mono text-[11px] text-muted">
        {labels.map((stop) => {
          const shown = displayMeasure(variable, stop.v, units);
          return (
            <span key={stop.v}>
              {shown.value.toFixed(shown.value >= 10 ? 0 : shown.digits)} {shown.unit}
            </span>
          );
        })}
      </div>
    </div>
  );
}

export function ProbabilityLegend() {
  const gradient = PROB.map((stop, index) => `${stop.color} ${(index / (PROB.length - 1)) * 100}%`).join(", ");
  return (
    <div>
      <div className="h-3 rounded-full" style={{ background: `linear-gradient(90deg, ${gradient})` }} />
      <div className="mt-1 flex justify-between font-mono text-[11px] text-muted">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
    </div>
  );
}

export function colorPreview(variable: string, value: number) {
  return colorAt(fieldStops(variable), value);
}
