import './ProgressBar.css'

export type ProgressBarTone = 'emerald' | 'primary' | 'amber' | 'rose'

export interface ProgressBarProps {
  value: number
  max: number
  label: string
  tone?: ProgressBarTone
}

export function ProgressBar({
  value,
  max,
  label,
  tone = 'primary',
}: ProgressBarProps) {
  const safeMax = max > 0 ? max : 1
  const percentage = Math.min(Math.max((value / safeMax) * 100, 0), 100)

  return (
    <div
      className="progress-bar"
      role="progressbar"
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <div
        className={`progress-bar__fill progress-bar__fill--${tone}`}
        style={{ width: `${percentage.toFixed(1)}%` }}
      />
    </div>
  )
}
