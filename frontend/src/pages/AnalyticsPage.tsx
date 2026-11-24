import { PagePlaceholder } from '../components/common/PagePlaceholder'

export function AnalyticsPage() {
  return (
    <PagePlaceholder
      icon="analytics"
      badge="Insights"
      heading="Occupancy & Utilization Analytics"
      description="Analyze historical demand curves, turnover rates, peak congestion windows, and zone performance."
      modules={[
        {
          title: 'Hourly Occupancy Trends',
          description: 'Time-series charts comparing weekday and weekend parking demand.',
        },
        {
          title: 'Turnover & Dwell Time',
          description: 'Average parking duration metrics segmented by floor and vehicle category.',
        },
        {
          title: 'Exportable Reports',
          description: 'Summary reports for facility capacity planning and operations review.',
        },
      ]}
    />
  )
}
