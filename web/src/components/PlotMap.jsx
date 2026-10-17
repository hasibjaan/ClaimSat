"use client";

// Client-only: import with next/dynamic and { ssr: false } (Leaflet needs `window`).
// Drawing map for OFFICERS registering a plot. Farmers never draw: they use
// FarmerPlotMap, which only shows plots an officer registered.

import { useEffect, useRef } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "@/lib/leafletGlobal";
import { useRemountKey } from "@/lib/useRemountKey";
import "@geoman-io/leaflet-geoman-free";
import "leaflet/dist/leaflet.css";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";

const KARNATAKA_CENTER = [15.3, 75.7];
const PLOT_STYLE = { color: "#ffd400", weight: 3, fillColor: "#ffd400", fillOpacity: 0.15 };

const REGISTERED_STYLE = { color: "#ffffff", weight: 2, fillColor: "#ffffff", fillOpacity: 0.25, dashArray: "6 4" };

// Survive map rebuilds (see useRemountKey): where the user was looking.
// Only one PlotMap exists at a time.
let savedView = { center: KARNATAKA_CENTER, zoom: 7 };

function DrawControl({ onChange, locked, geometry }) {
  const map = useMap();
  const layerRef = useRef(null);
  const adoptRef = useRef(null);
  const onChangeRef = useRef(onChange);
  const geometryRef = useRef(geometry);

  useEffect(() => {
    onChangeRef.current = onChange;
    geometryRef.current = geometry;
  }, [onChange, geometry]);

  // Toolbar and drawing events, set up once.
  useEffect(() => {
    map.pm.addControls({
      position: "topleft",
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawCircle: false,
      drawText: false,
      dragMode: false,
      cutPolygon: false,
      rotateMode: false,
      drawRectangle: true,
      drawPolygon: true,
      editMode: true,
      removalMode: true,
    });
    map.pm.setGlobalOptions({
      pathOptions: PLOT_STYLE,
      allowSelfIntersection: false,
    });

    const emit = () => {
      const layer = layerRef.current;
      onChangeRef.current(layer ? layer.toGeoJSON().geometry : null);
    };

    const adopt = (layer, { silent = false } = {}) => {
      // Only one plot at a time: drawing a new one replaces the old one.
      if (layerRef.current && layerRef.current !== layer) layerRef.current.remove();
      layerRef.current = layer;
      layer.setStyle?.(PLOT_STYLE);
      layer.on("pm:edit", emit);
      if (!silent) emit();
    };

    const onCreate = (e) => adopt(e.layer);
    const onRemove = (e) => {
      if (e.layer === layerRef.current) {
        layerRef.current = null;
        emit();
      }
    };

    const onMoveEnd = () => {
      savedView = { center: map.getCenter(), zoom: map.getZoom() };
    };

    map.on("pm:create", onCreate);
    map.on("pm:remove", onRemove);
    map.on("moveend", onMoveEnd);
    adoptRef.current = adopt;

    // A rebuilt map starts empty: put back the plot the user already has,
    // without reporting a change (that would clear their results).
    if (geometryRef.current) {
      adopt(L.geoJSON(geometryRef.current).getLayers()[0].addTo(map), { silent: true });
    }

    return () => {
      map.off("pm:create", onCreate);
      map.off("pm:remove", onRemove);
      map.off("moveend", onMoveEnd);
      map.pm.removeControls();
      adoptRef.current = null;
    };
  }, [map]);

  // While an assessment runs, stop the plot from being edited.
  useEffect(() => {
    if (locked) {
      map.pm.disableDraw();
      map.pm.disableGlobalEditMode();
      map.pm.disableGlobalRemovalMode();
    }
    map.getContainer().querySelectorAll(".leaflet-pm-toolbar").forEach((el) => {
      el.style.display = locked ? "none" : "";
    });
  }, [map, locked]);

  return null;
}

function LocateButton() {
  const map = useMap();
  const locate = () => {
    map.locate({ setView: true, maxZoom: 16 });
  };
  return (
    <button
      type="button"
      onClick={locate}
      className="absolute right-3 top-3 z-[1000] min-h-11 rounded-lg bg-surface px-3 text-sm font-medium text-ink shadow-md hover:bg-surface-muted"
    >
      My location
    </button>
  );
}

export default function PlotMap({ onChange, locked, areaLabel, geometry, registeredPlots = [] }) {
  const mapKey = useRemountKey();
  return (
    <div className="absolute inset-0">
      <MapContainer
        key={mapKey}
        center={savedView.center}
        zoom={savedView.zoom}
        maxZoom={19}
        className="h-full w-full"
        zoomControl={false}
      >
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
        {/* Already-registered plots: shown for reference, not editable (pmIgnore). */}
        <GeoJSON
          key={registeredPlots.map((p) => p.plot_id).join(",")}
          data={{
            type: "FeatureCollection",
            features: registeredPlots.map((p) => ({ type: "Feature", geometry: p.geometry })),
          }}
          style={REGISTERED_STYLE}
          interactive={false}
          pmIgnore
        />
        <DrawControl onChange={onChange} locked={locked} geometry={geometry} />
        <LocateButton />
      </MapContainer>
      <div className="pointer-events-none absolute left-1/2 top-16 z-[1000] md:top-3 -translate-x-1/2 rounded-full bg-ink/80 px-4 py-2 text-sm font-medium whitespace-nowrap text-white shadow-md">
        {areaLabel}
      </div>
    </div>
  );
}
