import { lazy, Suspense, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SpotInspectorPanel } from '../components/dashboard'
import { ParkingSearchBar } from '../components/parking-map/ParkingSearchBar'
import { matchBayQuery } from '../components/parking-map/searchUtils'
import { SMART_PARKING_DATA } from '../data/mockParkingData'
import './DashboardPage.css'

const IsometricGarage3D = lazy(() =>
  import('../components/garage3d/IsometricGarage3D').then((m) => ({
    default: m.IsometricGarage3D,
  })),
)

const DEFAULT_BAY_ID = 'bay-p204'

export function ParkingMapPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState<string>('')

  const bayParam = searchParams.get('bay')

  const selectedBay = useMemo(() => {
    if (bayParam) {
      const normalized = bayParam.trim().toLowerCase()
      const matched = SMART_PARKING_DATA.bays.find(
        (bay) => bay.code.toLowerCase() === normalized || bay.id.toLowerCase() === normalized,
      )
      if (matched) return matched
    }
    return (
      SMART_PARKING_DATA.bays.find((bay) => bay.id === DEFAULT_BAY_ID) ??
      SMART_PARKING_DATA.bays[0]
    )
  }, [bayParam])

  const matchedBayIds = useMemo(() => {
    if (!searchQuery.trim()) return null
    const matching = SMART_PARKING_DATA.bays
      .filter((bay) => matchBayQuery(bay, searchQuery))
      .map((bay) => bay.id)
    return new Set(matching)
  }, [searchQuery])

  const handleSelectBay = (bayId: string) => {
    const target = SMART_PARKING_DATA.bays.find((b) => b.id === bayId)
    if (target) {
      setSearchParams({ bay: target.code }, { replace: true })
    }
  }

  const handleSelectByCode = (bayCode: string) => {
    const target = SMART_PARKING_DATA.bays.find((b) => b.code === bayCode)
    if (target) {
      setSearchParams({ bay: target.code }, { replace: true })
    }
  }

  return (
    <div className="cyber-dashboard">
      <div className="cyber-dashboard__stage-col">
        <ParkingSearchBar
          bays={SMART_PARKING_DATA.bays}
          selectedBayId={selectedBay.id}
          query={searchQuery}
          onQueryChange={setSearchQuery}
          onSelectBay={handleSelectBay}
        />

        <Suspense
          fallback={
            <div
              className="cyber-dashboard__stage-skeleton cyber-dashboard__stage-skeleton--expanded"
              aria-busy="true"
            >
              Initializing 3D Digital Twin…
            </div>
          }
        >
          <IsometricGarage3D
            bays={SMART_PARKING_DATA.bays}
            selectedBayId={selectedBay.id}
            snapshotTimestamp={SMART_PARKING_DATA.snapshotTimestamp}
            onSelectBay={handleSelectBay}
            expanded
            matchedBayIds={matchedBayIds}
          />
        </Suspense>
      </div>

      <div className="cyber-dashboard__inspector-col">
        <SpotInspectorPanel
          bay={selectedBay}
          zones={SMART_PARKING_DATA.zones}
          gateLogs={SMART_PARKING_DATA.gateLogs}
          yearlySeries={SMART_PARKING_DATA.yearlyRentalSeries}
          todaySeries={SMART_PARKING_DATA.todayOccupancySeries}
          onSelectBayByCode={handleSelectByCode}
        />
      </div>
    </div>
  )
}
