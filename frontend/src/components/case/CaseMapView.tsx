"use client";

import { useEffect, useRef, useState } from "react";
import { CaseState } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Truck, Building2, AlertTriangle, ShieldAlert } from "lucide-react";

interface CaseMapViewProps {
  caseState: CaseState;
}

export function CaseMapView({ caseState }: CaseMapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [mapReady, setMapReady] = useState(false);

  const lat = caseState.intake?.location.lat || caseState.raw.lat || 37.7749;
  const lng = caseState.intake?.location.lng || caseState.raw.lng || -122.4194;
  const sensitiveSites = caseState.intake?.nearby_sensitive_sites || [];
  const assignedCrew = caseState.tickets?.[0]?.crew_id;

  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (typeof window === "undefined" || !mapContainerRef.current) return;
      try {
        const L = (await import("leaflet")).default;

        delete (L.Icon.Default.prototype as any)._getIconUrl;
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
          incidentMarker.bindPopup(
            `<b>Grievance #${caseState.id}</b><br/>${caseState.intake?.summary || "Reported Location"}`
          );

          // Simulated crew position near incident
          if (assignedCrew) {
            const crewLat = lat + 0.003;
            const crewLng = lng + 0.004;
            const crewMarker = L.circleMarker([crewLat, crewLng], {
              color: "#10b981",
              fillColor: "#34d399",
              fillOpacity: 0.8,
              radius: 8,
            }).addTo(map);
            crewMarker.bindPopup(`<b>Assigned Crew: ${assignedCrew}</b><br/>En-route to site`);
          }

          mapInstanceRef.current = map;
          if (isMounted) setMapReady(true);
        }
      } catch (err) {
        console.error("Map init error:", err);
      }
    }

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [lat, lng, assignedCrew, caseState.id, caseState.intake?.summary]);

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

          {caseState.tickets && caseState.tickets.length > 0 && (
            <div className="flex items-center justify-between pt-1 border-t text-[11px] font-mono">
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                <Truck className="h-3.5 w-3.5" />
                Crew: {caseState.tickets[0].crew_id || "Auto-dispatching"}
              </span>
              <span className="text-muted-foreground">
                Work Order #{caseState.tickets[0].id}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
