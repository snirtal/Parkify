import { PagePlaceholder } from '../components/common/PagePlaceholder'

export function ReservationsPage() {
  return (
    <PagePlaceholder
      icon="reservations"
      badge="Scheduling"
      heading="Parking Reservations"
      description="Manage advance bookings, scheduled arrivals, VIP allocations, and time-window availability."
      modules={[
        {
          title: 'Upcoming Arrivals',
          description: 'Timeline of expected vehicles arriving within the current shift.',
        },
        {
          title: 'Reservation Schedule',
          description: 'Calendar and list views of confirmed, active, and expired bookings.',
        },
        {
          title: 'Allocation Rules',
          description: 'Reserved bay buffer settings and hold-window configuration.',
        },
      ]}
    />
  )
}
