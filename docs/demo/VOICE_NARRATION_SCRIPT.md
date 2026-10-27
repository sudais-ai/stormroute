# StormRoute — Live Demo VOICE SCRIPT (for stormroute-walkthrough-DETAIL-12min-FINAL.mp4, 11:55)

How to use: play the video and read the lines at the timestamps below.
Timestamps ±5–10 s; if a ring appears, mention it. Speak slow and relaxed.
Silent breaks are fine — silence looks natural during loading.

---

## PART A — INTRO (0:00 – 0:26)

**[0:00 – 0:08] Aap apna personal intro yahan shuru karein — yeh placeholder hai:**
> "Hi everyone, this is **[your name]**, and today I am going to show you a live demo of a tool I built. It is called StormRoute. Let us start."

**[0:08 – 0:26] (Header ring dikhega, "Online" pill green)**
> "So here is the app. See the little green pill on the top right that says Online — that means the map, the geocoder and the weather services are all connected and healthy right now."

---

## PART B — PROJECT OVERVIEW (0:26 – 1:58)

**[0:26 – 0:50] (Poora layout scroll ho kar dikh raha hoga)**
> "What does this tool do? Very simply — you plan a truck trip, and it checks the weather along the whole road before you roll."
> "What is in it? The city you start from, the city you go to, your departure time, and the load weight. That is it."

**[0:50 – 1:06]**
> "How does it work? It asks a real routing provider for the real highways, and then it checks the weather for every stop on the way — at the exact hour your truck reaches there."

**[1:06 – 1:58] (Form fields par rings aa rahi hongi)**
> "Why does that matter? Because a loaded truck reacts very differently to wind than a small car. This tool warns the driver before the trip, not during it."
> "So in short: real roads, real weather, one clear answer — the safest route first."

---

## PART C — TRIP 1 (MAIN WALKTHROUGH)

**[1:58 – 3:09] (Form tour + validation: 4 red errors ek-ek ring ke saath)**
> "First, the form. Note the little notes under each field — plain city names only, no coordinates needed."
> "Now let me test the safety net: I submit with empty fields, and it shows a clear error under every missing one. Nothing is guessed, and the user always knows what to fix."

**[3:09 – 4:04] (Trip 1 fill — origin, destination, departure, load, interval rings)**
> "Now my first real trip: Chicago to Denver — a cross-country corridor on the I-80 and I-76."
> "Departure is two days out, so forecasts are fresh. Load is thirty-four thousand pounds — over the heavy-load line, so stricter wind rules apply to this truck."
> "And I ask for a weather reading every twenty-five miles."
> "The echo line under the form repeats exactly what I asked — this keeps the user and the tool on the same page."

**[4:04 – 4:44] (Submit + pending line + working)**
> "Press the button."
> "Now here is the honest part — no fake spinner. It tells us: checking real roads and live weather, usually ten to twenty-five seconds. Behind the scenes it is fetching route geometry and hourly forecasts for every checkpoint."

**[4:44 – 5:45] (Results: Route 1 card rings)**
> "Results are in. Route 1 is rank number one."
> "This badge is Low — the worst level found along the whole route decides the badge."
> "Everything is on the card: 1,003 miles, about fifteen hours of driving, arrival at 23:26 — the truck clock at the destination — and the highway names: I-80, then I-76 West. All real provider data."
> "One honest note: this corridor has two real routes, and only two are shown. It never invents a fake third route."

**[5:45 – 6:40] (Map corridor fit karte dekh lenge)**
> "Now the map. Blue is the selected route, and the other color is the alternative."
> "Every colored dot on the map is one weather reading for one checkpoint."

---

## PART D — RISK LEVELS LESSON (legend rows par rings aa rahi hongi)

**[6:40 – 7:42] Har level ke ring par yeh line boliye (pace: ek ring per breath):**
> "Let me explain the risk levels on this legend, one by one — this is the heart of the tool."
> "Green, Low — no rule triggered: wind under 25 miles per hour, rain under 0.10 inches per hour, snow under half an inch per hour."
> "Amber, Moderate — wind 25 to under 35, or the matching band for rain and snow."
> "Orange, High — wind 35 to under 45, or rain 0.25 to under 0.50, or snow 1 to under 2 inches per hour."
> "Red, Severe — wind 45 to under 55 for lighter loads, or rain up to exactly one inch per hour, or snow up to exactly three."
> "Dark red, No Travel — these numbers cross the safety line: wind 55 or more for any load, or 45 to 55 miles per hour with over 30,000 pounds, or rain over one inch, or snow over three. When this appears, the route is pulled from the top pick — it cannot be the recommendation."
> "And grey, Unknown — the weather data is missing for that stop. It is shown honestly instead of hiding it or inventing a number."

**[7:42 – 8:08] (Legend notes rings)**
> "These two notes matter: one reading every eleven kilometers, and colors follow the hour you choose on the slider."

---

## PART E — MAP + SLIDER

**[8:08 – 8:30] (Zoom in + one dot ringed + hover)**
> "Let me zoom in. Every dot is the forecast for the truck's arrival hour at that exact point on the road."
> "Hover a dot and you get the plain numbers: wind speed, rain, snowfall, and the matched forecast hour."

**[8:30 – 8:56] (Route pills)**
> "These pills at the bottom switch which route is highlighted. Pressed means selected. The data never changes, only the focus."

**[8:56 – 9:57] (Slider sweep +12, +24, +36, +48, back to 0)**
> "Now the forecasting slider. The ticks go from zero to forty-eight hours from the forecast baseline."
> "As I slide — say plus twenty-four hours — the dots recolor for that hour. Same checkpoints, same distances, just the forecast hour of every stop shifts with the slider."
> "Back to zero — the baseline hour."

**[9:57 – 10:23] (Footer / disclaimer ring)**
> "At the very bottom there is an honest disclaimer: these route-mile values are model estimates for planning, not real-time road conditions. Weather comes from Open-Meteo, the map from Carto, and routes from Mapbox."

---

## PART F — TRIP 2 (10:23 – 10:52)

**[10:23 – 10:52] (Reload + Dallas → Memphis fill + results)**
> "Trip two — a different part of the country: Dallas, Texas to Memphis, Tennessee."
> "Lighter load this time — twenty-seven thousand five hundred pounds, under the heavy-load line."
> "And tighter sampling: a stop every ten miles. That is why you see ninety-six checkpoint dots here. Same pipeline, new data, zero code changes."

---

## PART G — TRIP 3 + HEAVY LOAD RULES (10:52 – 11:21)

**[10:52 – 11:21] (NYC → Boston, 52,000 lb rings)**
> "Trip three — the heavy one. New York to Boston, at fifty-two thousand pounds, sampled every fifty miles — a short northeast hop."
> "Heavy loads catch severe winds sooner. Above forty thousand pounds, winds between thirty-five and fifty-five miles per hour escalate the level much faster for this specific truck."
> "And the No Travel line: over one hundred twenty-five miles per? No — wind fifty-five plus miles per hour for any load, forty-five to fifty-five with over thirty thousand pounds, rain over one inch per hour, or snow over three."
> "Today the forecast is calm, so it stays Low — but these rules are in the code and covered by automated tests. We show real results, never staged ones."

---

## PART H — CLOSING (11:21 – 11:55)

**[11:21 – 11:55] (Final recap + thanks)**
> "Quick recap of what you saw: real routes from a real provider, hourly weather for every stop, clear priority-based ranking, honest errors, and honest disclaimers."
> "Three different trips, one pipeline, zero fake data."
> "Thank you for watching!"

---

### Mic tips (short)
- Ek line boliye, 1–2 second pause, agli line. Rings aa to woh mention karo, na aaye to skip karo (aage chal lo).
- Numbers thoda dheere bolo: "thirty-four thousand pounds", "twenty-five miles".
- Loading scenes (8–15 s) me chup na bithao — wahan ke "it is working / behind the scenes" lines use karo.
- Timestamps ±5–10 s slide karte hain — ring/screen follow karke bolna sab se best hai.
