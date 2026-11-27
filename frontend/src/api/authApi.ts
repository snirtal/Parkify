import { apiRequest } from './client'

/** Readable CSRF cookie. The session JWT stays in the HttpOnly cookie. */
export const CSRF_COOKIE = 'parkify_csrf'
export const CSRF_HEADER = 'X-CSRF-Token'

export interface AuthUser {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

export function readCookie(source: string, name: string): string {
  const prefix = `${name}=`
  for (const part of source.split(';')) {
    const item = part.trim()
    if (item.startsWith(prefix)) {
      return decodeURIComponent(item.slice(prefix.length))
    }
  }
  return ''
}

export function browserCookie(name: string): string {
  if (typeof document === 'undefined') return ''
  return readCookie(document.cookie, name)
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const payload = await apiRequest<{ user: AuthUser }>('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    credentials: 'same-origin',
  })
  return payload.user
}

export async function fetchCurrentUser(signal?: AbortSignal): Promise<AuthUser> {
  const payload = await apiRequest<{ user: AuthUser }>('/api/auth/me', {
    signal,
    credentials: 'same-origin',
  })
  return payload.user
}

export async function logout(): Promise<void> {
  await apiRequest<null>('/api/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { [CSRF_HEADER]: browserCookie(CSRF_COOKIE) },
  })
}
