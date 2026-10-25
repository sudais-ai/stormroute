/**
 * Phase 4 browser verification harness (script-driven real Chrome via
 * Playwright). The Playwright MCP extension again wedges on synthesized
 * CLICKS (element resolves, click never completes; its own executor throws
 * `M_ID` errors), so this script drives REAL local Chrome with REAL
 * synthesized input events through CDP — the same engine, executed directly.
 *
 * Scope: verify the real frontend still renders genuine Mapbox routes and
 * now shows checkpoint counts/timing consistent with the API payload the
 * browser actually received. The capped-spacing UI branch is exercised with a
 * clearly-labeled synthetic fixture via request interception (the live
 * provider never hit the default cap); backend capped behavior is covered by
 * deterministic integration tests.
 *
 * Run: node scripts/phase4-verify.mjs   (backend :8001 + frontend :5174 up)
 */
import { chromium } from "playwright-core"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"

const APP_URL = process.env.APP_URL ?? "http://localhost:5174/"
const OUT_DIR = path.resolve("../docs/verification/phase-04")
fs.mkdirSync(OUT_DIR, { recursive: true })

const results = []
function record(name, passed, detail = "") {
  results.push({ name, passed, detail })
  console.log(`${passed ? "PASS" : "FAIL"} — ${name}${detail ? ` (${detail})` : ""}`)
}
async function expect(cond, message) {
  if (!cond) throw new Error(message)
}

const chromeDir = path.join(os.tmpdir(), "stormroute-phase4-chrome")
fs.mkdirSync(chromeDir, { recursive: true })
const browser = await chromium.launchPersistentContext(chromeDir, {
  headless: (process.env.HEADLESS ?? "true") !== "false",
  channel: "chrome",
  viewport: { width: 1280, height: 900 },
})
const page = browser.pages()[0] ?? (await browser.newPage())

const consoleIssues = []
const ignoredConsolePatterns = [
  /Download the React DevTools/i,
  /Failed to load resource.*status of 4\d\d/,
  /Failed to load resource.*status of 5\d\d/,
]
page.on("console", (msg) => {
  if (!["error", "warning"].includes(msg.type())) return
  const text = msg.text()
  if (!ignoredConsolePatterns.some((p) => p.test(text))) consoleIssues.push(`${msg.type()}: ${text}`)
})
page.on("pageerror", (err) => consoleIssues.push(`pageerror: ${err.message}`))
const failedRequests = []
page.on("requestfailed", (req) => failedRequests.push(`${req.method()} ${req.url()} — ${req.failure()?.errorText ?? "unknown"}`))

// Capture real API payloads exactly as the browser received them.
const apiResponses = []
page.on("response", async (res) => {
  if (!res.url().includes("/api/trips/routes/")) return
  try {
    const body = await res.json()
    apiResponses.push({ status: res.status(), body })
  } catch {
    apiResponses.push({ status: res.status(), body: null })
  }
})

const INTERVAL_METERS_PER_MILE = 1609.344
function expectedCheckpointCount(geometryMeters, effectiveIntervalMiles) {
  const spacing = effectiveIntervalMiles * INTERVAL_METERS_PER_MILE
  const full = Math.floor(geometryMeters / spacing + 1e-9)
  let count = full + 1 // origin
  if (geometryMeters - full * spacing > 0.5) count += 1 // partial final segment
  return count
}

function summarizeResponse(body) {
  if (!body || !body.routes) return { status: "unexpected-shape" }
  return {
    routeCount: body.routeCount,
    threeRoutesReturned: body.threeRoutesReturned,
    routes: body.routes.map((route) => ({
      routeId: route.routeId,
      label: route.label,
      distanceMiles: route.distanceMiles,
      durationReadable: route.durationReadable,
      arrivalISO: route.arrivalISO,
      checkpointSummary: route.checkpointSummary,
      checkpointFirst: route.checkpoints?.[0] ?? null,
      checkpointLast: route.checkpoints?.[route.checkpoints.length - 1] ?? null,
      geometryPointCount: route.geometry.coordinates.length,
    })),
  }
}

const panelText = async () => {
  const panel = page.locator("section").filter({ hasText: "Live route options" }).first()
  return (await panel.textContent()) ?? ""
}
const panelLocator = () => page.locator("section").filter({ hasText: "Live route options" }).first()

const local = (d) => {
  const pad = (n) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const SUBMIT = 'button[type="submit"]'

async function fillTrip(origin, destination, intervalMiles = 25) {
  await page.locator("#trip-origin").fill(origin)
  await page.locator("#trip-destination").fill(destination)
  await page.locator("#trip-departure").fill(local(new Date(Date.now() + 12 * 3600_000)))
  await page.locator("#trip-load-weight").fill("34000")
  await page.getByRole("radio", { name: `${intervalMiles} miles` }).check()
}

async function submitAndWaitForNewResponse(beforeCount) {
  await page.locator(SUBMIT).click()
  const deadline = Date.now() + 120_000
  while (apiResponses.length <= beforeCount && Date.now() < deadline) {
    await page.waitForTimeout(250)
  }
  await expect(apiResponses.length > beforeCount, "expected a new /api/trips/routes/ response")
  await panelLocator().waitFor({ state: "visible", timeout: 30_000 })
  return apiResponses[apiResponses.length - 1]
}

try {
  // ---- Check 1: Phase 4 landing renders ---------------------------------------
  await page.goto(APP_URL, { waitUntil: "networkidle" })
  const badge = (await page.locator("header span").first().textContent()) ?? ""
  await expect(badge.includes("Phase 4"), `Phase 4 badge expected, saw "${badge.trim()}"`)
  await expect(await page.getByLabel("Origin").isVisible(), "origin field visible")
  record("1. Phase 4 landing renders (badge + form)", true, badge.trim())
  await page.screenshot({ path: path.join(OUT_DIR, "phase4-01-initial-load.png"), fullPage: true })

  // ---- Check 2: client validation still blocks provider calls -----------------
  const responsesBeforeInvalid = apiResponses.length
  await page.locator("#trip-load-weight").fill("")
  await page.locator(SUBMIT).click()
  await page.waitForTimeout(400)
  const alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(alerts.includes("Load weight is required"), `load-weight alert expected, saw [${alerts}]`)
  await expect(apiResponses.length === responsesBeforeInvalid, "invalid form must not call the routes API")
  record("2. Invalid form still blocked client-side without a route POST", true)
  await page.screenshot({ path: path.join(OUT_DIR, "phase4-02-client-errors.png"), fullPage: true })

  // ---- Check 3: live 25-mile run: route cards + checkpoint disclosure --------
  await fillTrip("Chicago, IL", "Denver, CO", 25)
  const before25 = apiResponses.length
  const response25 = await submitAndWaitForNewResponse(before25)
  await expect(response25.status === 200, `live routes call must be 200, saw ${response25.status}`)
  const body25 = response25.body
  await expect(body25.routesAvailable === true, "routesAvailable true expected")
  let text25 = await panelText()
  await expect(text25.includes("Live route options"), "route panel heading present")
  const labels25 = await page.locator("article h3").allTextContents()
  for (const label of labels25) {
    await expect(/^Route \d+$/.test(label.trim()), `neutral route label expected, saw "${label}"`)
    await expect(!/safest|best|recommended/i.test(label), `no ranking claim allowed in "${label}"`)
  }
  const route25 = body25.routes[0]
  const summary25 = route25.checkpointSummary
  await expect(summary25.count === route25.checkpoints.length, "API count must equal checkpoint array length")
  const expected25 = expectedCheckpointCount(summary25.geometryDistanceMeters, summary25.effectiveIntervalMiles)
  await expect(
    summary25.count === expected25,
    `checkpoint count ${summary25.count} must match geometry/interval formula ${expected25}`
  )
  const spacingText25 = `${summary25.count} at ${summary25.effectiveIntervalMiles.toLocaleString(undefined, { maximumFractionDigits: 2 })} mi spacing`
  await expect(text25.includes(spacingText25), `UI must show "${spacingText25}"`)
  await expect(/sampled along the provider geometry/i.test(text25), "checkpoint sampling disclosure expected")
  await expect(/constant-average-speed estimate, not traffic- or weather-adjusted/i.test(text25), "ETA approximation disclosure expected")
  // Route-arrival / checkpoint-arrival / destination integrity from the real payload.
  for (const route of body25.routes) {
    const summary = route.checkpointSummary
    const cps = route.checkpoints
    const first = cps[0]
    const last = cps[cps.length - 1]
    await expect(first.sequence === 1 && first.distanceFromStartMeters === 0, "first checkpoint must be the origin at 0 m")
    await expect(last.sequence === summary.count, "last checkpoint sequence must equal count")
    await expect(last.arrivalISO === route.arrivalISO, "last checkpoint arrival must equal route arrival")
    await expect(last.coordinates[0] === route.geometry.coordinates.at(-1)[0] && last.coordinates[1] === route.geometry.coordinates.at(-1)[1], "last checkpoint must equal destination vertex")
    await expect(first.coordinates[0] === route.geometry.coordinates[0][0] && first.coordinates[1] === route.geometry.coordinates[0][1], "first checkpoint must equal origin vertex")
    const distances = cps.map((cp) => cp.distanceFromStartMeters)
    await expect(JSON.stringify(distances) === JSON.stringify([...distances].sort((a, b) => a - b)), "checkpoint distances must be monotonic")
    await expect(new Set(cps.map((cp) => cp.checkpointId)).size === cps.length, "checkpoint IDs must be unique")
  }
  record(
    "3. Live 25-mile run: route cards + checkpoint count matches geometry/interval",
    true,
    `counts=${body25.routes.map((r) => r.checkpointSummary.count).join("/")} geometryMi=${body25.routes
      .map((r) => r.checkpointSummary.geometryDistanceMiles)
      .join("/")}`
  )
  await page.screenshot({ path: path.join(OUT_DIR, "phase4-03-live-route-checkpoints-25mi.png"), fullPage: true })

  // ---- Check 4: honest 2-route warning still present, destinations included --
  await expect(text25.toLowerCase().includes("distinct routes"), "fewer-than-three honesty warning expected")
  await expect(text25.includes("no route is invented"), "no-invented-routes clause expected")
  const lastCps = body25.routes.map((r) => r.checkpoints.at(-1))
  for (const cp of lastCps) {
    await expect(cp.interpolated === false, "destination checkpoint must be a real provider vertex")
  }
  record("4. Provider-truth warning + destination checkpoint inclusion", true, `destinations=${lastCps.map((c) => c.distanceFromStartMiles).join("/")} mi`)

  // ---- Check 5: switching interval to 50 miles changes sampling (live) --------
  await fillTrip("Chicago, IL", "Denver, CO", 50)
  const before50 = apiResponses.length
  const response50 = await submitAndWaitForNewResponse(before50)
  const body50 = response50.body
  const route50 = body50.routes[0]
  const summary50 = route50.checkpointSummary
  const expected50 = expectedCheckpointCount(summary50.geometryDistanceMeters, summary50.effectiveIntervalMiles)
  await expect(summary50.effectiveIntervalMiles === 50, `effective interval must be 50, saw ${summary50.effectiveIntervalMiles}`)
  await expect(summary50.count === expected50, `50-mile count ${summary50.count} must match formula ${expected50}`)
  await expect(
    summary50.count < body25.routes[0].checkpointSummary.count,
    "50-mile sampling must produce fewer checkpoints than 25-mile sampling"
  )
  const text50 = await panelText()
  const spacingText50 = `${summary50.count} at 50 mi spacing`
  await expect(text50.includes(spacingText50), `UI must show "${spacingText50}"`)
  record(
    "5. Live 50-mile run: fewer checkpoints, UI reflects spacing",
    true,
    `25mi=${body25.routes[0].checkpointSummary.count} → 50mi=${summary50.count}`
  )
  await page.screenshot({ path: path.join(OUT_DIR, "phase4-04-interval-50mi.png"), fullPage: true })

  // ---- Check 6: capped-spacing disclosure (labeled synthetic fixture) ---------
  const fixtureBody = JSON.parse(JSON.stringify(body50))
  const cappedRoute = fixtureBody.routes[0]
  const requestedInterval = cappedRoute.checkpointSummary.requestedIntervalMiles
  cappedRoute.checkpointSummary = {
    ...cappedRoute.checkpointSummary,
    count: 12,
    capped: true,
    requestedIntervalMiles: requestedInterval,
    effectiveIntervalMiles: 120.5,
    maxPerRoute: 12,
  }
  await page.route("**/api/trips/routes/", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixtureBody) })
  )
  await page.locator(SUBMIT).click()
  await page.waitForTimeout(1200)
  const textFixture = await panelText()
  await expect(textFixture.includes("12 at 120.5 mi spacing"), "capped fixture count/spacing must render")
  await expect(
    textFixture.includes(`widened from ${requestedInterval} mi to stay within 12 per route`),
    "capped-fixture widening disclosure must render"
  )
  record(
    "6. Capped-spacing disclosure renders (SYNTHETIC labeled fixture; real provider never hit the cap)",
    true,
    `requested=${requestedInterval} effective=120.5 count=12`
  )
  await page.screenshot({ path: path.join(OUT_DIR, "phase4-05-capped-fixture.png"), fullPage: true })
  await page.unroute("**/api/trips/routes/")

  // ---- Check 7: no secret, no persistence, no out-of-phase map ---------------
  const html = await page.content()
  await expect(!html.includes("pk."), "no Mapbox token-shaped string may appear in the DOM")
  const storage = await page.evaluate(() => ({ local: Object.keys(window.localStorage).length, session: Object.keys(window.sessionStorage).length }))
  await expect(storage.local === 0 && storage.session === 0, "no browser persistence may be used")
  const canvasCount = await page.locator("canvas").count()
  await expect(canvasCount === 0, "the map is Phase 8 — no canvas expected yet")
  record("7. No token in DOM, no browser persistence, no map canvas this phase", true, `storage=${JSON.stringify(storage)}`)

  // ---- Check 8: mobile 420px keeps results readable ---------------------------
  await page.setViewportSize({ width: 420, height: 900 })
  await page.waitForTimeout(400)
  await expect(await page.locator("article").first().isVisible(), "route card visible on mobile")
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  await expect(mobileOverflow <= 1, `no horizontal page overflow expected on mobile, saw ${mobileOverflow}px`)
  record("8. Mobile 420px layout renders route cards without horizontal page overflow", true, `overflow=${mobileOverflow}px`)
  await page.screenshot({ path: path.join(OUT_DIR, "phase4-06-mobile-420.png"), fullPage: true })

  // ---- Check 9: console/network hygiene --------------------------------------
  await expect(consoleIssues.length === 0, `unexpected console issues: ${consoleIssues.join(" || ").slice(0, 500)}`)
  await expect(failedRequests.length === 0, `unexpected failed requests: ${failedRequests.join(" || ").slice(0, 500)}`)
  record("9. No unexpected console errors/warnings or failed requests", true, `apiCalls=${apiResponses.length}`)
} catch (err) {
  record(".EXECUTION", false, String(err?.message ?? err))
  try {
    await page.screenshot({ path: path.join(OUT_DIR, "phase4-99-failure.png"), fullPage: true })
    const dump = (await page.locator("main").textContent()) ?? ""
    fs.writeFileSync(path.join(OUT_DIR, "failure-dump.txt"), dump.slice(0, 5000), "utf8")
  } catch {
    /* ignore */
  }
} finally {
  const allPassed = results.every((r) => r.passed)
  const summary = {
    generatedAt: new Date().toISOString(),
    method:
      "script-driven real Chrome (playwright-core, channel=chrome, headless) via CDP — Playwright MCP clicks wedge (extension executor M_ID crash); navigation/snapshot/fill worked",
    appUrl: APP_URL,
    viewports: { desktop: "1280x900", mobile: "420x900" },
    apiCallsObserved: apiResponses.length,
    apiSummaries: apiResponses.map((entry) => ({
      status: entry.status,
      ...summarizeResponse(entry.body),
    })),
    fixtureDisclosure: "Check 6 uses a synthetic capped-summary fixture via request interception; all other API data is live Mapbox-backed.",
    consoleIssues,
    failedRequests,
    results,
    allPassed,
  }
  fs.writeFileSync(path.join(OUT_DIR, "results.json"), JSON.stringify(summary, null, 2), "utf8")
  console.log(`\n${allPassed ? "ALL CHECKS PASSED" : "SOME CHECKS FAILED"} — ${results.length} checks; screenshots + results.json in ${OUT_DIR}`)
  await browser.close()
}
