import { useState } from 'react'
import type { ParkingBay } from '../../types/parking'
import { matchBayQuery } from './searchUtils'
import './ParkingSearchBar.css'

export interface ParkingSearchBarProps {
  bays: ParkingBay[]
  selectedBayId: string
  query: string
  onQueryChange: (value: string) => void
  onSelectBay: (bayId: string) => void
}

export function ParkingSearchBar({
  bays,
  selectedBayId,
  query,
  onQueryChange,
  onSelectBay,
}: ParkingSearchBarProps) {
  const [isFocused, setIsFocused] = useState(false)

  const hasQuery = query.trim().length > 0
  const matches = hasQuery ? bays.filter((bay) => matchBayQuery(bay, query)) : []

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && matches.length > 0) {
      event.preventDefault()
      onSelectBay(matches[0].id)
    } else if (event.key === 'Escape' && hasQuery) {
      event.preventDefault()
      onQueryChange('')
    }
  }

  return (
    <div className="map-search" role="search" aria-label="Search parking spaces and license plates">
      <div className={`map-search__bar${isFocused ? ' map-search__bar--focused' : ''}`}>
        <svg
          className="map-search__icon"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input
          type="search"
          className="map-search__input"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Search space number (e.g. P-204) or license plate (e.g. VEL-204X)…"
          aria-label="Search space number or vehicle license plate"
        />

        {hasQuery && (
          <div className="map-search__meta">
            <span className="map-search__count">
              {matches.length} {matches.length === 1 ? 'match' : 'matches'}
            </span>
            <button
              type="button"
              className="map-search__clear"
              onClick={() => onQueryChange('')}
              aria-label="Clear search"
            >
              ×
            </button>
          </div>
        )}
      </div>

      {hasQuery && (
        <div className="map-search__results" aria-live="polite">
          {matches.length > 0 ? (
            matches.slice(0, 8).map((bay) => {
              const isSelected = bay.id === selectedBayId
              return (
                <button
                  key={bay.id}
                  type="button"
                  className={`map-search__chip map-search__chip--${bay.status}${isSelected ? ' map-search__chip--selected' : ''}`}
                  onClick={() => onSelectBay(bay.id)}
                >
                  <span className="map-search__chip-dot" aria-hidden="true" />
                  <span className="map-search__chip-code">{bay.code}</span>
                  {(bay.vehicle?.plateNumber ?? bay.reservedPlate) && (
                    <span className="map-search__chip-plate">
                      {bay.vehicle?.plateNumber ?? bay.reservedPlate}
                    </span>
                  )}
                  <span className="map-search__chip-deck">Deck {bay.deck}</span>
                </button>
              )
            })
          ) : (
            <span className="map-search__empty">
              No parking space or license plate matches &ldquo;{query.trim()}&rdquo;.
            </span>
          )}
        </div>
      )}
    </div>
  )
}
