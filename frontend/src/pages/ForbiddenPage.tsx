import { Link } from 'react-router-dom'
import { canVisit } from '../auth/permissions'
import { useAuth } from '../auth/useAuth'
import './NotFoundPage.css'

export function ForbiddenPage() {
  const { user } = useAuth()
  const home = canVisit(user?.role, '/')

  return (
    <section className="not-found">
      <span className="not-found__code">403</span>
      <h2 className="not-found__title">Access denied</h2>
      <p className="not-found__text">You do not have access to this page.</p>
      {home ? (
        <Link to="/" className="not-found__btn">
          Back to Dashboard
        </Link>
      ) : null}
    </section>
  )
}
