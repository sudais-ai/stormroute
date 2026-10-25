/**
 * riskColors — the single color module for every risk-tinted UI element
 * (badges, legend dots, map markers import from here, nowhere else).
 * Hex values are pinned by heatmap.test.ts — do NOT change; UI adapts to them.
 * Source of truth: CORRIDOR_RISK_COLORS in src/lib/heatmap.ts (frozen file).
 */

import type { CorridorRiskLevel } from "./heatmap";

export type RiskLevel = CorridorRiskLevel;

/** Exact test-pinned fill hexes (mirrored by --color-risk-* vars in index.css). */
export const RISK_HEX: Record<RiskLevel, string> = {
  low: "#22c55e",
  moderate: "#f59e0b",
  high: "#f97316",
  severe: "#ef4444",
  no_travel: "#dc2626",
  unknown: "#64748b",
};

/** Text color per badge fill: light ink on hue fills; dense no_travel fill uses near-black ink. */
export const RISK_TEXT: Record<RiskLevel, string> = {
  low: "#E7ECF3",
  moderate: "#E7ECF3",
  high: "#E7ECF3",
  severe: "#E7ECF3",
  no_travel: "#0B0E14",
  unknown: "#E7ECF3",
};

/** Badge class string consumed by markup: emits the RAW API level key
 *  (`risk-no_travel` underscore form included). index.css defines both spellings
 *  (hyphen + underscore alias) plus `.badge`/`.risk-badge` chrome, so either
 *  emission renders identically. */
export function riskBadgeClass(level: RiskLevel): string {
  return `risk-badge risk-${level}`;
}

/** Legend-dot class string consumed by markup: index.css owns real
 *  `.risk-dot-{level}` fills (same six pinned hexes), so dots need no inline
 *  background styles. Underscore alias covered in CSS like the badges. */
export function riskDotClass(level: RiskLevel): string {
  return `dot risk-dot-${level}`;
}
