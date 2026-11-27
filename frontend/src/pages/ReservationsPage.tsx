import { useState } from 'react'
import { Link } from 'react-router-dom'
import '../components/dashboard/DailyOccupancyChart.css'
import '../components/dashboard/GateActivityTable.css'
import { matchesCodeOrPlate } from '../components/parking-map/searchUtils'
import { RESERVATIONS_MANAGE, can } from '../auth/permissions'
import { useAuth } from '../auth/useAuth'
import { useParkingState } from '../context/useParkingState'
import type {
  ParkingBay,
  ReservationDraft,
  ReservationItem,
  ReservationRequestItem,
  ReservationStatus,
} from '../types/parking'
import './ReservationsPage.css'

type StatusFilter = 'all' | ReservationStatus

const STATUS_FILTER_OPTIONS: readonly { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'Active', label: 'Active' },
  { value: 'Scheduled', label: 'Scheduled' },
  { value: 'Completed', label: 'Completed' },
  { value: 'Cancelled', label: 'Cancelled' },
]

function formatBayOptionLabel(bay: ParkingBay): string {
  if (bay.status === 'available') {
    return `${bay.code} — ${bay.bayClass} (Available)`
  }
  if (bay.status === 'reserved') {
    return `${bay.code} — ${bay.bayClass} (Reserved)`
  }
  if (bay.status === 'occupied' && bay.vehicle) {
    return `${bay.code} — ${bay.bayClass} (Occupied until ${bay.vehicle.untilTime.replace('.', ':')})`
  }
  return `${bay.code} — ${bay.bayClass} (Offline)`
}

export function ReservationsPage() {
  const {
    dataset,
    reservations,
    reservationRequests,
    addReservation,
    updateReservation,
    cancelReservation,
    approveReservationRequest,
    rejectReservationRequest,
    submitting,
    status,
  } = useParkingState()
  const { user } = useAuth()
  const canManage = can(user?.role, RESERVATIONS_MANAGE)
  const [requestError, setRequestError] = useState<string | null>(null)

  const [searchQuery, setSearchQuery] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [formMode, setFormMode] = useState<'closed' | 'create' | 'edit'>('closed')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const defaultOpenBay =
    dataset.bays.find((b) => b.status === 'available')?.code ?? 'P-202'

  const [draft, setDraft] = useState<ReservationDraft>({
    plateNumber: '',
    bayCode: defaultOpenBay,
    date: dataset.simulatedDate,
    startTime: '15:00',
    endTime: '17:00',
  })

  const hasQuery = searchQuery.trim().length > 0

  const filteredReservations = reservations.filter((res) => {
    if (statusFilter !== 'all' && res.status !== statusFilter) return false
    return matchesCodeOrPlate(res.bayCode, res.plateNumber, searchQuery)
  })

  const deckP2Bays = dataset.bays.filter((b) => b.deck === 'P2')
  const deckP1Bays = dataset.bays.filter((b) => b.deck === 'P1')

  const handleOpenCreate = () => {
    const firstAvailable =
      dataset.bays.find((b) => b.status === 'available')?.code ?? 'P-202'
    setEditingId(null)
    setFormError(null)
    setDraft({
      plateNumber: '',
      bayCode: firstAvailable,
      date: dataset.simulatedDate,
      startTime: '15:00',
      endTime: '17:00',
    })
    setFormMode('create')
  }

  const handleOpenEdit = (res: ReservationItem) => {
    setEditingId(res.id)
    setFormError(null)
    setDraft({
      plateNumber: res.plateNumber,
      bayCode: res.bayCode,
      date: res.date,
      startTime: res.startTime,
      endTime: res.endTime,
    })
    setFormMode('edit')
  }

  const handleCloseForm = () => {
    setFormMode('closed')
    setEditingId(null)
    setFormError(null)
  }

  const updateField = <K extends keyof ReservationDraft>(
    key: K,
    value: ReservationDraft[K],
  ) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
    if (formError) setFormError(null)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitting) return

    const result =
      formMode === 'edit' && editingId
        ? await updateReservation(editingId, draft)
        : await addReservation(draft)

    if (!result.ok) {
      setFormError(result.error)
      return
    }

    handleCloseForm()
  }

  const handleCancelReservation = async (id: string) => {
    if (submitting) return
    const result = await cancelReservation(id)
    if (!result.ok) {
      setFormError(result.error)
      return
    }
    if (editingId === id) {
      handleCloseForm()
    }
  }

  return (
    <section className="dashboard-panel reservations" aria-labelledby="reservations-title">
      <div className="dashboard-panel__header">
        <div>
          <div className="dashboard-panel__title-row">
            <h2 id="reservations-title" className="dashboard-panel__title">
              Parking Reservations
            </h2>
            <span className="dashboard-panel__sim-tag">Live</span>
          </div>
          <p className="dashboard-panel__subtitle">
            {canManage
              ? 'Review customer requests, then manage scheduled bookings across Deck P2 and Deck P1'
              : 'Review customer requests. Approving a request holds a matching bay.'}
          </p>
        </div>

        {canManage ? (
          <button
            type="button"
            className="reservations__new-btn"
            onClick={handleOpenCreate}
          >
            <span aria-hidden="true">+</span>
            <span>New Reservation</span>
          </button>
        ) : null}
      </div>

      <RequestQueue
        requests={reservationRequests}
        loading={status === 'loading'}
        submitting={submitting}
        error={requestError}
        onApprove={(id) => {
          setRequestError(null)
          void approveReservationRequest(id).then((result) => {
            if (!result.ok) setRequestError(result.error)
          })
        }}
        onReject={(id) => {
          setRequestError(null)
          void rejectReservationRequest(id).then((result) => {
            if (!result.ok) setRequestError(result.error)
          })
        }}
      />

      {canManage && formMode !== 'closed' && (
        <form className="reservations__form" onSubmit={handleSubmit} noValidate>
          <div className="reservations__form-head">
            <h3 className="reservations__form-title">
              {formMode === 'edit' ? 'Edit Reservation' : 'New Reservation'}
            </h3>
            <button
              type="button"
              className="reservations__form-close"
              onClick={handleCloseForm}
              aria-label="Close reservation form"
            >
              ×
            </button>
          </div>

          <div className="reservations__form-grid">
            <div className="reservations__field">
              <label htmlFor="res-plate" className="reservations__label">
                License Plate
              </label>
              <input
                id="res-plate"
                type="text"
                className="reservations__input"
                maxLength={12}
                placeholder="e.g. SKY-712P"
                value={draft.plateNumber}
                onChange={(e) => updateField('plateNumber', e.target.value)}
                required
              />
            </div>

            <div className="reservations__field">
              <label htmlFor="res-bay" className="reservations__label">
                Parking Spot
              </label>
              <select
                id="res-bay"
                className="reservations__select"
                value={draft.bayCode}
                onChange={(e) => updateField('bayCode', e.target.value)}
              >
                <optgroup label="Deck P2">
                  {deckP2Bays.map((bay) => (
                    <option
                      key={bay.id}
                      value={bay.code}
                      disabled={bay.status === 'unavailable'}
                    >
                      {formatBayOptionLabel(bay)}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Deck P1">
                  {deckP1Bays.map((bay) => (
                    <option
                      key={bay.id}
                      value={bay.code}
                      disabled={bay.status === 'unavailable'}
                    >
                      {formatBayOptionLabel(bay)}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>

            <div className="reservations__field">
              <label htmlFor="res-date" className="reservations__label">
                Date
              </label>
              <input
                id="res-date"
                type="date"
                className="reservations__input"
                value={draft.date}
                onChange={(e) => updateField('date', e.target.value)}
                required
              />
            </div>

            <div className="reservations__field">
              <label htmlFor="res-start" className="reservations__label">
                Start Time
              </label>
              <input
                id="res-start"
                type="time"
                className="reservations__input"
                value={draft.startTime}
                onChange={(e) => updateField('startTime', e.target.value)}
                required
              />
            </div>

            <div className="reservations__field">
              <label htmlFor="res-end" className="reservations__label">
                End Time
              </label>
              <input
                id="res-end"
                type="time"
                className="reservations__input"
                value={draft.endTime}
                onChange={(e) => updateField('endTime', e.target.value)}
                required
              />
            </div>
          </div>

          {formError && (
            <div className="reservations__error" role="alert">
              {formError}
            </div>
          )}

          <div className="reservations__form-actions">
            <button
              type="button"
              className="reservations__btn-secondary"
              onClick={handleCloseForm}
            >
              Discard
            </button>
            <button type="submit" className="reservations__btn-primary" disabled={submitting}>
              {formMode === 'edit' ? 'Save Changes' : 'Create Reservation'}
            </button>
          </div>
        </form>
      )}

      {canManage && (
      <>
      <div className="gate-activity__toolbar">
        <div className="gate-activity__search" role="search">
          <svg
            className="gate-activity__search-icon"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="search"
            className="gate-activity__search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape' && hasQuery) {
                e.preventDefault()
                setSearchQuery('')
              }
            }}
            placeholder="Search license plate (e.g. VIP-700S) or spot (e.g. P-203)…"
            aria-label="Search reservations by license plate or parking spot"
          />
          {hasQuery && (
            <button
              type="button"
              className="gate-activity__search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        <div
          className="gate-activity__filters"
          role="group"
          aria-label="Filter reservations by status"
        >
          {STATUS_FILTER_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`gate-activity__filter-btn${statusFilter === option.value ? ' gate-activity__filter-btn--active' : ''}`}
              onClick={() => setStatusFilter(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="gate-activity__table-wrap">
        <table className="gate-activity__table">
          <thead>
            <tr>
              <th scope="col">License Plate</th>
              <th scope="col">Parking Spot</th>
              <th scope="col">Date</th>
              <th scope="col">Start Time</th>
              <th scope="col">End Time</th>
              <th scope="col">Status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredReservations.length > 0 ? (
              filteredReservations.map((res) => {
                const isEditable = res.status === 'Active' || res.status === 'Scheduled'
                const isBeingEdited = editingId === res.id
                return (
                  <tr
                    key={res.id}
                    className={isBeingEdited ? 'reservations__row--editing' : undefined}
                  >
                    <td>
                      <span className="gate-activity__plate">{res.plateNumber}</span>
                    </td>
                    <td>
                      <Link
                        to={`/parking-map?bay=${encodeURIComponent(res.bayCode)}`}
                        className="gate-activity__bay-link"
                        title={`Open ${res.bayCode} on Parking Map`}
                      >
                        <span>{res.bayCode}</span>
                        <span className="gate-activity__bay-arrow" aria-hidden="true">
                          ↗
                        </span>
                      </Link>
                    </td>
                    <td className="reservations__tabular">{res.date}</td>
                    <td className="reservations__tabular">{res.startTime}</td>
                    <td className="reservations__tabular">{res.endTime}</td>
                    <td>
                      <span
                        className={`reservations__status reservations__status--${res.status.toLowerCase()}`}
                      >
                        {res.status}
                      </span>
                    </td>
                    <td>
                      {isEditable ? (
                        <div className="reservations__actions">
                          <button
                            type="button"
                            className="reservations__action-btn"
                            onClick={() => handleOpenEdit(res)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="reservations__action-btn reservations__action-btn--danger"
                            onClick={() => handleCancelReservation(res.id)}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <span className="reservations__action-muted">—</span>
                      )}
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={7} className="gate-activity__empty">
                  No reservations match your search or selected status filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      </>
      )}
    </section>
  )
}

function RequestQueue({
  requests,
  loading,
  submitting,
  error,
  onApprove,
  onReject,
}: {
  requests: ReservationRequestItem[]
  loading: boolean
  submitting: boolean
  error: string | null
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const pending = requests.filter((request) => request.status === 'Pending')
  const reviewed = requests.filter((request) => request.status !== 'Pending').slice(0, 8)

  return (
    <div className="reservations__requests">
      <div className="reservations__requests-head">
        <h3 className="reservations__requests-title">Customer requests</h3>
        <span className="reservations__count">{pending.length} pending</span>
      </div>
      {error && (
        <div className="reservations__error" role="alert">
          {error}
        </div>
      )}
      {loading && requests.length === 0 ? (
        <p className="reservations__requests-empty">Loading requests…</p>
      ) : pending.length === 0 && reviewed.length === 0 ? (
        <p className="reservations__requests-empty">No reservation requests yet.</p>
      ) : (
        <ul className="reservations__request-list">
          {[...pending, ...reviewed].map((request) => (
            <li key={request.id} className="reservations__request">
              <div>
                <strong className="reservations__request-plate">{request.plateNumber}</strong>
                <p className="reservations__request-meta">
                  {request.bayClass} · {formatWhen(request.startsAt)} · {formatDuration(request.durationMinutes)}
                  {request.spotCode ? ` · ${request.spotCode}` : ''}
                </p>
              </div>
              <div className="reservations__request-actions">
                <span className={`reservations__status reservations__status--${request.status.toLowerCase()}`}>
                  {request.status}
                </span>
                {request.status === 'Pending' ? (
                  <>
                    <button
                      type="button"
                      className="reservations__btn-primary"
                      disabled={submitting}
                      onClick={() => onApprove(request.id)}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="reservations__btn-secondary"
                      disabled={submitting}
                      onClick={() => onReject(request.id)}
                    >
                      Reject
                    </button>
                  </>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function formatWhen(value: string): string {
  return value.replace('T', ' ').slice(0, 16)
}

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest}m`
  if (rest === 0) return `${hours}h`
  return `${hours}h ${rest}m`
}
