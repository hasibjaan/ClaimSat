// Leaflet-Geoman's bundle reads Leaflet from the global `L`, so expose it
// before Geoman is imported. Import this module first, then Geoman.
import L from "leaflet";

if (typeof window !== "undefined") window.L = L;

export default L;
