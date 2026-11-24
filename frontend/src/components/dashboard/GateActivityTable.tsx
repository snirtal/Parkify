import { useState } from 'react'
import type { GateActivityEvent, GateEventType } from '../../types/dashboard'
import './GateActivityTable.css'

export interface GateActivityTableProps {
  events: GateActivityEvent[]
}

type EventFilter = 'all' | GateEventType

export function GateActivityTable({ events }: GateActivityTableProps) {
  const [filter, setFilter] = useState<EventFilter>('all')

  const filteredEvents =
    filter === 'all' ? events : events.filter((evt) => evt.eventType === filter)

  return (
    <section className="dashboard-panel gate-activity" aria-labelledby="gate-activity-title">
      <div className="dashboard-panel__header">
        <div>
          <div className="dashboard-panel__title-row">
            <h2 id="gate-activity-title" className="dashboard-panel__title">
              Recent Gate Activity
            </h2>
            <span className="dashboard-panel__sim-tag">Simulated</span>
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
            {filteredEvents.map((event) => (
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
                  <span className="gate-activity__bay">{event.bayNumber}</span>
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
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
