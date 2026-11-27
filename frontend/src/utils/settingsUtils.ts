import type { FacilitySettings } from '../types/parking'

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
