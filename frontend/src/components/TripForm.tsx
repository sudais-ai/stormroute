import { useState, type FormEvent } from "react"
import { CHECKPOINT_INTERVAL_OPTIONS } from "../types/trip"
import type { CheckpointInterval, TripFieldKey, TripFormFields } from "../types/trip"
import type { RouteGenerationOk } from "../types/route"
import { defaultDepartureLocal, validateTripForm } from "../lib/validation"
import { generateRoutesOnBackend } from "../api/trips"
import { RouteOptions } from "./RouteOptions"

const SERVICE_UNAVAILABLE_COPY =
  "The StormRoute backend is not responding right now. Your trip details below are preserved — try again in a moment."

/* Design-system classes (index.css owns the definitions; see PLAN.md section 3). */
const FIELD_CLASSES =
  "block w-full rounded-control border border-border bg-bg px-3 py-2 text-sm text-ink placeholder:text-ink-3 outline-none focus:border-accent"

const LABEL_CLASSES = "block text-[13px] font-medium uppercase tracking-wide text-ink-2"

const HINT_CLASSES = "mt-1 text-xs text-ink-3"

const ERROR_CLASSES = "mt-1 border-l-2 border-risk-severe pl-2 text-[13px] text-risk-severe"

const ECHO_CLASSES = "font-mono text-[13px] text-ink-2"

/* Keyboard focus must mirror the checked state: the interval radios are
   sr-only inputs inside label rows, so an inline `:focus-visible` on the
   `<input>` would be invisible. Tailwind v4 `has-[input:focus-visible]:*`
   variant lifts the input's focus onto the label row instead. */
const INTERVAL_FOCUS_CLASSES =
  "has-[input:focus-visible]:border-accent has-[input:focus-visible]:bg-accent/10 has-[input:focus-visible]:text-accent"

export interface TripFormProps {
  onRouteData?: (data: RouteGenerationOk) => void
}

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

/** "Oct 25 07:30" style stamp for the mono input-echo line (viewer-local wall clock). */
function formatDepartureStamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${MONTHS_SHORT[date.getMonth()]} ${date.getDate()} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function TripForm({ onRouteData }: TripFormProps) {
  const [fields, setFields] = useState<TripFormFields>(() => ({
    origin: "",
    destination: "",
    departureLocal: defaultDepartureLocal(),
    loadWeightLb: "34000",
    checkpointIntervalMiles: 25,
  }))
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<TripFieldKey, string>> | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [routeData, setRouteData] = useState<RouteGenerationOk | null>(null)

  const update = (key: keyof TripFormFields) => (value: string) => {
    setFields((current) => {
      const next = { ...current }
      next[key] = (key === "checkpointIntervalMiles" ? (Number(value) as CheckpointInterval) : value) as never
      return next
    })
    if (fieldErrors && fieldErrors[key] !== undefined) {
      setFieldErrors((current) => {
        if (!current || current[key] === undefined) return current
        const clone = { ...current }
        delete clone[key]
        return clone
      })
    }
  }

  function clearAllErrors() {
    setFieldErrors(null)
    setFormError(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return

    const outcome = validateTripForm(fields)
    clearAllErrors()
    if (!outcome.ok) {
      setFieldErrors(outcome.errors)
      return
    }

    setRouteData(null)
    setPending(true)
    try {
      const result = await generateRoutesOnBackend({
        origin: outcome.trip.origin,
        destination: outcome.trip.destination,
        departureISO: outcome.trip.departureISO,
        loadWeightLb: outcome.trip.loadWeightLb,
        checkpointIntervalMiles: outcome.trip.checkpointIntervalMiles,
      })

      if (result.kind === "routes") {
        setRouteData(result.response)
        onRouteData?.(result.response)
      } else if (result.kind === "input-error") {
        setFieldErrors(Object.keys(result.errors).length > 0 ? result.errors : null)
        setFormError(result.formError)
      } else if (result.kind === "provider-error") {
        setFormError(result.message)
      } else {
        setFormError(SERVICE_UNAVAILABLE_COPY)
      }
    } finally {
      setPending(false)
    }
  }

  return (
    <section aria-labelledby="trip-form-heading" className="display-contents">
      {/* Column 1: the form panel. coder-fix gives the App wrapper the two-column grid. */}
      <div className="card-raised form-card p-6">
        <h2 id="trip-form-heading" className="text-[13px] font-semibold uppercase tracking-wide text-ink-2">
          Plan a trip
        </h2>

        <form className="mt-4 flex flex-col gap-5" data-testid="trip-form" noValidate onSubmit={handleSubmit} aria-busy={pending}>
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label className={LABEL_CLASSES} htmlFor="trip-origin">Origin</label>
              <input
                id="trip-origin"
                name="origin"
                type="text"
                className={FIELD_CLASSES}
                placeholder="Chicago, IL"
                autoComplete="off"
                value={fields.origin}
                onChange={(e) => update("origin")(e.target.value)}
                aria-describedby={fieldErrors?.origin ? "trip-origin-error" : undefined}
                aria-invalid={fieldErrors?.origin ? true : undefined}
              />
              {fieldErrors?.origin ? (
                <p className={ERROR_CLASSES} id="trip-origin-error" role="alert">
                  {fieldErrors.origin}
                </p>
              ) : null}
            </div>

            <div>
              <label className={LABEL_CLASSES} htmlFor="trip-destination">Destination</label>
              <input
                id="trip-destination"
                name="destination"
                type="text"
                className={FIELD_CLASSES}
                placeholder="Denver, CO"
                autoComplete="off"
                value={fields.destination}
                onChange={(e) => update("destination")(e.target.value)}
                aria-describedby={fieldErrors?.destination ? "trip-destination-error" : undefined}
                aria-invalid={fieldErrors?.destination ? true : undefined}
              />
              {fieldErrors?.destination ? (
                <p className={ERROR_CLASSES} id="trip-destination-error" role="alert">
                  {fieldErrors.destination}
                </p>
              ) : null}
            </div>

            <div>
              <label className={LABEL_CLASSES} htmlFor="trip-departure">Departure (your local time)</label>
              <input
                id="trip-departure"
                name="departureLocal"
                type="datetime-local"
                className={FIELD_CLASSES}
                value={fields.departureLocal}
                onChange={(e) => update("departureLocal")(e.target.value)}
                aria-describedby={fieldErrors?.departureLocal ? "trip-departure-error" : "trip-departure-hint"}
                aria-invalid={fieldErrors?.departureLocal ? true : undefined}
              />
              {fieldErrors?.departureLocal ? (
                <p className={ERROR_CLASSES} id="trip-departure-error" role="alert">
                  {fieldErrors.departureLocal}
                </p>
              ) : (
                <p className={HINT_CLASSES} id="trip-departure-hint">
                  Your own timezone is used, so what you see is what you send.
                </p>
              )}
            </div>

            <div>
              <label className={LABEL_CLASSES} htmlFor="trip-load-weight">Load weight (lb)</label>
              <input
                id="trip-load-weight"
                name="loadWeightLb"
                type="number"
                inputMode="numeric"
                min={0}
                step={1000}
                className={FIELD_CLASSES}
                value={fields.loadWeightLb}
                onChange={(e) => update("loadWeightLb")(e.target.value)}
                aria-describedby={fieldErrors?.loadWeightLb ? "trip-load-weight-error" : "trip-load-weight-hint"}
                aria-invalid={fieldErrors?.loadWeightLb ? true : undefined}
              />
              {fieldErrors?.loadWeightLb ? (
                <p className={ERROR_CLASSES} id="trip-load-weight-error" role="alert">
                  {fieldErrors.loadWeightLb}
                </p>
              ) : (
                <p className={HINT_CLASSES} id="trip-load-weight-hint">
                  Cargo weight in pounds; 0 lb is a valid empty load.
                </p>
              )}
            </div>
          </div>

          <fieldset
            aria-label="Weather checkpoint interval"
            aria-describedby={fieldErrors?.checkpointIntervalMiles ? "trip-interval-error" : "trip-interval-hint"}
          >
            <legend className={LABEL_CLASSES}>Weather checkpoint interval</legend>
            <div className="mt-2 flex flex-wrap gap-2" data-testid="interval-options">
              {CHECKPOINT_INTERVAL_OPTIONS.map((miles) => {
                const inputId = `interval-${miles}`
                const checked = fields.checkpointIntervalMiles === miles
                return (
                  <label
                    key={miles}
                    htmlFor={inputId}
                    className={
                      "inline-flex min-h-11 cursor-pointer select-none items-center justify-center rounded-control border px-4 text-sm font-medium transition-colors " +
                      (checked
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border-strong text-ink-2 hover:border-accent hover:text-ink") +
                      " " +
                      INTERVAL_FOCUS_CLASSES
                    }
                  >
                    <input
                      id={inputId}
                      type="radio"
                      name="checkpointIntervalMiles"
                      value={miles}
                      checked={checked}
                      onChange={() => update("checkpointIntervalMiles")(String(miles))}
                      className="sr-only"
                    />
                    {miles} miles
                  </label>
                )
              })}
            </div>
            {fieldErrors?.checkpointIntervalMiles ? (
              <p className={ERROR_CLASSES} id="trip-interval-error" role="alert">
                {fieldErrors.checkpointIntervalMiles}
              </p>
            ) : (
              <p className={HINT_CLASSES} id="trip-interval-hint">
                Distance between weather checkpoints along each route.
              </p>
            )}
          </fieldset>

          <button type="submit" disabled={pending} className="btn-primary w-full">
            {pending ? (
              <span
                aria-hidden="true"
                className="animate-spin inline-block border-2 border-current border-t-transparent"
                style={{ width: 14, height: 14, borderRadius: "50%" }}
              />
            ) : null}
            {pending ? "Finding routes…" : "Find route options"}
          </button>

          {formError ? (
            <div
              role="status"
              className="rounded-control border border-signal bg-signal/12 p-3 text-sm text-ink"
              data-testid="form-error"
            >
              {formError}
            </div>
          ) : null}
        </form>
      </div>

      {/* Full-width results band: one mono input-echo line, then the frozen RouteOptions tree.
          order-2 keeps the band BELOW the map column on <lg stacking (mobile: form → map → results). */}
      {routeData ? (
        <div className="results-band order-2">
          <p className={ECHO_CLASSES}>
            {routeData.trip.origin} → {routeData.trip.destination} · dep {formatDepartureStamp(routeData.trip.departureISO)} ·{" "}
            {new Intl.NumberFormat("en-US").format(routeData.trip.loadWeightLb)} lb · {routeData.trip.checkpointIntervalMiles} mi
            checkpoints
          </p>
          <RouteOptions response={routeData} />
        </div>
      ) : null}
    </section>
  )
}
