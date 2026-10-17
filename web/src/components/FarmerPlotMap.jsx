"use client";

// Client-only: import with next/dynamic and { ssr: false } (Leaflet needs `window`).
// View-only map for farmers: shows their registered plots. There are no drawing
// tools — farmers can't change the outline of their land.

import { useEffect, useMemo, useRef } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useRemountKey } from "@/lib/useRemountKey";

const KARNATAKA_CENTER = [15.3, 75.7];
// dashArray: null clears the dash an unselected plot had.
const SELECTED = { color: "#ffd400", weight: 3, fillColor: "#ffd400", fillOpacity: 0.2, dashArray: null };
const OTHER = { color: "#ffffff", weight: 2, fillColor: "#ffffff", fillOpacity: 0.1, dashArray: "6 4" };

// Keep the selected plot in the part of the map the panel doesn't cover.
function fitOptions() {
  const phone = window.innerWidth < 768;
  return {
    maxZoom: 17,
    paddingTopLeft: [40, phone ? 70 : 40],
    paddingBottomRight: phone ? [40, window.innerHeight * 0.65 + 20] : [460, 40],
  };
}

function FitToPlots({ plots, selectedId }) {
  const map = useMap();
  useEffect(() => {
    const selected = plots.find((p) => p.plot_id === selectedId);
    const target = selected ? [selected] : plots;
    if (!target.length) return;
    const bounds = L.geoJSON({ type: "FeatureCollection", features: target.map((p) => ({ type: "Feature", geometry: p.geometry })) }).getBounds();
    map.flyToBounds(bounds, { ...fitOptions(), duration: 1 });
  }, [map, plots, selectedId]);
  return null;
}

export default function FarmerPlotMap({ plots, selectedId, onSelect, label }) {
  const mapKey = useRemountKey();
  const layerRef = useRef(null);
  const data = useMemo(
    () => ({
      type: "FeatureCollection",
      features: plots.map((p) => ({ type: "Feature", geometry: p.geometry, properties: { plot_id: p.plot_id } })),
    }),
    [plots],
  );

  useEffect(() => {
    layerRef.current?.setStyle((f) => (f.properties.plot_id === selectedId ? SELECTED : OTHER));
  }, [selectedId]);

  return (
    <div className="absolute inset-0">
      <MapContainer key={mapKey} center={KARNATAKA_CENTER} zoom={7} maxZoom={19} className="h-full w-full" zoomControl={false}>
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community"
          maxNativeZoom={18}
          maxZoom={19}
        />
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
          maxNativeZoom={18}
          maxZoom={19}
        />
        <GeoJSON
          key={plots.map((p) => p.plot_id).join(",")}
          ref={layerRef}
          data={data}
          style={(f) => (f.properties.plot_id === selectedId ? SELECTED : OTHER)}
          onEachFeature={(feature, layer) => layer.on("click", () => onSelect?.(feature.properties.plot_id))}
        />
        <FitToPlots plots={plots} selectedId={selectedId} />
      </MapContainer>
      <div className="pointer-events-none absolute top-16 left-1/2 z-[1000] -translate-x-1/2 rounded-full bg-ink/80 px-4 py-2 text-sm font-medium whitespace-nowrap text-white shadow-md md:top-3">
        {label}
      </div>
    </div>
  );
}
