import { useMemo, useState } from 'react'
import { GateActivityTable } from '../components/dashboard'
import { useParkingState } from '../context/useParkingState'
import { deriveGateActivityEvents } from '../utils/reservationUtils'
import './ReservationsPage.css'
import './SettingsPage.css'

export function SessionsPage() {
  const { dataset, sessions, recordEntry, recordExit, submitting } = useParkingState()
  const events = useMemo(
    () => deriveGateActivityEvents(dataset.gateLogs),
    [dataset.gateLogs],
  )
  const [plateNumber, setPlateNumber] = useState('')
  const [spotCode, setSpotCode] = useState(dataset.bays[0]?.code ?? '')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submitEntry = async (event: React.FormEvent) => {
    event.preventDefault()
    if (submitting) return
    setMessage(null)
    const result = await recordEntry(plateNumber, spotCode)
    if (!result.ok) {
      setError(result.error)
      return
    }
    setError(null)
    setPlateNumber('')
    setMessage('Vehicle entry recorded.')
  }

  const submitExit = async () => {
    if (submitting) return
    setMessage(null)
    const result = await recordExit(plateNumber)
    if (!result.ok) {
      setError(result.error)
      return
    }
    setError(null)
    setPlateNumber('')
    setMessage('Vehicle exit recorded.')
  }

  return (
    <div className="sessions-page">
      <section className="dashboard-panel reservations" aria-labelledby="sessions-title">
        <div className="dashboard-panel__header">
          <div>
            <h2 id="sessions-title" className="dashboard-panel__title">
              Active Sessions
            </h2>
            <p className="dashboard-panel__subtitle">
              Open visits from the facility database
            </p>
          </div>
        </div>
        {sessions.length === 0 ? (
          <p className="gate-activity__empty">No active sessions.</p>
        ) : (
          <div className="gate-activity__table-wrap">
            <table className="gate-activity__table">
              <thead>
                <tr>
                  <th>Plate</th>
                  <th>Spot</th>
                  <th>Started</th>
                  <th>Paid until</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td className="gate-activity__plate">{session.plateNumber}</td>
                    <td>{session.bayCode}</td>
                    <td>{session.startedAt}</td>
                    <td>{session.paidUntil ? session.paidUntil.replace('T', ' ').slice(0, 16) : '—'}</td>
                    <td>
                      {session.hasAlert && session.alertTitle
                        ? `${session.status} · ${session.alertTitle}`
                        : session.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <form className="reservations__form" onSubmit={submitEntry}>
          <h3 className="reservations__form-title">Vehicle entry</h3>
          <div className="reservations__form-grid">
            <label className="reservations__field">
              <span className="reservations__label">License plate</span>
              <input
                className="reservations__input"
                value={plateNumber}
                onChange={(event) => setPlateNumber(event.target.value)}
                required
              />
            </label>
            <label className="reservations__field">
              <span className="reservations__label">Parking spot</span>
              <select
                className="reservations__select"
                value={spotCode}
                onChange={(event) => setSpotCode(event.target.value)}
              >
                {dataset.bays.map((bay) => (
                  <option key={bay.id} value={bay.code}>
                    {bay.code}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="reservations__form-actions">
            <button type="submit" className="reservations__btn-primary" disabled={submitting}>
              Record entry
            </button>
            <button
              type="button"
              className="reservations__btn-secondary"
              disabled={submitting}
              onClick={submitExit}
            >
              Record exit
            </button>
          </div>
          {error ? (
            <p className="reservations__error" role="alert">
              {error}
            </p>
          ) : null}
          {message ? (
            <p className="settings-feedback settings-feedback--success" role="status">
              {message}
            </p>
          ) : null}
        </form>
      </section>
      <GateActivityTable events={events} />
    </div>
  )
}
