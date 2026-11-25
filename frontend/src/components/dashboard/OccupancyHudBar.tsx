import './OccupancyHudBar.css'

export interface OccupancyHudBarProps {
  totalSpots: number
  availableSpots: number
  occupiedSpots: number
  reservedSpots: number
  unavailableSpots: number
  occupancyRate: number
  rateTrend: string
}

export function OccupancyHudBar({
  totalSpots,
  availableSpots,
  occupiedSpots,
  reservedSpots,
  unavailableSpots,
  occupancyRate,
  rateTrend,
}: OccupancyHudBarProps) {
  const radius = 17
  const circumference = 2 * Math.PI * radius
  const strokeOffset = circumference * (1 - Math.min(Math.max(occupancyRate, 0), 100) / 100)

  return (
    <section className="hud-strip" aria-label="Facility occupancy summary">
      <div className="hud-strip__card">
        <span className="hud-strip__dot hud-strip__dot--purple" />
        <div className="hud-strip__body">
          <span className="hud-strip__label">Total Spaces</span>
          <div className="hud-strip__val-row">
            <span className="hud-strip__val">{totalSpots}</span>
            <span className="hud-strip__meta">{unavailableSpots} offline</span>
          </div>
        </div>
      </div>

      <div className="hud-strip__card">
        <span className="hud-strip__dot hud-strip__dot--cyan" />
        <div className="hud-strip__body">
          <span className="hud-strip__label">Available Spaces</span>
          <div className="hud-strip__val-row">
            <span className="hud-strip__val hud-strip__val--cyan">{availableSpots}</span>
            <span className="hud-strip__meta">Open stalls</span>
          </div>
        </div>
      </div>

      <div className="hud-strip__card">
        <span className="hud-strip__dot hud-strip__dot--blue" />
        <div className="hud-strip__body">
          <span className="hud-strip__label">Occupied Spaces</span>
          <div className="hud-strip__val-row">
            <span className="hud-strip__val">{occupiedSpots}</span>
            <span className="hud-strip__meta">+{reservedSpots} reserved</span>
          </div>
        </div>
      </div>

      <div className="hud-strip__card hud-strip__card--rate">
        <svg width="44" height="44" viewBox="0 0 44 44" className="hud-strip__ring" aria-hidden="true">
          <circle
            cx="22"
            cy="22"
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="4"
          />
          <circle
            cx="22"
            cy="22"
            r={radius}
            fill="none"
            stroke="url(#hudRingGrad)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeOffset}
            transform="rotate(-90 22 22)"
          />
          <defs>
            <linearGradient id="hudRingGrad" x1="0" y1="0" x2="44" y2="44">
              <stop offset="0%" stopColor="#22D3EE" />
              <stop offset="100%" stopColor="#A855F7" />
            </linearGradient>
          </defs>
        </svg>

        <div className="hud-strip__body">
          <span className="hud-strip__label">Occupancy Rate</span>
          <div className="hud-strip__val-row">
            <span className="hud-strip__val">{occupancyRate}%</span>
            <span className="hud-strip__trend">{rateTrend}</span>
          </div>
        </div>
      </div>
    </section>
  )
}
