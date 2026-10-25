/**
 * Phase 9 tests — slider mapping + corridor classification helpers.
 *
 * Threshold fixtures mirror backend `core/test_risk.py` boundary cases on
 * purpose: both sides of the mirror must agree at the exact boundaries
 * (lower inclusive / upper exclusive; rain+snow severe upper inclusive).
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  FORECAST_SLIDER_MAX_HOURS,
  applyWindLoadRules,
  buildHeatmapGeoJSON,
  classifyCorridorWeather,
  classifyRainBand,
  classifySnowBand,
  classifyWindBand,
  combineCorridorRisk,
  createCoalescedDraw,
  checkpointWeatherAtHour,
  gridWeatherAtHour,
  hourOffsetToISO,
  isoToHourOffset,
  nearestGridPoint,
  pickRouteHeatmap,
  riskOrdinal,
  type HeatmapFeature,
  type HeatmapGridPoint,
  type RouteHeatmap,
} from "./heatmap";

afterEach(() => {
  vi.useRealTimers();
});

/* ---------------- Slider mapping ---------------- */

describe("hourOffsetToISO", () => {
  const start = "2099-01-01T16:00";

  it("offset 0 returns the start hour unchanged", () => {
    expect(hourOffsetToISO(start, 0)).toBe("2099-01-01T16:00");
  });

  it("adds whole hours", () => {
    expect(hourOffsetToISO(start, 1)).toBe("2099-01-01T17:00");
    expect(hourOffsetToISO(start, 8)).toBe("2099-01-02T00:00");
    expect(hourOffsetToISO(start, 48)).toBe("2099-01-03T16:00");
  });

  it("rolls across day boundaries deterministically", () => {
    expect(hourOffsetToISO("2099-01-01T23:00", 2)).toBe("2099-01-02T01:00");
    expect(hourOffsetToISO("2099-02-28T22:00", 3)).toBe("2099-03-01T01:00");
  });

  it("accepts full ISO input and returns provider shape", () => {
    expect(hourOffsetToISO("2099-01-01T16:00:00Z", 5)).toBe("2099-01-01T21:00");
  });

  it("rounds fractional offsets from slider steps", () => {
    expect(hourOffsetToISO(start, 1.4)).toBe("2099-01-01T17:00");
  });

  it("returns empty string for invalid input", () => {
    expect(hourOffsetToISO("", 5)).toBe("");
    expect(hourOffsetToISO("not-a-date", 5)).toBe("");
    expect(hourOffsetToISO(start, Number.NaN)).toBe("");
  });
});

describe("isoToHourOffset", () => {
  const start = "2099-01-01T16:00";

  it("is the exact inverse of hourOffsetToISO within 0–48", () => {
    for (const offset of [0, 1, 7, 12, 24, 47, 48]) {
      expect(isoToHourOffset(start, hourOffsetToISO(start, offset))).toBe(offset);
    }
  });

  it("rejects out-of-range hours honestly", () => {
    expect(isoToHourOffset(start, "2099-01-01T15:00")).toBeNull(); // before start
    expect(isoToHourOffset(start, hourOffsetToISO(start, 49))).toBeNull();
  });

  it("returns null for unparseable values", () => {
    expect(isoToHourOffset("", "2099-01-01T16:00")).toBeNull();
    expect(isoToHourOffset(start, "garbage")).toBeNull();
  });
});

describe("FORECAST_SLIDER_MAX_HOURS", () => {
  it("spans 0–48 h per the assessment spec", () => {
    expect(FORECAST_SLIDER_MAX_HOURS).toBe(48);
  });
});

/* ---------------- Grid point lookup ---------------- */

describe("gridWeatherAtHour", () => {
  const realPoint: HeatmapGridPoint = {
    longitude: -87.6,
    latitude: 41.8,
    hours: ["2099-01-01T16:00", "2099-01-01T17:00", "2099-01-01T18:00"],
    windMph: [10, null, 30],
    rainInPerHr: [0, 0.1, 0.6],
    snowfallInPerHr: [0, 0, 2.5],
  };

  it("returns weather at the requested offset", () => {
    const w = gridWeatherAtHour(realPoint, 0);
    expect(w?.forecastISO).toBe("2099-01-01T16:00");
    expect(w?.windMph).toBe(10);
    expect(w?.snowfallInPerHr).toBe(0);
  });

  it("keeps null values distinct from zero", () => {
    const w = gridWeatherAtHour(realPoint, 1);
    expect(w?.windMph).toBeNull();
    expect(w?.rainInPerHr).toBe(0.1);
  });

  it("returns null outside the available series", () => {
    expect(gridWeatherAtHour(realPoint, 3)).toBeNull();
    expect(gridWeatherAtHour(realPoint, -1)).toBeNull();
    expect(gridWeatherAtHour(realPoint, 48)).toBeNull();
    expect(gridWeatherAtHour(undefined, 0)).toBeNull();
  });
});

describe("nearestGridPoint", () => {
  const a: HeatmapGridPoint = {
    longitude: -87.0,
    latitude: 41.0,
    hours: ["2099-01-01T16:00"],
    windMph: [0],
    rainInPerHr: [0],
    snowfallInPerHr: [0],
  };
  const b: HeatmapGridPoint = {
    longitude: -90.0,
    latitude: 43.0,
    hours: ["2099-01-01T16:00"],
    windMph: [0],
    rainInPerHr: [0],
    snowfallInPerHr: [0],
  };

  it("selects the closest sample deterministically", () => {
    expect(nearestGridPoint([-87.2, 41.1], [a, b])).toBe(a);
    expect(nearestGridPoint([-89.9, 42.9], [a, b])).toBe(b);
  });

  it("returns null on an empty grid", () => {
    expect(nearestGridPoint([-87, 41], [])).toBeNull();
  });
});

describe("checkpointWeatherAtHour", () => {
  it("maps checkpoint to nearest grid point weather", () => {
    const cp = { coordinates: [-87.05, 41.02] as [number, number] };
    const grid: HeatmapGridPoint[] = [
      {
        longitude: -87.0,
        latitude: 41.0,
        hours: ["2099-01-01T16:00"],
        windMph: [42],
        rainInPerHr: [0],
        snowfallInPerHr: [0],
      },
    ];
    expect(checkpointWeatherAtHour(cp, grid, 0)?.windMph).toBe(42);
  });

  it("returns null when the corridor grid has no data", () => {
    expect(checkpointWeatherAtHour({ coordinates: [-87, 41] }, [], 0)).toBeNull();
  });
});

/* ---------------- Classification mirror ---------------- */

describe("classifyWindBand (spec §4 — lower inclusive, upper exclusive)", () => {
  it("matches the exact boundaries", () => {
    expect(classifyWindBand(0)).toBe("low");
    expect(classifyWindBand(24.9)).toBe("low");
    expect(classifyWindBand(25)).toBe("moderate");
    expect(classifyWindBand(34.9)).toBe("moderate");
    expect(classifyWindBand(35)).toBe("high");
    expect(classifyWindBand(44.9)).toBe("high");
    expect(classifyWindBand(45)).toBe("severe");
    expect(classifyWindBand(54.9)).toBe("severe");
    expect(classifyWindBand(55)).toBe("no_travel");
    expect(classifyWindBand(null)).toBeNull();
  });
});

describe("applyWindLoadRules (spec §5)", () => {
  it("wind ≥ 55 mph is No Travel for every load", () => {
    expect(applyWindLoadRules("no_travel", 1000)).toBe("no_travel");
  });

  it("severe band 45–55 becomes No Travel above 30,000 lb", () => {
    expect(applyWindLoadRules("severe", 30_001)).toBe("no_travel");
    expect(applyWindLoadRules("severe", 30_000)).toBe("severe");
  });

  it("high band 35–45 becomes Severe above 40,000 lb", () => {
    expect(applyWindLoadRules("high", 40_001)).toBe("severe");
    expect(applyWindLoadRules("high", 40_000)).toBe("high");
  });

  it("null stays null", () => {
    expect(applyWindLoadRules(null, 34_000)).toBeNull();
  });
});

describe("classifyRainBand / classifySnowBand (severe upper inclusive)", () => {
  it("rain boundaries", () => {
    expect(classifyRainBand(0)).toBe("low");
    expect(classifyRainBand(0.09)).toBe("low");
    expect(classifyRainBand(0.1)).toBe("moderate");
    expect(classifyRainBand(0.24)).toBe("moderate");
    expect(classifyRainBand(0.25)).toBe("high");
    expect(classifyRainBand(0.49)).toBe("high");
    expect(classifyRainBand(0.5)).toBe("severe");
    expect(classifyRainBand(1.0)).toBe("severe");
    expect(classifyRainBand(1.01)).toBe("no_travel");
    expect(classifyRainBand(null)).toBeNull();
  });

  it("snow boundaries", () => {
    expect(classifySnowBand(0)).toBe("low");
    expect(classifySnowBand(0.49)).toBe("low");
    expect(classifySnowBand(0.5)).toBe("moderate");
    expect(classifySnowBand(0.99)).toBe("moderate");
    expect(classifySnowBand(1.0)).toBe("high");
    expect(classifySnowBand(1.99)).toBe("high");
    expect(classifySnowBand(2.0)).toBe("severe");
    expect(classifySnowBand(3.0)).toBe("severe");
    expect(classifySnowBand(3.01)).toBe("no_travel");
    expect(classifySnowBand(null)).toBeNull();
  });
});

describe("combineCorridorRisk (§6 — max with No Travel precedence)", () => {
  it("keeps the max of known levels", () => {
    expect(combineCorridorRisk(["low", "high", "moderate"])).toBe("high");
    expect(combineCorridorRisk(["severe", "high"])).toBe("severe");
  });

  it("No Travel takes precedence over everything", () => {
    expect(combineCorridorRisk(["low", "no_travel", "severe"])).toBe("no_travel");
  });

  it("unknown never downgrades a known level", () => {
    expect(combineCorridorRisk(["low", null, null])).toBe("low");
  });

  it("all-unknown is unknown — never presented as low", () => {
    expect(combineCorridorRisk([null, null, null])).toBe("unknown");
  });
});

describe("classifyCorridorWeather (full mirror)", () => {
  it("clear weather is low", () => {
    expect(classifyCorridorWeather(10, 0, 0, 34_000)).toBe("low");
  });

  it("No Travel dominance across conditions with heavy load", () => {
    expect(classifyCorridorWeather(60, 0, 0, 34_000)).toBe("no_travel");
    expect(classifyCorridorWeather(50, 0, 0, 34_000)).toBe("no_travel"); // load rule
    expect(classifyCorridorWeather(10, 1.2, 0, 34_000)).toBe("no_travel");
    expect(classifyCorridorWeather(10, 0, 4.0, 34_000)).toBe("no_travel");
  });

  it("unknown data is never low", () => {
    expect(classifyCorridorWeather(null, null, null, 34_000)).toBe("unknown");
  });
});

describe("riskOrdinal", () => {
  it("orders unknown below low and no_travel above all", () => {
    expect(riskOrdinal("unknown")).toBe(-1);
    expect(riskOrdinal("low")).toBe(0);
    expect(riskOrdinal("moderate")).toBe(1);
    expect(riskOrdinal("high")).toBe(2);
    expect(riskOrdinal("severe")).toBe(3);
    expect(riskOrdinal("no_travel")).toBe(4);
  });
});

/* ---------------- Heatmap selection + GeoJSON ---------------- */

function makeHeatmap(routeId: string, points: HeatmapGridPoint[]): RouteHeatmap {
  return {
    routeId,
    gridPoints: points,
    forecastStartISO: points[0]?.hours[0] ?? null,
    forecastEndISO: points[0]?.hours[0] ?? null,
    forecastHours: 48,
  };
}

const emptyPoint: HeatmapGridPoint = {
  longitude: -87.0,
  latitude: 41.0,
  hours: [],
  windMph: [],
  rainInPerHr: [],
  snowfallInPerHr: [],
};

describe("pickRouteHeatmap", () => {
  it("prefers the selected route with actual data", () => {
    const heatmaps = [
      makeHeatmap("r1", [emptyPoint]),
      makeHeatmap(
        "r2",
        [
          {
            longitude: -90,
            latitude: 43,
            hours: ["2099-01-01T16:00"],
            windMph: [0],
            rainInPerHr: [0],
            snowfallInPerHr: [0],
          },
        ],
      ),
    ];
    expect(pickRouteHeatmap(heatmaps, "r2")?.routeId).toBe("r2");
  });

  it("falls back to the first heatmap with data", () => {
    const heatmaps = [
      makeHeatmap("r1", [emptyPoint]),
      makeHeatmap("r2", [{ ...emptyPoint, longitude: -88, hours: ["2099-01-01T16:00"], windMph: [0], rainInPerHr: [0], snowfallInPerHr: [0] }]),
    ];
    expect(pickRouteHeatmap(heatmaps, "r1")?.routeId).toBe("r2");
  });

  it("returns undefined when no grid data exists at all", () => {
    expect(pickRouteHeatmap([makeHeatmap("r1", [emptyPoint])], "r1")).toBeUndefined();
    expect(pickRouteHeatmap([], "r1")).toBeUndefined();
  });
});

describe("buildHeatmapGeoJSON", () => {
  const point: HeatmapGridPoint = {
    longitude: -87.6,
    latitude: 41.8,
    hours: ["2099-01-01T16:00"],
    windMph: [24],
    rainInPerHr: [0],
    snowfallInPerHr: [0],
  };

  it("produces one colored feature per grid point", () => {
    const fc = buildHeatmapGeoJSON(makeHeatmap("r1", [point]), 0, 34_000);
    expect(fc.type).toBe("FeatureCollection");
    expect(fc.features).toHaveLength(1);
    const f = fc.features[0] as HeatmapFeature;
    expect(f.geometry.coordinates).toEqual([-87.6, 41.8]);
    expect(f.properties.riskLevel).toBe("low");
    expect(f.properties.color).toBe("#22c55e");
    expect(f.properties.forecastISO).toBe("2099-01-01T16:00");
  });

  it("unknown weather is gray, never low/green", () => {
    const fc = buildHeatmapGeoJSON(makeHeatmap("r1", [emptyPoint]), 0, 34_000);
    expect(fc.features[0].properties.riskLevel).toBe("unknown");
    expect(fc.features[0].properties.color).toBe("#64748b");
  });

  it("empty heatmap yields an empty collection (no fabrication)", () => {
    const fc = buildHeatmapGeoJSON(undefined, 0, 34_000);
    expect(fc.features).toHaveLength(0);
  });

  it("classification changes with the slider hour", () => {
    const windy: HeatmapGridPoint = {
      longitude: -87.6,
      latitude: 41.8,
      hours: ["2099-01-01T16:00", "2099-01-01T17:00"],
      windMph: [10, 56],
      rainInPerHr: [0, 0],
      snowfallInPerHr: [0, 0],
    };
    const at0 = buildHeatmapGeoJSON(makeHeatmap("r1", [windy]), 0, 34_000).features[0].properties;
    const at1 = buildHeatmapGeoJSON(makeHeatmap("r1", [windy]), 1, 34_000).features[0].properties;
    expect(at0.riskLevel).toBe("low");
    expect(at1.riskLevel).toBe("no_travel");
    expect(at1.color).toBe("#dc2626");
  });
});

/* ---------------- Coalesced draw queue ---------------- */

/** Deterministic fake frame timer: tasks run only when `flush()` is called. */
function makeFakeFrameTimer() {
  const pending: Array<() => void> = [];
  return {
    timer: {
      enqueue: (step: () => void) => (pending.push(step), pending.length - 1),
      clear: (id: unknown) => delete pending[id as number],
    },
    flush: () => {
      const tasks = [...pending].filter(Boolean) as Array<() => void>;
      pending.length = 0;
      tasks.forEach((t) => t());
    },
    queuedCount: () => pending.filter(Boolean).length,
  };
}

describe("createCoalescedDraw", () => {
  it("holds the draw until the next frame", () => {
    const { timer, flush } = makeFakeFrameTimer();
    const q = createCoalescedDraw(timer);
    let ran = 0;
    q.enqueue(() => (ran += 1));
    expect(ran).toBe(0);
    flush();
    expect(ran).toBe(1);
  });

  it("collapses rapid enqueues into ONE frame draw (latest wins)", () => {
    const { timer, flush } = makeFakeFrameTimer();
    const q = createCoalescedDraw(timer);
    const ran: number[] = [];
    q.enqueue(() => ran.push(1));
    q.enqueue(() => ran.push(2));
    flush();
    expect(ran).toEqual([2]);
    // A second flush must not replay the consumed draw.
    flush();
    expect(ran).toEqual([2]);
  });

  it("schedules the next frame after drawing (continuous drag works)", () => {
    const { timer, flush } = makeFakeFrameTimer();
    const q = createCoalescedDraw(timer);
    const ran: number[] = [];
    q.enqueue(() => ran.push(1));
    flush();
    q.enqueue(() => ran.push(2));
    flush();
    expect(ran).toEqual([1, 2]);
  });

  it("cancel drops the queued draw entirely", () => {
    const { timer, flush, queuedCount } = makeFakeFrameTimer();
    const q = createCoalescedDraw(timer);
    let ran = 0;
    q.enqueue(() => (ran += 1));
    expect(queuedCount()).toBe(1);
    q.cancel();
    flush();
    expect(ran).toBe(0);
    expect(queuedCount()).toBe(0);
  });

  it("cancel without a pending draw is a safe no-op", () => {
    const { timer, flush } = makeFakeFrameTimer();
    const q = createCoalescedDraw(timer);
    expect(() => q.cancel()).not.toThrow();
    flush();
  });

  it("works with the real rAF path when available", () => {
    // Non-fake timer selection: if requestAnimationFrame exists, constructor
    // must not throw and enqueue/cancel must be callable.
    const q = createCoalescedDraw();
    let ran = 0;
    q.enqueue(() => (ran += 1));
    q.cancel();
    expect(ran).toBe(0);
  });

  it("falls back to setTimeout when the document is hidden (rAF pauses in hidden tabs)", () => {
    const originalRaf = window.requestAnimationFrame;
    const rafCalls: FrameRequestCallback[] = [];
    window.requestAnimationFrame = (cb) => (rafCalls.push(cb), 0);
    const defineState = (mode: string) =>
      Object.defineProperty(document, "visibilityState", {
        configurable: true,
        get: () => mode,
      });
    defineState("hidden");
    try {
      vi.useFakeTimers();
      const q = createCoalescedDraw();
      let ran = 0;
      q.enqueue(() => (ran += 1));
      expect(rafCalls.length).toBe(0);
      expect(ran).toBe(0);
      vi.advanceTimersByTime(20);
      expect(ran).toBe(1);
      vi.useRealTimers();
    } finally {
      defineState("visible");
      window.requestAnimationFrame = originalRaf;
    }
  });

  it("uses requestAnimationFrame when the document is visible", () => {
    const originalRaf = window.requestAnimationFrame;
    const capturedRef: { fn: ((...args: unknown[]) => void) | null } = { fn: null };
    window.requestAnimationFrame = (cb) => ((capturedRef.fn = cb as (...args: unknown[]) => void), 1);
    const defineState = (mode: string) =>
      Object.defineProperty(document, "visibilityState", {
        configurable: true,
        get: () => mode,
      });
    defineState("visible");
    try {
      const q = createCoalescedDraw();
      let ran = 0;
      q.enqueue(() => (ran += 1));
      expect(capturedRef.fn).not.toBeNull();
      expect(ran).toBe(0);
      capturedRef.fn?.();
      expect(ran).toBe(1);
      q.cancel();
    } finally {
      window.requestAnimationFrame = originalRaf;
    }
  });
});
