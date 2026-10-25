import { useCallback, useEffect, useRef, useState } from "react"
import * as maplibregl from "maplibre-gl"
import { setWorkerUrl } from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url"
setWorkerUrl(maplibreWorkerUrl)

import type { RouteCheckpoint, RouteHeatmap, RouteOption, RouteRiskSummary } from "../types/route"
import type { RiskLevel } from "../lib/riskColors"
import {
  buildHeatmapGeoJSON,
  checkpointWeatherAtHour,
  classifyCorridorWeather,
  CORRIDOR_RISK_COLORS,
  createCoalescedDraw,
  pickRouteHeatmap,
} from "../lib/heatmap"
import { RISK_HEX, riskDotClass } from "../lib/riskColors"

const HEATMAP_SOURCE_ID = "corridor-heatmap"

/** Marker/legend fills come only from the test-pinned risk color module (mirrors CORRIDOR_RISK_COLORS). */

/** Legend rows: F12 vocabulary words; unknown reads "Unknown" in the map
 *  legend (route cards keep the closed-state "No data" chip). */
const LEGEND: Array<{ level: RiskLevel; label: string }> = [
  { level: "low", label: "Low" },
  { level: "moderate", label: "Moderate" },
  { level: "high", label: "High" },
  { level: "severe", label: "Severe" },
  { level: "no_travel", label: "No Travel" },
  { level: "unknown", label: "Unknown" },
]

const ROUTE_LINE_SELECTED = "#2563EB" // CSS accent token (light theme)
const ROUTE_LINE_UNSELECTED = "#D1D5DB" // muted steel (border-strong token, light theme)

/**
 * Style mutations (addSource/addLayer/removeLayer) are unsafe while a fallback
 * style.json is still loading: run `draw` live when the style is ready, else
 * once its data lands. `isLive` keeps an effect that re-ran (or unmounted)
 * from drawing through a stale queue; one retry max — the next dep change
 * redraws anyway.
 */
function drawWhenStyleReady(
  map: maplibregl.Map,
  draw: () => void,
  isLive: () => boolean,
  retried = false,
) {
  if (map.isStyleLoaded()) {
    draw()
    return
  }
  if (retried) return
  map.once("styledata", () => {
    if (isLive()) drawWhenStyleReady(map, draw, isLive, true)
  })
}

function riskLabel(risk: string): string {
  switch (risk) {
    case "no_travel":
      return "No Travel"
    case "severe":
      return "Severe"
    case "high":
      return "High"
    case "moderate":
      return "Moderate"
    case "low":
      return "Low"
    default:
      return "Unknown"
  }
}

function stamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

export interface MapViewportProps {
  routes: RouteOption[]
  riskSummaries: RouteRiskSummary[]
  selectedRouteId: string | null
  heatmaps: RouteHeatmap[]
  selectedHourOffset: number
  loadWeightLb: number
}

export function MapViewport({
  routes,
  selectedRouteId,
  heatmaps,
  selectedHourOffset,
  loadWeightLb,
}: MapViewportProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const routeLayerIdsRef = useRef<string[]>([])
  const markerRefs = useRef<Map<string, maplibregl.Marker>>(new Map())
  const markerMetaRef = useRef<Map<string, { route: RouteOption; checkpoint: RouteCheckpoint }>>(new Map())
  const drawQueue = useRef(createCoalescedDraw()).current
  const [mapLoaded, setMapLoaded] = useState(false)
  // Bumped when the demotiles style fallback fires — it wipes sources/layers,
  // so both draw effects must re-run and redraw after the new style is live.
  const [styleRev, setStyleRev] = useState(0)
  const [hovered, setHovered] = useState<{ checkpoint: RouteCheckpoint; route: RouteOption } | null>(null)
  const corridorHeatmap = pickRouteHeatmap(heatmaps, selectedRouteId)

  const applyHourToMarkers = useCallback(() => {
    markerMetaRef.current.forEach((meta, key) => {
      const marker = markerRefs.current.get(key)
      if (!marker) return
      const el = marker.getElement()
      const perRouteHeatmap = heatmaps.find(
        (item) => item.routeId === meta.route.routeId && item.gridPoints.some((point) => point.hours.length > 0),
      )
      if (!perRouteHeatmap) {
        const level = meta.checkpoint.checkpointRisk?.riskLevel ?? "unknown"
        el.style.backgroundColor = RISK_HEX[level]
        el.title = `${meta.checkpoint.sequence}. ${riskLabel(level)}`
        return
      }
      const weather = checkpointWeatherAtHour(meta.checkpoint, perRouteHeatmap.gridPoints, selectedHourOffset)
      const level = weather
        ? classifyCorridorWeather(weather.windMph, weather.rainInPerHr, weather.snowfallInPerHr, loadWeightLb)
        : "unknown"
      el.style.backgroundColor = CORRIDOR_RISK_COLORS[level]
      const when = weather ? weather.forecastISO : "unavailable"
      el.title = `${meta.checkpoint.sequence}. ${riskLabel(level)} — forecast ${when}`
    })
  }, [heatmaps, loadWeightLb, selectedHourOffset])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: containerRef.current,
      // Carto Positron light basemap (light theme).
      // fallback if blocked: https://demotiles.maplibre.org/style.json
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [-98.5795, 39.8283],
      zoom: 4,
      attributionControl: false,
    })
    mapRef.current = map
    ;(window as unknown as { __stormrouteMap?: maplibregl.Map }).__stormrouteMap = map

    map.on("load", () => setMapLoaded(true))
    let triedStyleFallback = false
    map.on("error", (event) => {
      const message = (event as { error?: { message?: string } } | undefined)?.error?.message ?? ""
      if (triedStyleFallback || !/style/i.test(message)) return
      triedStyleFallback = true
      map.setStyle("https://demotiles.maplibre.org/style.json")
      // Right after setStyle: bump the revision so both draw effects re-run.
      // They defer style mutation until the demotiles style data lands, then
      // redraw routes + heatmap idempotently on the fallback basemap.
      setStyleRev((revision) => revision + 1)
    })
    return () => {
      markerRefs.current.forEach((marker) => marker.remove())
      markerRefs.current.clear()
      map.remove()
      mapRef.current = null
      delete (window as unknown as { __stormrouteMap?: maplibregl.Map }).__stormrouteMap
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!mapLoaded || !map) return
    // Candidate draw: runs live when the style is loaded, or once the fallback
    // style's data lands (styleRev re-runs this effect after setStyle). All
    // add/remove steps below are idempotent, so both paths redraw cleanly.
    const draw = () => {
      if (mapRef.current !== map) return // unmounted since scheduled
      // Reset previous layers/markers, then redraw everything for the current data.
      for (const id of routeLayerIdsRef.current) {
        if (map.getLayer(`${id}-line-layer`)) map.removeLayer(`${id}-line-layer`)
        if (map.getSource(`${id}-line-src`)) map.removeSource(`${id}-line-src`)
      }
      routeLayerIdsRef.current = []
      markerRefs.current.forEach((marker) => marker.remove())
      markerRefs.current.clear()
      markerMetaRef.current.clear()

      if (corridorHeatmap && !map.getSource(HEATMAP_SOURCE_ID)) {
        map.addSource(HEATMAP_SOURCE_ID, { type: "geojson", data: buildHeatmapGeoJSON(corridorHeatmap, selectedHourOffset, loadWeightLb) as never })
        map.addLayer({
          id: HEATMAP_SOURCE_ID,
          type: "circle",
          source: HEATMAP_SOURCE_ID,
          paint: {
            "circle-color": ["get", "color"],
            "circle-radius": ["match", ["get", "riskLevel"], "no_travel", 9, "severe", 8, "high", 7, "moderate", 6.5, "low", 6, 5.5],
            "circle-opacity": 0.3,
            "circle-stroke-width": 1,
            "circle-stroke-color": "#FAFAF9",
            "circle-stroke-opacity": 0.4,
          },
        })
      }

      routes.forEach((route) => {
        const sourceId = `${route.routeId}-line-src`
        const layerId = `${route.routeId}-line-layer`

        // Belt-and-braces idempotency: a mid-flight style fallback can leave a
        // source behind the tracking ref doesn't know about — drop any
        // leftovers before re-adding so addSource can never collide.
        if (map.getLayer(layerId)) map.removeLayer(layerId)
        if (map.getSource(sourceId)) map.removeSource(sourceId)

        map.addSource(sourceId, { type: "geojson", data: { type: "Feature", geometry: route.geometry, properties: {} } })
        map.addLayer({
          id: layerId,
          type: "line",
          source: sourceId,
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": selectedRouteId === route.routeId ? ROUTE_LINE_SELECTED : ROUTE_LINE_UNSELECTED,
            "line-width": selectedRouteId === route.routeId ? 4 : 2,
            "line-opacity": selectedRouteId === route.routeId ? 1 : 0.9,
          },
        })
        routeLayerIdsRef.current.push(route.routeId)

        route.checkpoints.forEach((checkpoint) => {
          const risk = checkpoint.checkpointRisk
          const level = risk?.riskLevel ?? "unknown"
          const el = document.createElement("div")
          const isNoTravel = level === "no_travel"
          el.className = "checkpoint-marker"
          el.style.width = isNoTravel ? "14px" : "10px"
          el.style.height = isNoTravel ? "14px" : "10px"
          el.style.borderRadius = "50%"
          el.style.backgroundColor = RISK_HEX[level]
          // border-strong token (#3D4654): matches the border system, no shadow on dark.
          el.style.border = "2px solid #D1D5DB"
          el.style.cursor = "pointer"
          el.style.transition = "transform 120ms ease"
          el.addEventListener("mouseenter", () => {
            el.style.transform = "scale(1.6)"
            setHovered({ checkpoint, route })
          })
          el.addEventListener("mouseleave", () => {
            el.style.transform = "scale(1)"
            setHovered(null)
          })
          el.title = `${checkpoint.sequence}. ${riskLabel(level)}`
          const marker = new maplibregl.Marker({ element: el, anchor: "center" })
            .setLngLat(checkpoint.coordinates)
            .addTo(map)
          const key = `${route.routeId}-${checkpoint.checkpointId}`
          markerRefs.current.set(key, marker)
          markerMetaRef.current.set(key, { route, checkpoint })
        })
      })

      applyHourToMarkers()
    }
    drawWhenStyleReady(map, draw, () => mapRef.current === map)
  }, [routes, selectedRouteId, mapLoaded, corridorHeatmap, selectedHourOffset, loadWeightLb, applyHourToMarkers, styleRev])

  useEffect(() => {
    const map = mapRef.current
    if (!mapLoaded || !map) return
    const enqueuePush = () => {
      const featureCollection = buildHeatmapGeoJSON(corridorHeatmap, selectedHourOffset, loadWeightLb)
      drawQueue.enqueue(() => {
        const source = map.getSource(HEATMAP_SOURCE_ID)
        if (source) (source as maplibregl.GeoJSONSource).setData(featureCollection as never)
        applyHourToMarkers()
      })
    }
    drawWhenStyleReady(map, enqueuePush, () => mapRef.current === map)
    return () => drawQueue.cancel()
  }, [mapLoaded, corridorHeatmap, selectedHourOffset, loadWeightLb, drawQueue, applyHourToMarkers, styleRev])

  // One stable container node across renders: swapping the container div on
  // `mapLoaded` detaches the live MapLibre DOM (canvas keeps rendering in an
  // off-screen node), so the loading state is an overlay, not a tree swap.
  return (
    <div className="relative">
      <div ref={containerRef} data-testid="map-viewport" className="h-[440px] w-full rounded-card border border-border" />

      {!mapLoaded ? (
        <div className="absolute inset-0 grid place-items-center rounded-card border border-border bg-panel text-sm text-ink-2">
          Loading the map…
        </div>
      ) : null}

      <div className="pointer-events-none absolute right-3 top-3 flex max-w-[13rem] flex-col items-start">
        <div className="card-raised p-3">
          <p className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-ink-2">Risk at selected hour</p>
          <ul className="space-y-1">
            {LEGEND.map((entry) => (
              <li key={entry.level} className="flex items-center gap-2 text-[12px] text-ink-2">
                <span aria-hidden="true" className={riskDotClass(entry.level)} />
                {entry.label}
              </li>
            ))}
          </ul>
          <p className="mt-2 font-mono text-[10px] text-ink-3">One reading every 11 km.</p>
          <p className="mt-1.5 text-[11px] text-ink-3">Colors follow the hour you choose on the slider.</p>
        </div>
        {/* Sits below the legend card, outside it: the card is display-only, the
            hint is plain explanation copy for a first-time user. */}
        <p className="mt-2 text-[11px] leading-snug text-ink-3">
          Every dot is one stop on your route. Its color is the weather risk when your truck gets there.
        </p>
      </div>

      {hovered ? (
        <div className="card-raised absolute bottom-3 left-3 z-10 max-w-xs p-3 text-xs">
          <p className="font-semibold text-ink">
            Checkpoint #{hovered.checkpoint.sequence} · {hovered.route.label}
          </p>
          <p className="mt-1 font-mono text-[11px] text-ink-3">
            At +{selectedHourOffset} h · Arrives {stamp(hovered.checkpoint.arrivalISO)}
          </p>
          {hovered.checkpoint.checkpointRisk ? (
            <p className="mt-1 flex flex-wrap items-center gap-2 text-ink-2">
              <span className={`badge risk-${hovered.checkpoint.checkpointRisk.riskLevel} text-[10px] font-medium`}>
                {riskLabel(hovered.checkpoint.checkpointRisk.riskLevel)}
              </span>
              <span>
                wind {hovered.checkpoint.checkpointRisk.windMph === null ? "n/a" : `${hovered.checkpoint.checkpointRisk.windMph.toFixed(1)} mph`}
              </span>
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
