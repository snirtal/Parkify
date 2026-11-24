import { PagePlaceholder } from '../components/common/PagePlaceholder'

export function DashboardPage() {
  return (
    <PagePlaceholder
      icon="dashboard"
      badge="Operations"
      heading="Facility Operations Overview"
      description="Central command view for monitoring live parking capacity, zone occupancy, recent gate events, and operational alerts across the facility."
      modules={[
        {
          title: 'Occupancy KPI Summary',
          description: 'Total spots, available bays, occupied count, and utilization rate cards.',
        },
        {
          title: 'Live Gate Activity Feed',
          description: 'Real-time stream of vehicle entries, exits, and barrier events.',
        },
        {
          title: 'Zone Capacity Breakdown',
          description: 'Floor-by-floor and EV/accessible zone availability bars.',
        },
      ]}
    />
  )
}
