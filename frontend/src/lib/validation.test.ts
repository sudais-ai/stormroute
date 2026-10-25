import { describe, it, expect } from 'vitest'
import {
  departureLocalToISO,
  defaultDepartureLocal,
  validateTripForm,
} from './validation'

const futureLocalStr = (): string => {
  const d = new Date(Date.now() + 3 * 3_600_000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const validForm = () => ({
  origin: 'Chicago, IL',
  destination: 'Denver, CO',
  departureLocal: futureLocalStr(),
  loadWeightLb: '34000',
  checkpointIntervalMiles: 25 as const,
})

describe('departureLocalToISO', () => {
  it('produces an ISO timestamp with a real offset suffix', () => {
    const iso = departureLocalToISO(futureLocalStr())
    expect(iso).toMatch(/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}$/)
  })

  it('matches the browser-local offset (minutes-level round trip)', () => {
    const local = futureLocalStr()
    const iso = departureLocalToISO(local)
    const built = new Date(iso)
    const roundTrip = `${built.getFullYear()}-${String(built.getMonth() + 1).padStart(2, '0')}-${String(built.getDate()).padStart(2, '0')}T${String(built.getHours()).padStart(2, '0')}:${String(built.getMinutes()).padStart(2, '0')}`
    expect(roundTrip).toBe(local)
  })

  it('returns empty string for unparseable input', () => {
    expect(departureLocalToISO('not-a-date')).toBe('')
  })
})

describe('defaultDepartureLocal', () => {
  it('is a future datetime-local string rounded to 5 minutes', () => {
    const value = defaultDepartureLocal()
    expect(value).toMatch(/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}$/)
    expect(new Date(value).getTime()).toBeGreaterThan(Date.now())
    const parsed = new Date(value)
    expect(parsed.getSeconds()).toBe(0)
  })
})

describe('validateTripForm', () => {
  it('accepts a fully valid form and returns normalized values', () => {
    const result = validateTripForm(validForm())
    expect(result.ok).toBe(true)
    if (!result.ok) return
    expect(result.trip.origin).toBe('Chicago, IL')
    expect(result.trip.destination).toBe('Denver, CO')
    expect(result.trip.loadWeightLb).toBe(34000)
    expect(result.trip.checkpointIntervalMiles).toBe(25)
    expect(result.trip.departureISO).toContain('T')
  })

  it('rejects missing origin', () => {
    const result = validateTripForm({ ...validForm(), origin: '' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.origin).toMatch(/origin/i)
  })

  it('rejects whitespace-only origin', () => {
    const result = validateTripForm({ ...validForm(), origin: '   ' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.origin).toBeDefined()
  })

  it('rejects identical origin and destination', () => {
    const result = validateTripForm({ ...validForm(), destination: 'Chicago, IL' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.destination).toMatch(/differ/i)
  })

  it('rejects identical after trim normalization', () => {
    const result = validateTripForm({ ...validForm(), origin: '  Denver, CO', destination: 'Denver, CO  ' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.destination).toBeDefined()
  })

  it('rejects missing departure', () => {
    const result = validateTripForm({ ...validForm(), departureLocal: '' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.departureLocal).toMatch(/required/i)
  })

  it('rejects past departure', () => {
    const d = new Date(Date.now() - 2 * 3_600_000)
    const pad = (n: number) => String(n).padStart(2, '0')
    const pastLocal = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
    const result = validateTripForm({ ...validForm(), departureLocal: pastLocal })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.departureLocal).toMatch(/past/i)
  })

  it('accepts zero load weight', () => {
    const result = validateTripForm({ ...validForm(), loadWeightLb: '0' })
    expect(result.ok).toBe(true)
  })

  it('rejects negative load weight', () => {
    const result = validateTripForm({ ...validForm(), loadWeightLb: '-50' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.loadWeightLb).toMatch(/negative/i)
  })

  it('rejects non-numeric load weight', () => {
    const result = validateTripForm({ ...validForm(), loadWeightLb: 'heavy' })
    expect(result.ok).toBe(false)
    if (result.ok) return
    expect(result.errors.loadWeightLb).toMatch(/number/i)
  })

  it('accepts all spec intervals', () => {
    for (const interval of [10, 25, 50] as const) {
      const result = validateTripForm({ ...validForm(), checkpointIntervalMiles: interval })
      expect(result.ok).toBe(true)
    }
  })
})
