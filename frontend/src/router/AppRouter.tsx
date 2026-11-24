import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { MainLayout } from '../components/layout'
import { AnalyticsPage } from '../pages/AnalyticsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ParkingMapPage } from '../pages/ParkingMapPage'
import { ReservationsPage } from '../pages/ReservationsPage'
import { SessionsPage } from '../pages/SessionsPage'
import { SettingsPage } from '../pages/SettingsPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="parking-map" element={<ParkingMapPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="reservations" element={<ReservationsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
