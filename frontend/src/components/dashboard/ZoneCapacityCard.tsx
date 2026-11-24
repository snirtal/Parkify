import type { ZoneCapacity } from '../../types/dashboard'
import { ProgressBar, type ProgressBarTone } from './ProgressBar'
import './ZoneCapacityCard.css'

export interface ZoneCapacityCardProps {
  zones: ZoneCapacity[]
}

function getZoneTone(rate: number): ProgressBarTone {
  if (rate >= 90) return 'rose'
  if (rate >= 80) return 'amber'
  if (rate >= 65) return 'primary'
  return 'emerald'
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
            Spot utilization and open capacity by garage zone
          </p>
        </div>
      </div>

      <ul className="zone-capacity__list">
        {zones.map((zone) => {
          const available = Math.max(zone.capacity - zone.occupied, 0)
          const rate = zone.capacity > 0 ? (zone.occupied / zone.capacity) * 100 : 0
          const tone = getZoneTone(rate)

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
                    <strong>{zone.occupied}</strong> / {zone.capacity}
                  </span>
                  <span className="zone-capacity__available">{available} free</span>
                </div>
              </div>

              <ProgressBar
                value={zone.occupied}
                max={zone.capacity}
                tone={tone}
                label={`${zone.name}: ${zone.occupied} of ${zone.capacity} spots occupied`}
              />
            </li>
          )
        })}
      </ul>
    </section>
  )
}
