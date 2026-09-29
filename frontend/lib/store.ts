"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { RegionId } from "./types";
import type { UnitSystem } from "./units";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  email: string | null;
  fullName: string | null;
  setSession: (session: { accessToken: string; refreshToken: string; email: string; fullName?: string | null }) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      email: null,
      fullName: null,
      setSession: (session) =>
        set({
          accessToken: session.accessToken,
          refreshToken: session.refreshToken,
          email: session.email,
          fullName: session.fullName ?? null,
        }),
      logout: () => set({ accessToken: null, refreshToken: null, email: null, fullName: null }),
    }),
    { name: "hfb-auth" },
  ),
);

interface SettingsState {
  region: RegionId;
  units: UnitSystem;
  theme: "light" | "dark";
  setRegion: (region: RegionId) => void;
  setUnits: (units: UnitSystem) => void;
  setTheme: (theme: "light" | "dark") => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      region: "india",
      units: "metric",
      theme: "light",
      setRegion: (region) => set({ region }),
      setUnits: (units) => set({ units }),
      setTheme: (theme) => set({ theme }),
    }),
    { name: "hfb-settings" },
  ),
);
