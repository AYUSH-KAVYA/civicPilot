"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap } from "leaflet";
import { CaseState } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Truck, Building2, AlertTriangle, ShieldAlert } from "lucide-react";

interface CaseMapViewProps {
  caseState: CaseState;
}

export function CaseMapView({ caseState }: CaseMapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<LeafletMap | null>(null);

  const lat = caseState.intake?.location.lat ?? caseState.raw.lat;
  const lng = caseState.intake?.location.lng ?? caseState.raw.lng;
  const hasCoordinates = lat !== null && lat !== undefined && lng !== null && lng !== undefined;
  const sensitiveSites = caseState.intake?.nearby_sensitive_sites || [];

  useEffect(() => {
    async function initMap() {
      if (typeof window === "undefined" || !mapContainerRef.current || !hasCoordinates) return;
      try {
        const L = (await import("leaflet")).default;

        delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
        L.Icon.Default.mergeOptions({
          iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
          iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
          shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
        });

        if (!mapInstanceRef.current && mapContainerRef.current) {
          const map = L.map(mapContainerRef.current).setView([lat, lng], 14);
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19,
          }).addTo(map);

          // Incident marker (Red/Blue)
          const incidentMarker = L.marker([lat, lng]).addTo(map);
          const popup = document.createElement("div");
          popup.textContent = `Case #${caseState.id}: ${caseState.intake?.summary || "Reported location"}`;
          incidentMarker.bindPopup(popup);

          mapInstanceRef.current = map;
        }
      } catch (err) {
        console.error("Map init error:", err);
      }
    }

    initMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [hasCoordinates, lat, lng, caseState.id, caseState.intake?.summary]);

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <MapPin className="h-4 w-4 text-blue-600" />
            <span>Incident &amp; Field Crew Spatial Map</span>
          </CardTitle>
          <Badge variant="outline" className="text-[10px] font-mono">
            Ward: {caseState.triage?.ward_id || "ward-5"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        <div className="relative overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
          <div ref={mapContainerRef} className="h-64 w-full bg-slate-100 dark:bg-slate-900" />
          {!hasCoordinates && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-100/90 p-6 text-center text-sm text-muted-foreground dark:bg-slate-900/90">
              Incident coordinates are not available in this case.
            </div>
          )}
        </div>

        {/* Location & Sensitive Sites Details */}
        <div className="space-y-2 text-xs">
          <div className="flex items-start gap-1.5 text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 text-blue-600 mt-0.5 shrink-0" />
            <span>{caseState.intake?.location.address || caseState.raw.address_text || "San Francisco"}</span>
          </div>

          {sensitiveSites.length > 0 && (
            <div className="flex items-start gap-1.5 text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2 rounded-lg border border-amber-200 dark:border-amber-900">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Nearby Sensitive Infrastructure: </span>
                <span>{sensitiveSites.join(", ")}</span>
              </div>
            </div>
          )}

          {caseState.tickets?.length ? caseState.tickets.map((ticket) => (
            <div key={ticket.id} className="flex flex-wrap items-center justify-between gap-2 border-t pt-2 text-[11px] font-mono">
              <span className="flex items-center gap-1 text-emerald-700 dark:text-emerald-400">
                <Truck className="h-3.5 w-3.5" /> Ticket {ticket.id} · Crew {ticket.crew_id || "unassigned"}
              </span>
              <span className="text-muted-foreground">Crew coordinates not supplied</span>
            </div>
          )) : null}
        </div>
      </CardContent>
    </Card>
  );
}
