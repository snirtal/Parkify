import type { ZoneCapacity } from '../../types/dashboard'
import './ZoneCapacityCard.css'

export interface ZoneCapacityCardProps {
  zones: ZoneCapacity[]
}

export function ZoneCapacityCard({ zones }: ZoneCapacityCardProps) {
  return (
    <section className="dashboard-panel zone-capacity" aria-labelledby="zone-capacity-title">
      <div className="dashboard-panel__header">
        <div>
          <div className="dashboard-panel__title-row">
            <h2 id="zone-capacity-title" className="dashboard-panel__title">
              Zone Capacity Breakdown
            </h2>
            <span className="dashboard-panel__sim-tag">Simulated</span>
          </div>
          <p className="dashboard-panel__subtitle">
            Available, occupied, reserved, and unavailable space distribution by zone
          </p>
        </div>

        <div className="zone-capacity__legend" aria-label="Space status legend">
          <span className="zone-capacity__legend-item">
            <span className="zone-capacity__swatch zone-capacity__swatch--occupied" />
            Occupied
          </span>
          <span className="zone-capacity__legend-item">
            <span className="zone-capacity__swatch zone-capacity__swatch--available" />
            Available
          </span>
          <span className="zone-capacity__legend-item">
            <span className="zone-capacity__swatch zone-capacity__swatch--reserved" />
            Reserved
          </span>
          <span className="zone-capacity__legend-item">
            <span className="zone-capacity__swatch zone-capacity__swatch--unavailable" />
            Unavailable
          </span>
        </div>
      </div>

      <ul className="zone-capacity__list">
        {zones.map((zone) => {
          const safeCap = zone.capacity > 0 ? zone.capacity : 1
          const available = Math.max(
            zone.capacity - zone.occupied - zone.reserved - zone.unavailable,
            0,
          )
          const occPct = (zone.occupied / safeCap) * 100
          const avlPct = (available / safeCap) * 100
          const resPct = (zone.reserved / safeCap) * 100
          const unvPct = (zone.unavailable / safeCap) * 100

          return (
            <li key={zone.id} className="zone-capacity__item">
              <div className="zone-capacity__top">
                <div className="zone-capacity__identity">
                  <span className="zone-capacity__code">{zone.code}</span>
                  <div>
                    <span className="zone-capacity__name">{zone.name}</span>
                    <span className="zone-capacity__category">{zone.category}</span>
                  </div>
                </div>

                <div className="zone-capacity__numbers">
                  <span className="zone-capacity__ratio">
                    <strong>{zone.occupied}</strong> / {zone.capacity} occupied
                  </span>
                  <span className="zone-capacity__available">{available} available</span>
                </div>
              </div>

              <div
                className="zone-capacity__multi-bar"
                role="img"
                aria-label={`${zone.name}: ${zone.occupied} occupied, ${available} available, ${zone.reserved} reserved, ${zone.unavailable} unavailable of ${zone.capacity} spaces`}
              >
                {occPct > 0 && (
                  <span
                    className="zone-capacity__seg zone-capacity__seg--occupied"
                    style={{ width: `${occPct.toFixed(1)}%` }}
                  />
                )}
                {avlPct > 0 && (
                  <span
                    className="zone-capacity__seg zone-capacity__seg--available"
                    style={{ width: `${avlPct.toFixed(1)}%` }}
                  />
                )}
                {resPct > 0 && (
                  <span
                    className="zone-capacity__seg zone-capacity__seg--reserved"
                    style={{ width: `${resPct.toFixed(1)}%` }}
                  />
                )}
                {unvPct > 0 && (
                  <span
                    className="zone-capacity__seg zone-capacity__seg--unavailable"
                    style={{ width: `${unvPct.toFixed(1)}%` }}
                  />
                )}
              </div>

              <div className="zone-capacity__breakdown">
                <span>{zone.occupied} occupied</span>
                <span aria-hidden="true">•</span>
                <span>{available} available</span>
                <span aria-hidden="true">•</span>
                <span>{zone.reserved} reserved</span>
                <span aria-hidden="true">•</span>
                <span>{zone.unavailable} unavailable</span>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
