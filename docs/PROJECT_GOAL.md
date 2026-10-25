# StormRoute — Project Goal

## What StormRoute is

StormRoute is a web application that helps truck drivers and dispatchers choose the safest practical route for a planned trip when hazardous weather (wind, rain, snow) is expected along the way.

Built for the **Spotter AI Full Stack Developer assessment** (Weather-Aware Truck Routing). The single end user to serve well is an ordinary truck driver who is not technical: they enter where they are going, when they leave, and how heavy their load is — and get a clear recommendation of which of three route options carries the least weather risk, with reasons they can read at a glance.

## Problem being solved

A driver hauling a heavy load through a storm system faces different danger levels on different highways: exposed mountain passes in high wind, managed lanes in heavy rain, or unplowed stretches during snowfall. Generic navigation apps rank routes by speed only. StormRoute samples the forecast **along each candidate route at the times the truck would actually arrive there**, classifies risk against truck-load-specific thresholds, counts "risk miles" per route, and recommends the safest route using a fixed priority order mandated by the assessment.

## Intended end-to-end user workflow

1. **Input.** User enters origin, destination, departure date & time, truck load weight (lb), and chooses a checkpoint spacing (10 / 25 / 50 miles).
2. **Routes.** The app geocodes both places and fetches three route alternatives from the routing provider (with distance, duration, ETA, and geometry).
3. **Checkpoints.** For each route, the app computes checkpoint positions at the chosen mile spacing (handling the final partial segment) and estimates each checkpoint's arrival time from route progress.
4. **Weather.** For each checkpoint, the app fetches the hourly forecast at that location for that arrival hour: wind speed, rainfall rate, snowfall rate.
5. **Risk.** A deterministic engine classifies each checkpoint (Low / Moderate / High / Severe / No Travel) using the assessment thresholds plus load-weight rules, and rolls No Travel up to the overall risk per checkpoint.
6. **Score & recommend.** Routes are ranked lexicographically: fewest Severe miles → fewest High miles → lowest average risk → shortest travel time. Routes containing No Travel checkpoints are never presented as safe; if all candidates have No Travel, the user sees "No safe route found" with an explanation.
7. **Map & heatmap.** All three routes, checkpoint markers colored/graded by risk, route metrics and ETAs render on an interactive MapLibre map. A trip-corridor weather heatmap plus a real-data forecast slider (0–48 h) lets the user see how conditions evolve across the departure window, with map/labels/checkpoint values staying consistent with the selected forecast hour.

## Core technologies

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Map | MapLibre GL |
| Backend | Python + Django + Django REST Framework |
| Routing/geocoding | Third-party API selected in `docs/API_PROVIDER_RESEARCH.md` |
| Weather | Third-party hourly forecast API (same doc) |
| Testing | Django `manage.py test`, frontend `tsc` + production build, Playwright browser verification |

## Definition of a successful project

1. All assessment requirements in `docs/ASSESSMENT_SPEC.md` implemented and verified (routes + weather + risk = 40%, UI/map/heatmap performance = 40% weighting).
2. Clean, honest code (15%), docs + walkthrough (5%).
3. Delivered as: GitHub repo, hosted application, 5–10 minute Loom walkthrough — within 16 working hours / 4 calendar days.
4. No fabricated data presented as real; every claim about completeness verified in the real browser.
