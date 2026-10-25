# StormRoute — Permanent Project Instructions (READ FIRST)

**Weather-Aware Truck Routing** — Spotter AI Full Stack Developer assessment build.

## Project identity

- Name: `StormRoute`
- Root: `C:\files\Personal\projects\New folder\StormRoute CH` (Windows)
- Stack: React + TypeScript + Vite + Tailwind (frontend) · Python + Django + DRF (backend) · MapLibre GL (map) · routing/geocoding/weather via third-party APIs (see `docs/API_PROVIDER_RESEARCH.md`)
- Time budget: ≤ 16 working hours, ≤ 4 calendar days. Ten-phase plan with hour budgets in `docs/PHASE_PLAN.md`.

## Mandatory startup ritual for every session

1. Read `docs/STATUS.md` FIRST (canonical status), then `docs/PHASE_PLAN.md`, `docs/ASSESSMENT_SPEC.md`, and `docs/DECISIONS.md` / `docs/TEST_LOG.md` / `docs/MISSING_INFO.md` as relevant to the task.
2. Do not start coding until you know: current phase, last completed phase, next authorized phase, and open blockers.
3. Execute **only the authorized phase**. If a new phase appears needed, stop and note it in `STATUS.md` rather than proceeding.

## Phase-by-phase process (mandatory)

- Work proceeds in the ten phases defined in `docs/PHASE_PLAN.md`. Phases are executed on explicit instruction.
- A phase may only be marked complete in `STATUS.md` when every acceptance criterion for that phase has actually been executed and passed. Acceptance criteria for each phase are listed in `docs/PHASE_PLAN.md`.
- Never label untested functionality as working. "Built" ≠ "verified".

## Playwright verification policy (mandatory)

- Every phase that changes the frontend or its behavior MUST be verified in the real browser via the connected Playwright MCP **before** the phase is marked complete:
  1. Start frontend + backend locally, confirm both respond.
  2. Open the real app URL in the browser (Playwright MCP).
  3. Exercise the phase's actual workflows (clicks, inputs, navigation) — not just page load.
  4. Inspect console messages (errors/warnings) and failed network requests.
  5. Capture screenshots into `docs/verification/phase-XX/`.
  6. Investigate and fix in-scope failures, then re-verify.
  7. Record real results in `docs/TEST_LOG.md` and `docs/STATUS.md`.
- A successful production build is not proof the UI works. A screenshot is not proof interactions work.
- Full protocol: `docs/VERIFICATION_PROTOCOL.md`.

## Local development workflow (Windows)

- Frontend: `cd frontend && npm run dev` → http://localhost:5173
- Backend: `cd backend && .venv\Scripts\python.exe manage.py runserver` → http://localhost:8000 (`/api/health/` is the health endpoint; deps live in `backend/.venv`)
- **Port conflict rule (real, applies while `StormRoute CL` sibling dev servers hold 5173/8000):** never kill foreign processes. Probe ports first; if 8000/5173 are held by the stale `StormRoute CL` session, run ours as `manage.py runserver 127.0.0.1:8001` and `npm run dev -- --port 5174` with `API_PROXY_TARGET=http://localhost:8001` set before `npm run dev`. The Vite proxy target is env-configurable; backend CORS already allows 5173+5174.
- Keep dev servers alive after verification so the app stays observable. Do not kill unrelated processes; check ports before binding.
- Logs of running sessions: use Desktop Commander session tools (`list_sessions` / `read_process_output`) — never guess that a server is up; probe the endpoint.

## Testing expectations

- Backend business logic (risk engine, checkpoint sampling, route scoring, provider integration) gets deterministic Python tests (`python manage.py test`), with fixtures clearly identified as test fixtures, not production results.
- Frontend: `npm run build` + `tsc` type checking must pass every phase.
- Playwright browser verification per the policy above.
- Record every real command + outcome in `docs/TEST_LOG.md`.

## Secrets & API keys (mandatory)

- Never commit real `.env` files, keys, tokens, or credentials. Use `.env.example` with placeholder names only.
- Configure real keys only in `.env` files excluded by `.gitignore`.
- Do not echo secret values into logs, docs, screenshots, or chat. Report only whether a variable is set/unset.
- Provider API keys status is tracked (set/unset only) in `docs/MISSING_INFO.md`.

## Documentation sync rules

- Update `docs/STATUS.md` whenever real progress happens. Keep `docs/DECISIONS.md` dated and append-only in spirit.
- Test evidence goes in `docs/TEST_LOG.md`; screenshots in `docs/verification/`.
- Docs must always match what the code actually does. If documentation and reality diverge, fix docs immediately.
- `docs/ASSESSMENT_SPEC.md` is the authority; do not silently reinterpret requirements — record interpretations in `docs/DECISIONS.md`.

## Honesty rules (non-negotiable)

- Never claim a test, build, screenshot, or verification happened if it did not run.
- Never replace a failed API call with fabricated data without clearly labeled, disclosed fallback.
- Do not describe core assessment features as complete if they contain placeholders.
- Do not claim weather scoring guarantees real-world safety or checks vehicle restrictions (bridge clearances, axle limits) — the spec does not require those.
- Risk-mile values are checkpoint-based estimates; present them as such in the UI.
- Git: inspect changes before committing; only commit when instructed; never run destructive commands to fake-clean a repo.
