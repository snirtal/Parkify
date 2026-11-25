import { Link } from 'react-router-dom'
import './NotFoundPage.css'

export function NotFoundPage() {
  return (
    <section className="not-found">
      <span className="not-found__code">404</span>
      <h2 className="not-found__title">Route Not Found</h2>
      <p className="not-found__text">
        The page you are looking for doesn&apos;t exist or has been moved.
      </p>
      <Link to="/" className="not-found__btn">
        Back to Dashboard
      </Link>
    </section>
  )
}
