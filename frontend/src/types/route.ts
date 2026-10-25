import type { ValidatedTrip, ApiValidationErrors } from "./trip"

/** A resolved endpoint coordinate from Mapbox geocoding. */
export type PlaceRef = {
  query: string
  resolvedName: string
  longitude: number
  latitude: number
}

/** Weather for one checkpoint at its arrival hour (Phase 5). */
export type CheckpointWeather = {
  checkpointId: string
  /** The checkpoint's own arrival timestamp (UTC). */
  arrivalISO: string
  /** The provider forecast hour matched (same as arrival hour when available). */
  matchedForecastISO: string | null
  /** "exact" when matched, "out_of_horizon" when hour not in provider response,
   *  "provider_error" on upstream failure. */
  timeMatch: "exact" | "out_of_horizon" | "provider_error"
  /** Wind speed in mph at 10m. None when unavailable. */
  windMph: number | null
  /** Rain rate in inches per hour. None when unavailable. */
  rainInPerHr: number | null
  /** Snowfall rate in inches per hour. None when unavailable. */
  snowfallInPerHr: number | null
  /** Provider identifier for attribution. */
  provider: "open-meteo"
  /** The raw provider time string (e.g., "2099-01-01T16:00"). */
  providerForecastISO: string | null
}

/** Per-route weather coverage metadata. */
export type RouteWeatherSummary = {
  routeId: string
  totalCheckpoints: number
  checkpointsWithWeather: number
  checkpointsUnavailable: number
  providerForecastStartISO: string | null
  providerForecastEndISO: string | null
}

/** Risk classification for one checkpoint (Phase 6). */
export type CheckpointRisk = {
  checkpointId: string
  arrivalISO: string
  riskLevel: "low" | "moderate" | "high" | "severe" | "no_travel" | "unknown"
  riskOrdinal: number // -1 unknown, 0 low, 1 moderate, 2 high, 3 severe, 4 no_travel
  /** Per-condition risk levels when available. */
  wind: "low" | "moderate" | "high" | "severe" | "no_travel" | null
  rain: "low" | "moderate" | "high" | "severe" | "no_travel" | null
  snow: "low" | "moderate" | "high" | "severe" | "no_travel" | null
  /** Source weather values for evidence display. */
  windMph: number | null
  rainInPerHr: number | null
  snowfallInPerHr: number | null
  /** Human-readable contributing factors. */
  factors: string[]
  /** Provider forecast hour matched. */
  matchedForecastISO: string | null
  /** Time match status. */
  timeMatch: "exact" | "out_of_horizon" | "provider_error" | "missing"
}

/** Route-level risk aggregation (Phase 6). */
export type RouteRiskSummary = {
  routeId: string
  totalCheckpoints: number
  checkpointsWithWeather: number
  checkpointsUnknown: number
  lowCount: number
  moderateCount: number
  highCount: number
  severeCount: number
  noTravelCount: number
  severeMiles: number
  highMiles: number
  avgRiskOrdinal: number | null
  worstCheckpoint: {
    checkpointId: string
    arrivalISO: string
    riskLevel: string
    factors: string[]
  } | null
  explanation: string
}

/** Heatmap grid point (Phase 9). */
export type HeatmapGridPoint = {
  longitude: number
  latitude: number
  hours: string[]
  windMph: (number | null)[]
  rainInPerHr: (number | null)[]
  snowfallInPerHr: (number | null)[]
}

/** Route heatmap data (Phase 9). */
export type RouteHeatmap = {
  routeId: string
  gridPoints: HeatmapGridPoint[]
  forecastStartISO: string
  forecastEndISO: string
  forecastHours: number
}

/** One sampled checkpoint along a route (Phase 4+5+6). */
export type RouteCheckpoint = {
  checkpointId: string
  routeId: string
  /** 1-based ordinal along the route; origin is 1. */
  sequence: number
  /** [longitude, latitude] along the provider geometry (interpolated when `interpolated`). */
  coordinates: [number, number]
  distanceFromStartMeters: number
  distanceFromStartMiles: number
  elapsedSeconds: number
  /** Estimated arrival = departure + provider duration × distance fraction (UTC). */
  arrivalISO: string
  /** true when the position falls between provider vertices (not an original vertex). */
  interpolated: boolean
  /** Hourly weather at the checkpoint's arrival hour (Phase 5). */
  weather?: CheckpointWeather
  /** Risk classification at this checkpoint (Phase 6). */
  checkpointRisk?: CheckpointRisk
}

/** Sampling metadata for one route — mirrors the backend checkpointSummary. */
export type RouteCheckpointSummary = {
  count: number
  requestedIntervalMiles: number
  effectiveIntervalMiles: number
  capped: boolean
  maxPerRoute: number
  geometryDistanceMeters: number
  geometryDistanceMiles: number
  providerDistanceMeters: number
  durationSeconds: number
  samplingMethod: string
  etaMethod: string
}

/** One normalized route exactly as the backend produced it. */
export type RouteOption = {
  routeId: string
  label: string
  geometry: { type: "LineString"; coordinates: [number, number][] } // [lng, lat]
  distanceMeters: number
  distanceMiles: number
  durationSeconds: number
  durationReadable: string
  arrivalISO: string
  providerRouteSummary: string
  checkpoints: RouteCheckpoint[]
  checkpointSummary: RouteCheckpointSummary
  /** Optional weather enrichment error if weather provider failed (Phase 5). */
  weatherError?: { code: string; message: string }
  /** Per-checkpoint risk classifications (Phase 6). */
  checkpointRisks?: CheckpointRisk[]
  /** Route-level risk summary (Phase 6). */
  riskSummary?: RouteRiskSummary
}

/** Route recommendation result (Phase 7). */
export type RouteRecommendation = {
  status: "recommended" | "no_safe_route_found" | "no_routes" | "scoring_unavailable"
  explanation: string
  recommendedRouteId: string | null
  rankedRouteIds: string[]
  routeExplanations: Record<string, string>
}

export type RouteGenerationOk = {
  routesAvailable: true
  trip: ValidatedTrip
  origin: PlaceRef
  destination: PlaceRef
  routesRequested: number
  routeCount: number
  threeRoutesReturned: boolean
  /** Present only when Mapbox returned fewer than three distinct routes. */
  warning: string | null
  duplicatesDropped: number
  routes: RouteOption[]
  /** Per-route weather coverage metadata (Phase 5). */
  weatherSummaries: RouteWeatherSummary[]
  /** Per-route risk summaries (Phase 6). */
  riskSummaries: RouteRiskSummary[]
  /** Route recommendation (Phase 7). */
  recommendation: RouteRecommendation
  /** Weather heatmaps (Phase 9). */
  heatmaps: RouteHeatmap[]
}

/** Structured safe provider failure (never carries credentials). */
export type RouteProviderError = {
  routesAvailable: false
  error: { code: string; message: string; stage?: string }
}

/** Field-level validation failure shape (Phase 2 contract reused). */
export type RouteInputError = {
  routesAvailable: false
  inputErrors: ApiValidationErrors
}
