import type { RouteGenerationOk, RouteOption, RouteRiskSummary } from "../types/route"

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

/** Route-level rollup: the most urgent level present in any checkpoint. */
function overallRisk(summary: RouteRiskSummary | undefined): string {
  if (!summary) return "unknown"
  if (summary.noTravelCount > 0) return "no_travel"
  if (summary.severeCount > 0) return "severe"
  if (summary.highCount > 0) return "high"
  if (summary.moderateCount > 0) return "moderate"
  if (summary.lowCount > 0) return "low"
  return "unknown"
}

const numberFmt0 = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 })
const numberFmt1 = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })

function milesFmt1(miles: number): string {
  return `${numberFmt1.format(miles)} mi`
}

function localStamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

/** "15:42" style local clock for the inline arrival note. */
function localClock(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false })
}

function conditionMph(mph: number | null): string {
  return mph === null ? "n/a" : `${numberFmt1.format(mph)} mph`
}

function conditionRate(inPerHour: number | null): string {
  return inPerHour === null ? "n/a" : `${inPerHour.toFixed(3)} in/hr`
}

/** First sentence of an API explanation; drops any banned ranking phrasing. */
function firstSentence(text: string | undefined): string | null {
  if (!text) return null
  // Sentence end = terminator followed by a capital letter (or end of string),
  // so decimal numbers like "0.0" never truncate the line mid-phrase.
  const match = text.match(/^(.+?[.!?])(?=\s+[A-Z]|$)/)
  const first = match ? match[1] : text
  return (
    first
      .replace(/top pick by combined ranking\.?/gi, "")
      .replace(/combined ranking\.?/gi, "")
      .trim() || null
  )
}

function RouteCard({
  route,
  riskSummary,
  recommended,
  rank,
  reason,
}: {
  route: RouteOption
  riskSummary: RouteRiskSummary | undefined
  recommended: boolean
  rank: number | null
  reason: string | null
}) {
  const summary = route.checkpointSummary
  const geometryTo = Math.round(summary.geometryDistanceMiles / 1000) * 1000
  const overall = overallRisk(riskSummary)

  return (
    <article className="card-raised p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 className="text-base font-semibold text-ink">{route.label}</h3>
        {rank !== null ? (
          recommended ? (
            <span className="badge border-signal bg-signal/10 font-mono text-[11px] font-medium text-signal">
              Rank #{rank}
            </span>
          ) : (
            <span className="font-mono text-[11px] text-ink-3">Rank #{rank}</span>
          )
        ) : null}
      </div>

      {reason ? <p className="mt-1 text-[13px] text-ink-2">{reason}</p> : null}

      <ul className="mt-3 grid grid-cols-1 gap-3 border-t border-border pt-3 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-border">
        <li className="sm:pr-3">
          <span className="block text-[11px] text-ink-3">Distance</span>
          <span className="text-sm font-medium text-ink">{milesFmt1(route.distanceMiles)}</span>
        </li>
        <li className="sm:px-3">
          <span className="block text-[11px] text-ink-3">Driving time</span>
          <span className="text-sm font-medium text-ink">{route.durationReadable}</span>
          {" "}
          <span className="font-mono text-[12px] text-ink-2">(arr {localClock(route.arrivalISO)})</span>
        </li>
        <li className="sm:pl-3">
          <span className="block text-[11px] text-ink-3">Roads</span>
          <span className="font-mono text-[12px] text-ink-2">via {route.providerRouteSummary}</span>
        </li>
      </ul>

      <p className="mt-2">
        <span className={`badge risk-${overall} text-[11px] font-medium`}>{riskLabel(overall)}</span>
      </p>

      <p className="mt-3 text-xs text-ink-2">
        {summary.count} at {summary.effectiveIntervalMiles} mi spacing
        {summary.capped
          ? ` — widened from ${summary.requestedIntervalMiles} mi to stay within ${summary.maxPerRoute} per route`
          : ""}{" "}
        · sampled along the provider geometry from 0 mi to {numberFmt0.format(geometryTo)} mi
      </p>

      <details className="group mt-3 rounded-control border border-border px-3 py-2">
        <summary className="flex cursor-pointer list-none items-center gap-2 text-[13px] font-medium text-ink-2 marker:content-none">
          Checkpoint weather
          <span className="font-mono text-[11px] text-ink-3">({route.checkpoints.length})</span>
        </summary>
        <ul className="mt-2 space-y-1.5 font-mono text-[12px] text-ink-2">
          {route.checkpoints.map((checkpoint) => {
            const risk = checkpoint.checkpointRisk
            return (
              <li key={checkpoint.checkpointId} className="flex flex-wrap items-baseline gap-x-2">
                <span className="text-[11px] text-ink-3">#{checkpoint.sequence}</span>
                <span>{localStamp(checkpoint.arrivalISO)}</span>
                <span className={`badge risk-${risk ? risk.riskLevel : "unknown"} text-[10px] font-medium`}>
                  {risk ? riskLabel(risk.riskLevel) : "No data"}
                </span>
                <span>
                  wind {conditionMph(checkpoint.weather?.windMph ?? risk?.windMph ?? null)}
                  {" · "}
                  rain {conditionRate(checkpoint.weather?.rainInPerHr ?? risk?.rainInPerHr ?? null)}
                  {" · "}
                  snow {conditionRate(checkpoint.weather?.snowfallInPerHr ?? risk?.snowfallInPerHr ?? null)}
                  {" · "}
                  {milesFmt1(checkpoint.distanceFromStartMiles)} from start
                </span>
              </li>
            )
          })}
        </ul>
        {riskSummary ? (
          <p className="mt-2 font-mono text-[11px] text-ink-3">
            Checkpoints marked up: {riskSummary.totalCheckpoints} · with weather data: {riskSummary.checkpointsWithWeather} ·
            high-risk miles ≈ {numberFmt1.format(riskSummary.highMiles)} · severe-risk miles ≈{" "}
            {numberFmt1.format(riskSummary.severeMiles)}. {riskSummary.worstCheckpoint ? `Most concerning stop: #${riskSummary.worstCheckpoint.checkpointId} (${riskSummary.worstCheckpoint.riskLevel}).` : ""}
          </p>
        ) : null}
      </details>
    </article>
  )
}

export function RouteOptions({ response }: { response: RouteGenerationOk }) {
  const { routes, riskSummaries, recommendation, warning, duplicatesDropped } = response

  const summaryFor = (routeId: string): RouteRiskSummary | undefined =>
    riskSummaries.find((item) => item.routeId === routeId)

  const recommendedId = recommendation.recommendedRouteId
  const rankedRouteIds = recommendation.rankedRouteIds

  return (
    <section aria-label="Live route options" className="mt-6">
      {/* The mono input-echo line lives once, in TripForm's results band above this heading. */}
      <h2 className="text-[16px] font-semibold text-ink">Route options</h2>

      {warning ? (
        <p role="alert" className="mt-2 rounded-control border border-signal/40 bg-signal/10 p-3 text-[13px] text-ink">
          {warning}
        </p>
      ) : null}

      {duplicatesDropped > 0 ? (
        <p className="mt-2 text-[13px] text-ink-3">
          {duplicatesDropped} duplicate route{duplicatesDropped === 1 ? "" : "s"} from the provider {duplicatesDropped === 1 ? "was" : "were"} filtered out.
        </p>
      ) : null}

      <ol aria-label="route options" className="mt-3 space-y-3">
        {routes.map((route) => {
          const rankIndex = rankedRouteIds.indexOf(route.routeId)
          const reason = firstSentence(recommendation.routeExplanations?.[route.routeId])
          return (
            <li key={route.routeId}>
              <RouteCard
                route={route}
                riskSummary={summaryFor(route.routeId)}
                recommended={recommendedId === route.routeId}
                rank={rankIndex >= 0 ? rankIndex + 1 : null}
                reason={reason}
              />
            </li>
          )
        })}
      </ol>

      <details className="mt-4 rounded-control border border-border px-3 py-2">
        <summary className="cursor-pointer list-none text-[13px] font-medium text-ink-2">
          Estimate methods
        </summary>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-2">
          Risk values are model estimates for planning, not real-time road conditions. Weather data from Open-Meteo is matched to the exact
          forecast hour at each checkpoint. Risk classification uses assessment-mandated thresholds for wind, rain and snow by hour.
          Driving-time values are a constant-average-speed estimate, not traffic- or weather-adjusted. Checkpoint distances are
          great-circle (haversine) samples along the provider geometry and may differ slightly from the provider&apos;s road distance.
        </p>
      </details>
    </section>
  )
}
