import { useMemo, useState } from 'react'
import '../components/dashboard/DailyOccupancyChart.css'
import { useParkingState } from '../context/useParkingState'
import type { FacilitySettings } from '../types/parking'
import './SettingsPage.css'

interface SettingsFormState {
  facilityName: string
  facilityAddress: string
  operatingHours: string
  hourlyRate: string
  dailyMaxRate: string
  gracePeriodMinutes: string
  evSurcharge: string
  highOccupancyAlert: boolean
  reservationOverstayAlert: boolean
  spaceFaultAlert: boolean
}

function toFormState(settings: FacilitySettings): SettingsFormState {
  return {
    facilityName: settings.facilityName,
    facilityAddress: settings.facilityAddress,
    operatingHours: settings.operatingHours,
    hourlyRate: settings.hourlyRate.toFixed(2),
    dailyMaxRate: settings.dailyMaxRate.toFixed(2),
    gracePeriodMinutes: String(settings.gracePeriodMinutes),
    evSurcharge: settings.evSurcharge.toFixed(2),
    highOccupancyAlert: settings.highOccupancyAlert,
    reservationOverstayAlert: settings.reservationOverstayAlert,
    spaceFaultAlert: settings.spaceFaultAlert,
  }
}

export function SettingsPage() {
  const { dataset, settings, updateSettings, resetSettings } = useParkingState()

  const [form, setForm] = useState<SettingsFormState>(() => toFormState(settings))
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const floorSummary = useMemo(() => {
    const decks = Array.from(new Set(dataset.bays.map((b) => b.deck)))
    return `${decks.length} ${decks.length === 1 ? 'floor' : 'floors'} (${decks
      .map((d) => `Deck ${d}`)
      .join(', ')})`
  }, [dataset.bays])

  const updateField = <K extends keyof SettingsFormState>(
    key: K,
    value: SettingsFormState[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    if (errorMessage) setErrorMessage(null)
    if (statusMessage) setStatusMessage(null)
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const parsedHourly =
      form.hourlyRate.trim() === '' ? Number.NaN : Number(form.hourlyRate)
    const parsedDailyMax =
      form.dailyMaxRate.trim() === '' ? Number.NaN : Number(form.dailyMaxRate)
    const parsedGrace =
      form.gracePeriodMinutes.trim() === ''
        ? Number.NaN
        : Number(form.gracePeriodMinutes)
    const parsedEvSurcharge =
      form.evSurcharge.trim() === '' ? Number.NaN : Number(form.evSurcharge)

    const candidate: FacilitySettings = {
      facilityName: form.facilityName,
      facilityAddress: form.facilityAddress,
      operatingHours: form.operatingHours,
      hourlyRate: parsedHourly,
      dailyMaxRate: parsedDailyMax,
      gracePeriodMinutes: parsedGrace,
      evSurcharge: parsedEvSurcharge,
      highOccupancyAlert: form.highOccupancyAlert,
      reservationOverstayAlert: form.reservationOverstayAlert,
      spaceFaultAlert: form.spaceFaultAlert,
    }

    const result = updateSettings(candidate)
    if (!result.ok) {
      setStatusMessage(null)
      setErrorMessage(result.error)
      return
    }

    setErrorMessage(null)
    setForm(
      toFormState({
        ...candidate,
        facilityName: candidate.facilityName.trim(),
        facilityAddress: candidate.facilityAddress.trim(),
        operatingHours: candidate.operatingHours.trim(),
        hourlyRate: Number(parsedHourly.toFixed(2)),
        dailyMaxRate: Number(parsedDailyMax.toFixed(2)),
        gracePeriodMinutes: Math.round(parsedGrace),
        evSurcharge: Number(parsedEvSurcharge.toFixed(2)),
      }),
    )
    setStatusMessage('Settings saved to browser storage.')
  }

  const handleReset = () => {
    const defaults = resetSettings()
    setForm(toFormState(defaults))
    setErrorMessage(null)
    setStatusMessage('Settings restored to default values.')
  }

  return (
    <form className="settings-form" onSubmit={handleSubmit} noValidate>
      <div className="settings-grid">
        {/* 1. Facility Profile */}
        <section className="dashboard-panel" aria-labelledby="settings-profile-title">
          <div className="dashboard-panel__header">
            <div>
              <div className="dashboard-panel__title-row">
                <h2 id="settings-profile-title" className="dashboard-panel__title">
                  Facility Profile
                </h2>
                <span className="dashboard-panel__sim-tag">Simulated</span>
              </div>
              <p className="dashboard-panel__subtitle">
                Identity, location, operating window, and live structural capacity
              </p>
            </div>
          </div>

          <div className="settings-fields">
            <div className="settings-field">
              <label htmlFor="setting-facility-name" className="settings-label">
                Facility Name
              </label>
              <input
                id="setting-facility-name"
                type="text"
                className="settings-input"
                maxLength={60}
                value={form.facilityName}
                onChange={(e) => updateField('facilityName', e.target.value)}
                required
              />
            </div>

            <div className="settings-field">
              <label htmlFor="setting-facility-address" className="settings-label">
                Address
              </label>
              <input
                id="setting-facility-address"
                type="text"
                className="settings-input"
                maxLength={90}
                value={form.facilityAddress}
                onChange={(e) => updateField('facilityAddress', e.target.value)}
                required
              />
            </div>

            <div className="settings-field">
              <label htmlFor="setting-operating-hours" className="settings-label">
                Operating Hours
              </label>
              <input
                id="setting-operating-hours"
                type="text"
                className="settings-input"
                maxLength={50}
                value={form.operatingHours}
                onChange={(e) => updateField('operatingHours', e.target.value)}
                required
              />
            </div>

            <div className="settings-readonly-row">
              <div className="settings-field">
                <label htmlFor="setting-capacity" className="settings-label">
                  Parking Capacity (Read-Only)
                </label>
                <input
                  id="setting-capacity"
                  type="text"
                  className="settings-input settings-input--readonly"
                  value={`${dataset.totalSpots} spaces`}
                  readOnly
                />
              </div>

              <div className="settings-field">
                <label htmlFor="setting-floors" className="settings-label">
                  Floor Count (Read-Only)
                </label>
                <input
                  id="setting-floors"
                  type="text"
                  className="settings-input settings-input--readonly"
                  value={floorSummary}
                  readOnly
                />
              </div>
            </div>
          </div>
        </section>

        {/* 2. Pricing */}
        <section className="dashboard-panel" aria-labelledby="settings-pricing-title">
          <div className="dashboard-panel__header">
            <div>
              <div className="dashboard-panel__title-row">
                <h2 id="settings-pricing-title" className="dashboard-panel__title">
                  Pricing
                </h2>
                <span className="dashboard-panel__sim-tag">Simulated</span>
              </div>
              <p className="dashboard-panel__subtitle">
                Base parking rates, daily caps, grace period, and EV fast-charge add-on
              </p>
            </div>
          </div>

          <div className="settings-fields settings-fields--two-col">
            <div className="settings-field">
              <label htmlFor="setting-hourly-rate" className="settings-label">
                Hourly Parking Rate ($/hr)
              </label>
              <input
                id="setting-hourly-rate"
                type="number"
                step="0.10"
                min="0.10"
                max="500"
                className="settings-input"
                value={form.hourlyRate}
                onChange={(e) => updateField('hourlyRate', e.target.value)}
                required
              />
            </div>

            <div className="settings-field">
              <label htmlFor="setting-daily-max" className="settings-label">
                Daily Maximum Rate ($/day)
              </label>
              <input
                id="setting-daily-max"
                type="number"
                step="0.50"
                min="0.50"
                max="2000"
                className="settings-input"
                value={form.dailyMaxRate}
                onChange={(e) => updateField('dailyMaxRate', e.target.value)}
                required
              />
            </div>

            <div className="settings-field">
              <label htmlFor="setting-grace-period" className="settings-label">
                Free Grace Period (minutes)
              </label>
              <input
                id="setting-grace-period"
                type="number"
                step="1"
                min="0"
                max="180"
                className="settings-input"
                value={form.gracePeriodMinutes}
                onChange={(e) => updateField('gracePeriodMinutes', e.target.value)}
                required
              />
            </div>

            <div className="settings-field">
              <label htmlFor="setting-ev-surcharge" className="settings-label">
                EV Charging Surcharge ($/hr)
              </label>
              <input
                id="setting-ev-surcharge"
                type="number"
                step="0.10"
                min="0"
                max="100"
                className="settings-input"
                value={form.evSurcharge}
                onChange={(e) => updateField('evSurcharge', e.target.value)}
                required
              />
            </div>
          </div>
        </section>
      </div>

      {/* 3. Notification Preferences */}
      <section className="dashboard-panel" aria-labelledby="settings-notifications-title">
        <div className="dashboard-panel__header">
          <div>
            <div className="dashboard-panel__title-row">
              <h2 id="settings-notifications-title" className="dashboard-panel__title">
                Notification Preferences
              </h2>
              <span className="dashboard-panel__sim-tag">Simulated</span>
            </div>
            <p className="dashboard-panel__subtitle">
              Configure which simulated telemetry alerts surface in the operator header feed
            </p>
          </div>
        </div>

        <div className="settings-toggles">
          <div className="settings-toggle-row">
            <div className="settings-toggle-copy">
              <span id="lbl-high-occ" className="settings-toggle-title">
                High occupancy alert
              </span>
              <span className="settings-toggle-desc">
                Alert operator console when facility utilization exceeds 85% capacity.
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={form.highOccupancyAlert}
              aria-labelledby="lbl-high-occ"
              className={`settings-switch${form.highOccupancyAlert ? ' settings-switch--on' : ''}`}
              onClick={() => updateField('highOccupancyAlert', !form.highOccupancyAlert)}
            >
              <span className="settings-switch__thumb" aria-hidden="true" />
            </button>
          </div>

          <div className="settings-toggle-row">
            <div className="settings-toggle-copy">
              <span id="lbl-overstay" className="settings-toggle-title">
                Reservation overstay alert
              </span>
              <span className="settings-toggle-desc">
                Flag vehicles remaining in a bay past their scheduled or paid parking window.
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={form.reservationOverstayAlert}
              aria-labelledby="lbl-overstay"
              className={`settings-switch${form.reservationOverstayAlert ? ' settings-switch--on' : ''}`}
              onClick={() =>
                updateField('reservationOverstayAlert', !form.reservationOverstayAlert)
              }
            >
              <span className="settings-switch__thumb" aria-hidden="true" />
            </button>
          </div>

          <div className="settings-toggle-row">
            <div className="settings-toggle-copy">
              <span id="lbl-fault" className="settings-toggle-title">
                Parking space fault alert
              </span>
              <span className="settings-toggle-desc">
                Surface offline stalls, surface sensor recalibrations, and charger diagnostics.
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={form.spaceFaultAlert}
              aria-labelledby="lbl-fault"
              className={`settings-switch${form.spaceFaultAlert ? ' settings-switch--on' : ''}`}
              onClick={() => updateField('spaceFaultAlert', !form.spaceFaultAlert)}
            >
              <span className="settings-switch__thumb" aria-hidden="true" />
            </button>
          </div>
        </div>
      </section>

      <div className="settings-footer">
        {errorMessage ? (
          <span className="settings-feedback settings-feedback--error" role="alert">
            {errorMessage}
          </span>
        ) : statusMessage ? (
          <span className="settings-feedback settings-feedback--success" role="status">
            {statusMessage}
          </span>
        ) : (
          <span className="settings-feedback">
            Changes persist locally in browser storage and update the header immediately.
          </span>
        )}

        <div className="settings-actions">
          <button
            type="button"
            className="settings-btn-reset"
            onClick={handleReset}
          >
            Reset
          </button>
          <button type="submit" className="settings-btn-save">
            Save Changes
          </button>
        </div>
      </div>
    </form>
  )
}
