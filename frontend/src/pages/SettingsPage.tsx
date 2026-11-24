import { PagePlaceholder } from '../components/common/PagePlaceholder'

export function SettingsPage() {
  return (
    <PagePlaceholder
      icon="settings"
      badge="Configuration"
      heading="Facility & System Settings"
      description="Configure garage levels, bay categories, operating hours, tariff schedules, and display preferences."
      modules={[
        {
          title: 'Facility Profile',
          description: 'Garage metadata, operating hours, address, and zone hierarchy.',
        },
        {
          title: 'Rate & Tariff Structure',
          description: 'Hourly tiers, daily maximums, grace periods, and EV charging add-ons.',
        },
        {
          title: 'Notification Preferences',
          description: 'Capacity threshold alerts and operator console display options.',
        },
      ]}
    />
  )
}
