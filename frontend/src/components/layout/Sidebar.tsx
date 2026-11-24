import { NavLink } from 'react-router-dom'
import { NAV_ITEMS, type NavItem, type NavSection } from '../../config/navigation'
import { BrandLogoIcon, CloseIcon, CollapseIcon, NavIcon } from '../icons/AppIcons'
import './Sidebar.css'

export interface SidebarProps {
  items?: NavItem[]
  isCollapsed: boolean
  isMobileOpen: boolean
  onToggleCollapse: () => void
  onCloseMobile: () => void
}

const SECTIONS: NavSection[] = ['Operations', 'Management']

export function Sidebar({
  items = NAV_ITEMS,
  isCollapsed,
  isMobileOpen,
  onToggleCollapse,
  onCloseMobile,
}: SidebarProps) {
  const sidebarClasses = [
    'sidebar',
    isCollapsed ? 'sidebar--collapsed' : '',
    isMobileOpen ? 'sidebar--mobile-open' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <aside className={sidebarClasses} aria-label="Primary navigation">
      <div className="sidebar__brand">
        <div className="sidebar__brand-main">
          <BrandLogoIcon className="sidebar__logo" />
          <div className="sidebar__brand-copy">
            <span className="sidebar__brand-title">Parkify</span>
            <span className="sidebar__brand-subtitle">Smart Parking OS</span>
          </div>
        </div>

        <button
          type="button"
          className="sidebar__mobile-close"
          onClick={onCloseMobile}
          aria-label="Close navigation menu"
        >
          <CloseIcon />
        </button>
      </div>

      <nav className="sidebar__nav">
        {SECTIONS.map((section) => {
          const sectionItems = items.filter((item) => item.section === section)
          if (sectionItems.length === 0) return null

          return (
            <div key={section} className="sidebar__section">
              <span className="sidebar__section-label">{section}</span>
              <ul className="sidebar__list">
                {sectionItems.map((item) => (
                  <li key={item.path} className="sidebar__list-item">
                    <NavLink
                      to={item.path}
                      end={item.path === '/'}
                      title={isCollapsed ? item.label : undefined}
                      onClick={onCloseMobile}
                      className={({ isActive }) =>
                        `sidebar__link${isActive ? ' sidebar__link--active' : ''}`
                      }
                    >
                      <span className="sidebar__link-icon">
                        <NavIcon name={item.icon} />
                      </span>
                      <span className="sidebar__link-label">{item.label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__status" title="Frontend Shell Active">
          <span className="sidebar__status-dot" aria-hidden="true" />
          <div className="sidebar__status-copy">
            <span className="sidebar__status-title">System Shell</span>
            <span className="sidebar__status-meta">UI Ready</span>
          </div>
        </div>

        <button
          type="button"
          className="sidebar__collapse-btn"
          onClick={onToggleCollapse}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <CollapseIcon collapsed={isCollapsed} />
        </button>
      </div>
    </aside>
  )
}
