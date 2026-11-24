import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { getRouteMeta } from '../../config/navigation'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import './MainLayout.css'

export function MainLayout() {
  const location = useLocation()
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [mobileOpenPath, setMobileOpenPath] = useState<string | null>(null)

  const isMobileMenuOpen = mobileOpenPath === location.pathname
  const { title, subtitle } = getRouteMeta(location.pathname)

  useEffect(() => {
    if (!isMobileMenuOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileOpenPath(null)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMobileMenuOpen])

  const shellClassName = [
    'app-shell',
    isSidebarCollapsed ? 'app-shell--sidebar-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={shellClassName}>
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        isMobileOpen={isMobileMenuOpen}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        onCloseMobile={() => setMobileOpenPath(null)}
      />

      {isMobileMenuOpen && (
        <div
          className="app-shell__backdrop"
          onClick={() => setMobileOpenPath(null)}
          aria-hidden="true"
        />
      )}

      <div className="app-shell__viewport">
        <Header
          title={title}
          subtitle={subtitle}
          isMobileMenuOpen={isMobileMenuOpen}
          onOpenMobileMenu={() => setMobileOpenPath(location.pathname)}
        />

        <main className="app-shell__content">
          <div className="app-shell__container">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
