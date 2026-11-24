import { OrbitControls, OrthographicCamera } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { Component, type ReactNode, useMemo, useRef, useState } from 'react'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import type { BayStatus, ParkingBay } from '../../types/parking'
import { GarageArchitecture3D } from './GarageArchitecture3D'
import { ParkingBay3D } from './ParkingBay3D'
import { StudioEnvironment3D } from './StudioEnvironment3D'
import './IsometricGarage3D.css'

export interface IsometricGarage3DProps {
  bays: ParkingBay[]
  selectedBayId: string
  snapshotTimestamp: string
  onSelectBay: (bayId: string) => void
  expanded?: boolean
}

type StatusFilter = 'all' | BayStatus

interface SceneErrorBoundaryProps {
  fallback: ReactNode
  children: ReactNode
}

interface SceneErrorBoundaryState {
  hasError: boolean
}

class SceneErrorBoundary extends Component<SceneErrorBoundaryProps, SceneErrorBoundaryState> {
  state: SceneErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): SceneErrorBoundaryState {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback
    }
    return this.props.children
  }
}

function canUseWebGL(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const canvas = document.createElement('canvas')
    return Boolean(
      canvas.getContext('webgl2') ||
        canvas.getContext('webgl') ||
        canvas.getContext('experimental-webgl'),
    )
  } catch {
    return false
  }
}

const DEFAULT_ZOOM = 37
const MIN_ZOOM = 24
const MAX_ZOOM = 66

export function IsometricGarage3D({
  bays,
  selectedBayId,
  snapshotTimestamp,
  onSelectBay,
  expanded = false,
}: IsometricGarage3DProps) {
  const selectedBayObj = bays.find((b) => b.id === selectedBayId)
  const [activeDeck, setActiveDeck] = useState<'P2' | 'P1'>(selectedBayObj?.deck ?? 'P2')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [cameraZoom, setCameraZoom] = useState(DEFAULT_ZOOM)
  const controlsRef = useRef<OrbitControlsImpl | null>(null)

  const webglAvailable = useMemo(() => canUseWebGL(), [])

  const currentDeck =
    selectedBayObj && selectedBayObj.deck !== activeDeck ? selectedBayObj.deck : activeDeck

  const deckBays = useMemo(
    () => bays.filter((bay) => bay.deck === currentDeck),
    [bays, currentDeck],
  )

  const statusCounts = useMemo(() => {
    return {
      available: deckBays.filter((b) => b.status === 'available').length,
      occupied: deckBays.filter((b) => b.status === 'occupied').length,
      reserved: deckBays.filter((b) => b.status === 'reserved').length,
      unavailable: deckBays.filter((b) => b.status === 'unavailable').length,
    }
  }, [deckBays])

  const handleDeckSwitch = (deck: 'P2' | 'P1') => {
    setActiveDeck(deck)
    const firstOnDeck = bays.find((b) => b.deck === deck)
    if (firstOnDeck) {
      onSelectBay(firstOnDeck.id)
    }
  }

  const handleZoomIn = () => {
    setCameraZoom((prev) => Math.min(prev + 6, MAX_ZOOM))
  }

  const handleZoomOut = () => {
    setCameraZoom((prev) => Math.max(prev - 6, MIN_ZOOM))
  }

  const handleResetView = () => {
    setCameraZoom(DEFAULT_ZOOM)
    controlsRef.current?.reset()
  }

  const fallbackGrid = (
    <div className="garage-stage__fallback" role="region" aria-label="Interactive bay grid">
      {deckBays.map((bay) => {
        const isSelected = bay.id === selectedBayId
        return (
          <button
            key={bay.id}
            type="button"
            className={`garage-fallback-bay garage-fallback-bay--${bay.status}${isSelected ? ' garage-fallback-bay--selected' : ''}`}
            onClick={() => onSelectBay(bay.id)}
          >
            <span className="garage-fallback-bay__code">{bay.code}</span>
            <span className="garage-fallback-bay__state">
              {bay.vehicle ? bay.vehicle.model : bay.status}
            </span>
          </button>
        )
      })}
    </div>
  )

  const startX = -6.75
  const spacingX = 2.7

  return (
    <section
      className={`garage-stage${expanded ? ' garage-stage--expanded' : ''}`}
      aria-label="Interactive 3D isometric parking garage"
    >
      {/* Top Floating HUD Bar: Deck Switcher + Status Legend Filters */}
      <div className="garage-stage__hud-top">
        <div className="garage-stage__decks" role="tablist" aria-label="Garage deck selector">
          {(['P2', 'P1'] as const).map((deck) => (
            <button
              key={deck}
              type="button"
              role="tab"
              aria-selected={currentDeck === deck}
              className={`garage-stage__deck-btn${currentDeck === deck ? ' garage-stage__deck-btn--active' : ''}`}
              onClick={() => handleDeckSwitch(deck)}
            >
              Deck {deck}
            </button>
          ))}
        </div>

        <div className="garage-stage__legend" role="group" aria-label="Filter parking spaces by state">
          <button
            type="button"
            className={`garage-legend-pill${statusFilter === 'all' ? ' garage-legend-pill--active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            All ({deckBays.length})
          </button>
          <button
            type="button"
            className={`garage-legend-pill${statusFilter === 'available' ? ' garage-legend-pill--active' : ''}`}
            onClick={() =>
              setStatusFilter((prev) => (prev === 'available' ? 'all' : 'available'))
            }
          >
            <span className="garage-legend-dot garage-legend-dot--available" />
            Available ({statusCounts.available})
          </button>
          <button
            type="button"
            className={`garage-legend-pill${statusFilter === 'occupied' ? ' garage-legend-pill--active' : ''}`}
            onClick={() =>
              setStatusFilter((prev) => (prev === 'occupied' ? 'all' : 'occupied'))
            }
          >
            <span className="garage-legend-dot garage-legend-dot--occupied" />
            Occupied ({statusCounts.occupied})
          </button>
          <button
            type="button"
            className={`garage-legend-pill${statusFilter === 'reserved' ? ' garage-legend-pill--active' : ''}`}
            onClick={() =>
              setStatusFilter((prev) => (prev === 'reserved' ? 'all' : 'reserved'))
            }
          >
            <span className="garage-legend-dot garage-legend-dot--reserved" />
            Reserved ({statusCounts.reserved})
          </button>
          <button
            type="button"
            className={`garage-legend-pill${statusFilter === 'unavailable' ? ' garage-legend-pill--active' : ''}`}
            onClick={() =>
              setStatusFilter((prev) => (prev === 'unavailable' ? 'all' : 'unavailable'))
            }
          >
            <span className="garage-legend-dot garage-legend-dot--unavailable" />
            Unavailable ({statusCounts.unavailable})
          </button>
        </div>
      </div>

      {/* 3D Canvas Viewport */}
      <div className="garage-stage__canvas-wrap">
        {webglAvailable ? (
          <SceneErrorBoundary fallback={fallbackGrid}>
            <Canvas shadows dpr={[1, 2]}>
              <color attach="background" args={['#0b0918']} />
              <fog attach="fog" args={['#0b0918', 28, 56]} />

              <StudioEnvironment3D />

              <OrthographicCamera
                makeDefault
                position={[15.2, 13.5, 15.8]}
                zoom={cameraZoom}
                near={-50}
                far={120}
              />

              <OrbitControls
                ref={controlsRef}
                enableDamping
                dampingFactor={0.08}
                minPolarAngle={0.48}
                maxPolarAngle={1.24}
                minAzimuthAngle={-0.35}
                maxAzimuthAngle={1.35}
                minZoom={MIN_ZOOM}
                maxZoom={MAX_ZOOM}
                target={[0, 0.15, 0.35]}
              />

              {/* Multi-Source Showroom & Architectural Garage Lighting */}
              <hemisphereLight args={['#f1f5f9', '#2e1065', 1.15]} />
              <directionalLight
                position={[11, 20, 13]}
                intensity={2.2}
                color="#ffffff"
                castShadow
                shadow-mapSize-width={1024}
                shadow-mapSize-height={1024}
              />
              <directionalLight position={[-12, 11, -9]} intensity={1.05} color="#d8b4fe" />
              <pointLight position={[-4, 5.5, -2.5]} intensity={3.2} color="#c084fc" distance={22} />
              <pointLight position={[5, 5.5, 4.5]} intensity={2.8} color="#38bdf8" distance={22} />

              <GarageArchitecture3D />

              {deckBays.map((bay) => {
                const x = startX + bay.slotIndex * spacingX
                const z = bay.row === 'north' ? -3.55 : 4.25
                const rotationY = bay.row === 'north' ? 0 : Math.PI
                const isDimmed = statusFilter !== 'all' && bay.status !== statusFilter

                return (
                  <ParkingBay3D
                    key={bay.id}
                    bay={bay}
                    position={[x, 0, z]}
                    rotationY={rotationY}
                    isSelected={bay.id === selectedBayId}
                    isDimmed={isDimmed}
                    onSelect={onSelectBay}
                  />
                )
              })}
            </Canvas>
          </SceneErrorBoundary>
        ) : (
          fallbackGrid
        )}
      </div>

      {/* Bottom-Left Quick Bay Selector Rail (Keyboard + Click Accessible) */}
      <div className="garage-stage__bay-rail" role="group" aria-label="Quick select bay on deck">
        {deckBays.map((bay) => {
          const isSelected = bay.id === selectedBayId
          return (
            <button
              key={bay.id}
              type="button"
              className={`garage-rail-chip garage-rail-chip--${bay.status}${isSelected ? ' garage-rail-chip--selected' : ''}`}
              onClick={() => onSelectBay(bay.id)}
              title={`${bay.code} (${bay.status})`}
            >
              {bay.code}
            </button>
          )
        })}
      </div>

      {/* Bottom-Right Timestamp + Camera Zoom Stack */}
      <div className="garage-stage__hud-bottom-right">
        <div className="garage-stage__timestamp">{snapshotTimestamp}</div>

        <div className="garage-stage__controls" role="group" aria-label="3D camera controls">
          <button
            type="button"
            className="garage-ctrl-btn"
            onClick={handleZoomIn}
            aria-label="Zoom in"
            title="Zoom in"
          >
            +
          </button>
          <button
            type="button"
            className="garage-ctrl-btn"
            onClick={handleZoomOut}
            aria-label="Zoom out"
            title="Zoom out"
          >
            −
          </button>
          <button
            type="button"
            className="garage-ctrl-btn"
            onClick={handleResetView}
            aria-label="Reset camera view"
            title="Reset isometric view"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M4 9V5h4M20 9V5h-4M4 15v4h4M20 15v4h-4" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  )
}
