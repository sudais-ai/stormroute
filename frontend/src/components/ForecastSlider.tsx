import { useMemo } from "react"
import { FORECAST_SLIDER_MAX_HOURS, hourOffsetToISO } from "../lib/heatmap"
import type { RouteHeatmap } from "../types/route"

function stamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

export interface ForecastSliderProps {
  heatmaps: RouteHeatmap[]
  selectedRouteId: string | null
  value: number
  onChange: (offset: number) => void
  disabled?: boolean
}

/**
 * Phase 9 forecast scrubber: 0–48 h after the provider's forecast start.
 * The value is an hour OFFSET (kept stable for heatmap/marker logic), and the
 * label renders the resulting wall-clock time in the viewer's locale.
 */
export function ForecastSlider({ heatmaps, selectedRouteId, value, onChange, disabled = false }: ForecastSliderProps) {
  const startISO = useMemo(() => {
    if (heatmaps.length === 0) return null
    const forSelection = heatmaps.find((item) => item.routeId === selectedRouteId) ?? heatmaps[0]
    return forSelection.forecastStartISO
  }, [heatmaps, selectedRouteId])

  if (disabled || !startISO) {
    return (
      <section aria-label="Weather forecast timeline" className="rounded-card border border-border bg-panel p-4">
        <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-2">Forecast hour</h3>
        <p className="mt-1.5 text-sm text-ink-3" data-testid="forecast-slider-unavailable">
          Detailed forecast samples are not available for this corridor right now. Checkpoint arrival-hour
          weather and risk are still shown on the map and route cards.
        </p>
      </section>
    )
  }

  const selectedISO = hourOffsetToISO(startISO, value)

  return (
    <section aria-label="Weather forecast timeline" className="rounded-card border border-border bg-panel p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-2">Forecast hour</h3>
        <p className="font-mono text-[13px] text-ink" data-testid="forecast-label">
          {stamp(selectedISO)}
          <span className="badge ml-1.5 font-mono text-[12px] text-accent">+{value} h from forecast start</span>
        </p>
      </div>

      {/* Exactly ONE small-print caption under the slider; the how-many-hours
          meaning travels on the input's aria-label (no visible label line). */}
      <input
        id="forecast-hour-slider"
        type="range"
        min={0}
        max={FORECAST_SLIDER_MAX_HOURS}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="slider mt-1.5 w-full"
        data-testid="forecast-slider"
        aria-label="How many hours after the provider forecast starts"
      />
      <div className="mt-1 flex justify-between font-mono text-[11px] text-ink-3" data-testid="forecast-ticks">
        {[0, 12, 24, 36, 48].map((hour) => (
          <span key={hour}>+{hour} h</span>
        ))}
      </div>
      <p className="mt-2 text-[11px] text-ink-3">
        You choose the forecast hour with this slider.
      </p>
    </section>
  )
}
