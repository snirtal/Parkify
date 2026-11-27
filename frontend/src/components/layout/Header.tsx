import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '../../config/navigation'
import { can, SETTINGS_READ } from '../../auth/permissions'
import { useAuth, useSignOut } from '../../auth/useAuth'
import { useParkingState } from '../../context/useParkingState'
import { BellIcon, BrandLogoIcon, GearIcon, MenuIcon, PinIcon } from '../icons/AppIcons'
import './Header.css'

export interface HeaderProps {
  title: string
  subtitle?: string
  isMobileMenuOpen: boolean
  onOpenMobileMenu: () => void
}

const PRIMARY_TABS = NAV_ITEMS.filter((item) => item.path !== '/settings')

export function Header({
  isMobileMenuOpen,
  onOpenMobileMenu,
}: HeaderProps) {
  const { settings, dataset, sessions } = useParkingState()
  const { user } = useAuth()
  const { signOut, signingOut, error: signOutError } = useSignOut()
  const [showAlerts, setShowAlerts] = useState(false)
  const tabs = PRIMARY_TABS.filter((item) => can(user?.role, item.permission))
  const showSettings = can(user?.role, SETTINGS_READ)

  const alerts: { id: string; label: string; body: string }[] = []
  const offlineBays = dataset.bays.filter((bay) => bay.status === 'unavailable')
  if (settings.spaceFaultAlert && offlineBays.length > 0) {
    alerts.push({
      id: 'fault',
      label: `${offlineBays.map((bay) => bay.code).join(', ')} • Space Fault`,
      body: `${offlineBays.length} bays are offline.`,
    })
  }
  const clock = dataset.snapshotTimestamp.replace(' ', 'T')
  const overstays = sessions.filter(
    (session) => session.paidUntil !== null && session.paidUntil < clock,
  )
  if (settings.reservationOverstayAlert && dataset.overstaySessions > 0) {
    const plates = overstays.map((session) => `${session.bayCode} • ${session.plateNumber}`)
    alerts.push({
      id: 'overstay',
      label: plates[0] ?? 'Reservation overstay',
      body: `${dataset.overstaySessions} active session${dataset.overstaySessions === 1 ? '' : 's'} passed the paid-until time.`,
    })
  }
  if (settings.highOccupancyAlert && dataset.aboveHighOccupancy) {
    alerts.push({
      id: 'occupancy',
      label: `Capacity Watch • ${dataset.occupancyRate}%`,
      body: `Occupancy is at or above 85% (${dataset.occupiedSpots}/${dataset.totalSpots} occupied).`,
    })
  }

  return (
    <header className="top-nav">
      <div className="top-nav__left">
        <button
          type="button"
          className="top-nav__mobile-trigger"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation drawer"
          aria-expanded={isMobileMenuOpen}
        >
          <MenuIcon />
        </button>

        <NavLink to="/" className="top-nav__brand" aria-label="Parkify Home">
          <BrandLogoIcon className="top-nav__brand-logo" />
          <div className="top-nav__brand-copy">
            <span className="top-nav__brand-name">Parkify</span>
            <span className="top-nav__sim-pill">{dataset.isSimulated ? 'Simulated' : 'Live'}</span>
          </div>
        </NavLink>
      </div>

      <nav className="top-nav__segmented" aria-label="Main navigation">
        {tabs.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `top-nav__tab${isActive ? ' top-nav__tab--active' : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="top-nav__right">
        <div
          className="top-nav__location"
          title={`${settings.facilityName} • ${settings.facilityAddress} • ${settings.operatingHours}`}
        >
          <PinIcon className="top-nav__location-icon" />
          <div className="top-nav__location-copy">
            <span className="top-nav__location-name">{settings.facilityName}</span>
            <span className="top-nav__location-text">{settings.facilityAddress}</span>
          </div>
        </div>

        <div className="top-nav__alert-wrap">
          <button
            type="button"
            className={`top-nav__icon-btn${showAlerts ? ' top-nav__icon-btn--active' : ''}`}
            onClick={() => setShowAlerts((prev) => !prev)}
            aria-label="Toggle facility alerts"
            aria-expanded={showAlerts}
          >
            <BellIcon />
            {alerts.length > 0 && <span className="top-nav__alert-dot" aria-hidden="true" />}
          </button>

          {showAlerts && (
            <div className="top-nav__popover" role="dialog" aria-label="Facility notifications">
              <div className="top-nav__popover-head">
                <span>Facility alerts</span>
                <span className="top-nav__popover-tag">{dataset.isSimulated ? 'Simulated' : 'Live'}</span>
              </div>
              {alerts.length > 0 ? (
                alerts.map((alert) => (
                  <p key={alert.id} className="top-nav__popover-item">
                    <strong>{alert.label}:</strong> {alert.body}
                  </p>
                ))
              ) : (
                <p className="top-nav__popover-item">No facility alerts right now.</p>
              )}
            </div>
          )}
        </div>

        {showSettings ? (
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `top-nav__icon-btn${isActive ? ' top-nav__icon-btn--route-active' : ''}`
            }
            aria-label="System Settings"
            title="Settings"
          >
            <GearIcon />
          </NavLink>
        ) : null}

        <button
          type="button"
          className="top-nav__logout"
          onClick={() => void signOut()}
          disabled={signingOut}
        >
          {signingOut ? 'Signing out…' : 'Log out'}
        </button>
        {signOutError ? (
          <p className="top-nav__logout-error" role="alert">
            {signOutError}
          </p>
        ) : null}
      </div>
    </header>
  )
}
