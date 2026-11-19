"use client";

import { useEffect, useState, useRef } from "react";
import type { LeafletMouseEvent, Map as LeafletMap, Marker } from "leaflet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MapPin, Navigation, Crosshair } from "lucide-react";

interface LocationPickerProps {
  lat: number;
  lng: number;
  address: string;
  onChange: (lat: number, lng: number, address: string) => void;
}

export function LocationPicker({
  lat,
  lng,
  address,
  onChange,
}: LocationPickerProps) {
  const [locating, setLocating] = useState(false);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<LeafletMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const latestLocationRef = useRef({ lat, lng, onChange });

  useEffect(() => {
    latestLocationRef.current = { lat, lng, onChange };
  }, [lat, lng, onChange]);

  useEffect(() => {
    async function initMap() {
      if (typeof window === "undefined" || !mapContainerRef.current) return;
      try {
        const L = (await import("leaflet")).default;

        // Leaflet icon fix
        delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
        L.Icon.Default.mergeOptions({
          iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
          iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
          shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
        });

        if (!mapInstanceRef.current && mapContainerRef.current) {
          const currentLocation = latestLocationRef.current;
          const map = L.map(mapContainerRef.current).setView([currentLocation.lat, currentLocation.lng], 14);
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
          }).addTo(map);

          const marker = L.marker([currentLocation.lat, currentLocation.lng], { draggable: true }).addTo(map);

          marker.on("dragend", () => {
            const position = marker.getLatLng();
            const newLat = position.lat;
            const newLng = position.lng;
            const formatted = `Lat: ${newLat.toFixed(4)}, Lng: ${newLng.toFixed(4)}`;
            latestLocationRef.current.onChange(newLat, newLng, formatted);
          });

          map.on("click", (e: LeafletMouseEvent) => {
            marker.setLatLng(e.latlng);
            latestLocationRef.current.onChange(e.latlng.lat, e.latlng.lng, `Location near [${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}]`);
          });

          mapInstanceRef.current = map;
          markerRef.current = marker;
        }
      } catch (err) {
        console.error("Leaflet map init error:", err);
      }
    }

    initMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  const handleCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userLat = pos.coords.latitude;
        const userLng = pos.coords.longitude;
        const locDesc = `Current GPS Location (${userLat.toFixed(4)}, ${userLng.toFixed(4)})`;
        onChange(userLat, userLng, locDesc);
        if (mapInstanceRef.current && markerRef.current) {
          mapInstanceRef.current.setView([userLat, userLng], 15);
          markerRef.current.setLatLng([userLat, userLng]);
        }
        setLocating(false);
      },
      (err) => {
        console.warn("Geolocation failed:", err.message);
        setLocating(false);
      },
      { timeout: 10000 }
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <MapPin className="absolute left-3 top-3 h-4 w-4 text-blue-600" />
          <Input
            value={address}
            onChange={(e) => onChange(lat, lng, e.target.value)}
            placeholder="Street address or landmark (e.g. Oak St & 5th Ave)"
            className="pl-9 text-sm"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={handleCurrentLocation}
          disabled={locating}
          className="gap-1.5 text-xs whitespace-nowrap"
        >
          <Navigation className={`h-3.5 w-3.5 ${locating ? "animate-spin" : "text-blue-600"}`} />
          <span>{locating ? "Locating..." : "Use My GPS"}</span>
        </Button>
      </div>

      <div className="relative overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 shadow-inner">
        <div ref={mapContainerRef} className="h-56 w-full z-0 bg-slate-100 dark:bg-slate-900" />
        <div className="absolute bottom-2 left-2 z-10 rounded-md bg-white/90 dark:bg-black/80 px-2.5 py-1 text-[11px] font-mono text-muted-foreground shadow-xs backdrop-blur-xs flex items-center gap-1.5">
          <Crosshair className="h-3 w-3 text-blue-600" />
          <span>Click map or drag pin to adjust coordinates</span>
        </div>
      </div>
    </div>
  );
}
