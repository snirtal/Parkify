import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { ParkingStateProvider } from '../context/ParkingStateProvider'
import { useAuth } from '../auth/useAuth'
import { redirectForAuth } from '../auth/session'
import { MainLayout } from '../components/layout'
import { AnalyticsPage } from '../pages/AnalyticsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage, SessionGate } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ParkingMapPage } from '../pages/ParkingMapPage'
import { ReservationsPage } from '../pages/ReservationsPage'
import { SessionsPage } from '../pages/SessionsPage'
import { SettingsPage } from '../pages/SettingsPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route element={<RequireAuth />}>
          <Route element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="parking-map" element={<ParkingMapPage />} />
            <Route path="sessions" element={<SessionsPage />} />
            <Route path="reservations" element={<ReservationsPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

function LoginRoute() {
  const auth = useAuth()
  if (auth.status === 'loading') return <SessionGate />
  const redirect = redirectForAuth('/login', auth.status)
  if (redirect) return <Navigate to={redirect} replace />
  return <LoginPage notice={auth.notice} onSubmit={auth.login} />
}

function RequireAuth() {
  const auth = useAuth()
  if (auth.status === 'loading') return <SessionGate />
  const redirect = redirectForAuth('/app', auth.status)
  if (redirect) return <Navigate to={redirect} replace />
  return (
    <ParkingStateProvider>
      <Outlet />
    </ParkingStateProvider>
  )
}
