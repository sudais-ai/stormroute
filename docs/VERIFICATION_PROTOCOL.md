# StormRoute — Browser Verification Protocol (Mandatory)

Applies to **every phase that changes the frontend or its behavior**. Phase is not complete until this protocol has been executed and its outcomes recorded in `docs/TEST_LOG.md` + `docs/STATUS.md`.

## Preconditions

1. Read current `docs/STATUS.md`; know the phase under verification.
2. Frontend: `cd frontend && npm run dev` → must respond at http://localhost:5173.
3. Backend: `cd backend && python manage.py runserver` → must respond at http://localhost:8000 (`/api/health/`).
4. Probe endpoints before claiming servers are up (HTTP GET, check response body/status).

## Verification steps (all required)

1. **Open the real app** at the actual dev URL using the Playwright MCP (browser extension session). Never test a stale screenshot, a file:// copy, or a different app.
2. **Snapshot** the page; confirm structural elements exist (headings, form controls, buttons, map when in later phases).
3. **Exercise real workflows**: click/type/navigate through the phase's functional paths — e.g., submit the form with valid and invalid inputs; trigger map interactions; move the slider. Page-load-only checks are insufficient.
4. **Console inspection**: collect console messages (errors and warnings). Relevant errors must be investigated and fixed or explicitly justified. Clean console is the goal for shipped work.
5. **Network inspection**: review requests; identify failures (4xx/5xx, aborts) tied to app functionality and resolve or justify.
6. **Screenshots**: capture state evidence into `docs/verification/phase-XX/` with meaningful filenames (`02-form-validation-errors.png`, etc.).
7. **Responsive sanity**: at least desktop (≈1280px) and narrow (≈420px) viewport checks when UI phase is verified; record layout observations.
8. **Fix & re-verify**: in-scope failures are fixed and the affected steps re-run.
9. **Record**: append actual commands/checks/outcomes to `docs/TEST_LOG.md`; update phase status in `docs/STATUS.md` only when everything passed.

## Honesty rules baked into this protocol

- A production build passing (`npm run build`) is **not** proof the UI works.
- A screenshot is **not** proof interactions work — screenshots accompany interaction evidence.
- If Playwright MCP is unavailable/blocked, do not fake results: document the blocker, what was attempted, and mark browser-dependent acceptance criteria as not verified.

## Feature-verification matrix (kept current)

| Phase | Key browser checks |
|---|---|
| 1 | Page renders at 5173; title/branding; no console errors; backend health reaches 8000 |
| 2 | Form fills; validation messages appear for invalid inputs; console clean |
| 3 | Submit real trip; routes area shows provider truth (3 / fewer alternatives / error honestly) |
| 4 | Checkpoint count/logic visible in payloads; partial-final-segment included |
| 5 | Checkpoint weather shows real values (or honest unconfigured-key message) |
| 6–7 | Risk badges and recommendation text reflect fixtures→UI integration |
| 8 | 3 routes on map; markers clickable; selection syncs summary cards |
| 9 | Slider moves; displayed timestamp + checkpoint values + heatmap change consistently |
| 10 | Full end-to-end re-run of above; hosted URL checked; responsive re-check |
