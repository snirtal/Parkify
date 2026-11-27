import { createContext, useContext, useState } from 'react'
import type { AuthUser } from '../api/authApi'
import { ApiError } from '../api/client'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  notice: string | null
  signingOut: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return value
}

export function useSignOut() {
  const { logout, signingOut } = useAuth()
  const [error, setError] = useState<string | null>(null)

  async function signOut() {
    setError(null)
    try {
      await logout()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Sign out failed.')
    }
  }

  return { signOut, signingOut, error }
}
