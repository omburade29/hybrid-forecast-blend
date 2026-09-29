"use client";

import type { Feature as GeoFeature, FeatureCollection } from "geojson";
import { CircleMarker, GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";

import { fieldColor, probabilityColor } from "@/lib/colors";
import type { CellProperties, Feature } from "@/lib/types";
import { formatMeasure, type UnitSystem, type Variable } from "@/lib/units";
import "leaflet/dist/leaflet.css";

function Fit({ regionKey, points }: { regionKey: string; points: [number, number][] }) {
  const map = useMap();
  const signature = `${regionKey}:${points.length}:${points[0]?.join(",") ?? ""}`;
  useEffect(() => {
    if (points.length === 0) return;
    map.fitBounds(points, { padding: [16, 16] });
    // Refit when the region or the grid changes, not on every hover or selection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, signature]);
  return null;
}

export default function ForecastMap({
  features,
  mode,
  variable,
  units,
  theme,
  regionKey,
  selected,
  onSelect,
}: {
  features: Feature[];
  mode: "field" | "dominant" | "probability";
  variable: Variable;
  units: UnitSystem;
  theme: "light" | "dark";
  regionKey: string;
  selected: CellProperties | null;
  onSelect: (properties: CellProperties) => void;
}) {
  const collection: FeatureCollection = {
    type: "FeatureCollection",
    features: features as unknown as GeoFeature[],
  };
  const points = features.map((feature) => [feature.properties.lat, feature.properties.lon] as [number, number]);
  const tiles = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

  return (
    <MapContainer center={[22.5, 82]} zoom={5} className={`h-full w-full ${theme === "dark" ? "map-dark" : ""}`} scrollWheelZoom>
      <TileLayer attribution="&copy; OpenStreetMap contributors" url={tiles} />
      <Fit regionKey={regionKey} points={points} />
      <GeoJSON
        key={`${mode}-${variable}-${regionKey}-${features.length}-${selected?.lat ?? ""}-${selected?.lon ?? ""}`}
        data={collection}
        style={(feature) => {
          const props = feature?.properties as CellProperties;
          const active = selected && selected.lat === props.lat && selected.lon === props.lon;
          let fill = "#94a3b8";
          if (mode === "dominant") fill = props.dominant_color || "#334155";
          else if (mode === "probability") fill = probabilityColor(props.probability ?? 0);
          else fill = fieldColor(variable, props.blended ?? props.blended_value ?? 0);
          return {
            color: active ? "#0f172a" : "rgba(255,255,255,0.9)",
            weight: active ? 2.4 : 0.6,
            fillColor: fill,
            fillOpacity: 0.84,
          };
        }}
        onEachFeature={(feature, layer) => {
          const props = feature.properties as CellProperties;
          const value =
            mode === "probability"
              ? `${Math.round((props.probability ?? 0) * 100)}%`
              : mode === "dominant"
                ? `${props.dominant_model} ${Math.round((props.dominant_weight ?? 0) * 100)}%`
                : formatMeasure(variable, props.blended ?? 0, units);
          layer.bindTooltip(`${props.lat.toFixed(1)}°N, ${props.lon.toFixed(1)}°E · ${value}`, { sticky: true });
          layer.on("click", () => onSelect(props));
        }}
      />
      {selected ? <CircleMarker center={[selected.lat, selected.lon]} radius={6} pathOptions={{ color: "#0f172a", weight: 2, fillColor: "#fff", fillOpacity: 1 }} /> : null}
    </MapContainer>
  );
}
