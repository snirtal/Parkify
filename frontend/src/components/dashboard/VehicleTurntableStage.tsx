import { Component, lazy, type ReactNode, Suspense, useMemo, useState } from 'react'
import type { ParkingBay } from '../../types/parking'

const VehiclePreview3D = lazy(() =>
  import('./VehiclePreview3D').then((m) => ({ default: m.VehiclePreview3D })),
)

export interface VehicleTurntableStageProps {
  bay: ParkingBay
}

interface PreviewBoundaryProps {
  fallback: ReactNode
  children: ReactNode
}

class PreviewErrorBoundary extends Component<PreviewBoundaryProps, { hasError: boolean }> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) return this.props.fallback
    return this.props.children
  }
}

function canUseWebGL(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const c = document.createElement('canvas')
    return Boolean(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

export function VehicleTurntableStage({ bay }: VehicleTurntableStageProps) {
  const [stepIndex, setStepIndex] = useState(0)
  const webglSupported = useMemo(() => canUseWebGL(), [])

  const vehicle = bay.vehicle
  // Initial quarter-front showroom angle (-0.52 rad), step rotates by 55 degrees
  const targetRotationY = -0.52 + stepIndex * ((Math.PI * 2) / 6)

  const stageGlow =
    bay.status === 'available'
      ? '#22d3ee'
      : bay.status === 'unavailable'
        ? '#f59e0b'
        : '#a855f7'

  const holoBadge = (
    <div className={`turntable__holo turntable__holo--${bay.status}`}>
      <span className="turntable__holo-code">{bay.code}</span>
      <span className="turntable__holo-sub">
        {vehicle ? `${vehicle.model} (${vehicle.bodyType})` : bay.bayClass}
      </span>
    </div>
  )

  return (
    <div className="turntable">
      {/* Status / Alert Floating Pill */}
      {vehicle?.hasAlert ? (
        <div className="turntable__alert-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="#EF4444" aria-hidden="true">
            <path d="M12 3 2 20h20L12 3Zm1 13h-2v2h2v-2Zm0-6h-2v4h2v-4Z" />
          </svg>
          <span>{vehicle.alertTitle ?? 'Sensor Alert'}</span>
        </div>
      ) : (
        <div className={`turntable__state-pill turntable__state-pill--${bay.status}`}>
          <span className="turntable__state-dot" />
          <span>
            {bay.status === 'available'
              ? 'Available Stall'
              : bay.status === 'reserved'
                ? 'Reserved Hold'
                : bay.status === 'unavailable'
                  ? 'Unavailable'
                  : '3D Live Vehicle Preview'}
          </span>
        </div>
      )}

      <div className="turntable__stage">
        {bay.status === 'occupied' && vehicle && webglSupported ? (
          <div className="turntable__canvas-3d" role="img" aria-label={`3D preview of ${vehicle.model}`}>
            <PreviewErrorBoundary fallback={holoBadge}>
              <Suspense fallback={holoBadge}>
                <VehiclePreview3D vehicle={vehicle} targetRotationY={targetRotationY} />
              </Suspense>
            </PreviewErrorBoundary>
          </div>
        ) : (
          <>
            {holoBadge}
            <div
              className="turntable__pedestal"
              style={{
                boxShadow: `0 8px 34px ${stageGlow}55, inset 0 0 18px ${stageGlow}44`,
                borderColor: stageGlow,
              }}
            />
          </>
        )}
        <div className="turntable__orbit-ring" aria-hidden="true" />
      </div>

      {/* Interactive 360° Turntable Rotation Controls */}
      {bay.status === 'occupied' && vehicle && (
        <div className="turntable__rotate-controls" role="group" aria-label="Rotate 3D vehicle preview">
          <button
            type="button"
            className="turntable__rotate-btn"
            onClick={() => setStepIndex((prev) => prev - 1)}
            aria-label="Rotate vehicle left"
            title="Rotate left"
          >
            ‹
          </button>
          <span className="turntable__rotate-dot" aria-hidden="true" />
          <button
            type="button"
            className="turntable__rotate-btn"
            onClick={() => setStepIndex((prev) => prev + 1)}
            aria-label="Rotate vehicle right"
            title="Rotate right"
          >
            ›
          </button>
        </div>
      )}
    </div>
  )
}
