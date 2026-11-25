import { describe, expect, it } from 'vitest'
import { FACILITY_REFRESH_MS } from './liveRefresh'

describe('live facility refresh', () => {
  it('reloads facility data every two seconds', () => {
    expect(FACILITY_REFRESH_MS).toBe(2000)
  })
})
