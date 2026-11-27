import { useState, type FormEvent } from 'react'
import { BrandLogoIcon } from '../components/icons/AppIcons'
import { loginFailureMessage } from '../auth/session'
import './LoginPage.css'

interface LoginPageProps {
  notice: string | null
  onSubmit: (email: string, password: string) => Promise<void>
}

export function LoginPage({ notice, onSubmit }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit(email.trim(), password)
    } catch (caught) {
      setError(loginFailureMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login">
      <form className="login__card" onSubmit={handleSubmit}>
        <div className="login__brand">
          <BrandLogoIcon />
          <div>
            <p className="login__name">Parkify</p>
            <h1 className="login__title">Sign in</h1>
          </div>
        </div>
        <p className="login__hint">Use your operator account to open the facility dashboard.</p>

        {notice ? (
          <p className="login__notice" role="status">
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="login__error" role="alert">
            {error}
          </p>
        ) : null}

        <label className="login__field">
          <span>Email</span>
          <input
            type="email"
            name="email"
            autoComplete="username"
            inputMode="email"
            required
            maxLength={254}
            value={email}
            disabled={submitting}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <div className="login__field">
          <label htmlFor="login-password">Password</label>
          <span className="login__password">
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              name="password"
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              disabled={submitting}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              type="button"
              className="login__toggle"
              aria-pressed={showPassword}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              onClick={() => setShowPassword((current) => !current)}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </span>
        </div>

        <button type="submit" className="login__submit" disabled={submitting} aria-busy={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  )
}

export function SessionGate() {
  return (
    <main className="login">
      <p className="login__gate" role="status">
        Checking your session…
      </p>
    </main>
  )
}
