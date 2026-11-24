import { MenuIcon } from '../icons/AppIcons'
import './Header.css'

export interface HeaderProps {
  title: string
  subtitle?: string
  facilityName?: string
  isMobileMenuOpen: boolean
  onOpenMobileMenu: () => void
}

export function Header({
  title,
  subtitle,
  facilityName = 'Central Plaza Garage',
  isMobileMenuOpen,
  onOpenMobileMenu,
}: HeaderProps) {
  return (
    <header className="header">
      <div className="header__left">
        <button
          type="button"
          className="header__menu-btn"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation menu"
          aria-expanded={isMobileMenuOpen}
        >
          <MenuIcon />
        </button>

        <div className="header__titles">
          <h1 className="header__title">{title}</h1>
          {subtitle && <p className="header__subtitle">{subtitle}</p>}
        </div>
      </div>

      <div className="header__right">
        <div className="header__facility" aria-label="Selected facility">
          <span className="header__facility-indicator" aria-hidden="true" />
          <span className="header__facility-name">{facilityName}</span>
        </div>

        <div className="header__operator" title="Operator Console">
          <span className="header__avatar" aria-hidden="true">
            OP
          </span>
          <span className="header__operator-label">Console</span>
        </div>
      </div>
    </header>
  )
}
