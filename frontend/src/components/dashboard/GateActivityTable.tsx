import { useState } from 'react'
import { Link } from 'react-router-dom'
import type {
  GateActivityEvent,
  GateEventType,
  GateSessionStatus,
} from '../../types/dashboard'
import { matchesCodeOrPlate } from '../parking-map/searchUtils'
import './GateActivityTable.css'

export interface GateActivityTableProps {
  events: GateActivityEvent[]
}

type EventFilter = 'all' | GateEventType
type StatusFilter = 'all' | GateSessionStatus

const STATUS_OPTIONS: readonly { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'Active', label: 'Active' },
  { value: 'Reserved', label: 'Reserved' },
  { value: 'Completed', label: 'Completed' },
]

export function GateActivityTable({ events }: GateActivityTableProps) {
  const [filter, setFilter] = useState<EventFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')

  const hasQuery = searchQuery.trim().length > 0

  const filteredEvents = events.filter((evt) => {
    if (filter !== 'all' && evt.eventType !== filter) return false
    if (statusFilter !== 'all' && evt.status !== statusFilter) return false
    return matchesCodeOrPlate(evt.bayNumber, evt.plateNumber, searchQuery)
  })

  return (
    <section className="dashboard-panel gate-activity" aria-labelledby="gate-activity-title">
      <div className="dashboard-panel__header">
        <div>
          <div className="dashboard-panel__title-row">
            <h2 id="gate-activity-title" className="dashboard-panel__title">
              Recent Gate Activity
            </h2>
            <span className="dashboard-panel__sim-tag">Live</span>
          </div>
          <p className="dashboard-panel__subtitle">
            Latest vehicle barrier events across facility entry and exit lanes
          </p>
        </div>

        <div className="gate-activity__filters" role="group" aria-label="Filter gate events">
          {(['all', 'entry', 'exit'] as const).map((option) => {
            const label =
              option === 'all' ? 'All Events' : option === 'entry' ? 'Entries' : 'Exits'
            return (
              <button
                key={option}
                type="button"
                className={`gate-activity__filter-btn${filter === option ? ' gate-activity__filter-btn--active' : ''}`}
                onClick={() => setFilter(option)}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

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
            placeholder="Search license plate (e.g. VEL-204X) or space (e.g. P-204)…"
            aria-label="Search license plate or parking space number"
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
          aria-label="Filter by session status"
        >
          {STATUS_OPTIONS.map((option) => (
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
              <th scope="col">Time</th>
              <th scope="col">License Plate</th>
              <th scope="col">Direction</th>
              <th scope="col">Gate Lane</th>
              <th scope="col">Assigned Bay</th>
              <th scope="col">Session Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.length > 0 ? (
              filteredEvents.map((event) => (
                <tr key={event.id}>
                  <td className="gate-activity__time">{event.timestamp}</td>
                  <td>
                    <span className="gate-activity__plate">{event.plateNumber}</span>
                  </td>
                  <td>
                    <span
                      className={`gate-activity__direction gate-activity__direction--${event.eventType}`}
                    >
                      {event.eventType === 'entry' ? 'Entry' : 'Exit'}
                    </span>
                  </td>
                  <td className="gate-activity__gate">{event.gateName}</td>
                  <td>
                    <Link
                      to={`/parking-map?bay=${encodeURIComponent(event.bayNumber)}`}
                      className="gate-activity__bay-link"
                      title={`Open ${event.bayNumber} on Parking Map`}
                    >
                      <span>{event.bayNumber}</span>
                      <span className="gate-activity__bay-arrow" aria-hidden="true">
                        ↗
                      </span>
                    </Link>
                  </td>
                  <td>
                    <div className="gate-activity__status-cell">
                      <span
                        className={`gate-activity__status gate-activity__status--${event.status.toLowerCase()}`}
                      >
                        {event.status}
                      </span>
                      {event.duration && (
                        <span className="gate-activity__duration">{event.duration}</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="gate-activity__empty">
                  No sessions match your search or selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
