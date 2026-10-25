import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, cleanup, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TripForm } from './TripForm'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const pad = (n: number) => String(n).padStart(2, '0')

function localStrFrom(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function setDeparture(value: string) {
  const dep = screen.getByLabelText(/Departure/) as HTMLInputElement
  fireEvent.change(dep, { target: { value } })
}

const SUBMIT_BUTTON_NAME = /find route options/i

beforeEach(() => {
  // Default: any network call in a test that did not arrange a mock response fails.
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('network down (default test stub)'))))
})

type CheckpointFixture = {
  checkpointId: string
  routeId: string
  sequence: number
  coordinates: [number, number]
  distanceFromStartMeters: number
  distanceFromStartMiles: number
  elapsedSeconds: number
  arrivalISO: string
  interpolated: boolean
  weather?: {
    checkpointId: string
    arrivalISO: string
    matchedForecastISO: string | null
    timeMatch: "exact" | "out_of_horizon" | "provider_error"
    windMph: number | null
    rainInPerHr: number | null
    snowfallInPerHr: number | null
    provider: "open-meteo"
    providerForecastISO: string | null
  }
}

type CheckpointSummaryFixture = {
  count: number
  requestedIntervalMiles: number
  effectiveIntervalMiles: number
  capped: boolean
  maxPerRoute: number
  geometryDistanceMeters: number
  geometryDistanceMiles: number
  providerDistanceMeters: number
  durationSeconds: number
  samplingMethod: string
  etaMethod: string
}

type RouteFixture = {
  routeId: string
  label: string
  geometry: { type: 'LineString'; coordinates: [number, number][] }
  distanceMeters: number
  distanceMiles: number
  durationSeconds: number
  durationReadable: string
  arrivalISO: string
  providerRouteSummary: string
  checkpoints: CheckpointFixture[]
  checkpointSummary: CheckpointSummaryFixture
}

function routeFixture(index: number, overrides?: Partial<RouteFixture>): RouteFixture {
  const routeId = `rt_fixture${index}000000`
  const distanceMeters = 1614300 + index * 1000
  const durationSeconds = 53400 + index * 600
  const checkpoints: CheckpointFixture[] = [0, 1, 2].map((step) => ({
    checkpointId: `cp_fixture${index}000${step}`,
    routeId,
    sequence: step + 1,
    coordinates: [-87.6324 + step, 41.882 - step] as [number, number],
    distanceFromStartMeters: step * 804672,
    distanceFromStartMiles: step * 500,
    elapsedSeconds: step * 26700,
    arrivalISO: '2026-10-25T12:30:00+00:00',
    interpolated: step === 1,
    weather: {
      checkpointId: `cp_fixture${index}000${step}`,
      arrivalISO: '2026-10-25T12:30:00+00:00',
      matchedForecastISO: '2026-10-25T12:00',
      timeMatch: 'exact' as const,
      windMph: 12.5 + step,
      rainInPerHr: 0.0,
      snowfallInPerHr: 0.0,
      provider: 'open-meteo',
      providerForecastISO: '2026-10-25T12:00',
    },
  }))
  return {
    routeId,
    label: `Route ${index}`,
    geometry: {
      type: 'LineString',
      coordinates: [
        [-87.6324, 41.882],
        [-95.5, 41.2],
        [-104.9861, 39.7417],
      ],
    },
    distanceMeters,
    distanceMiles: 1003 + index * 0.6,
    durationSeconds,
    durationReadable: '14 h 50 min',
    arrivalISO: '2099-01-02T06:50:00+00:00',
    providerRouteSummary: 'I-80 W; I-76 W',
    checkpoints,
    checkpointSummary: {
      count: checkpoints.length,
      requestedIntervalMiles: 25,
      effectiveIntervalMiles: 25,
      capped: false,
      maxPerRoute: 500,
      geometryDistanceMeters: distanceMeters,
      geometryDistanceMiles: 1003.1,
      providerDistanceMeters: distanceMeters,
      durationSeconds,
      samplingMethod: 'haversine-distance-along-linestring',
      etaMethod: 'distance-weighted-provider-duration',
    },
    ...overrides,
  }
}

function routesOkFixture(routes: unknown[], warning: string | null = null) {
  const routeArray = routes as any[];
  return {
    routesAvailable: true,
    trip: {
      origin: 'Chicago, IL',
      destination: 'Denver, CO',
      departureISO: '2026-10-25T12:30:00+00:00',
      loadWeightLb: 34000,
      checkpointIntervalMiles: 25,
    },
    origin: { query: 'Chicago, IL', resolvedName: 'Chicago, Illinois, United States', longitude: -87.6324, latitude: 41.882 },
    destination: { query: 'Denver, CO', resolvedName: 'Denver, Colorado, United States', longitude: -104.9861, latitude: 39.7417 },
    routesRequested: 3,
    routeCount: routes.length,
    threeRoutesReturned: routes.length === 3,
    warning,
    duplicatesDropped: 0,
    routes,
    weatherSummaries: routeArray.map((r) => ({
      routeId: r.routeId,
      totalCheckpoints: r.checkpointSummary.count,
      checkpointsWithWeather: r.checkpointSummary.count,
      checkpointsUnavailable: 0,
      providerForecastStartISO: '2026-10-25T12:00',
      providerForecastEndISO: '2026-10-26T12:00',
    })),
    riskSummaries: routeArray.map((r) => ({
      routeId: r.routeId,
      totalCheckpoints: r.checkpointSummary.count,
      checkpointsWithWeather: r.checkpointSummary.count,
      checkpointsUnknown: 0,
      lowCount: r.checkpointSummary.count,
      moderateCount: 0,
      highCount: 0,
      severeCount: 0,
      noTravelCount: 0,
      severeMiles: 0,
      highMiles: 0,
      avgRiskOrdinal: 0,
      worstCheckpoint: {
        checkpointId: r.checkpoints[0]?.checkpointId ?? 'cp_test',
        arrivalISO: r.checkpoints[0]?.arrivalISO ?? '2026-10-25T12:00:00+00:00',
        riskLevel: 'low',
        factors: ['wind 10.0 mph < 25 → Low; rain 0.000 in/hr < 0.10 → Low; snow 0.00 in/hr < 0.5 → Low'],
      },
      explanation: `Route conditions: ${r.checkpointSummary.count} Low`,
    })),
    recommendation: {
      status: 'recommended',
      explanation: routeArray.length > 0 
        ? `Recommended: ${routeArray[0]?.label ?? 'Route 1'} — best eligible route by lexicographic ranking (fewest severe miles → fewest high miles → lowest avg risk → shortest time).`
        : 'No routes available.',
      recommendedRouteId: routeArray[0]?.routeId ?? 'rt_test',
      rankedRouteIds: routeArray.map((r) => r.routeId),
      routeExplanations: routeArray.reduce((acc: any, r: any) => {
        acc[r.routeId] = `Ranked 1st (0.0 severe mi | 0.0 high mi | avg risk 0.00 | ${r.durationReadable}). Route conditions: ${r.checkpointSummary.count} Low. Distance: ${r.distanceMiles.toFixed(1)} mi. Est. driving time: ${r.durationReadable}.`
        return acc
      }, {}),
    },
  }
}

describe('TripForm initial rendering (a11y contract)', () => {
  it('renders labeled inputs with accessible wiring and sensible defaults', () => {
    render(<TripForm />)
    expect(screen.getByLabelText('Origin')).toHaveValue('')
    expect(screen.getByLabelText('Destination')).toHaveValue('')
    expect(screen.getByLabelText(/Load weight/)).toHaveValue(34_000)
    expect(screen.getByLabelText(/Departure/)).not.toHaveValue('')
    expect(screen.getByRole('group', { name: /checkpoint interval/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '25 miles' })).toBeChecked()
    expect(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME })).toBeEnabled()
  })

  it('limits interval choices to 10, 25, and 50 miles', () => {
    render(<TripForm />)
    expect(screen.getByRole('radio', { name: '10 miles' })).not.toBeDisabled()
    expect(screen.getByRole('radio', { name: '25 miles' })).not.toBeDisabled()
    expect(screen.getByRole('radio', { name: '50 miles' })).not.toBeDisabled()
  })
})

describe('TripForm client-side validation', () => {
  it('shows all first-pass errors together for an emptied form', async () => {
    const user = userEvent.setup()
    render(<TripForm />)
    const weight = screen.getByLabelText(/Load weight/)
    await user.clear(weight)
    setDeparture('')
    await user.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
    expect(screen.getByText(/origin is required/i)).toBeInTheDocument()
    expect(screen.getByText(/destination is required/i)).toBeInTheDocument()
    expect(screen.getByText(/departure date and time is required/i)).toBeInTheDocument()
    expect(screen.getByText(/required — enter pounds/i)).toBeInTheDocument()
    expect(screen.getAllByRole('alert').length).toBeGreaterThanOrEqual(4)
  })

  it('rejects identical origin and destination inline', async () => {
    const user = userEvent.setup()
    render(<TripForm />)
    await user.type(screen.getByLabelText('Origin'), 'Denver, CO')
    await user.type(screen.getByLabelText('Destination'), 'Denver, CO')
    await user.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
    expect(screen.getByText(/must differ from the origin/i)).toBeInTheDocument()
  })

  it('rejects whitespace-only origin', async () => {
    const user = userEvent.setup()
    render(<TripForm />)
    await user.type(screen.getByLabelText('Origin'), '   ')
    await user.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
    expect(screen.getByText(/origin is required/i)).toBeInTheDocument()
  })

  it('rejects negative load weight', async () => {
    const user = userEvent.setup()
    render(<TripForm />)
    const weight = screen.getByLabelText(/Load weight/)
    await user.clear(weight)
    await user.type(weight, '-50')
    await user.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
    expect(screen.getByText(/must not be negative/i)).toBeInTheDocument()
  })

  it('rejects a past departure', () => {
    render(<TripForm />)
    setDeparture(localStrFrom(new Date(Date.now() - 90 * 60 * 1000)))
    fireEvent.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
    expect(screen.getByText(/past/i)).toBeInTheDocument()
  })
})

describe('TripForm backend interaction (Phase 3 route generation)', () => {
  function resolveFetchWith(status: number, body: unknown) {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
      )
    )
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  async function fillValidTrip(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText('Origin'), 'Chicago, IL')
    await user.type(screen.getByLabelText('Destination'), 'Denver, CO')
    // Use a fixed departure time that matches the test fixture (2026-10-25T12:30:00+00:00)
    // Local time for UTC-5 (EST) would be 2026-10-25T07:30
    const dep = screen.getByLabelText(/Departure/) as HTMLInputElement
    fireEvent.change(dep, { target: { value: '2026-10-25T07:30' } })
    await user.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
  }

  it('sends a valid trip payload to the routes endpoint and renders three real route cards', async () => {
    const fetchMock = resolveFetchWith(200, routesOkFixture([routeFixture(1), routeFixture(2), routeFixture(3)]))
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)

    await waitFor(() => expect(screen.getByRole('region', { name: /live route options/i })).toBeInTheDocument())
    // Use getAllByText since route names appear in both route cards and recommendation section
    expect(screen.getAllByText('Route 1').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Route 2').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Route 3').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/via I-80 W; I-76 W/).length).toBe(3)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, requestInit] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(String(url)).toContain('/api/trips/routes/')
    const sent = JSON.parse(String(requestInit.body))
    expect(sent).toMatchObject({
      origin: 'Chicago, IL',
      destination: 'Denver, CO',
      loadWeightLb: 34000,
      checkpointIntervalMiles: 25,
    })
    expect(String(sent.departureISO)).toMatch(/[+-][0-9]{2}:[0-9]{2}$/)
  })

  it('shows distance, duration, checkpoint timing, and honest phase-scope note on each card, without safety claims', async () => {
    resolveFetchWith(200, routesOkFixture([routeFixture(1)]))
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)

    await waitFor(() => expect(screen.getAllByText('Route 1').length).toBeGreaterThanOrEqual(1))
    expect(screen.getAllByText(/^1,00[0-9]\.6? mi/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('14 h 50 min')).toBeInTheDocument()
    expect(screen.getByText(/3 at 25 mi spacing/)).toBeInTheDocument()
    expect(screen.getByText(/sampled along the provider geometry from 0 mi to 1,000 mi/i)).toBeInTheDocument()
    expect(screen.getByText(/weather data from open-meteo.*matched to the exact forecast hour/i)).toBeInTheDocument()
    expect(screen.getByText(/risk classification uses assessment-mandated thresholds/i)).toBeInTheDocument()
    expect(screen.getByText(/constant-average-speed estimate, not traffic- or weather-adjusted/i)).toBeInTheDocument()
    // No card is presented as safest/best: route card headings (h3) must stay neutral.
    const cardHeadings = Array.from(document.querySelectorAll('ol[aria-label="route options"] article h3')).map((el) => el.textContent ?? '')
    for (const heading of cardHeadings) {
      expect(heading.toLowerCase()).not.toMatch(/safest|best|recommended/)
      expect(heading).toMatch(/^Route [0-9]+$/)
    }
  })

  it('discloses a widened checkpoint spacing when the per-route cap applies', async () => {
    const route = routeFixture(1, {
      checkpointSummary: {
        count: 12,
        requestedIntervalMiles: 10,
        effectiveIntervalMiles: 76.25,
        capped: true,
        maxPerRoute: 12,
        geometryDistanceMeters: 1614300,
        geometryDistanceMiles: 1003.1,
        providerDistanceMeters: 1614300,
        durationSeconds: 53400,
        samplingMethod: 'haversine-distance-along-linestring',
        etaMethod: 'distance-weighted-provider-duration',
      },
    })
    resolveFetchWith(200, routesOkFixture([route]))
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)

    await waitFor(() => expect(screen.getAllByText('Route 1').length).toBeGreaterThanOrEqual(1))
    expect(screen.getByText(/12 at 76.25 mi spacing/)).toBeInTheDocument()
    expect(screen.getByText(/widened from 10 mi to stay within 12 per route/i)).toBeInTheDocument()
  })

  it('renders fewer-than-three route counts with the truthful warning', async () => {
    resolveFetchWith(200, routesOkFixture([routeFixture(1), routeFixture(2)], 'Mapbox returned 2 distinct routes for this corridor (three were requested).'))
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)

    await waitFor(() => expect(screen.getAllByText('Route 2').length).toBeGreaterThanOrEqual(1))
    const warning = screen.getByRole('alert')
    expect(warning).toHaveTextContent(/2 distinct routes/)
    expect(screen.queryByText('Route 3')).not.toBeInTheDocument()
  })

  it('single route: card only, warning present, no fabricated alternatives', async () => {
    resolveFetchWith(200, routesOkFixture([routeFixture(3)], 'Mapbox returned 1 distinct route for this corridor (three were requested).'))
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)

    await waitFor(() => expect(screen.getAllByText('Route 3').length).toBeGreaterThanOrEqual(1))
    expect(screen.queryByText(/^Route 1$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^Route 2$/)).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/1 distinct route/)
  })

  it('trims location strings before sending', async () => {
    const fetchMock = resolveFetchWith(200, routesOkFixture([routeFixture(1)]))
    const user = userEvent.setup()
    render(<TripForm />)
    await user.type(screen.getByLabelText('Origin'), '  Chicago, IL  ')
    await user.type(screen.getByLabelText('Destination'), ' Denver, CO ')
    await user.click(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [, requestInit] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    const sent = JSON.parse(String(requestInit.body))
    expect(sent.origin).toBe('Chicago, IL')
    expect(sent.destination).toBe('Denver, CO')
  })

  it('disables submit while pending, preventing duplicate submissions', async () => {
    let settle: (value: Response) => void = () => undefined
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => (settle = resolve)))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<TripForm />)
    await user.type(screen.getByLabelText('Origin'), 'Chicago, IL')
    await user.type(screen.getByLabelText('Destination'), 'Denver, CO')
    const submit = screen.getByRole('button', { name: SUBMIT_BUTTON_NAME })
    await user.click(submit)
    expect(screen.getByRole('button', { name: /finding routes/i })).toBeDisabled()
    await user.click(screen.getByRole('button'))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    settle(
      new Response(JSON.stringify(routesOkFixture([routeFixture(1)])), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    await waitFor(() => expect(screen.getByRole('button', { name: SUBMIT_BUTTON_NAME })).toBeEnabled())
  })

  it('shows backend field errors verbatim and preserves typed values (400 inputs)', async () => {
    resolveFetchWith(400, {
      routesAvailable: false,
      inputErrors: {
        origin: ['Origin must contain some text — please enter a starting location.'],
        loadWeightLb: ['Load weight must not be negative — enter 0 (empty) or more pounds.'],
      },
    })
    const user = userEvent.setup()
    render(<TripForm />)
    const weight = screen.getByLabelText(/Load weight/)
    await user.clear(weight)
    await user.type(weight, '123')
    await fillValidTrip(user)
    await waitFor(() => expect(screen.getByText(/origin must contain some text/i)).toBeInTheDocument())
    expect(screen.getByText(/load weight must not be negative/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Origin')).toHaveValue('Chicago, IL')
    expect(screen.getByLabelText('Destination')).toHaveValue('Denver, CO')
  })

  it('surfaces structured provider errors verbatim and preserves inputs', async () => {
    resolveFetchWith(422, {
      routesAvailable: false,
      error: { code: 'geocode_failed', stage: 'origin', message: 'Could not turn the origin into coordinates. Try a more specific city name or address.' },
    })
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)
    expect(await screen.findByText(/could not turn the origin into coordinates/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Origin')).toHaveValue('Chicago, IL')
    expect(screen.getByLabelText('Destination')).toHaveValue('Denver, CO')
    expect(screen.queryByRole('list', { name: /route options/i })).not.toBeInTheDocument()
  })

  it('surfaces rate-limit copy without tokens on 429', async () => {
    resolveFetchWith(429, {
      routesAvailable: false,
      error: { code: 'rate_limited', message: 'The routing provider temporarily rate-limited this server. Please try again in a few moments.' },
    })
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)
    expect(await screen.findByText(/temporarily rate-limited/i)).toBeInTheDocument()
  })

  it('shows an honest service-unavailable message on network failure, preserving inputs', async () => {
    const user = userEvent.setup()
    render(<TripForm />)
    await fillValidTrip(user)
    expect(await screen.findByText(/backend is not responding/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Origin')).toHaveValue('Chicago, IL')
    expect(screen.getByLabelText('Destination')).toHaveValue('Denver, CO')
    expect(screen.queryByText(/live route options/i)).not.toBeInTheDocument()
  })
})
