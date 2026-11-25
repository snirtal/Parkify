import { useState } from 'react'
import type { ChartSlotPoint } from '../../types/parking'

export interface RentalOccupancyChartProps {
  yearlySeries: ChartSlotPoint[]
  todaySeries: ChartSlotPoint[]
  totalSpots: number
}

export function RentalOccupancyChart({
  yearlySeries,
  todaySeries,
  totalSpots,
}: RentalOccupancyChartProps) {
  const [period, setPeriod] = useState<'today' | 'year'>('today')
  const series = period === 'today' ? todaySeries : yearlySeries
  const [activeIdx, setActiveIdx] = useState(series.length - 1)

  const safeIdx = Math.min(activeIdx, series.length - 1)
  const activePoint = series[safeIdx]

  const svgW = 300
  const svgH = 112
  const padX = 25
  const padTop = 16
  const padBottom = 8
  const plotW = svgW - padX * 2
  const plotH = svgH - padTop - padBottom

  const coords = series.map((pt, idx) => {
    const x = padX + (idx / Math.max(series.length - 1, 1)) * plotW
    const y = padTop + (1 - pt.occupancyPct / 100) * plotH
    return { ...pt, x, y }
  })

  const curvePath = coords.reduce((acc, pt, i, arr) => {
    if (i === 0) return `M ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`
    const prev = arr[i - 1]
    const cx1 = prev.x + (pt.x - prev.x) * 0.45
    const cy1 = prev.y
    const cx2 = prev.x + (pt.x - prev.x) * 0.55
    const cy2 = pt.y
    return `${acc} C ${cx1.toFixed(1)} ${cy1.toFixed(1)}, ${cx2.toFixed(1)} ${cy2.toFixed(1)}, ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`
  }, '')

  return (
    <div className="inspector-chart">
      <div className="inspector-chart__head">
        <div>
          <span className="inspector-chart__title">
            {period === 'today' ? 'Daily Occupancy' : 'Monthly Avg Occupancy'}
          </span>
          <span className="inspector-chart__live-val">
            <strong>{activePoint.label}:</strong> {activePoint.occupancyPct}% ({activePoint.vehicles}/
            {totalSpots} bays)
          </span>
        </div>

        <button
          type="button"
          className="inspector-chart__period-btn"
          onClick={() => {
            const next = period === 'today' ? 'year' : 'today'
            setPeriod(next)
            setActiveIdx(next === 'today' ? todaySeries.length - 1 : 2)
          }}
          aria-label="Toggle chart timeframe"
        >
          <span>{period === 'today' ? 'Today' : 'This year'}</span>
          <span aria-hidden="true">▾</span>
        </button>
      </div>

      <div className="inspector-chart__stage">
        {/* Horizontal Y-Axis Reference Gridlines (100%, 50%, 0%) */}
        <div className="inspector-chart__gridlines" aria-hidden="true">
          <div className="inspector-chart__gridline">
            <span>100%</span>
          </div>
          <div className="inspector-chart__gridline">
            <span>50%</span>
          </div>
          <div className="inspector-chart__gridline">
            <span>0%</span>
          </div>
        </div>

        {/* Vertical Rounded Pillars with Direct Value Readout */}
        <div className="inspector-chart__bars">
          {coords.map((pt, idx) => {
            const isSelected = idx === safeIdx
            const barClasses = [
              'inspector-chart__bar-col',
              isSelected ? 'inspector-chart__bar-col--active' : '',
              pt.isHatched && !isSelected ? 'inspector-chart__bar-col--hatched' : '',
            ]
              .filter(Boolean)
              .join(' ')

            return (
              <button
                key={pt.label}
                type="button"
                className={barClasses}
                onMouseEnter={() => setActiveIdx(idx)}
                onFocus={() => setActiveIdx(idx)}
                onClick={() => setActiveIdx(idx)}
                aria-label={`${pt.label}: ${pt.occupancyPct}% (${pt.vehicles} of ${totalSpots} spaces)`}
              >
                <span
                  className={`inspector-chart__bar-pct${isSelected ? ' inspector-chart__bar-pct--active' : ''}`}
                >
                  {pt.occupancyPct}%
                </span>
                <div className="inspector-chart__bar-track">
                  <div
                    className="inspector-chart__bar-fill"
                    style={{ height: `${Math.max(pt.occupancyPct, 14)}%` }}
                  />
                </div>
                <span
                  className={`inspector-chart__bar-label${isSelected ? ' inspector-chart__bar-label--active' : ''}`}
                >
                  {pt.label}
                </span>
              </button>
            )
          })}
        </div>

        {/* Smooth Spline Curve + Data Point Markers */}
        <svg
          viewBox={`0 0 ${svgW} ${svgH}`}
          className="inspector-chart__curve-svg"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path
            d={curvePath}
            fill="none"
            stroke="#22d3ee"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
          {coords.map((pt, idx) => {
            const isSelected = idx === safeIdx
            return (
              <circle
                key={pt.label}
                cx={pt.x}
                cy={pt.y}
                r={isSelected ? 4.2 : 2.6}
                fill={isSelected ? '#ffffff' : '#17142b'}
                stroke="#22d3ee"
                strokeWidth="2"
              />
            )
          })}
        </svg>
      </div>
    </div>
  )
}
