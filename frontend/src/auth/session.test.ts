import { describe, expect, it } from 'vitest'
import { ApiError } from '../api/client'
import {
  anonymousNotice,
  loginFailureMessage,
  redirectForAuth,
  sessionEndedMessage,
  shouldEndSession,
} from './session'

describe('auth redirects', () => {
  it('sends anonymous visitors to the login page and signed-in visitors to the dashboard', () => {
    expect(redirectForAuth('/sessions', 'anonymous')).toBe('/login')
    expect(redirectForAuth('/', 'anonymous')).toBe('/login')
    expect(redirectForAuth('/login', 'anonymous')).toBeNull()
    expect(redirectForAuth('/login', 'authenticated')).toBe('/')
    expect(redirectForAuth('/sessions', 'authenticated')).toBeNull()
    expect(redirectForAuth('/sessions', 'loading')).toBeNull()
  })
})

describe('session failures', () => {
  it('shows an expired or revoked session and keeps a live session on other errors', () => {
    const expired = new ApiError(401, 'token_expired', 'The session has expired.')
    const revoked = new ApiError(401, 'invalid_token', 'The session is not valid.')
    const missing = new ApiError(401, 'unauthenticated', 'Authentication is required.')
    const offline = new ApiError(0, 'network_error', 'The server could not be reached.')

    expect(sessionEndedMessage(expired)).toBe('The session has expired.')
    expect(sessionEndedMessage(revoked)).toBe('The session is not valid.')
    expect(sessionEndedMessage(missing)).toBeNull()
    expect(shouldEndSession(expired)).toBe(true)
    expect(shouldEndSession(offline)).toBe(false)
    expect(anonymousNotice(expired, null)).toBe('The session has expired.')
    expect(anonymousNotice(missing, 'The session has expired.')).toBe('The session has expired.')
    expect(loginFailureMessage(new ApiError(403, 'account_inactive', 'This account is inactive.'))).toBe(
      'This account is inactive.',
    )
    expect(loginFailureMessage(new ApiError(429, 'rate_limited', 'Too many sign-in attempts. Try again later.'))).toBe(
      'Too many sign-in attempts. Try again later.',
    )
  })
})
