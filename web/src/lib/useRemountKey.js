"use client";

import { useLayoutEffect, useState } from "react";

// With Cache Components, Next.js keeps recent pages alive but hidden (React
// <Activity>): effects clean up when you navigate away and run again when you
// come back, but state survives. react-leaflet's MapContainer can't survive
// that: its Leaflet map is destroyed on hide and child layers then try to
// attach to it ("Cannot read properties of undefined (reading 'appendChild')").
//
// Use the returned value as the map's `key`: it changes every time the page is
// hidden, so a fresh map is built when the page is shown again.
export function useRemountKey() {
  const [key, setKey] = useState(0);
  useLayoutEffect(() => () => setKey((k) => k + 1), []);
  return key;
}
