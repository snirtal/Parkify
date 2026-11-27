import { ApiError } from '../api/client'

export type AuthPhase = 'loading' | 'authenticated' | 'anonymous'

const ENDED_SESSION = new Set(['token_expired', 'invalid_token'])

/** Where to send the operator, or null to stay on the current page. */
export function redirectForAuth(pathname: string, phase: AuthPhase): '/login' | '/' | null {
  if (phase === 'loading') return null
  if (phase === 'authenticated' && pathname === '/login') return '/'
  if (phase === 'anonymous' && pathname !== '/login') return '/login'
  return null
}

export function sessionEndedMessage(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.status !== 401) return null
  if (!ENDED_SESSION.has(error.code)) return null
  return error.message
}

/** A 401 ends the session. Other failures keep a session that is already open. */
export function shouldEndSession(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

export function loginFailureMessage(error: unknown): string {
  if (error instanceof ApiError && error.message) return error.message
  return 'Sign in failed.'
}

export function anonymousNotice(error: unknown, currentNotice: string | null): string | null {
  const ended = sessionEndedMessage(error)
  if (ended) return ended
  if (error instanceof ApiError && error.status === 401) return currentNotice
  if (error instanceof ApiError) return error.message
  return currentNotice
}
