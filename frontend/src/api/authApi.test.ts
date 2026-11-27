import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from './client'
import { CSRF_HEADER, fetchCurrentUser, login, logout, readCookie } from './authApi'

const user = {
  id: 'user-1',
  email: 'admin@parkify.com',
  full_name: 'Parkify Admin',
  role: 'admin',
  is_active: true,
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('auth API', () => {
  it('signs in with a relative URL and leaves the token in the cookie', async () => {
    const setItem = vi.fn()
    vi.stubGlobal('localStorage', { setItem, getItem: vi.fn(), removeItem: vi.fn() })
    vi.stubGlobal('sessionStorage', { setItem, getItem: vi.fn(), removeItem: vi.fn() })
    const fetchMock = vi.fn(async () => json({ user }))
    vi.stubGlobal('fetch', fetchMock)

    const account = await login(' Admin@Parkify.com ', 'correct-horse-battery')

    expect(account).toEqual(user)
    expect(account).not.toHaveProperty('password')
    expect(account).not.toHaveProperty('token')
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/auth/login')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('same-origin')
    expect(JSON.parse(String(init.body))).toEqual({
      email: ' Admin@Parkify.com ',
      password: 'correct-horse-battery',
    })
    expect(setItem).not.toHaveBeenCalled()
  })

  it('reads the current operator from the session cookie', async () => {
    const fetchMock = vi.fn(async () => json({ user }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(fetchCurrentUser()).resolves.toEqual(user)
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/auth/me')
    expect(init.credentials).toBe('same-origin')
    expect(init.body).toBeUndefined()
  })

  it('logs out with the CSRF cookie and does not send the password', async () => {
    vi.stubGlobal('document', { cookie: 'parkify_session=hidden; parkify_csrf=abc%2B123' })
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await logout()

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/auth/logout')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('same-origin')
    expect(init.body).toBeUndefined()
    const headers = init.headers as Record<string, string>
    expect(headers[CSRF_HEADER]).toBe('abc+123')
    expect(JSON.stringify(init)).not.toContain('hidden')
    expect(JSON.stringify(init)).not.toContain('password')
  })

  it('surfaces the shared invalid-credentials error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        json({ error: { code: 'invalid_credentials', message: 'The email or password is incorrect.' } }, 401),
      ),
    )
    await expect(login('ada@example.com', 'wrong-password')).rejects.toEqual(
      expect.any(ApiError),
    )
    await expect(login('missing@example.com', 'wrong-password')).rejects.toMatchObject({
      status: 401,
      code: 'invalid_credentials',
      message: 'The email or password is incorrect.',
    })
  })
})

describe('csrf header', () => {
  it('sends the readable cookie on a change and not the session token', async () => {
    vi.stubGlobal('document', { cookie: 'parkify_session=hidden; parkify_csrf=csrf-value' })
    const fetchMock = vi.fn(async () => json({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    await apiRequest('/api/facilities/facility-skyline/entries', { method: 'POST', body: { spot_code: 'P-210' } })
    const init = fetchMock.mock.calls[0] as unknown as [string, { headers: Record<string, string>; body: string }]
    const request = init[1]
    expect(request.headers['X-CSRF-Token']).toBe('csrf-value')
    expect(request.body).not.toContain('hidden')
    expect(JSON.stringify(request.headers)).not.toContain('hidden')
  })
})

describe('csrf cookie', () => {
  it('reads one named cookie', () => {
    expect(readCookie('parkify_csrf=token; theme=dark', 'parkify_csrf')).toBe('token')
    expect(readCookie('theme=dark', 'parkify_csrf')).toBe('')
  })
})
