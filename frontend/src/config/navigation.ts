export type NavIconName =
  | 'dashboard'
  | 'map'
  | 'sessions'
  | 'reservations'
  | 'analytics'
  | 'settings'

export type NavSection = 'Operations' | 'Management'

export interface NavItem {
  path: string
  label: string
  subtitle: string
  icon: NavIconName
  section: NavSection
}

export const NAV_ITEMS: NavItem[] = [
  {
    path: '/',
    label: 'Dashboard',
    subtitle: 'Real-time facility overview and occupancy summary',
    icon: 'dashboard',
    section: 'Operations',
  },
  {
    path: '/parking-map',
    label: 'Parking Map',
    subtitle: 'Interactive zone and bay availability layout',
    icon: 'map',
    section: 'Operations',
  },
  {
    path: '/sessions',
    label: 'Active Sessions',
    subtitle: 'Live vehicle entries, durations, and exits',
    icon: 'sessions',
    section: 'Operations',
  },
  {
    path: '/reservations',
    label: 'Reservations',
    subtitle: 'Scheduled parking bookings and upcoming arrivals',
    icon: 'reservations',
    section: 'Management',
  },
  {
    path: '/analytics',
    label: 'Analytics',
    subtitle: 'Utilization trends, peak hours, and capacity insights',
    icon: 'analytics',
    section: 'Management',
  },
  {
    path: '/settings',
    label: 'Settings',
    subtitle: 'Facility zones, rates, and system preferences',
    icon: 'settings',
    section: 'Management',
  },
]

export function getRouteMeta(pathname: string): { title: string; subtitle: string } {
  const matched = NAV_ITEMS.find((item) =>
    item.path === '/' ? pathname === '/' : pathname.startsWith(item.path),
  )

  if (matched) {
    return {
      title: matched.label,
      subtitle: matched.subtitle,
    }
  }

  return {
    title: 'Page Not Found',
    subtitle: 'The requested view does not exist in Parkify',
  }
}
