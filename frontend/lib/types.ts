import type { Variable } from "./units";

export type RegionId = "india" | "north" | "south" | "west" | "east" | "northeast";
export type Hazard = "heavy_rain" | "heat_wave" | "high_wind";

export const REGIONS: { id: RegionId; label: string }[] = [
  { id: "india", label: "All India" },
  { id: "north", label: "North India" },
  { id: "south", label: "South India" },
  { id: "west", label: "West India" },
  { id: "east", label: "East India" },
  { id: "northeast", label: "Northeast India" },
];

export const VARIABLES: { id: Variable; label: string }[] = [
  { id: "rainfall", label: "Rainfall" },
  { id: "tmax", label: "Max temp" },
  { id: "tmin", label: "Min temp" },
  { id: "wind_speed", label: "Wind" },
];

export interface CellProperties {
  lat: number;
  lon: number;
  blended?: number;
  raw?: Record<string, number>;
  corrected?: Record<string, number>;
  weights?: Record<string, number>;
  dominant_model?: string;
  dominant_weight?: number;
  dominant_color?: string;
  wind_direction?: number;
  probability?: number;
  confidence?: number;
  blended_value?: number;
  threshold?: number;
  mae?: Record<string, number>;
}

export interface Feature {
  type: "Feature";
  geometry: GeoJSON.Polygon;
  properties: CellProperties;
}

export interface ForecastResponse {
  type: "FeatureCollection";
  features: Feature[];
  summary: {
    domain_mean: number | null;
    domain_max: number | null;
    domain_min: number | null;
    dominant_model: string | null;
    dominant_counts: Record<string, number>;
    cells: number;
  };
  variable: Variable;
  variable_label: string;
  unit: string;
  lead_hour: number;
  init_time: string;
  valid_time: string;
  season: string;
  region: string;
  region_label: string;
  regime: string;
  available_inits: string[];
  leads: number[];
}

export interface SeriesResponse {
  lat: number;
  lon: number;
  variable: Variable;
  unit: string;
  variable_label: string;
  init_time: string;
  leads: number[];
  blend: number[];
  models: Record<string, number[]>;
  weights: Record<string, number[]>;
  wind_direction: number[];
}

export interface SkillRow {
  mae: number;
  rmse: number;
  bias: number;
  crps: number;
  mae_bias_corrected?: number;
}

export interface SkillResponse {
  region: string;
  variable?: string;
  by_model: Record<string, SkillRow>;
  by_lead: { lead_hour: number; models: Record<string, { mae: number; mae_bias_corrected?: number }> }[];
  by_season: { season: string; models: Record<string, { mae: number; mae_bias_corrected?: number }> }[];
  best_model: string;
  best_model_mae_bias_corrected: number;
  blend_mae: number;
  improvement_pct_vs_best_corrected: number;
  truth_std: number;
  crps_note: string;
  normalized_mae: Record<string, number>;
  improvement_pct_vs_best_normalized: number;
  best_model_normalized: string;
  blend_normalized_mae: number;
  ensemble_crps_normalized?: number;
  scorecard_rows: number;
}

export interface ModelCard {
  id: string;
  name: string;
  family: string;
  center: string;
  color: string;
  description: string;
  normalized_mae: number;
  strongest_variable: string;
}

export interface WeightMapResponse {
  type: "FeatureCollection";
  features: Feature[];
  legend: { model: string; name: string; color: string; share: number; cells: number }[];
  season: string;
  lead_hour: number;
  variable: string;
  region: string;
}

export interface ExtremeResponse {
  type: "FeatureCollection";
  features: Feature[];
  hazard: Hazard;
  title: string;
  explanation: string;
  threshold: number;
  unit: string;
  comparator: string;
  variable: Variable;
  summary: { cells: number; elevated: number; high: number; max_probability: number; mean_probability: number };
  lead_hour: number;
  init_time: string;
  region: string;
  leads: number[];
  caveat: string;
}

export interface ExtremeOverview {
  init_time: string;
  region: string;
  leads: number[];
  regime: string;
  hazards: Record<Hazard, { title: string; mean_probability: number[]; elevated_fraction: number[]; max_probability: number[] }>;
}

export interface Job {
  id: string;
  status: string;
  trigger: string;
  init_time: string;
  message: string;
  log: string;
  started_at: string;
  finished_at: string | null;
}
