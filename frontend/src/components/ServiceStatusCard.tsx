import { useEffect, useState } from "react"
import type { HealthResponse, HealthStatus } from "../types/health"

const STATUS_LABELS: Record<HealthStatus, string> = {
  checking: "Checking…",
  healthy: "Online",
  unhealthy: "Unhealthy",
  unreachable: "Offline",
}

const STATUS_DOT_COLORS: Record<HealthStatus, string> = {
  checking: "#FFB224",
  healthy: "#22c55e",
  unhealthy: "#ef4444",
  unreachable: "#ef4444",
}

interface ServiceCardProps {
  title: string
  /** Kept on the props contract (App passes it) but no longer shown in copy. */
  serviceType: string
  status: HealthStatus
  details?: string
  children?: never
}

export function ServiceStatusCard({ title, status, details }: ServiceCardProps) {
  const tooltip = `${title} · ${details ?? STATUS_LABELS[status]}`

  return (
    <span className="inline-flex items-center gap-2 text-xs font-medium text-ink-2" title={tooltip}>
      <span
        aria-hidden="true"
        className="dot"
        style={{ backgroundColor: STATUS_DOT_COLORS[status] }}
      />
      <span aria-live="polite">{STATUS_LABELS[status]}</span>
    </span>
  )
}

export function useBackendHealth(url = "/api/health/") {
  const [status, setStatus] = useState<HealthStatus>("checking")
  const [info, setInfo] = useState<HealthResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    setStatus("checking")
    fetch(url)
      .then((res) => (res.ok ? (res.json() as Promise<HealthResponse>) : Promise.reject(res.status)))
      .then((data) => {
        if (cancelled) return
        setInfo(data)
        setStatus(data?.status === "ok" ? "healthy" : "unhealthy")
      })
      .catch(() => {
        if (cancelled) return
        setInfo(null)
        setStatus("unreachable")
      })
    return () => {
      cancelled = true
    }
  }, [url])

  return { status, info }
}
