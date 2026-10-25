/**
 * Phase 9 — corridor heatmap + forecast slider helpers.
 *
 * Pure, dependency-free functions used by ForecastSlider and MapViewport.
 * Indexed ranges (e.g. thresholds) MUST mirror backend `core/services/risk.py`
 * (spec §4–5) exactly — the backend remains the authoritative engine for
 * checkpoints/recommendations; this mirror is only for rendering gridded
 * samples deterministically in the browser. Any threshold change here must
 * be mirrored in risk.py and vice versa (kept in test fixtures on both sides).
 *
 * Timestamp contract: provider hours are UTC ISO strings WITHOUT a zone
 * suffix ("2099-01-01T16:00"), 60-minute buckets. Slider offset N (0…48)
 * indexes the per-point hourly arrays produced by the backend
 * (grid points store the first 49 provider buckets).
 */

import type {
  HeatmapGridPoint,
  RouteCheckpoint,
  RouteHeatmap,
} from "../types/route";

// Re-export grid types so slider/map components import heat-related types
// from one module (backend shapes remain in types/route.ts).
export type { HeatmapGridPoint, RouteHeatmap };

export type CorridorRiskLevel =
  | "no_travel"
  | "severe"
  | "high"
  | "moderate"
  | "low"
  | "unknown";

export type CorridorWeatherAtHour = {
  /** UTC ISO of the provider hour used (without zone suffix). */
  forecastISO: string;
  windMph: number | null;
  rainInPerHr: number | null;
  snowfallInPerHr: number | null;
};

/* ------------------------------------------------------------------ */
/* Risk classification (mirror of backend risk.py — see header note)   */
/* ------------------------------------------------------------------ */

export const WIND_MPH_NO_TRAVEL = 55;
export const WIND_MPH_SEVERE_MAX = 55; // 45 ≤ w < 55
export const WIND_MPH_HIGH_MAX = 45; // 35 ≤ w < 45
export const WIND_MPH_MODERATE_MAX = 35; // 25 ≤ w < 35
export const SEVERE_WIND_LOAD_LB = 30_000; // w ≥ 45 & load > this → no travel (55+ is always),
export const HIGH_WIND_LOAD_LB = 40_000; // 35 ≤ w < 45 & load > this → severe

export const RAIN_IN_PER_HR_SEVERE_MAX = 1.0; // 0.50 ≤ r ≤ 1.00
export const RAIN_IN_PER_HR_HIGH_MAX = 0.5;
export const RAIN_IN_PER_HR_MODERATE_MAX = 0.25;
export const RAIN_IN_PER_HR_MODERATE_MIN = 0.1;

export const SNOW_IN_PER_HR_SEVERE_MAX = 3.0; // 2.0 ≤ s ≤ 3.0
export const SNOW_IN_PER_HR_HIGH_MAX = 2.0;
export const SNOW_IN_PER_HR_MODERATE_MAX = 1.0;
export const SNOW_IN_PER_HR_MODERATE_MIN = 0.5;

const RISK_ORDINAL: Record<CorridorRiskLevel, number> = {
  unknown: -1,
  low: 0,
  moderate: 1,
  high: 2,
  severe: 3,
  no_travel: 4,
};

export function riskOrdinal(level: CorridorRiskLevel): number {
  return RISK_ORDINAL[level];
}

/** Wind band WITHOUT load rules: <25 low, <35 moderate, <45 high, <55 severe, ≥55 no travel. */
export function classifyWindBand(
  windMph: number | null | undefined,
): Exclude<CorridorRiskLevel, "unknown"> | null {
  if (windMph === null || windMph === undefined) return null;
  if (windMph < 25) return "low";
  if (windMph < 35) return "moderate";
  if (windMph < 45) return "high";
  if (windMph < 55) return "severe";
  return "no_travel";
}

/** Applies the spec §5 load rules to an already banded wind level. */
export function applyWindLoadRules(
  windBand: Exclude<CorridorRiskLevel, "unknown"> | null,
  loadWeightLb: number,
): Exclude<CorridorRiskLevel, "unknown"> | null {
  if (!windBand) return null;
  if (loadWeightLb > SEVERE_WIND_LOAD_LB && windBand === "severe") return "no_travel";
  if (loadWeightLb > HIGH_WIND_LOAD_LB && windBand === "high") return "severe";
  return windBand;
}

export function classifyRainBand(rainInPerHr: number | null | undefined) {
  if (rainInPerHr === null || rainInPerHr === undefined) return null;
  if (rainInPerHr < RAIN_IN_PER_HR_MODERATE_MIN) return "low";
  if (rainInPerHr < RAIN_IN_PER_HR_MODERATE_MAX) return "moderate";
  if (rainInPerHr < RAIN_IN_PER_HR_HIGH_MAX) return "high";
  if (rainInPerHr <= RAIN_IN_PER_HR_SEVERE_MAX) return "severe";
  return "no_travel";
}

export function classifySnowBand(snowInPerHr: number | null | undefined) {
  if (snowInPerHr === null || snowInPerHr === undefined) return null;
  if (snowInPerHr < SNOW_IN_PER_HR_MODERATE_MIN) return "low";
  if (snowInPerHr < SNOW_IN_PER_HR_MODERATE_MAX) return "moderate";
  if (snowInPerHr < SNOW_IN_PER_HR_HIGH_MAX) return "high";
  if (snowInPerHr <= SNOW_IN_PER_HR_SEVERE_MAX) return "severe";
  return "no_travel";
}

/**
 * Combined map-render risk level: max of known bands; No Travel precedence;
 * unknown fields never downgrade; all-unknown → "unknown".
 */
export function combineCorridorRisk(
  levels: Array<Exclude<CorridorRiskLevel, "unknown"> | null>,
): CorridorRiskLevel {
  const known = levels.filter((l): l is Exclude<CorridorRiskLevel, "unknown"> => l !== null);
  if (known.length === 0) return "unknown";
  if (known.includes("no_travel")) return "no_travel";
  return known.reduce((best, l) => (RISK_ORDINAL[l] > RISK_ORDINAL[best] ? l : best), "low" as Exclude<CorridorRiskLevel, "unknown">);
}

/** Full mirror of backend per-point classification for a single location/hour. */
export function classifyCorridorWeather(
  windMph: number | null,
  rainInPerHr: number | null,
  snowfallInPerHr: number | null,
  loadWeightLb: number,
): CorridorRiskLevel {
  return combineCorridorRisk([
    applyWindLoadRules(classifyWindBand(windMph), loadWeightLb),
    classifyRainBand(rainInPerHr),
    classifySnowBand(snowfallInPerHr),
  ]);
}

/* ------------------------------------------------------------------ */
/* Slider mapping (hour offset ↔ provider timestamp)                   */
/* ------------------------------------------------------------------ */

/** Parses provider hour strings ("2099-01-01T16:00" or full-ish ISO) strictly as UTC. */
function parseUtcHour(iso: string): Date | null {
  if (typeof iso !== "string") return null;
  const m = iso
    .trim()
    .match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?Z?)?$/);
  if (!m) return null;
  const y = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  const hh = m[4] !== undefined ? Number(m[4]) : 0;
  const mm = m[5] !== undefined ? Number(m[5]) : 0;
  const ss = m[6] !== undefined ? Number(m[6]) : 0;
  const d = new Date(Date.UTC(y, month - 1, day, hh, mm, ss));
  // Reject rollover inputs (e.g. "2099-02-30") that JS Date would silently shift.
  if (
    d.getUTCFullYear() !== y ||
    d.getUTCMonth() !== month - 1 ||
    d.getUTCDate() !== day
  ) {
    return null;
  }
  return d;
}

function formatUtcHour(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:00`;
}

/** Slider offset (integer 0…∞ hours) → provider-shaped UTC hour string. */
export function hourOffsetToISO(forecastStartISO: string, offsetHours: number): string {
  const start = parseUtcHour(forecastStartISO);
  if (!start || !Number.isFinite(offsetHours)) return "";
  const shifted = new Date(start.getTime() + Math.round(offsetHours) * 3_600_000);
  return formatUtcHour(shifted);
}

/** Provider hour string → integer offset from the start (null when unrepresentable/out of 0…48+). */
export function isoToHourOffset(
  forecastStartISO: string,
  targetISO: string,
  maxOffsetHours = 48,
): number | null {
  const start = parseUtcHour(forecastStartISO);
  const target = parseUtcHour(targetISO);
  if (!start || !target) return null;
  const diffHours = (target.getTime() - start.getTime()) / 3_600_000;
  const rounded = Math.round(diffHours);
  if (Math.abs(diffHours - rounded) > 1e-6) return null; // not on an hour boundary
  if (rounded < 0 || rounded > maxOffsetHours) return null;
  return rounded;
}

export const FORECAST_SLIDER_MAX_HOURS = 48;

/* ------------------------------------------------------------------ */
/* Grid point lookup                                                   */
/* ------------------------------------------------------------------ */

/** Weather for a grid point at hour offset (null when point has no series). */
export function gridWeatherAtHour(
  point: HeatmapGridPoint | undefined,
  offsetHours: number,
): CorridorWeatherAtHour | null {
  if (!point || !Array.isArray(point.hours) || point.hours.length === 0) return null;
  const index = Math.round(offsetHours);
  if (index < 0 || index >= point.hours.length) return null;
  return {
    forecastISO: point.hours[index],
    windMph: point.windMph[index] ?? null,
    rainInPerHr: point.rainInPerHr[index] ?? null,
    snowfallInPerHr: point.snowfallInPerHr[index] ?? null,
  };
}

/** Equirectangular squared distance (deterministic nearest-neighbor only). */
function equirectSqDistance(
  aLon: number,
  aLat: number,
  bLon: number,
  bLat: number,
): number {
  const dLat = bLat - aLat;
  const dLon = (bLon - aLon) * Math.cos(((aLat + bLat) / 2) * (Math.PI / 180));
  return dLat * dLat + dLon * dLon;
}

/** Nearest gridded sample to a checkpoint (disclosed approximation). */
export function nearestGridPoint(
  coordinates: readonly [number, number],
  gridPoints: readonly HeatmapGridPoint[],
): HeatmapGridPoint | null {
  if (!gridPoints.length) return null;
  const [lon, lat] = coordinates;
  let best: HeatmapGridPoint | null = null;
  let bestDist = Infinity;
  for (const p of gridPoints) {
    const d = equirectSqDistance(lon, lat, p.longitude, p.latitude);
    if (d < bestDist) {
      bestDist = d;
      best = p;
    }
  }
  return best;
}

/** Weather at a checkpoint's nearest grid point for the selected slider hour. */
export function checkpointWeatherAtHour(
  checkpoint: Pick<RouteCheckpoint, "coordinates">,
  gridPoints: readonly HeatmapGridPoint[],
  offsetHours: number,
): CorridorWeatherAtHour | null {
  const point = nearestGridPoint(checkpoint.coordinates, gridPoints);
  return gridWeatherAtHour(point ?? undefined, offsetHours);
}

/* ------------------------------------------------------------------ */
/* Heatmap GeoJSON + selection                                         */
/* ------------------------------------------------------------------ */

/** First heatmap with actual gridded series; undefined when none. */
export function pickRouteHeatmap(
  heatmaps: readonly RouteHeatmap[],
  routeId: string | null,
): RouteHeatmap | undefined {
  if (heatmaps.length === 0) return undefined;
  const hasData = (h: RouteHeatmap) => h.gridPoints.some((p) => p.hours.length > 0);
  const forRoute = routeId ? heatmaps.find((h) => h.routeId === routeId) : undefined;
  if (forRoute && hasData(forRoute)) return forRoute;
  return heatmaps.find(hasData);
}

export type HeatmapFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    riskLevel: CorridorRiskLevel;
    color: string;
    windMph: number | null;
    rainInPerHr: number | null;
    snowfallInPerHr: number | null;
    forecastISO: string;
  };
};

export type HeatmapFeatureCollection = {
  type: "FeatureCollection";
  features: HeatmapFeature[];
};

export const CORRIDOR_RISK_COLORS: Record<CorridorRiskLevel, string> = {
  no_travel: "#dc2626",
  severe: "#ef4444",
  high: "#f97316",
  moderate: "#f59e0b",
  low: "#22c55e",
  unknown: "#64748b",
};

/** GeoJSON for the corridor circles at the selected hour (empty FC when unavailable). */
export function buildHeatmapGeoJSON(
  heatmap: RouteHeatmap | undefined,
  offsetHours: number,
  loadWeightLb: number,
): HeatmapFeatureCollection {
  const features: HeatmapFeature[] = [];
  if (heatmap) {
    for (const point of heatmap.gridPoints) {
      const weather = gridWeatherAtHour(point, offsetHours);
      const level = weather
        ? classifyCorridorWeather(
            weather.windMph,
            weather.rainInPerHr,
            weather.snowfallInPerHr,
            loadWeightLb,
          )
        : "unknown";
      features.push({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [point.longitude, point.latitude],
        },
        properties: {
          riskLevel: level,
          color: CORRIDOR_RISK_COLORS[level],
          windMph: weather?.windMph ?? null,
          rainInPerHr: weather?.rainInPerHr ?? null,
          snowfallInPerHr: weather?.snowfallInPerHr ?? null,
          forecastISO: weather?.forecastISO ?? "",
        },
      });
    }
  }
  return { type: "FeatureCollection", features };
}

/* ------------------------------------------------------------------ */
/* Coalesced draw (slider drag → at most one map update per frame)     */
/* ------------------------------------------------------------------ */

/**
 * Frame-coalesced, latest-wins draw queue: every `enqueue` call schedules
 * ONE step callback (requestAnimationFrame by default); at most one step is
 * ever in flight, and the LAST enqueued thunk wins — intermediate drags are
 * simply skipped. Immune to React async effect flushing order (a plain
 * trailing timer lost the newest value in live verification; rAF
 * coalescing fractionates exactly one draw per frame instead).
 *
 * Visibility-aware scheduling: BROWSER COALESCED draws only make animation
 * smooth — they must never hold correctness hostage to rAF, which Chrome
 * PAUSES entirely in hidden/occluded tabs (live verification caught the
 * latest slider draw never landing while `document.hidden`). So when the
 * document is visible we schedule with requestAnimationFrame (fluid dragging);
 * when it is hidden — or rAF is unavailable (SSR/tests) — we fall back to a
 * 16 ms setTimeout, which Chrome throttles but still eventually fires, so the
 * newest draw always lands (≤ ~1 s while hidden).
 *
 * `timer` is injectable so tests can drive frames deterministically; an
 * injected timer overrides all global scheduling (unit tests decide the mode).
 */
export function createCoalescedDraw(
  timer: { enqueue: (step: () => void) => unknown; clear: (id: unknown) => void } | null = null,
) {
  // setTimeout fires even in hidden tabs (Chrome throttles to ≥ 1 s but
  // never drops it entirely) — the eventual-consistency path.
  let pendingThunk: (() => void) | null = null;
  let cancelCurrent: (() => void) | null = null;

  const rafAvailable = typeof requestAnimationFrame === "function";

  // `step` runs exactly one batch: it clears the in-flight handle FIRST,
  // so a callback scheduled during the draw re-arms cleanly.
  const step = () => {
    cancelCurrent = null;
    const thunk = pendingThunk;
    pendingThunk = null;
    thunk?.();
  };

  return {
    /** Queue the latest draw thunk; coalesces everything queued ≤ 1 frame. */
    enqueue(thunk: () => void): void {
      pendingThunk = thunk;
      if (cancelCurrent === null) {
        // Decide PER ENQUEUE: visibility can flip any time between factory
        // creation and the next draw (an instance made while visible must
        // still schedule with a timer once the tab hides).
        let id: unknown;
        let cancelLocal: (handle: unknown) => void;
        if (timer) {
          id = timer.enqueue(step);
          cancelLocal = (h) => timer.clear(h);
        } else if (
          rafAvailable &&
          (typeof document === "undefined" || document.visibilityState === "visible")
        ) {
          id = requestAnimationFrame(step);
          cancelLocal = (h) => cancelAnimationFrame(h as number);
        } else {
          id = setTimeout(step, 16);
          cancelLocal = (h) => clearTimeout(h as ReturnType<typeof setTimeout>);
        }
        cancelCurrent = () => cancelLocal(id);
      }
    },
    /** Drop any queued draw (unmount / route reset). */
    cancel(): void {
      if (cancelCurrent !== null) cancelCurrent();
      cancelCurrent = null;
      pendingThunk = null;
    },
  };
}
