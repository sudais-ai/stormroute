export type HealthStatus = "checking" | "healthy" | "unhealthy" | "unreachable"

export interface HealthResponse {
  status: string
  service: string
  version: string
}
