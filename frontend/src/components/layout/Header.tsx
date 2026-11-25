import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '../../config/navigation'
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
  const { settings, dataset } = useParkingState()
  const [showAlerts, setShowAlerts] = useState(false)

  const alerts: { id: string; label: string; body: string }[] = []
  if (settings.spaceFaultAlert && dataset.unavailableSpots > 0) {
    alerts.push({
      id: 'fault',
      label: 'P-208 & P-106 • Space Fault',
      body: `${dataset.unavailableSpots} bays offline for sensor and induction pad calibration.`,
    })
  }
  if (settings.reservationOverstayAlert) {
    alerts.push({
      id: 'overstay',
      label: 'P-204 • VEL-204X',
      body: 'Paid window elapsed at 14:08; reservation overstay monitor armed.',
    })
  }
  if (settings.highOccupancyAlert) {
    alerts.push({
      id: 'occupancy',
      label: `Capacity Watch • ${dataset.occupancyRate}%`,
      body: `High-occupancy threshold armed at 85% (${dataset.occupiedSpots}/${dataset.totalSpots} occupied).`,
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
            <span className="top-nav__sim-pill">Simulated</span>
          </div>
        </NavLink>
      </div>

      <nav className="top-nav__segmented" aria-label="Main navigation">
        {PRIMARY_TABS.map((item) => (
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
            <div className="top-nav__popover" role="dialog" aria-label="Simulated notifications">
              <div className="top-nav__popover-head">
                <span>AI Sensor Feed</span>
                <span className="top-nav__popover-tag">Simulated</span>
              </div>
              {alerts.length > 0 ? (
                alerts.map((alert) => (
                  <p key={alert.id} className="top-nav__popover-item">
                    <strong>{alert.label}:</strong> {alert.body}
                  </p>
                ))
              ) : (
                <p className="top-nav__popover-item">
                  All simulated alert notifications are currently disabled in Settings.
                </p>
              )}
            </div>
          )}
        </div>

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
      </div>
    </header>
  )
}
