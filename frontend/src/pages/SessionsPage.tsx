import { GateActivityTable } from '../components/dashboard'
import { MOCK_DASHBOARD_DATA } from '../data/mockDashboardData'

export function SessionsPage() {
  return <GateActivityTable events={MOCK_DASHBOARD_DATA.recentGateActivity} />
}
