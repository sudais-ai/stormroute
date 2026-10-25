import { useState } from "react"
import { TripForm } from "./components/TripForm"
import { MapViewport } from "./components/MapViewport"
import { ForecastSlider } from "./components/ForecastSlider"
import { ServiceStatusCard, useBackendHealth } from "./components/ServiceStatusCard"
import type { RouteGenerationOk } from "./types/route"

export default function App() {
  const { status, info } = useBackendHealth()
  const [routeData, setRouteData] = useState<RouteGenerationOk | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [forecastHourOffset, setForecastHourOffset] = useState(0)

  function handleRouteData(response: RouteGenerationOk) {
    if (!response.routeCount) {
      setRouteData(null)
      setSelectedRouteId(null)
      setForecastHourOffset(0)
      return
    }
    setRouteData(response)
    setForecastHourOffset(0)
    setSelectedRouteId(response.recommendation.recommendedRouteId ?? response.routes[0]?.routeId ?? null)
  }

  const selectedRoute = routeData?.routes.find((route) => route.routeId === selectedRouteId) ?? null
  const healthCard = (
    <ServiceStatusCard
      title="Backend API"
      serviceType="Python · Django + DRF"
      status={status}
      details={
        status === "checking"
          ? "Calling /api/health/…"
          : info
            ? `/api/health/ answered: JSON ${info.version}`
            : "No response from /api/health/."
      }
    />
  )

  return (
    <div className="min-h-screen bg-bg">
      <a href="#main-content" className="skip-link sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-accent focus:px-3 focus:py-1.5 focus:text-sm focus:font-semibold focus:text-bg">
        Skip to main content
      </a>

      <header className="border-b border-border bg-panel">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3.5">
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="h-7 w-7 rounded-control border-4 border-accent"
              style={{
                backgroundImage: "repeating-linear-gradient(45deg, var(--color-accent) 0 4px, #0B0E14 4px 6px)",
                backgroundClip: "content-box",
              }}
            />
            <div>
              <p className="text-[16px] font-semibold tracking-tight text-ink">StormRoute</p>
              <p className="text-[12px] text-ink-2">Road-weather routing</p>
            </div>
          </div>
          {healthCard}
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-7xl px-6 py-8">
        <section className="mb-8 max-w-3xl">
          <h1 className="text-2xl font-semibold leading-tight text-ink sm:text-3xl">
            Plan a trip, see the weather before the wheels roll
          </h1>
          <p className="mt-2 text-[14px] text-ink-2">
            Set a trip and a load; route options below show weather risk at the exact forecast hour.
          </p>
        </section>

        <div className="grid gap-6 lg:grid-cols-[minmax(380px,5fr)_minmax(0,7fr)] lg:items-start">
          <TripForm onRouteData={handleRouteData} />

          {/* Mobile stacking (Tailwind order utilities): form-card → map sidebar → results band.
              At lg this is a no-op: the explicit col-start-2/row-start-1 placement wins. */}
          <div className="order-1 space-y-4 lg:col-start-2 lg:row-start-1">
            {routeData ? (
              <>
                <MapViewport
                  routes={routeData.routes}
                  riskSummaries={routeData.riskSummaries}
                  selectedRouteId={selectedRouteId}
                  heatmaps={routeData.heatmaps}
                  selectedHourOffset={forecastHourOffset}
                  loadWeightLb={routeData.trip.loadWeightLb}
                />
                <ForecastSlider
                  heatmaps={routeData.heatmaps}
                  selectedRouteId={selectedRouteId}
                  value={forecastHourOffset}
                  onChange={setForecastHourOffset}
                  disabled={routeData.heatmaps.length === 0}
                />
                {routeData.routeCount > 1 && selectedRoute ? (
                  <div className="flex flex-wrap items-center gap-2">
                    {routeData.routes.map((route) => {
                      const active = route.routeId === selectedRouteId
                      const isRecommended = route.routeId === routeData.recommendation.recommendedRouteId
                      const chipClass = active
                        ? "chip-pill" + (isRecommended ? " badge" : "") + " border-signal bg-signal/10 text-ink"
                        : isRecommended
                          ? "chip-pill badge border-accent text-accent"
                          : "chip-pill border-border text-ink-2"
                      return (
                        <button
                          key={route.routeId}
                          type="button"
                          aria-pressed={active}
                          onClick={() => setSelectedRouteId(route.routeId)}
                          className={chipClass}
                        >
                          {route.label}
                          {" "}
                          <span className="font-mono">{Math.round(route.distanceMiles)} mi</span>
                        </button>
                      )
                    })}
                  </div>
                ) : null}
              </>
            ) : (
              <div className="card-raised p-8 text-center">
                <p className="text-base font-semibold text-ink">Your trip map appears here</p>
                <p className="mt-2 text-sm text-ink-2">Run a trip to see routes, checkpoints, and the sliding corridor forecast.</p>
                <ul className="mx-auto mt-5 max-w-sm space-y-2 text-left text-sm text-ink-2">
                  <li>Confirm origin and destination are real city names.</li>
                  <li>Widen the checkpoint radius to 50 miles to find more options.</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="mt-10 border-t border-border bg-panel px-6 py-5 text-center">
        <p className="text-[13px] text-ink-3">
          Risk route-mile values are model estimates for planning, not real-time road conditions. Weather: Open-Meteo ·
          Basemap: Carto dark-matter · Routing: Mapbox.
        </p>
      </footer>
    </div>
  )
}
