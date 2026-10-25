export const CHECKPOINT_INTERVAL_OPTIONS = [10, 25, 50] as const
export type CheckpointInterval = (typeof CHECKPOINT_INTERVAL_OPTIONS)[number]

export type TripFieldKey =
  | "origin"
  | "destination"
  | "departureLocal"
  | "loadWeightLb"
  | "checkpointIntervalMiles"

export type TripFormFields = {
  origin: string
  destination: string
  departureLocal: string
  loadWeightLb: string
  checkpointIntervalMiles: CheckpointInterval
}

export type ValidatedTrip = {
  origin: string
  destination: string
  departureISO: string
  loadWeightLb: number
  checkpointIntervalMiles: number
}

export type ValidationOutcome =
  | { ok: true; trip: ValidatedTrip }
  | { ok: false; errors: Partial<Record<TripFieldKey, string>> }

export type ApiValidationErrors = Partial<Record<string, string[]>>

export type TripValidateRequest = {
  origin: string
  destination: string
  departureISO: string
  loadWeightLb: number
  checkpointIntervalMiles: number
}

export type TripValidateOk = { valid: true; trip: ValidatedTrip; message?: string }
export type TripValidateError = { valid: false; errors: ApiValidationErrors }
export type TripValidateResponse = TripValidateOk | TripValidateError
