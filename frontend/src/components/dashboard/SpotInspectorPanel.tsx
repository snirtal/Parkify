import { useState } from 'react'
import type {
  ChartSlotPoint,
  GateLogItem,
  ParkingBay,
  ZoneBreakdownItem,
} from '../../types/parking'
import { RentalOccupancyChart } from './RentalOccupancyChart'
import { VehicleTurntableStage } from './VehicleTurntableStage'
import './SpotInspectorPanel.css'

export interface SpotInspectorPanelProps {
  bay: ParkingBay
  zones: ZoneBreakdownItem[]
  gateLogs: GateLogItem[]
  yearlySeries: ChartSlotPoint[]
  todaySeries: ChartSlotPoint[]
  onSelectBayByCode?: (bayCode: string) => void
}

type InspectorTab = 'overview' | 'zones' | 'activity'

export function SpotInspectorPanel({
  bay,
  zones,
  gateLogs,
  yearlySeries,
  todaySeries,
  onSelectBayByCode,
}: SpotInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>('overview')

  const vehicle = bay.vehicle
  const primaryTitle = vehicle
    ? vehicle.model
    : bay.status === 'available'
      ? `Bay ${bay.code} — Open Stall`
      : bay.status === 'reserved'
        ? `Bay ${bay.code} — Reserved`
        : `Bay ${bay.code} — Offline`

  const specNumber = vehicle
    ? vehicle.plateNumber
    : bay.status === 'available'
      ? 'OPEN'
      : bay.status === 'reserved'
        ? (bay.reservedPlate ?? 'HOLD')
        : 'LOCK'

  const specBody = vehicle ? vehicle.bodyType : bay.bayClass.split(' ')[0]

  const leftCardTitle = vehicle
    ? vehicle.driverName || vehicle.plateNumber
    : bay.status === 'reserved'
      ? (bay.reservedBy ?? 'Reserved')
      : bay.status === 'available'
        ? 'Instant Check-In'
        : 'Field Tech Ops'

  const leftCardSub = vehicle
    ? vehicle.monitoringLabel
    : bay.status === 'reserved'
      ? 'ANPR Gate Armed'
      : bay.status === 'available'
        ? bay.bayClass
        : (bay.maintenanceReason ?? 'Diagnostics active')

  const leftInitials = vehicle
    ? vehicle.driverInitials
    : bay.status === 'available'
      ? 'GO'
      : bay.status === 'reserved'
        ? 'VIP'
        : 'OP'

  const rightCardHeading =
    bay.status === 'available'
      ? 'Smart tariff'
      : bay.status === 'unavailable'
        ? 'Est. online'
        : vehicle
          ? 'Paid until'
          : 'Reserved until'

  const rightCardSub =
    bay.status === 'available'
      ? bay.ratePerHour
        ? 'Dynamic bay rate'
        : 'Available now'
      : bay.status === 'unavailable'
        ? 'Automated check'
        : (vehicle?.untilCaption ?? 'Scheduled window')

  const rightCardValue = vehicle
    ? vehicle.untilTime
    : bay.status === 'reserved'
      ? (bay.reservedUntil ?? '--.--')
      : bay.status === 'available'
        ? bay.ratePerHour || 'Open'
        : '--.--'

  return (
    <aside className="inspector-shell" aria-label="Selected parking space details">
      {/* Folder-Style Top Tabs matching reference screenshot */}
      <div className="inspector-tabs" role="tablist" aria-label="Inspector sections">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={`inspector-tab${activeTab === 'overview' ? ' inspector-tab--active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'activity'}
          className={`inspector-tab${activeTab === 'activity' ? ' inspector-tab--active' : ''}`}
          onClick={() => setActiveTab('activity')}
        >
          <span>Gate Log</span>
          <span className="inspector-tab__badge">{gateLogs.length}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'zones'}
          className={`inspector-tab${activeTab === 'zones' ? ' inspector-tab--active' : ''}`}
          onClick={() => setActiveTab('zones')}
        >
          Zones
        </button>
      </div>

      {/* Main Glassmorphic Inspector Card */}
      <div className="inspector-card">
        <span className="inspector-card__edge-notch" aria-hidden="true" />

        {activeTab === 'overview' && (
          <div className="inspector-overview">
            <VehicleTurntableStage bay={bay} />

            <div className="inspector-specs">
              <h2 className="inspector-specs__title">{primaryTitle}</h2>

              <div className="inspector-specs__grid">
                <div className="inspector-specs__item">
                  <span className="inspector-specs__val">{bay.code}</span>
                  <span className="inspector-specs__lbl">Seat</span>
                </div>
                <div className="inspector-specs__item">
                  <span className="inspector-specs__val">{specNumber}</span>
                  <span className="inspector-specs__lbl">Number</span>
                </div>
                <div className="inspector-specs__item">
                  <span className="inspector-specs__val">{specBody}</span>
                  <span className="inspector-specs__lbl">Body</span>
                </div>
              </div>
            </div>

            {/* Dual Bento Subcards matching Sarah Connor + Reserved until 14.08 */}
            <div className="inspector-bento">
              <div className="inspector-bento__purple">
                <div>
                  <div className="inspector-bento__name">{leftCardTitle}</div>
                  <div className="inspector-bento__caption">{leftCardSub}</div>
                </div>

                <div className="inspector-bento__footer">
                  <span className="inspector-bento__avatar">{leftInitials}</span>
                  <span className="inspector-bento__action-icon" aria-hidden="true">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1C10.61 21 3 13.39 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.58a1 1 0 0 1-.25 1.01l-2.2 2.2Z" />
                    </svg>
                  </span>
                </div>
              </div>

              <div className="inspector-bento__dark">
                <div>
                  <div className="inspector-bento__name">{rightCardHeading}</div>
                  <div className="inspector-bento__caption">{rightCardSub}</div>
                </div>

                <div className="inspector-bento__footer">
                  <span className="inspector-bento__big-time">{rightCardValue}</span>
                  <span className="inspector-bento__cal-icon" aria-hidden="true">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <rect x="3" y="4" width="18" height="18" rx="2" />
                      <line x1="16" y1="2" x2="16" y2="6" />
                      <line x1="8" y1="2" x2="8" y2="6" />
                      <line x1="3" y1="10" x2="21" y2="10" />
                    </svg>
                  </span>
                </div>
              </div>
            </div>

            <RentalOccupancyChart
              yearlySeries={yearlySeries}
              todaySeries={todaySeries}
              totalSpots={zones.reduce((sum, z) => sum + z.capacity, 0)}
            />
          </div>
        )}

        {activeTab === 'zones' && (
          <div className="inspector-subview">
            <div className="inspector-subview__header">
              <h3>Zone Capacity Breakdown</h3>
              <span>Current zone distribution</span>
            </div>

            <ul className="inspector-zones">
              {zones.map((zone) => {
                const pct = Math.round((zone.occupied / zone.capacity) * 100)
                const free = zone.capacity - zone.occupied - zone.reserved - zone.unavailable
                return (
                  <li key={zone.id} className="inspector-zones__item">
                    <div className="inspector-zones__top">
                      <div>
                        <span className="inspector-zones__name">{zone.name}</span>
                        <span className="inspector-zones__meta">
                          {zone.occupied}/{zone.capacity} occupied • {free} free
                          {zone.reserved > 0 ? ` • ${zone.reserved} reserved` : ''}
                        </span>
                      </div>
                      <span className="inspector-zones__pct">{pct}%</span>
                    </div>
                    <div
                      className="inspector-zones__bar"
                      role="progressbar"
                      aria-label={zone.name}
                      aria-valuenow={zone.occupied}
                      aria-valuemin={0}
                      aria-valuemax={zone.capacity}
                    >
                      <div
                        className={`inspector-zones__fill inspector-zones__fill--${zone.accent}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="inspector-subview">
            <div className="inspector-subview__header">
              <h3>Recent Gate Activity</h3>
              <span>Click a bay code to focus in 3D</span>
            </div>

            <ul className="inspector-logs">
              {gateLogs.map((log) => (
                <li key={log.id} className="inspector-logs__item">
                  <div className="inspector-logs__left">
                    <span
                      className={`inspector-logs__dir inspector-logs__dir--${log.direction}`}
                    >
                      {log.direction === 'entry' ? 'IN' : 'OUT'}
                    </span>
                    <div>
                      <span className="inspector-logs__plate">{log.plateNumber}</span>
                      <span className="inspector-logs__gate">
                        {log.gateName} • {log.timestamp}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="inspector-logs__bay-btn"
                    onClick={() => {
                      onSelectBayByCode?.(log.bayCode)
                      setActiveTab('overview')
                    }}
                  >
                    {log.bayCode}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </aside>
  )
}
