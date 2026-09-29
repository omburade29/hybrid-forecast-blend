import { useAuth } from "./store";
import type {
  ExtremeOverview,
  ExtremeResponse,
  ForecastResponse,
  Hazard,
  Job,
  ModelCard,
  RegionId,
  SeriesResponse,
  SkillResponse,
  WeightMapResponse,
} from "./types";
import type { Variable } from "./units";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function errorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : "Invalid request"))
      .join(", ");
  }
  return fallback;
}

async function refreshAccess(): Promise<string | null> {
  const refresh = useAuth.getState().refreshToken;
  if (!refresh) return null;
  const response = await fetch(`${API_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!response.ok) {
    useAuth.getState().logout();
    return null;
  }
  const data = (await response.json()) as { access_token: string; refresh_token: string };
  const current = useAuth.getState();
  current.setSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    email: current.email || "",
    fullName: current.fullName,
  });
  return data.access_token;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const token = useAuth.getState().accessToken;
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (response.status === 401 && retry && useAuth.getState().refreshToken) {
    const next = await refreshAccess();
    if (next) return api<T>(path, init, false);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(errorMessage(body, response.statusText));
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string) {
  const data = await api<{ access_token: string; refresh_token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  useAuth.getState().setSession({ accessToken: data.access_token, refreshToken: data.refresh_token, email });
  const profile = await api<{ email: string; full_name: string }>("/api/auth/me");
  useAuth.getState().setSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    email: profile.email,
    fullName: profile.full_name,
  });
  return profile;
}

export async function register(email: string, password: string, fullName: string) {
  const data = await api<{ access_token: string; refresh_token: string }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  useAuth.getState().setSession({ accessToken: data.access_token, refreshToken: data.refresh_token, email, fullName });
}

export function getBlended(params: { variable: Variable; lead_hour: number; region: RegionId; init_time?: string }) {
  const query = new URLSearchParams({
    variable: params.variable,
    lead_hour: String(params.lead_hour),
    region: params.region,
  });
  if (params.init_time) query.set("init_time", params.init_time);
  return api<ForecastResponse>(`/api/forecasts/blended?${query.toString()}`);
}

export function getSeries(params: { variable: Variable; lat: number; lon: number; init_time?: string }) {
  const query = new URLSearchParams({
    variable: params.variable,
    lat: String(params.lat),
    lon: String(params.lon),
  });
  if (params.init_time) query.set("init_time", params.init_time);
  return api<SeriesResponse>(`/api/forecasts/series?${query.toString()}`);
}

export function getModels() {
  return api<{ models: ModelCard[]; blend: { normalized_mae: number; improvement_pct_vs_best: number; best_single_model: string } }>(
    "/api/forecasts/models",
  );
}

export function getSkill(variable: Variable, region: RegionId) {
  return api<SkillResponse>(`/api/metrics/skill?variable=${variable}&region=${region}`);
}

export function getWeightMap(params: { variable: Variable; lead_hour: number; season: string; region: RegionId }) {
  const query = new URLSearchParams({
    variable: params.variable,
    lead_hour: String(params.lead_hour),
    season: params.season,
    region: params.region,
  });
  return api<WeightMapResponse>(`/api/weights/maps?${query.toString()}`);
}

export function getExtremes(params: { hazard: Hazard; lead_hour: number; region: RegionId; init_time?: string }) {
  const query = new URLSearchParams({
    hazard: params.hazard,
    lead_hour: String(params.lead_hour),
    region: params.region,
  });
  if (params.init_time) query.set("init_time", params.init_time);
  return api<ExtremeResponse>(`/api/extremes?${query.toString()}`);
}

export function getExtremeOverview(region: RegionId, initTime?: string) {
  const query = new URLSearchParams({ region });
  if (initTime) query.set("init_time", initTime);
  return api<ExtremeOverview>(`/api/extremes/overview?${query.toString()}`);
}

export function getJobs() {
  return api<{ schedule: string; scheduler_enabled: boolean; jobs: Job[] }>("/api/jobs");
}

export function runJob() {
  return api<Job>("/api/jobs/run", { method: "POST" });
}

export function getHealth() {
  return fetch(`${API_URL}/api/health`).then(async (response) => {
    if (!response.ok) throw new Error("API unreachable");
    return (await response.json()) as { status: string; latest_init: string | null };
  });
}
