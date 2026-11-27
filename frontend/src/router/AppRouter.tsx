import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { canVisit } from '../auth/permissions'
import { redirectForAuth } from '../auth/session'
import { useAuth } from '../auth/useAuth'
import { MainLayout } from '../components/layout'
import { ParkingStateProvider } from '../context/ParkingStateProvider'
import { AnalyticsPage } from '../pages/AnalyticsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { ForbiddenPage } from '../pages/ForbiddenPage'
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
            <Route index element={<Permit path="/"><DashboardPage /></Permit>} />
            <Route path="parking-map" element={<Permit path="/parking-map"><ParkingMapPage /></Permit>} />
            <Route path="sessions" element={<Permit path="/sessions"><SessionsPage /></Permit>} />
            <Route path="reservations" element={<Permit path="/reservations"><ReservationsPage /></Permit>} />
            <Route path="analytics" element={<Permit path="/analytics"><AnalyticsPage /></Permit>} />
            <Route path="settings" element={<Permit path="/settings"><SettingsPage /></Permit>} />
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

function Permit({ path, children }: { path: string; children: ReactNode }) {
  const { user } = useAuth()
  if (!canVisit(user?.role, path)) return <ForbiddenPage />
  return children
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
