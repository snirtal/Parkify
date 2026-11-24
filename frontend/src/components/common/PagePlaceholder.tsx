import type { NavIconName } from '../../config/navigation'
import { NavIcon } from '../icons/AppIcons'
import './PagePlaceholder.css'

export interface PlaceholderModule {
  title: string
  description: string
}

export interface PagePlaceholderProps {
  icon: NavIconName
  badge: string
  heading: string
  description: string
  modules: PlaceholderModule[]
}

export function PagePlaceholder({
  icon,
  badge,
  heading,
  description,
  modules,
}: PagePlaceholderProps) {
  return (
    <div className="page-shell">
      <section className="page-shell__hero">
        <div className="page-shell__icon-wrap">
          <NavIcon name={icon} />
        </div>

        <div className="page-shell__hero-copy">
          <span className="page-shell__badge">{badge}</span>
          <h2 className="page-shell__heading">{heading}</h2>
          <p className="page-shell__description">{description}</p>
        </div>
      </section>

      <section className="page-shell__grid" aria-label="Planned workspace modules">
        {modules.map((module) => (
          <article key={module.title} className="page-shell__card">
            <div className="page-shell__card-header">
              <h3 className="page-shell__card-title">{module.title}</h3>
              <span className="page-shell__card-tag">Planned</span>
            </div>
            <p className="page-shell__card-text">{module.description}</p>
            <div className="page-shell__slot" aria-hidden="true" />
          </article>
        ))}
      </section>
    </div>
  )
}
