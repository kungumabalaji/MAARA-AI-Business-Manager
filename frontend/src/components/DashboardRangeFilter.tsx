import { RANGE_OPTIONS, type RangeKey } from '../lib/dashboardRange'

type Props = {
  value: RangeKey
  onChange: (range: RangeKey) => void
}

/** The 7 / 30 / 90 / All-time toggle shown at the top of each dashboard. */
export function DashboardRangeFilter({ value, onChange }: Props) {
  return (
    <div className="dashboard-range-filter" role="group" aria-label="Date range">
      {RANGE_OPTIONS.map((opt) => (
        <button
          key={opt.key}
          type="button"
          className={`dashboard-range-btn ${value === opt.key ? 'is-active' : ''}`}
          aria-pressed={value === opt.key}
          onClick={() => onChange(opt.key)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
