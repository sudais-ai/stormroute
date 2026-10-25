# StormRoute — PLAN.md — Frontend-Only UI Redesign Round

**Date:** 2026-10-25 · **Author:** architect · **Supersedes:** the previous Phase-10 QA/deployment plan (deleted in full; it was stale).
**Change class (DIFF POLICY):** classNames + copy + inline structure + layout ONLY, inside what the frozen test contract permits. Zero behavior changes. Zero test edits.

---

## 1. Goal / Scope / Non-goals

**Goal.** Kill AI-generated tells (emoji logo, teal accent, glass blur, chip walls, em-dash prose, chatbot phrasing, docgen defaults) and make INPUT to OUTPUT instantly readable: form + map row on top, one full-width Results band below opened by a one-line mono input echo. Look = cool-steel ops console with one warm amber signal; 1px borders, no shadows, no blur, radius 6/10.

**Scope (IN).** Frontend restyle + re-layout + copy cleanup per sections 3-5. Fonts via @fontsource. One test-pinned risk-color module. Dead code deletion. Docs + screenshot updates.

**Non-goals (OUT).**
- No backend changes at all (routing.py already fixed; API contract untouched).
- No edits to ANY *.test.* file — the 80-test contract is frozen and not editable.
- No edits to: src/lib/heatmap.ts (CORRIDOR_RISK_COLORS hexes are test-pinned), src/lib/validation.ts, src/types/*, src/api/*, src/main.tsx (keeps documentElement.classList.add('dark'), line 8).
- No new features, no state/routing changes, no new dependencies beyond @fontsource/barlow and @fontsource/jetbrains-mono.

---

## 2. Step-0 greps — EVERY build agent re-runs these BEFORE its first edit

(Architect already ran them on 2026-10-25; verdicts below are locked plan facts.)

1. Run in frontend/: grep -E "recommendation|Rank|Recommended|Route recommendation" src/components/TripForm.test.tsx
   **Verdict:** the rank-list text is NOT asserted verbatim (mock data only at lines 190-198); real assertions are getAllByText('Route N') >= 1 (lines 303-306) and card h3 must NOT contain /safest|best|recommended/ (line 338).
   => **Approved:** merge the recommendation rank-list into the recommended card's Rank #1 chip + one-line reason (section 4.3).
2. Run in frontend/: grep -E "CORRIDOR_RISK_COLORS|#[0-9A-Fa-f]{6}" src/lib/heatmap.test.ts
   **Verdict:** tests pin low #22c55e (L364), unknown #64748b (L371), no_travel #dc2626 (L392); buildHeatmapGeoJSON colors come from CORRIDOR_RISK_COLORS (heatmap.ts:335).
   => **heatmap.ts:300-307 is the single frozen color source (all 6 hexes).** The UI adapts to it; nobody edits heatmap.ts.
3. Run in frontend/: grep -rE 'from "[./]*ui|components/ui' src  (architect run: **0 matches**)
   => **Approved:** delete src/components/ui/ (Badge, Button, Card, Input, Select, Skeleton, index.ts): 0 imports anywhere, Skeleton references nonexistent hsl(var(--muted)) — dead docgen scaffolding.

---

## 3. Design system sheet (refactor implements; ALL agents use exactly these names)

### 3.1 Fonts — runner first installs, then exact import lines

runner command (in frontend/): npm i @fontsource/barlow @fontsource/jetbrains-mono

src/index.css imports — EXACT lines, at the very top, ABOVE @import "tailwindcss":

    @import "@fontsource/barlow/400.css";
    @import "@fontsource/barlow/500.css";
    @import "@fontsource/barlow/600.css";
    @import "@fontsource/jetbrains-mono/400.css";
    @import "@fontsource/jetbrains-mono/500.css";

Typography: Barlow 600 headings / 500 labels / 400 body. JetBrains Mono ONLY for: input-echo line, coordinates, weight numbers, the via-road strings, timestamps, slider label and ticks. @theme tokens: --font-sans: "Barlow", ui-sans-serif, system-ui, sans-serif; --font-mono: "JetBrains Mono", ui-monospace, monospace;

### 3.2 Color tokens (CSS vars defined dark-correct in :root; single dark look; the existing .dark class stays as harmless alias)

    --bg #0B0E14   | --panel #141922   | --raised #1B212B
    --border #262D38 | --border-strong #3D4654
    --text #E7ECF3 | --text-2 #9AA6B5 | --text-3 #5A6472
    --accent #5C9DFF | --amber-signal #FFB224

Risk hexes = test-pinned values read from src/lib/heatmap.ts:300-307 (no_travel, severe, high, moderate, low, unknown):

    low #22c55e | moderate #f59e0b | high #f97316 | severe #ef4444 | no_travel #dc2626 | unknown #64748b

Badge/badge-like fills: full-hue border + full-hue text, fill = same hue at 12-15% alpha over panel. Focus ring: accent 2px (white on map overlays). Radius: --radius-control: 6px, --radius-card: 10px. 1px borders everywhere, NO box-shadows; floating map panels use bg panel + border only. New module src/lib/riskColors.ts re-exports these pinned hexes plus semantic UI variants; index.css --color-risk-* vars mirror it so CSS and JS agree.

### 3.3 Tailwind v4 mapping (via @theme inline in index.css — utility names every agent uses)

    --color-bg/--color-panel/--color-raised/--color-border/--color-border-strong  => bg-panel, border-border-strong, ...
    --color-ink/--color-ink-2/--color-ink-3 (mapped to --text/--text-2/--text-3) => text-ink, text-ink-2, text-ink-3
    --color-accent/--color-signal (mapped to --accent/--amber-signal)            => text-accent, bg-signal, ring-accent
    --color-risk-low/moderate/high/severe/no-travel/unknown                       => bg-risk-low, text-risk-severe, ...
    --radius-control / --radius-card                                              => rounded-control, rounded-card

Delete on sight: legacy manual classes .text-slate-* and .bg-storm-*; dead tokens (primary/secondary/accent/popover/card); the default accent-teal-400 slider style; Skeleton's hsl(var(--muted)) (file is deleted anyway).

---

## 4. Layout spec + copy deck

### 4.1 Frozen strings — keep byte-identical, restyle only (never reword)

F1 labels Origin, Destination + /Departure/, /Load weight/ · F2 radios exactly 10 miles / 25 miles (default checked) / 50 miles · F3 group name /checkpoint interval/i · F4 single submit /find route options/i pending /finding routes/i · F5 field-error strings verbatim from lib/validation.ts, each in its own role="alert" paragraph · F6 results section keeps aria-label /live route options/i on the RouteOptions root section · F7 <ol aria-label="route options"> with <article> + <h3>Route N</h3> (h3 never contains safest|best|recommended) · F8 per card literal "via {providerRouteSummary}" (fixture counts 3) · F9 checkpoint sentences verbatim: "{count} at {interval} mi spacing", "— widened from {req} mi to stay within {max} per route", "sampled along the provider geometry from 0 mi to {N} mi" · F10 three methodology regexes each EXACTLY ONCE per page · F11 results region contains exactly ONE role="alert" (the run-warning; field alerts live in the form region) · F12 risk words Low / Moderate / High / Severe / No Travel / Unknown · F13 testids trip-form, interval-options, form-error, forecast-slider, forecast-label, forecast-ticks, forecast-slider-unavailable, map-viewport · F14 marker title "{n}. {Risk} — forecast {ISO}" (em-dash inside frozen strings is fine) · F15 aria-busy on the form, role="status" on the formError box.

### 4.2 Layout decision — Option A, implemented as a CSS breakout inside TripForm (chosen)

Why: all TripForm tests render <TripForm/> alone (18 render calls) and RouteOptions is mounted inside it (TripForm.tsx:275), so results MUST stay in TripForm's React tree. Cleanest CSS-safe approach: TripForm's root <form> becomes a full-width display:grid page grid — grid-template-columns: minmax(0, 26rem) minmax(0, 1fr); the form column and the map column fill row 1; the wrapper div around <RouteOptions/> gets grid-column: 1 / -1 plus width:100%. Visually this IS the full-width results band of Option A, below form+map; structurally RouteOptions remains TripForm's child, so screen queries in the frozen tests are untouched. Map stays right of the form. No component moves, no state moves.

Page flow: header wordmark -> H1 -> subhead -> form+map row -> results band (input echo, then route cards grid, 1-col) -> footer single line. Route cards remain <article> inside the frozen <ol>.

### 4.3 Copy deck — every rewritten string, verbatim (em-dash ban applies to everything here)

1. Brand wordmark (replaces the 🚦 emoji logo): StormRoute — plain Barlow 600 text, no emoji, no glyph; optional 2px accent underline bar as the single decorative element.
2. H1 (kept as): Plan a trip, see the weather before the wheels roll
3. Hero subhead (new, one line): Set a trip and a load; route options below show weather risk at the exact forecast hour.
4. Placeholders (docgen defaults removed): origin Chicago, IL — destination Denver, CO.
5. Departure hint: Local departure time; adjust the forecast hour in the results band.
6. Load hint: Gross trip load in pounds.
7. Interval caption: Distance between weather checkpoints along each route. (visible group keeps the frozen substring Checkpoint interval)
8. Submit/pending: keep current frozen strings and count (F4); restyle only.
9. Results band visible heading: Route options — the section's aria-label stays frozen per F6.
10. Input echo (JetBrains Mono, exactly one line, pattern): {origin} → {destination} · dep {MMM D HH:mm} · {weight with commas} lb · {interval} mi checkpoints — rendered example: Chicago, IL → Denver, CO · dep Oct 26 08:30 · 34,000 lb · 25 mi checkpoints
11. Rank chip (recommended card ONLY): Rank #1 — amber-signal text + border over 12% fill, mono, radius control.
12. Card reason line (recommended card ONLY): Chosen by ranking: severe-route miles, then high-route miles, then average risk, then driving time.
13. Card stat labels: Distance / Driving time / Roads. Values: 1,004.6 mi style number · 14 h 30 m (arr 15:42) with arrival inline beside duration · roads row keeps the frozen literal via I-80 W; I-76 W in mono.
14. Per-card checkpoints block label: Checkpoints — the F9 sentences render verbatim inside, as today.
15. Merged map-layers row (replaces the old pills row + the separate Highlighted: caption line): prefix word Layers: then the EXISTING pill labels byte-identical, aria-pressed preserved; pills remain the only full-pill shapes on the page. Highlight state = signal border + pressed styling; no new wording, no new chip texts.
16. Map legend: consolidated inside the top-right map panel as a dot + word list (NOT chips), words = F12 set: Low, Moderate, High, Severe, No Travel, Unknown, dots = pinned hexes from 3.2. The old separate legend caption and the second slider caption are deleted; the forecast slider keeps its own single caption byte-identical.
17. Slider restyle: all F13 testids untouched; 4px track on raised, 14px accent thumb (never the default teal), mono label and ticks.
18. Empty state (max 2 bullets): Confirm origin and destination are real city names. / Widen the checkpoint radius to 50 miles to find more options.
19. Methodology: replaces the 5 separate disclaimer prose blocks with ONE <details> under the results band. Summary text: Estimate methods. Body paragraph, verbatim (contains each F10 regex exactly once; fixes the garbled haverine word-salad): Risk values are model estimates for planning, not real-time road conditions. Weather data from Open-Meteo is matched to the exact forecast hour at each checkpoint. Risk classification uses assessment-mandated thresholds for wind, rain and snow by hour. Driving-time values are a constant-average-speed estimate, not traffic- or weather-adjusted. Checkpoint distances are great-circle (haversine) samples along the provider geometry and may differ slightly from the provider's road distance.
20. Banned phrasing (never appear): somewhere on the way · Top pick by combined ranking · any corridor-chatter chatbot phrasing.
21. Header status (ServiceStatusCard): colored dot + single word: Online / Offline (dot green #22c55e / red #dc2626); title tooltip: Backend API online / Backend API offline. formError copy stays frozen (/backend is not responding/i).
22. Footer (single line, replaces today's block): Risk route-mile values are model estimates for planning, not real-time road conditions. — optionally followed by: Weather: Open-Meteo · Basemap: Carto dark-matter (NEVER write the phrase weather data from open-meteo anywhere else on the page or the F10 regex-count breaks).
23. Map basemap (coder-fix): style URL https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json — keep the current style object as catch-fallback (comment: // fallback: https://demotiles.maplibre.org/style.json).

---

## 5. File ownership map (unique, no overlap) + build order

| Agent | ALLOWED files | Deliverable |
|---|---|---|
| coder-fix | src/App.tsx; src/components/RouteOptions.tsx; src/components/MapViewport.tsx | Header/hero/footer de-AI (wordmark, subhead, footer line); results cards: Rank chip, reason, stat labels, merged layers row handling outside RouteOptions; garbled sentence fix inside the details; MapViewport: dark-matter basemap, consolidated dot-list legend, colors imported only from riskColors.ts, marker title format untouched |
| coder-new | src/components/TripForm.tsx; src/components/ForecastSlider.tsx; src/lib/riskColors.ts (NEW); DELETE src/components/ui/* (Badge, Button, Card, Input, Select, Skeleton, index.ts) after the final 0-import grep | Grid page shell in the form + full-bleed results wrapper (grid-column: 1 / -1) + mono input echo + hints/placeholders; slider restyle with all testids; riskColors.ts exporting the 6 pinned hexes + UI variants |
| refactor | src/index.css; src/components/ServiceStatusCard.tsx | Full token + font rewrite per section 3 (imports, :root vars, @theme inline, radius tokens, legacy/dead-class purge); ServiceStatusCard to dot+word+tooltip |
| tester | runs gates ONLY (npm test); NO test edits | Gate report: 80/80 |
| runner | frontend/package.json, frontend/package-lock.json (npm i @fontsource/barlow @fontsource/jetbrains-mono); runs build + lint gates | Gates: tsc -b && vite build PASS; lint exit 0 |
| docs-writer | docs/STATUS.md; docs/TEST_LOG.md (append 2026-10-25 second entry); docs/DECISIONS.md (append); docs/verification/product-quality/ README-tier note | Docs synced to shipped reality |
| browser-qa | Playwright E2E; writes ONLY docs/verification/product-quality/* screenshots | E2E pass + screenshot set |
| reviewer-quality / reviewer-standards | read-only | Findings only |
| fixer | failure-only; any file EXCEPT *.test.*, src/lib/heatmap.ts, src/lib/validation.ts | Gate re-run after fixes |

**Milestones / build order (dependency-gated):**
0. M0: all agents run the section 2 step-0 greps.
1. M1: runner installs fonts; **refactor lands index.css FIRST** (+ ServiceStatusCard). All later agents code only against the agreed names; if they start early they still use the final names and the build is gated after refactor.
2. M2: coder-new + coder-fix run in PARALLEL (disjoint files).
3. M3: tester + runner gates (80/80; tsc -b && vite build; lint 0).
4. M4: browser-qa E2E + screenshots (fixer loop if needed, see section 7).
5. M5: docs-writer appends and closes the round.

---

## 6. Done criteria per agent (measurable)

1. **refactor:** the 5 @fontsource imports present at top of index.css; every token of 3.2 present with exact values; grep 'text-slate|bg-storm|backdrop-blur|bg-white/5' over src = 0 matches; no --radius defaults changed for other components.
2. **coder-new:** npm test = 80/80 with its changes in the tree; RouteOptions still rendered at the SAME DOM position inside TripForm; results wrapper has grid-column: 1 / -1 and renders below the map in the real viewport; src/components/ui/ gone and grep -r 'components/ui' src = 0; all eight F13 testids still present; single submit button only (F4).
3. **coder-fix:** App.tsx contains no emoji and no glass/backdrop utilities; RouteOptions body contains the great-circle (haversine) sentence and each F10 regex exactly ONCE (grep -c == 1 per regex); results region has exactly one role="alert"; every card h3 stays Route N with no banned words; MapViewport imports colors ONLY from riskColors.ts (local MARKER_COLORS hex array deleted) and carries the dark-matter style URL with fallback comment.
4. **tester + runner:** npm test 80/80 PASS; tsc -b && vite build PASS; lint exit 0.
5. **browser-qa:** full E2E — fill form (Origin/Destination/Departure/Load/25 miles) -> submit -> results band appears -> map markers render -> move slider +24 h -> marker title still matches "{n}. {Risk} — forecast {ISO}"; console 0 errors; screenshots saved as docs/verification/product-quality/product-quality-05 (initial form), 06 (results after submit), 07 (marker retitle after slider +24h); 08 optional production-style smoke; ALL previous screenshot files kept untouched.
6. **docs-writer:** STATUS.md shows the redesign round logged; TEST_LOG.md contains the second 2026-10-25 entry with the real commands and real outputs; DECISIONS.md appends four dated decisions: (a) Option A via CSS breakout inside TripForm, (b) risk colors follow the test-pinned heatmap.ts hexes (recorded deviation from the originally proposed design sheet), (c) ui/ primitives deleted (0 imports), (d) fonts via @fontsource with exact import lines.

---

## 7. QA gates, hard UI rules, risks, fix-loop

**Gates (all must be green to ship):** npm test 80/80 · tsc -b && vite build PASS · lint exit 0 · Playwright E2E per 6.5 · console 0 errors · visual self-check against the AI-generic tell list: no emoji anywhere (logo included), at most 2 accent hues on any screen (steel accent + amber signal; risk hues are semantic and do not count), no glass/blur/backdrop utilities, chip patterns <= 2 (the layers pills row + the Rank #1 chip; the legend is a dot-list, not chips), rounded-full ONLY on the layers pills row (cards use rounded-card, controls rounded-control), no em-dashes in new copy (em-dash allowed only inside frozen F9/F14 strings).

**Hard invariants:** results stay inside TripForm's tree (18 test renders of <TripForm/>) · RouteOptions root section aria-label untouched (F6) · heatmap.ts and validation.ts untouched · any NEW button inside the form MUST be type="button" (single-submit invariant) · no test files edited, ever.

**Risks + mitigations:**
1. Band breakout clipped by an outer page max-width — mitigation: TripForm's grid is the full-width shell; browser-qa checks 1280 and 1440 widths.
2. Parallel classname drift between coder-new and coder-fix — mitigation: refactor lands first; agents use only 3.3 names; joint gates at M3.
3. dark-matter style fetch fails or is slow — mitigation: current style object kept as catch-fallback (comment with demotiles URL).
4. Accidental F10 double-match (e.g. footer wording) — mitigation: footer attribution phrasing fixed in 4.3-22; grep -c checks in done criteria.
5. Brand-sheet risk hues conflict with tests — resolved: pinned heatmap.ts hexes WIN everywhere; deviation recorded in DECISIONS.md.
6. Patching TripForm near frozen DOM — mitigation: diff policy enforced; reviewer-standards diff vs frozen list 4.1 before M3.

**Fix-loop policy:** fixer reacts only to a failed gate; after every fix the SAME gate re-runs; maximum 3 rounds, then stop and escalate to the orchestrator/user with the failing diff. Tests are recreated by re-running gates, never by editing them.

---

End of plan. Every build agent starts at section 2.

