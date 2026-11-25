import { useState } from 'react'
import type { ParkingBay } from '../../types/parking'
import './BottomDeckCards.css'

export interface BottomDeckCardsProps {
  selectedBay: ParkingBay
}

export function BottomDeckCards({ selectedBay }: BottomDeckCardsProps) {
  const [isMonitoringLive, setIsMonitoringLive] = useState(true)
  const [assistTriggered, setAssistTriggered] = useState(false)

  const message =
    selectedBay.vehicle?.alertNote ??
    `AI Sentinel (${selectedBay.code}): ${selectedBay.sensorNote}`

  return (
    <div className="bottom-deck">
      {/* Left Card: AI Sentinel Transcript + Neon Plasma Waveform (matches bottom-left of reference) */}
      <div className="sentinel-stack">
        <article className="sentinel-card">
          <span className="sentinel-card__handle" aria-hidden="true" />
          <div className="sentinel-card__meta">
            <span className="sentinel-card__tag">AI Optical Guard • {selectedBay.code}</span>
            <span className="sentinel-card__sim">Live feed</span>
          </div>
          <p className="sentinel-card__text">
            {message}
            <span className="sentinel-card__cursor" aria-hidden="true" />
          </p>
        </article>

        <div className="waveform-bar">
          <div className="waveform-bar__visual" aria-hidden="true">
            <span
              className={`waveform-bar__orb${isMonitoringLive ? ' waveform-bar__orb--live' : ''}`}
            />
            <svg viewBox="0 0 220 32" className="waveform-bar__svg" preserveAspectRatio="none">
              <defs>
                <linearGradient id="waveGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.15" />
                  <stop offset="45%" stopColor="#A855F7" stopOpacity="0.95" />
                  <stop offset="75%" stopColor="#EC4899" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#6366F1" stopOpacity="0.1" />
                </linearGradient>
              </defs>
              <path
                d="M 0 16 Q 28 16, 48 11 T 92 18 T 136 8 T 176 20 T 220 16"
                fill="none"
                stroke="url(#waveGrad)"
                strokeWidth="2.4"
              />
              <path
                d="M 0 16 Q 34 21, 62 15 T 112 10 T 158 22 T 220 16"
                fill="none"
                stroke="rgba(34, 211, 238, 0.45)"
                strokeWidth="1.2"
              />
            </svg>
          </div>

          <div className="waveform-bar__controls">
            <span className="waveform-bar__status">
              {isMonitoringLive ? 'Pause record' : 'Paused'}
            </span>
            <button
              type="button"
              className="waveform-bar__btn"
              onClick={() => setIsMonitoringLive((prev) => !prev)}
              aria-label={isMonitoringLive ? 'Pause telemetry stream' : 'Resume telemetry stream'}
            >
              {isMonitoringLive ? '❚❚' : '▶'}
            </button>
          </div>
        </div>
      </div>

      {/* Right Card: Security Camera & Emergency Operator Assist (matches reference 'Something wrong?') */}
      <article className="security-card">
        <div className="security-card__top">
          <div className="security-card__copy">
            <h3 className="security-card__title">Something wrong?</h3>
            <p className="security-card__sub">
              Don&apos;t think!
              <br />
              Call for help!
            </p>
          </div>

          {/* Stylized 3D-shaded CCTV Camera with Glowing Crimson Ring */}
          <svg
            width="116"
            height="88"
            viewBox="0 0 120 92"
            className="security-card__cam"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="camBody" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#353052" />
                <stop offset="100%" stopColor="#141126" />
              </linearGradient>
            </defs>
            {/* Wall bracket */}
            <rect x="96" y="34" width="16" height="44" rx="4" fill="#231f3a" />
            <path d="M 74 56 L 98 56 L 98 64 L 70 64 Z" fill="#1b1830" />
            {/* Camera housing */}
            <g transform="rotate(8 56 46)">
              <rect x="24" y="24" width="62" height="36" rx="10" fill="url(#camBody)" />
              <rect x="18" y="28" width="28" height="32" rx="9" fill="#0d0b1a" />
              {/* Glowing crimson optical ring */}
              <circle
                cx="32"
                cy="44"
                r="10"
                fill="#090712"
                stroke="#f43f5e"
                strokeWidth="2.8"
              />
              <circle cx="32" cy="44" r="3.5" fill="#fb7185" />
            </g>
          </svg>
        </div>

        <button
          type="button"
          className={`security-card__cta${assistTriggered ? ' security-card__cta--active' : ''}`}
          onClick={() => setAssistTriggered((prev) => !prev)}
        >
          <span className="security-card__cta-pill">((•))</span>
          <span className="security-card__cta-label">
            {assistTriggered
              ? `Operator linked to ${selectedBay.code}`
              : 'Click for operator assist'}
          </span>
        </button>
      </article>
    </div>
  )
}
