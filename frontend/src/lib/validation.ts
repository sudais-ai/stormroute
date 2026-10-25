import { CHECKPOINT_INTERVAL_OPTIONS } from "../types/trip"
import type { TripFieldKey, TripFormFields, ValidationOutcome } from "../types/trip"

export type FieldErrors = Partial<Record<TripFieldKey, string>>

const pad = (n: number) => String(n).padStart(2, "0")

/**
 * The backend re-derives UTC; a Dst-transition edge (local time that does not
 * exist) resolves through JS date parsing and is rejected here if NaN.
 */
export function departureLocalToISO(local: string): string {
  const date = new Date(local)
  if (Number.isNaN(date.getTime())) return ""
  const offsetMinutes = date.getTimezoneOffset()
  const sign = offsetMinutes <= 0 ? "+" : "-"
  const abs = Math.abs(offsetMinutes)
  return (
    `${pad(date.getFullYear())}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  )
}

export function defaultDepartureLocal(minutesFromNow = 120, roundToMinutes = 5): string {
  const target = new Date(Date.now() + minutesFromNow * 60_000)
  target.setSeconds(0, 0)
  target.setMinutes(Math.round(target.getMinutes() / roundToMinutes) * roundToMinutes)
  return `${pad(target.getFullYear())}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}T${pad(target.getHours())}:${pad(target.getMinutes())}`
}

/**
 * Pure frontend validation for trip input. Mirrors the backend rules so obvious
 * mistakes never leave the browser; the backend remains authoritative — its
 * errors are surfaced verbatim in the UI.
 */
export function validateTripForm(fields: TripFormFields): ValidationOutcome {
  const errors: Partial<Record<TripFieldKey, string>> = {}

  const origin = fields.origin.trim()
  if (!origin) {
    errors.origin = "Origin is required — enter a starting location."
  }

  const destination = fields.destination.trim()
  if (!destination) {
    errors.destination = "Destination is required — enter where the trip ends."
  } else if (origin && destination && destination === origin) {
    errors.destination = "Destination must differ from the origin — pick where the trip actually ends."
  }

  if (!fields.departureLocal) {
    errors.departureLocal = "Departure date and time is required."
  } else {
    const departureMs = new Date(fields.departureLocal).getTime()
    if (Number.isNaN(departureMs)) {
      errors.departureLocal = "Departure must be a valid date and time."
    } else if (departureMs <= Date.now()) {
      errors.departureLocal = "Departure time is in the past — choose a future date and time."
    }
  }

  const weightText = fields.loadWeightLb.trim()
  if (!weightText) {
    errors.loadWeightLb = "Load weight is required — enter pounds (0 for empty cargo)."
  } else {
    const weight = Number(weightText)
    if (!Number.isFinite(weight)) {
      errors.loadWeightLb = "Load weight must be a number (in pounds)."
    } else if (weight < 0) {
      errors.loadWeightLb = "Load weight must not be negative — enter 0 (empty) or more pounds."
    }
  }

  if (!(CHECKPOINT_INTERVAL_OPTIONS as readonly number[]).includes(fields.checkpointIntervalMiles)) {
    errors.checkpointIntervalMiles = "Sampling interval must be one of: 10, 25, or 50 miles."
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors }
  }
  return {
    ok: true,
    trip: {
      origin,
      destination,
      departureISO: departureLocalToISO(fields.departureLocal),
      loadWeightLb: Number(weightText),
      checkpointIntervalMiles: fields.checkpointIntervalMiles,
    },
  }
}
