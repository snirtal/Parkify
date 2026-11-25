export interface ActiveSessionRow {
  id: string
  plateNumber: string
  bayCode: string
  startedAt: string
  paidUntil: string | null
  hasAlert: boolean
  alertTitle: string | null
  status: string
}
