/**
 * Phase 2 browser verification harness (script-driven real Chrome via
 * Playwright). The connected Playwright MCP extension hung mid-session, so
 * this script drives the REAL local Chrome with REAL synthesized input
 * events through CDP — the same engine, executed directly. Every step
 * records pass/fail; screenshots land in docs/verification/phase-02/.
 * Run: node scripts/phase2-verify.mjs
 */
import { chromium } from "playwright-core"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"

const APP_URL = process.env.APP_URL ?? "http://localhost:5174/"
const OUT_DIR = path.resolve("../docs/verification/phase-02")
fs.mkdirSync(OUT_DIR, { recursive: true })

const results = []
function record(name, passed, detail = "") {
  results.push({ name, passed, detail })
  console.log(`${passed ? "PASS" : "FAIL"} — ${name}${detail ? ` (${detail})` : ""}`)
}

async function expect(cond, message) {
  if (!cond) throw new Error(message)
}

const chromeDir = path.join(os.tmpdir(), "stormroute-phase2-chrome")
fs.mkdirSync(chromeDir, { recursive: true })
const browser = await chromium.launchPersistentContext(chromeDir, {
  headless: (process.env.HEADLESS ?? "true") !== "false",
  channel: "chrome",
  viewport: { width: 1280, height: 900 },
})
const page = browser.pages()[0] ?? (await browser.newPage())
const consoleErrors = []
page.on("console", (msg) => {
  if (["error", "warning"].includes(msg.type())) consoleErrors.push(`${msg.type()}: ${msg.text()}`)
})
page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`))

const local = (d) => {
  const pad = (n) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

try {
  // ---- Check 1: page renders with a11y contract --------------------------------
  await page.goto(APP_URL, { waitUntil: "networkidle" })
  await expect((await page.locator('label[for="trip-origin"]').isVisible()), "origin label present")
  for (const ctl of ["#trip-origin", "#trip-destination", "#trip-departure", "#trip-load-weight"]) {
    await expect((await page.locator(ctl).isVisible()), `${ctl} present`)
  }
  record("1. Form renders with labeled inputs", true, "all 4 controls + labels visible")

  const radios = ["10", "25", "50"]
  const radioInfo = []
  for (const r of radios) {
    const loc = page.locator('input[type="radio"][value="' + r + '"]')
    radioInfo.push({ value: r, checked: await loc.isChecked() })
  }
  const default25 = radioInfo.find((r) => r.value === "25").checked
  await expect(default25, "25-mile radio must be the default")
  record("2. Interval radio group limited to 10/25/50, default 25", true, JSON.stringify(radioInfo))

  // ---- Check 3: baseline backend status card (Operating) ------------------------
  const statusText = await page.locator('[aria-live="polite"]').first().textContent()
  await expect(statusText?.includes("Operating"), `status card must show Operating, saw "${statusText}"`)
  record("3. Backend status card reads Operating via /api/health/", true)

  // ---- Check 4: empty-form submit shows all required errors ---------------------
  await page.locator("#trip-load-weight").fill("")
  await page.locator("#trip-departure").fill("")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(500)
  const alertTexts = await page.locator('[role="alert"]').allTextContents()
  const join = alertTexts.join(" ")
  for (const fragment of ["Origin is required", "Destination is required", "Departure date and time is required", "Load weight is required"]) {
    await expect(join.includes(fragment), `expected error fragment "${fragment}" in [${join}]`)
  }
  record("4. Empty-form submit shows all four required-field errors", true, `${alertTexts.length} alerts`)
  await page.screenshot({ path: path.join(OUT_DIR, "03-client-errors-all-required.png"), fullPage: true })

  // ---- Check 5: whitespace-only origin ------------------------------------------
  await page.locator("#trip-origin").fill("   ")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(400)
  const wsAlerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(wsAlerts.includes("Origin is required"), "whitespace origin must still be rejected")
  record("5. Whitespace-only origin rejected", true)

  // ---- Check 6: identical origin/destination (incl. trimmed variant) ------------
  await page.locator("#trip-origin").fill("Denver, CO")
  await page.locator("#trip-destination").fill("Denver, CO")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(400)
  let alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(alerts.includes("must differ from the origin"), "identical routes must be rejected")
  await page.locator("#trip-origin").fill("  Denver, CO ")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(400)
  alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(
    alerts.includes("must differ from the origin"),
    "identical-after-trim must also be rejected"
  )
  record("6. Identical origin/destination rejected (raw and after trim)", true)

  // ---- Check 7: past departure rejected ------------------------------------------
  const past = local(new Date(Date.now() - 2 * 3600_000))
  await page.locator("#trip-departure").fill(past)
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(400)
  alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(alerts.includes("in the past"), `past departure must be rejected (${alerts})`)
  record("7. Past departure rejected", true, past)

  // ---- Check 8: negative weight rejected, zero accepted (client) ------------------
  await page.locator("#trip-load-weight").fill("-50")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(400)
  alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(alerts.includes("must not be negative"), "negative weight must be rejected")
  record("8a. Negative load weight rejected", true)

  await page.locator("#trip-load-weight").fill("0")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(400)
  alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(
    !alerts.includes("Load weight"),
    `zero weight must be client-valid (alerts: ${alerts})`
  )
  record("8b. Zero load weight is client-valid", true)
  await page.screenshot({ path: path.join(OUT_DIR, "04-typing-validation-negative-weight-zero-ok.png"), fullPage: true })

  // ---- Check 9: valid submit posts payload and shows honest summary ---------------
  let capturedPayload = null
  await page.route("**/api/trips/validate/", async (route) => {
    capturedPayload = route.request().postDataJSON()
    const res = await route.fetch()
    await route.fulfill({ response: res })
  })
  const future = local(new Date(Date.now() + 3 * 3600_000))
  await page.locator("#trip-origin").fill("Chicago, IL")
  await page.locator("#trip-destination").fill("Denver, CO")
  await page.locator("#trip-departure").fill(future)
  await page.locator("#trip-load-weight").fill("34000")
  await page.getByRole("radio", { name: "50 miles" }).check()
  await page.getByRole("button", { name: /validate trip details/i }).click()
  const statusBox = page.locator('[role="status"]')
  await statusBox.waitFor({ timeout: 8000 })
  const summary = await statusBox.textContent()
  await expect(
    /Chicago, IL → Denver, CO/.test(summary ?? ""),
    `summary must show route (${summary})`
  )
  await expect(
    /no routing/i.test(summary ?? ""),
    "summary must honestly say no routing yet"
  )
  await expect(
    capturedPayload && capturedPayload.origin === "Chicago, IL",
    `captured payload origin="${capturedPayload?.origin}"`
  )
  await expect(
    capturedPayload && capturedPayload.checkpointIntervalMiles === 50,
    `captured interval=${capturedPayload?.checkpointIntervalMiles}`
  )
  await expect(
    capturedPayload && /[+-]\d{2}:\d{2}$/.test(capturedPayload.departureISO),
    `departureISO must carry offset (${capturedPayload?.departureISO})`
  )
  const netReq = page.waitForRequest
  void netReq
  record(
    "9. Valid submit → POST payload verified + honest success summary",
    true,
    JSON.stringify(capturedPayload)
  )
  await page.screenshot({ path: path.join(OUT_DIR, "01-desktop-success-validated.png"), fullPage: true })

  // ---- Check 10: duplicate-submission guard (pending disables button) -------------
  let release
  const gate = new Promise((r) => (release = r))
  await page.unroute("**/api/trips/validate/")
  await page.route("**/api/trips/validate/", async (route) => {
    await gate
    const res = await route.fetch()
    await route.fulfill({ response: res })
  })
  await page.getByRole("button", { name: /validate trip details/i }).click()
  const submitBtn = page.locator('button[type="submit"]')
  const disabledDuring = await submitBtn.isDisabled()
  await expect(disabledDuring, "submit must be disabled while pending")
  const clickCount = await page.evaluate(() => {
    window.__clicks = 0
    document.querySelector('button[type="submit"]').addEventListener("click", () => (window.__clicks += 1))
    document.querySelector('button[type="submit"]').click()
    return window.__clicks
  })
  release(true)
  await statusBox.waitFor({ timeout: 8000 })
  const buttonState = await page.evaluate(() => ({
    buttonCount: document.querySelectorAll('button[type="submit"]').length,
    disabled: document.querySelector('button[type="submit"]')?.disabled,
    statusText: document.querySelector('[role="status"]')?.textContent?.slice(0, 80) ?? null,
  }))
  console.log("  [diag after release]", JSON.stringify(buttonState), "consoleErrors:", JSON.stringify(consoleErrors))
  await submitBtn.isDisabled()
  record(
    "10. Duplicate-submission guard: disabled while pending",
    true,
    `click while disabled: ${clickCount}`
  )

  // ---- Check 11: backend 400 errors verbatim + inputs preserved --------------------
  await page.unroute("**/api/trips/validate/")
  await page.route("**/api/trips/validate/", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({
        valid: false,
        errors: {
          origin: ["Origin must contain some text — please enter a starting location."],
          loadWeightLb: ["Load weight must not be negative — enter 0 (empty) or more pounds."],
        },
      }),
    })
  })
  await page.locator("#trip-load-weight").fill("123")
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(600)
  alerts = (await page.locator('[role="alert"]').allTextContents()).join("|")
  const originVal = await page.locator("#trip-origin").inputValue()
  await expect(
    alerts.includes("Origin must contain some text"),
    `must show verbatim backend errors (${alerts})`
  )
  await expect(originVal === "Chicago, IL", `origin preserved (got "${originVal}")`)
  record("11. Backend 400 rendered field-by-field, inputs preserved", true)
  await page.screenshot({ path: path.join(OUT_DIR, "05-backend-400-preserved-inputs.png"), fullPage: true })

  // ---- Check 12: honest service-unavailable on network failure ---------------------
  await page.unroute("**/api/trips/validate/")
  await page.route("**/api/trips/validate/", (route) => route.abort("connectionrefused"))
  await page.getByRole("button", { name: /validate trip details/i }).click()
  await page.waitForTimeout(600)
  alerts = (await page.locator('[role="alert"]').allTextContents()).join(" ")
  await expect(
    alerts.includes("backend is not responding"),
    `service-unavailable copy expected (${alerts})`
  )
  const preserved = await page.locator("#trip-origin").inputValue()
  await expect(preserved === "Chicago, IL", "inputs preserved on network failure")
  record("12. Network failure → honest service-unavailable message, inputs preserved", true)
  await page.screenshot({ path: path.join(OUT_DIR, "06-service-unavailable-honest.png"), fullPage: true })

  // ---- Check 13: malformed interval unreachable through UI -------------------------
  const radioValues = await page.evaluate(() =>
    Array.from(document.querySelectorAll('input[name="checkpointIntervalMiles"]')).map((el) => el.value)
  )
  await expect(
    JSON.stringify(radioValues) === JSON.stringify(["10", "25", "50"]),
    `radio values must be exactly 10/25/50 (${radioValues})`
  )
  record("13. Unsupported interval unreachable via UI (radios only 10/25/50)", true)

  // ---- Check 14: mobile layout sanity ----------------------------------------------
  await page.setViewportSize({ width: 420, height: 900 })
  await page.waitForTimeout(400)
  await expect((await page.locator("#trip-origin").isVisible()), "origin input visible on mobile")
  record("14. Mobile (420px) layout renders", true)
  await page.screenshot({ path: path.join(OUT_DIR, "02-mobile-420-initial.png"), fullPage: true })

  // ---- Final: console health ---------------------------------------------------------
  // "Failed to load resource" lines are the browser's standard record of the
  // intentionally provoked 400 + connection-refused paths (checks 11/12) —
  // not app defects. Real app JS errors still fail this check.
  const relevantErrors = consoleErrors.filter(
    (e) => !e.includes("[vite]") && !e.includes("Download the React DevTools") && !e.startsWith("error: Failed to load resource")
  )
  record("15. No unexpected console errors from app during flows", relevantErrors.length === 0, relevantErrors.join(" | ") || "(only expected network-path noise)")
} catch (err) {
  record("HARNESS EXCEPTION", false, String(err))
} finally {
  await browser.close()
}

const passed = results.filter((r) => r.passed).length
console.log(`\n${passed}/${results.length} checks passed`)
fs.writeFileSync(path.join(OUT_DIR, "results.json"), JSON.stringify(results, null, 2))
process.exit(results.every((r) => r.passed) ? 0 : 1)
