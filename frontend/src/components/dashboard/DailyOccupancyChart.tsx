import { useState } from 'react'
import type { HourlyOccupancyPoint } from '../../types/dashboard'
import './DailyOccupancyChart.css'

export interface DailyOccupancyChartProps {
  data: HourlyOccupancyPoint[]
  totalCapacity: number
  reservedSpots?: number
  unavailableSpots?: number
}

const CHART_WIDTH = 640
const CHART_HEIGHT = 230
const PADDING = { top: 18, right: 18, bottom: 34, left: 42 }

function latestOccupiedIndex(data: HourlyOccupancyPoint[]): number {
  for (let index = data.length - 1; index >= 0; index -= 1) {
    if (data[index].occupied > 0) return index
  }
  return Math.max(data.length - 1, 0)
}

export function DailyOccupancyChart({
  data,
  totalCapacity,
  reservedSpots = 0,
  unavailableSpots = 0,
}: DailyOccupancyChartProps) {
  const [activeIndex, setActiveIndex] = useState<number>(latestOccupiedIndex(data))

  if (data.length === 0 || totalCapacity <= 0) {
    return null
  }

  const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom

  const points = data.map((point, index) => {
    const pointReserved = reservedSpots
    const pointUnavailable = unavailableSpots
    const xRatio = data.length === 1 ? 0.5 : index / (data.length - 1)
    const yRatio = Math.min(Math.max(point.occupied / totalCapacity, 0), 1)
    const x = PADDING.left + xRatio * plotWidth
    const y = PADDING.top + (1 - yRatio) * plotHeight
    const rate = Number(((point.occupied / totalCapacity) * 100).toFixed(1))

    return {
      ...point,
      x,
      y,
      rate,
      reserved: pointReserved,
      unavailable: pointUnavailable,
      available: Math.max(
        totalCapacity - point.occupied - pointReserved - pointUnavailable,
        0,
      ),
    }
  })

  const linePath = points
    .map((pt, idx) => `${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`)
    .join(' ')

  const baselineY = PADDING.top + plotHeight
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${baselineY.toFixed(1)} L ${points[0].x.toFixed(1)} ${baselineY.toFixed(1)} Z`

  const peakPoint = points.reduce((best, current) =>
    current.occupied > best.occupied ? current : best,
  )
  const avgOccupied = Math.round(
    points.reduce((sum, pt) => sum + pt.occupied, 0) / points.length,
  )
  const avgRate = Number(((avgOccupied / totalCapacity) * 100).toFixed(1))

  const selected = points[Math.min(activeIndex, points.length - 1)]
  const yTicks = [0, 0.25, 0.5, 0.75, 1]

  return (
    <section className="dashboard-panel occupancy-chart" aria-labelledby="occupancy-chart-title">
      <div className="dashboard-panel__header">
        <div>
          <div className="dashboard-panel__title-row">
            <h2 id="occupancy-chart-title" className="dashboard-panel__title">
              Daily Occupancy Curve
            </h2>
            <span className="dashboard-panel__sim-tag">Live</span>
          </div>
          <p className="dashboard-panel__subtitle">
            Hourly vehicle occupancy across {totalCapacity} total bays today
          </p>
        </div>

        <div className="occupancy-chart__stats">
          <div className="occupancy-chart__stat">
            <span className="occupancy-chart__stat-label">Peak</span>
            <span className="occupancy-chart__stat-value">
              {peakPoint.occupied} ({peakPoint.hour})
            </span>
          </div>
          <div className="occupancy-chart__stat">
            <span className="occupancy-chart__stat-label">Daily Avg</span>
            <span className="occupancy-chart__stat-value">{avgRate}%</span>
          </div>
        </div>
      </div>

      <div className="occupancy-chart__readout" aria-live="polite">
        <span className="occupancy-chart__readout-time">{selected.hour}</span>
        <span className="occupancy-chart__readout-metric">
          <strong>{selected.occupied}</strong> occupied
        </span>
        <span className="occupancy-chart__readout-sep" aria-hidden="true">
          •
        </span>
        <span className="occupancy-chart__readout-metric">
          <strong>{selected.available}</strong> available
        </span>
        {selected.reserved > 0 && (
          <>
            <span className="occupancy-chart__readout-sep" aria-hidden="true">
              •
            </span>
            <span className="occupancy-chart__readout-metric">
              <strong>{selected.reserved}</strong> reserved
            </span>
          </>
        )}
        {selected.unavailable > 0 && (
          <>
            <span className="occupancy-chart__readout-sep" aria-hidden="true">
              •
            </span>
            <span className="occupancy-chart__readout-metric">
              <strong>{selected.unavailable}</strong> unavailable
            </span>
          </>
        )}
        <span className="occupancy-chart__readout-rate">{selected.rate}% utilization</span>
      </div>

      <div className="occupancy-chart__canvas">
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          className="occupancy-chart__svg"
          role="img"
          aria-label="Line chart of hourly parking occupancy"
        >
          <defs>
            <linearGradient id="occupancyAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.24" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {yTicks.map((tick) => {
            const y = PADDING.top + (1 - tick) * plotHeight
            return (
              <g key={tick}>
                <line
                  x1={PADDING.left}
                  y1={y}
                  x2={CHART_WIDTH - PADDING.right}
                  y2={y}
                  className="occupancy-chart__gridline"
                />
                <text
                  x={PADDING.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="occupancy-chart__axis-label"
                >
                  {Math.round(tick * 100)}%
                </text>
              </g>
            )
          })}

          <path d={areaPath} fill="url(#occupancyAreaGradient)" />
          <path d={linePath} className="occupancy-chart__line" />

          <line
            x1={selected.x}
            y1={PADDING.top}
            x2={selected.x}
            y2={baselineY}
            className="occupancy-chart__cursor-line"
          />

          {points.map((pt, index) => {
            const isSelected = index === activeIndex
            return (
              <g key={pt.hour}>
                <text
                  x={pt.x}
                  y={CHART_HEIGHT - 10}
                  textAnchor="middle"
                  className={`occupancy-chart__axis-label${isSelected ? ' occupancy-chart__axis-label--active' : ''}`}
                >
                  {pt.hour}
                </text>

                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isSelected ? 5.5 : 3.5}
                  className={`occupancy-chart__dot${isSelected ? ' occupancy-chart__dot--active' : ''}`}
                />

                <rect
                  x={pt.x - plotWidth / (points.length * 2)}
                  y={PADDING.top}
                  width={plotWidth / points.length}
                  height={plotHeight}
                  fill="transparent"
                  tabIndex={0}
                  role="button"
                  aria-label={`${pt.hour}: ${pt.occupied} occupied (${pt.rate}%)`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onFocus={() => setActiveIndex(index)}
                  onClick={() => setActiveIndex(index)}
                  className="occupancy-chart__hit-area"
                />
              </g>
            )
          })}
        </svg>
      </div>
    </section>
  )
}
