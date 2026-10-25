import type {
  TripValidateError,
  TripValidateOk,
  TripValidateRequest,
} from "../types/trip"
import type {
  RouteGenerationOk,
  RouteInputError,
  RouteProviderError,
} from "../types/route"
import type { FieldErrors } from "../lib/validation"

export type TripSubmitResult =
  | { kind: "validated"; trip: TripValidateOk["trip"]; message: string }
  | { kind: "invalid"; errors: FieldErrors; formError: string | null }
  | { kind: "service-unavailable" }

const ENDPOINT = "/api/trips/validate/"
const ROUTES_ENDPOINT = "/api/trips/routes/"

const KNOWN_FIELDS = ["origin", "destination", "departureISO", "loadWeightLb", "checkpointIntervalMiles"] as const

function mapApiErrors(apiErrors: TripValidateError["errors"], known: Set<string>): { mapped: FieldErrors; formMessages: string[] } {
  const mapped: FieldErrors = {}
  const formMessages: string[] = []
  for (const [key, messages] of Object.entries(apiErrors)) {
    const first = Array.isArray(messages) ? messages[0] : messages
    if (typeof first !== "string" || !first) continue
    if (known.has(key)) {
      mapped[key as keyof FieldErrors] = first
    } else {
      formMessages.push(first)
    }
  }
  return { mapped, formMessages }
}

export async function validateTripOnBackend(payload: TripValidateRequest): Promise<TripSubmitResult> {
  try {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (res.status === 200) {
      const data = (await res.json()) as TripValidateOk
      return { kind: "validated", trip: data.trip, message: data.message ?? "Trip inputs are valid." }
    }
    if (res.status === 400) {
      const data = (await res.json()) as TripValidateError
      const known = new Set<string>(KNOWN_FIELDS)
      const { mapped, formMessages } = mapApiErrors(data.errors ?? {}, known)
      return { kind: "invalid", errors: mapped, formError: formMessages.length ? formMessages.join(" ") : null }
    }
    return { kind: "service-unavailable" }
  } catch {
    return { kind: "service-unavailable" }
  }
}

export type TripRoutesResult =
  | { kind: "routes"; response: RouteGenerationOk }
  | { kind: "input-error"; errors: FieldErrors; formError: string | null }
  | { kind: "provider-error"; message: string }
  | { kind: "service-unavailable" }

/**
 * Phase 3: generate real routes on the backend for a validated trip request.
 * The Mapbox token stays server-side; this client only consumes normalized
 * backend JSON.
 */
export async function generateRoutesOnBackend(payload: TripValidateRequest): Promise<TripRoutesResult> {
  try {
    const res = await fetch(ROUTES_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (res.status === 200) {
      const data = (await res.json()) as RouteGenerationOk
      return { kind: "routes", response: data }
    }
    if (res.status === 400) {
      const data = (await res.json()) as RouteInputError
      const known = new Set<string>(KNOWN_FIELDS)
      const raw = (data.inputErrors ?? (data as unknown as { errors?: typeof data.inputErrors }).errors) ?? {}
      const { mapped, formMessages } = mapApiErrors(raw, known)
      return { kind: "input-error", errors: mapped, formError: formMessages.length ? formMessages.join(" ") : null }
    }
    let providerMessage: string | null = null
    try {
      const data = (await res.json()) as RouteProviderError
      if (data?.error?.code) providerMessage = data.error.message
    } catch {
      providerMessage = null
    }
    if (providerMessage) return { kind: "provider-error", message: providerMessage }
    return { kind: "service-unavailable" }
  } catch {
    return { kind: "service-unavailable" }
  }
}
