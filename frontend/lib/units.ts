export type UnitSystem = "metric" | "imperial";
export type Variable = "rainfall" | "tmin" | "tmax" | "wind_speed";

export function displayMeasure(variable: Variable, raw: number, units: UnitSystem): { value: number; unit: string; digits: number } {
  if (variable === "rainfall") {
    if (units === "imperial") return { value: raw / 25.4, unit: "in", digits: 2 };
    return { value: raw, unit: "mm", digits: 1 };
  }
  if (variable === "tmin" || variable === "tmax") {
    if (units === "imperial") return { value: (raw * 9) / 5 + 32, unit: "°F", digits: 1 };
    return { value: raw, unit: "°C", digits: 1 };
  }
  if (units === "imperial") return { value: raw * 2.23694, unit: "mph", digits: 1 };
  return { value: raw * 3.6, unit: "km/h", digits: 1 };
}

export function formatMeasure(variable: Variable, raw: number, units: UnitSystem): string {
  const measure = displayMeasure(variable, raw, units);
  return `${measure.value.toFixed(measure.digits)} ${measure.unit}`;
}

export function unitLabel(variable: Variable, units: UnitSystem): string {
  return displayMeasure(variable, 0, units).unit;
}

/** Skill scores stay in the archive's native units so MAE is not rescaled. */
export function nativeUnit(variable: Variable): string {
  if (variable === "rainfall") return "mm";
  if (variable === "wind_speed") return "m/s";
  return "°C";
}
