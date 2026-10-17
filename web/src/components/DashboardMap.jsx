"use client";

// Client-only: import with next/dynamic and { ssr: false } (Leaflet needs `window`).

import { useCallback, useEffect, useMemo, useRef } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useRemountKey } from "@/lib/useRemountKey";
import { LEVEL_LABELS } from "@/lib/format";

export const LEVEL_ORDER = ["severe", "moderate", "low", "none", "unknown"];

function levelColours() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(
    LEVEL_ORDER.map((level) => [level, style.getPropertyValue(`--color-level-${level}`).trim() || "#888888"]),
  );
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function popupHtml(plot) {
  const lines = [
    `<strong>${escapeHtml(LEVEL_LABELS[plot.damage_level] ?? plot.damage_level)}</strong> · score ${plot.damage_score ?? "—"}`,
    `${escapeHtml(plot.confidence)} confidence`,
    plot.severity_level ? `Case severity: ${escapeHtml(LEVEL_LABELS[plot.severity_level] ?? plot.severity_level)}` : null,
    plot.verification_status ? `Verification: ${escapeHtml(plot.verification_status.replace("_", " "))}` : null,
    plot.nearby_farmers != null ? `Nearby reports: ${escapeHtml(plot.nearby_farmers)}` : null,
    plot.flood_fraction != null ? `Newly under water: ${Math.round(plot.flood_fraction * 100)}%` : null,
    plot.ndvi_loss != null ? `Crop health lost: ${Math.round(plot.ndvi_loss * 100)}%` : null,
    plot.farmer_name ? `Farmer: ${escapeHtml(plot.farmer_name)}` : null,
    plot.survey_number ? `Survey no. ${escapeHtml(plot.survey_number)}` : null,
    plot.village ? escapeHtml(plot.village) : null,
    plot.source !== "batch" && plot.source !== "sample"
      ? `<a href="/report/${encodeURIComponent(plot.assessment_id)}">Open report →</a>`
      : `<span style="color:#5c625e">Village survey plot (no individual report)</span>`,
  ];
  return lines.filter(Boolean).join("<br>");
}

function FitAndSelect({ layerRef, selectedId, plots }) {
  const map = useMap();

  useEffect(() => {
    const layer = layerRef.current;
    if (layer && layer.getLayers().length) map.fitBounds(layer.getBounds(), { padding: [24, 24] });
  }, [map, layerRef, plots]);

  useEffect(() => {
    if (!selectedId || !layerRef.current) return;
    const target = layerRef.current.getLayers().find((l) => l.feature.properties.assessment_id === selectedId);
    if (target) {
      map.flyToBounds(target.getBounds(), { maxZoom: 17, duration: 0.8 });
      target.openPopup();
    }
  }, [map, layerRef, selectedId]);

  return null;
}

export default function DashboardMap({ plots, selectedId, onSelect }) {
  const layerRef = useRef(null);
  const mapKey = useRemountKey();
  const colours = useMemo(() => levelColours(), []);

  const data = useMemo(
    () => ({
      type: "FeatureCollection",
      features: plots
        .filter((p) => p.geometry)
        .map((p) => ({ type: "Feature", geometry: p.geometry, properties: p })),
    }),
    [plots],
  );

  const style = useCallback(
    (feature) => {
      const p = feature.properties;
      const colour = colours[p.damage_level] ?? colours.unknown;
      const selected = p.assessment_id === selectedId;
      return {
        color: selected ? "#ffffff" : colour,
        weight: selected ? 3 : 1,
        fillColor: colour,
        fillOpacity: 0.7,
      };
    },
    [colours, selectedId],
  );

  // Restyle in place when the selection changes (no redraw).
  useEffect(() => {
    layerRef.current?.setStyle(style);
  }, [style]);

  const onEachFeature = (feature, layer) => {
    layer.bindPopup(popupHtml(feature.properties));
    layer.on("click", () => onSelect(feature.properties.assessment_id));
  };

  return (
    <div className="relative h-full w-full">
      <MapContainer key={mapKey} center={[16.73, 75.06]} zoom={13} maxZoom={19} className="h-full w-full">
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community"
          maxNativeZoom={18}
          maxZoom={19}
        />
        {/* key redraws the layer when a new set of plots arrives */}
        <GeoJSON
          key={plots.length}
          data={data}
          style={style}
          onEachFeature={onEachFeature}
          ref={layerRef}
        />
        <FitAndSelect layerRef={layerRef} selectedId={selectedId} plots={plots} />
      </MapContainer>
      <div className="absolute bottom-3 left-3 z-[1000] rounded-lg bg-surface/95 p-3 text-xs shadow-md">
        {LEVEL_ORDER.map((level) => (
          <div key={level} className="flex items-center gap-2 py-0.5">
            <span className="size-3 rounded-sm" style={{ background: colours[level] }} />
            {LEVEL_LABELS[level]}
          </div>
        ))}
      </div>
    </div>
  );
}
