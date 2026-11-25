import { SMART_PARKING_DATA } from '../data/mockParkingData'
import type { FacilitySettings } from '../types/parking'

export const SETTINGS_STORAGE_KEY = 'parkify.facilitySettings.v1'

export const DEFAULT_FACILITY_SETTINGS: FacilitySettings = {
  facilityName: SMART_PARKING_DATA.facilityName,
  facilityAddress: SMART_PARKING_DATA.facilityAddress,
  operatingHours: '00:00 – 23:59 (24/7)',
  hourlyRate: 4.2,
  dailyMaxRate: 28.0,
  gracePeriodMinutes: 15,
  evSurcharge: 0.6,
  highOccupancyAlert: true,
  reservationOverstayAlert: true,
  spaceFaultAlert: true,
}

export function validateFacilitySettings(settings: FacilitySettings): string | null {
  if (settings.facilityName.trim().length < 2) {
    return 'Facility name must be at least 2 characters.'
  }

  if (settings.facilityAddress.trim().length < 4) {
    return 'Facility address must be at least 4 characters.'
  }

  if (settings.operatingHours.trim().length < 3) {
    return 'Operating hours cannot be empty.'
  }

  if (!Number.isFinite(settings.hourlyRate) || settings.hourlyRate <= 0 || settings.hourlyRate > 500) {
    return 'Hourly parking rate must be greater than $0.00 and at most $500.00.'
  }

  if (
    !Number.isFinite(settings.dailyMaxRate) ||
    settings.dailyMaxRate <= 0 ||
    settings.dailyMaxRate > 2000
  ) {
    return 'Daily maximum rate must be greater than $0.00 and at most $2,000.00.'
  }

  if (settings.dailyMaxRate < settings.hourlyRate) {
    return 'Daily maximum rate must be greater than or equal to the hourly parking rate.'
  }

  if (
    !Number.isFinite(settings.gracePeriodMinutes) ||
    !Number.isInteger(settings.gracePeriodMinutes) ||
    settings.gracePeriodMinutes < 0 ||
    settings.gracePeriodMinutes > 180
  ) {
    return 'Free grace period must be a whole number between 0 and 180 minutes.'
  }

  if (
    !Number.isFinite(settings.evSurcharge) ||
    settings.evSurcharge < 0 ||
    settings.evSurcharge > 100
  ) {
    return 'EV charging surcharge must be between $0.00 and $100.00.'
  }

  return null
}

export function loadStoredSettings(): FacilitySettings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (!raw) return DEFAULT_FACILITY_SETTINGS

    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return DEFAULT_FACILITY_SETTINGS

    const obj = parsed as Record<string, unknown>

    const candidate: FacilitySettings = {
      facilityName:
        typeof obj.facilityName === 'string'
          ? obj.facilityName
          : DEFAULT_FACILITY_SETTINGS.facilityName,
      facilityAddress:
        typeof obj.facilityAddress === 'string'
          ? obj.facilityAddress
          : DEFAULT_FACILITY_SETTINGS.facilityAddress,
      operatingHours:
        typeof obj.operatingHours === 'string'
          ? obj.operatingHours
          : DEFAULT_FACILITY_SETTINGS.operatingHours,
      hourlyRate:
        typeof obj.hourlyRate === 'number'
          ? obj.hourlyRate
          : DEFAULT_FACILITY_SETTINGS.hourlyRate,
      dailyMaxRate:
        typeof obj.dailyMaxRate === 'number'
          ? obj.dailyMaxRate
          : DEFAULT_FACILITY_SETTINGS.dailyMaxRate,
      gracePeriodMinutes:
        typeof obj.gracePeriodMinutes === 'number'
          ? obj.gracePeriodMinutes
          : DEFAULT_FACILITY_SETTINGS.gracePeriodMinutes,
      evSurcharge:
        typeof obj.evSurcharge === 'number'
          ? obj.evSurcharge
          : DEFAULT_FACILITY_SETTINGS.evSurcharge,
      highOccupancyAlert:
        typeof obj.highOccupancyAlert === 'boolean'
          ? obj.highOccupancyAlert
          : DEFAULT_FACILITY_SETTINGS.highOccupancyAlert,
      reservationOverstayAlert:
        typeof obj.reservationOverstayAlert === 'boolean'
          ? obj.reservationOverstayAlert
          : DEFAULT_FACILITY_SETTINGS.reservationOverstayAlert,
      spaceFaultAlert:
        typeof obj.spaceFaultAlert === 'boolean'
          ? obj.spaceFaultAlert
          : DEFAULT_FACILITY_SETTINGS.spaceFaultAlert,
    }

    return validateFacilitySettings(candidate) === null
      ? candidate
      : DEFAULT_FACILITY_SETTINGS
  } catch {
    return DEFAULT_FACILITY_SETTINGS
  }
}

export function saveStoredSettings(settings: FacilitySettings): void {
  try {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  } catch {
    // Ignore storage quota / private mode failures
  }
}

export function clearStoredSettings(): void {
  try {
    window.localStorage.removeItem(SETTINGS_STORAGE_KEY)
  } catch {
    // Ignore storage quota / private mode failures
  }
}
