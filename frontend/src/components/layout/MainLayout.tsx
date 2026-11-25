import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { getRouteMeta } from '../../config/navigation'
import { useParkingState } from '../../context/useParkingState'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import './MainLayout.css'

export function MainLayout() {
  const location = useLocation()
  const [mobileOpenPath, setMobileOpenPath] = useState<string | null>(null)

  const isMobileMenuOpen = mobileOpenPath === location.pathname
  const { title, subtitle } = getRouteMeta(location.pathname)
  const { status, error, reload } = useParkingState()

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

  return (
    <div className="futuristic-shell">
      <div className="futuristic-shell__ambient" aria-hidden="true" />

      <Sidebar
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setMobileOpenPath(null)}
      />

      {isMobileMenuOpen && (
        <div
          className="futuristic-shell__backdrop"
          onClick={() => setMobileOpenPath(null)}
          aria-hidden="true"
        />
      )}

      <Header
        title={title}
        subtitle={subtitle}
        isMobileMenuOpen={isMobileMenuOpen}
        onOpenMobileMenu={() => setMobileOpenPath(location.pathname)}
      />

      <main className="futuristic-shell__main">
        <div className="futuristic-shell__container">
          {status === 'loading' ? (
            <p className="facility-status" role="status">
              Loading facility data…
            </p>
          ) : status === 'error' ? (
            <div className="facility-status" role="alert">
              <p>{error ?? 'The facility could not be loaded.'}</p>
              <button type="button" onClick={reload}>
                Try again
              </button>
            </div>
          ) : (
            <Outlet />
          )}
        </div>
      </main>
    </div>
  )
}
