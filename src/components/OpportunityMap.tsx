import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import { Skeleton } from "@/components/ui/skeleton";
import { MapPin } from "lucide-react";
import type { ScoredOpportunity } from "@/api/client";

// ─── Fix Leaflet default icon issue ───────────────────────────
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

const DefaultIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

// ─── Types ─────────────────────────────────────────────────

export type LocationPoint = {
  city?: string;
  state?: string;
  country?: string;
  lat: number;
  lng: number;
  count: number;
  avg_score?: number | null;
  opportunities?: ScoredOpportunity[];
};

type Props = {
  locations: LocationPoint[];
  isLoading?: boolean;
  onSelectOpp?: (opp: ScoredOpportunity) => void;
};

// ─── Custom Cluster Icon ────────────────────────────────

function clusterIcon(cluster: L.MarkerCluster): L.DivIcon {
  const count = cluster.getChildCount();
  return L.divIcon({
    className: "",
    html: `<div style="
      display: flex;
      align-items: center;
      justify-content: center;
      ${clusterSizeStyle(count)}
      border-radius: 50%;
      background: linear-gradient(135deg, ${clusterGradient(count)});
      border: 2px solid ${clusterBorder(count)};
      color: white;
      font-weight: 700;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    ">${count}</div>`,
    iconSize: count < 10 ? [36, 36] : count < 50 ? [44, 44] : [56, 56],
    iconAnchor: count < 10 ? [18, 18] : count < 50 ? [22, 22] : [28, 28],
  });
}

function clusterSizeStyle(count: number): string {
  if (count < 10) return "width: 36px; height: 36px; font-size: 12px;";
  if (count < 50) return "width: 44px; height: 44px; font-size: 14px;";
  return "width: 56px; height: 56px; font-size: 16px;";
}

function clusterGradient(count: number): string {
  if (count < 10) return "#8b5cf6, #6366f1";
  if (count < 50) return "#f59e0b, #f97316";
  return "#e11d48, #ec4899";
}

function clusterBorder(count: number): string {
  if (count < 10) return "#a78bfa";
  if (count < 50) return "#fbbf24";
  return "#fb7185";
}

// ─── Cluster Group Component (imperative markers) ──────────

function MarkerClusterGroup({
  locations,
  onSelectOpp,
}: {
  locations: LocationPoint[];
  onSelectOpp?: (opp: ScoredOpportunity) => void;
}) {
  const map = useMap();
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    if (!map) return;

    // Clean up previous cluster group
    if (clusterGroupRef.current) {
      map.removeLayer(clusterGroupRef.current);
    }

    // Create new cluster group with custom styling
    const mcg = L.markerClusterGroup({
      chunkedLoading: true,
      maxClusterRadius: 60,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      disableClusteringAtZoom: 14,
      iconCreateFunction: clusterIcon,
    });

    locations.forEach((loc) => {
      const marker = L.marker([loc.lat, loc.lng], {
        icon: (loc.avg_score ?? 0) >= 85 ? highMatchIcon() : defaultMarkerIcon(),
      });

      // Build popup content
      const popupContent = document.createElement("div");
      popupContent.className = "font-sans min-w-[200px]";

      // Location header
      const header = document.createElement("div");
      header.className = "font-semibold text-sm mb-1 flex items-center gap-1.5";
      header.innerHTML = `<span>📍</span> ${[loc.city, loc.state, loc.country].filter(Boolean).join(", ")}`;
      popupContent.appendChild(header);

      // Count + score row
      const meta = document.createElement("div");
      meta.className = "flex items-center gap-2 text-xs text-gray-500 mb-2";
      meta.innerHTML = `<span>🏢 ${loc.count} ${loc.count === 1 ? "opportunity" : "opportunities"}</span>` +
        (loc.avg_score ? `<span style="color: ${scoreColor(loc.avg_score)}">📈 ${loc.avg_score.toFixed(0)}% avg match</span>` : "");
      popupContent.appendChild(meta);

      // Opportunity list
      if (loc.opportunities && loc.opportunities.length > 0) {
        const list = document.createElement("div");
        list.className = "space-y-1.5 max-h-[200px] overflow-y-auto";

        loc.opportunities.slice(0, 5).forEach((opp) => {
          const item = document.createElement("div");
          item.className = "flex items-center justify-between p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer transition-colors text-xs";
          item.innerHTML = `<div class="min-w-0 flex-1">
            <div class="font-medium truncate">${opp.title}</div>
            <div class="text-gray-400 truncate">${opp.company}</div>
          </div>
          <span class="ml-2 text-[10px] shrink-0" style="color: ${scoreColor(opp.match_score)}; border: 1px solid ${scoreColor(opp.match_score)}; padding: 0 4px; border-radius: 4px;">
            ${opp.match_score}%
          </span>`;
          item.addEventListener("click", () => onSelectOpp?.(opp));
          list.appendChild(item);
        });

        if ((loc.opportunities?.length ?? 0) > 5) {
          const more = document.createElement("div");
          more.className = "text-[10px] text-gray-400 text-center pt-1 border-t border-gray-200 dark:border-gray-700";
          more.textContent = `+${loc.opportunities.length - 5} more`;
          list.appendChild(more);
        }

        popupContent.appendChild(list);
      }

      marker.bindPopup(popupContent);
      mcg.addLayer(marker);
    });

    // Fit bounds to all markers
    if (locations.length > 0) {
      const bounds = L.latLngBounds(locations.map((loc) => [loc.lat, loc.lng]));
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
      }
    }

    map.addLayer(mcg);
    clusterGroupRef.current = mcg;

    return () => {
      if (clusterGroupRef.current) {
        map.removeLayer(clusterGroupRef.current);
        clusterGroupRef.current = null;
      }
    };
  }, [locations, map, onSelectOpp]);

  return null;
}

// ─── Score Color Helper ────────────────────────────────────

function scoreColor(score: number | null | undefined): string {
  if (!score) return "#94a3b8";
  if (score >= 85) return "#22c55e";
  if (score >= 70) return "#8b5cf6";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

// ─── Map Component ─────────────────────────────────────────

export default function OpportunityMap({ locations, isLoading, onSelectOpp }: Props) {
  const defaultCenter: [number, number] = [39.8283, -98.5795];

  if (isLoading) {
    return (
      <div className="w-full h-[500px] rounded-xl overflow-hidden border border-border/40">
        <Skeleton className="w-full h-full" />
      </div>
    );
  }

  if (locations.length === 0) {
    return (
      <div className="w-full h-[500px] rounded-xl overflow-hidden border border-border/40 flex items-center justify-center bg-muted/10">
        <div className="text-center space-y-2">
          <MapPin className="h-8 w-8 text-muted-foreground/40 mx-auto" />
          <p className="text-sm text-muted-foreground">No location data available</p>
          <p className="text-xs text-muted-foreground/60">Opportunities need city/state/country info to appear on the map</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-[500px] rounded-xl overflow-hidden border border-border/40 relative">
      <MapContainer
        center={defaultCenter}
        zoom={4}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={true}
        className="z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MarkerClusterGroup
          locations={locations}
          onSelectOpp={onSelectOpp}
        />
      </MapContainer>
    </div>
  );
}
