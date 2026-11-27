import { describe, expect, it } from 'vitest'
import { FACILITY_ID, facilityId } from './facility'

describe('facility configuration', () => {
  it('keeps facility-skyline when no override is configured', () => {
    expect(facilityId(undefined)).toBe('facility-skyline')
    expect(facilityId('')).toBe('facility-skyline')
    expect(facilityId('   ')).toBe('facility-skyline')
  })

  it('uses a configured facility id', () => {
    expect(facilityId(' facility-other ')).toBe('facility-other')
  })

  it('points the app at the resolved facility', () => {
    expect(FACILITY_ID).toBe(facilityId())
  })
})
