import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '../../config/navigation'
import { SMART_PARKING_DATA } from '../../data/mockParkingData'
import { BellIcon, BrandLogoIcon, GearIcon, MenuIcon, PinIcon } from '../icons/AppIcons'
import './Header.css'

export interface HeaderProps {
  title: string
  subtitle?: string
  facilityName?: string
  isMobileMenuOpen: boolean
  onOpenMobileMenu: () => void
}

const PRIMARY_TABS = NAV_ITEMS.filter((item) => item.path !== '/settings')

export function Header({
  facilityName = SMART_PARKING_DATA.facilityAddress,
  isMobileMenuOpen,
  onOpenMobileMenu,
}: HeaderProps) {
  const [showAlerts, setShowAlerts] = useState(false)

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
        <div className="top-nav__location" title="Simulated Facility Location">
          <PinIcon className="top-nav__location-icon" />
          <span className="top-nav__location-text">{facilityName}</span>
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
            <span className="top-nav__alert-dot" aria-hidden="true" />
          </button>

          {showAlerts && (
            <div className="top-nav__popover" role="dialog" aria-label="Simulated notifications">
              <div className="top-nav__popover-head">
                <span>AI Sensor Feed</span>
                <span className="top-nav__popover-tag">Simulated</span>
              </div>
              <p className="top-nav__popover-item">
                <strong>P-204 • VEL-204X:</strong> Minor vibration detected near windshield; AI
                optical check verified zero surface damage.
              </p>
              <p className="top-nav__popover-item">
                <strong>P-208 • Maintenance:</strong> Induction pad calibration in progress.
              </p>
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
