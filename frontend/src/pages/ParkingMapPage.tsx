import { PagePlaceholder } from '../components/common/PagePlaceholder'

export function ParkingMapPage() {
  return (
    <PagePlaceholder
      icon="map"
      badge="Live Layout"
      heading="Interactive Parking Floor Map"
      description="Visual spatial grid of parking levels, individual bays, sensor states, and special-purpose stalls."
      modules={[
        {
          title: 'Level & Zone Selector',
          description: 'Switch between garage levels and filter by standard, EV, or accessible spots.',
        },
        {
          title: 'Interactive Bay Grid',
          description: 'Color-coded bay statuses for vacant, occupied, reserved, and maintenance stalls.',
        },
        {
          title: 'Spot Inspector Panel',
          description: 'Detailed side panel for inspecting individual stall status and session info.',
        },
      ]}
    />
  )
}
