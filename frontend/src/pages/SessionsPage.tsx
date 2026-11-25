import { useMemo } from 'react'
import { GateActivityTable } from '../components/dashboard'
import { useParkingState } from '../context/useParkingState'
import { deriveGateActivityEvents } from '../utils/reservationUtils'

export function SessionsPage() {
  const { dataset } = useParkingState()
  const events = useMemo(
    () => deriveGateActivityEvents(dataset.gateLogs),
    [dataset.gateLogs],
  )

  return <GateActivityTable events={events} />
}
