import { NavLink } from 'react-router-dom'
import { NAV_ITEMS, type NavItem } from '../../config/navigation'
import { useSignOut } from '../../auth/useAuth'
import { useParkingState } from '../../context/useParkingState'
import { BrandLogoIcon, CloseIcon, NavIcon } from '../icons/AppIcons'
import './Sidebar.css'

export interface SidebarProps {
  items?: NavItem[]
  isCollapsed?: boolean
  isMobileOpen: boolean
  onToggleCollapse?: () => void
  onCloseMobile: () => void
}

export function Sidebar({
  items = NAV_ITEMS,
  isMobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const { settings, dataset } = useParkingState()
  const { signOut, signingOut, error } = useSignOut()

  return (
    <aside
      className={`mobile-drawer${isMobileOpen ? ' mobile-drawer--open' : ''}`}
      aria-label="Mobile navigation drawer"
      aria-hidden={!isMobileOpen}
    >
      <div className="mobile-drawer__header">
        <div className="mobile-drawer__brand">
          <BrandLogoIcon />
          <div>
            <span className="mobile-drawer__title">Parkify</span>
            <span className="mobile-drawer__subtitle">{settings.facilityName}</span>
          </div>
        </div>

        <button
          type="button"
          className="mobile-drawer__close"
          onClick={onCloseMobile}
          aria-label="Close navigation menu"
        >
          <CloseIcon />
        </button>
      </div>

      <nav className="mobile-drawer__nav">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `mobile-drawer__link${isActive ? ' mobile-drawer__link--active' : ''}`
            }
          >
            <NavIcon name={item.icon} />
            <div className="mobile-drawer__link-copy">
              <span className="mobile-drawer__link-label">{item.label}</span>
              <span className="mobile-drawer__link-desc">{item.subtitle}</span>
            </div>
          </NavLink>
        ))}
      </nav>

      <div className="mobile-drawer__session">
        <button
          type="button"
          className="mobile-drawer__logout"
          onClick={() => void signOut()}
          disabled={signingOut}
        >
          {signingOut ? 'Signing out…' : 'Log out'}
        </button>
        {error ? (
          <p className="mobile-drawer__logout-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="mobile-drawer__footer">
        <span className="mobile-drawer__dot" aria-hidden="true" />
        <span>
          {dataset.isSimulated ? 'Simulated Telemetry Mode Active' : 'Live facility data'}
        </span>
      </div>
    </aside>
  )
}
