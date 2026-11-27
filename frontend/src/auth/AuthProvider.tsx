import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from '../api/authApi'
import { ApiError, isAbortError } from '../api/client'
import { AuthContext, type AuthContextValue, type AuthStatus } from './useAuth'
import { anonymousNotice, sessionEndedMessage, shouldEndSession } from './session'

interface AuthState {
  status: AuthStatus
  user: AuthContextValue['user']
  notice: string | null
}

const INITIAL: AuthState = { status: 'loading', user: null, notice: null }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(INITIAL)
  const [signingOut, setSigningOut] = useState(false)
  const epoch = useRef(0)

  const restore = useCallback(async (ticket: number, signal?: AbortSignal) => {
    try {
      const user = await fetchCurrentUser(signal)
      if (epoch.current !== ticket) return
      setState({ status: 'authenticated', user, notice: null })
    } catch (error) {
      if (isAbortError(error) || epoch.current !== ticket) return
      if (!shouldEndSession(error)) {
        setState((current) => {
          if (current.status === 'authenticated') return current
          const notice = error instanceof ApiError ? error.message : 'The server could not be reached.'
          return { status: 'anonymous', user: null, notice }
        })
        return
      }
      setState((current) => ({
        status: 'anonymous',
        user: null,
        notice: anonymousNotice(error, current.status === 'anonymous' ? current.notice : null),
      }))
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void restore(epoch.current, controller.signal)
    return () => controller.abort()
  }, [restore])

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      void restore(epoch.current)
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [restore])

  const login = useCallback(async (email: string, password: string) => {
    const ticket = ++epoch.current
    const user = await loginRequest(email, password)
    if (epoch.current !== ticket) return
    setState({ status: 'authenticated', user, notice: null })
  }, [])

  const logout = useCallback(async () => {
    const ticket = ++epoch.current
    setSigningOut(true)
    try {
      await logoutRequest()
    } catch (error) {
      if (epoch.current !== ticket) return
      if (error instanceof ApiError && error.status === 401) {
        setState({ status: 'anonymous', user: null, notice: sessionEndedMessage(error) })
        return
      }
      throw error
    } finally {
      setSigningOut(false)
    }
    if (epoch.current !== ticket) return
    setState({ status: 'anonymous', user: null, notice: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, signingOut, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
