import { PagePlaceholder } from '../components/common/PagePlaceholder'

export function SessionsPage() {
  return (
    <PagePlaceholder
      icon="sessions"
      badge="Live Tracking"
      heading="Active Parking Sessions"
      description="Track currently parked vehicles, entry timestamps, elapsed durations, and completed check-outs."
      modules={[
        {
          title: 'Session Search & Filters',
          description: 'Quick lookup by license plate, zone, bay number, or session status.',
        },
        {
          title: 'Active Vehicles Table',
          description: 'Live tabular view of ongoing parking sessions and elapsed stay duration.',
        },
        {
          title: 'Manual Check-In / Check-Out',
          description: 'Operator controls for assisting entries, exits, and exception handling.',
        },
      ]}
    />
  )
}
