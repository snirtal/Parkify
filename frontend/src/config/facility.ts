const DEFAULT_FACILITY_ID = 'facility-skyline'

export function facilityId(configured: string | undefined = import.meta.env.VITE_FACILITY_ID): string {
  const value = configured?.trim()
  return value ? value : DEFAULT_FACILITY_ID
}

export const FACILITY_ID = facilityId()
