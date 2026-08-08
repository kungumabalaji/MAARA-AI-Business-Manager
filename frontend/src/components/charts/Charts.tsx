import { useState } from 'react'

type BarDatum = { label: string; value: number }

export function BarTrend({
  data,
  color,
  formatValue = (value: number) => value.toLocaleString('en-GB'),
}: {
  data: BarDatum[]
  color: string
  formatValue?: (value: number) => string
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  const max = Math.max(...data.map((d) => d.value), 1)

  return (
    <div className="chart-bar-trend">
      <div className="chart-bar-trend-bars">
        {data.map((d, i) => {
          const heightPct = Math.max((d.value / max) * 100, 2)
          return (
            <div
              key={`${d.label}-${i}`}
              className="chart-bar-trend-col"
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered((current) => (current === i ? null : current))}
            >
              {hovered === i ? (
                <div className="chart-tooltip" role="tooltip">
                  <strong>{formatValue(d.value)}</strong>
                  <span>{d.label}</span>
                </div>
              ) : null}
              <div className="chart-bar-trend-bar" style={{ height: `${heightPct}%`, background: color }} />
              <span className="chart-bar-trend-label">{d.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

type LineSeries = { key: string; label: string; color: string }
type LinePoint = { label: string; values: Record<string, number> }

export function MultiLineTrend({
  data,
  series,
  formatValue = (value: number) => value.toLocaleString('en-GB'),
}: {
  data: LinePoint[]
  series: LineSeries[]
  formatValue?: (value: number) => string
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const width = 600
  const height = 230
  const paddingLeft = 52
  const paddingBottom = 24
  const paddingTop = 14
  const innerWidth = width - paddingLeft - 14
  const innerHeight = height - paddingTop - paddingBottom

  const allValues = data.flatMap((point) => series.map((s) => point.values[s.key] ?? 0))
  const maxValue = Math.max(...allValues, 1)
  const niceMax = Math.ceil(maxValue / 5) * 5 || 1

  const xFor = (i: number) => paddingLeft + (data.length === 1 ? 0 : (i / (data.length - 1)) * innerWidth)
  const yFor = (value: number) => paddingTop + innerHeight - (value / niceMax) * innerHeight

  function pointsFor(key: string) {
    return data.map((point, i) => `${xFor(i)},${yFor(point.values[key] ?? 0)}`).join(' ')
  }

  const gridLines = [0, 0.25, 0.5, 0.75, 1]
  const clampedHover = hoverIndex === null ? null : Math.min(Math.max(hoverIndex, 0), data.length - 1)

  return (
    <div className="chart-line-trend">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="chart-line-trend-svg"
        onMouseLeave={() => setHoverIndex(null)}
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect()
          const relativeX = ((event.clientX - rect.left) / rect.width) * width
          const ratio = (relativeX - paddingLeft) / innerWidth
          const index = Math.round(ratio * (data.length - 1))
          setHoverIndex(Math.min(Math.max(index, 0), data.length - 1))
        }}
      >
        {gridLines.map((g) => {
          const y = paddingTop + innerHeight * (1 - g)
          return (
            <g key={g}>
              <line x1={paddingLeft} x2={width - 14} y1={y} y2={y} className="chart-gridline" />
              <text x={paddingLeft - 8} y={y + 4} className="chart-axis-label" textAnchor="end">
                {formatValue(niceMax * g)}
              </text>
            </g>
          )
        })}

        {series.map((s) => (
          <polyline
            key={s.key}
            points={pointsFor(s.key)}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
            className="chart-line"
          />
        ))}

        {data.map((point, i) => (
          <text key={point.label} x={xFor(i)} y={height - 4} textAnchor="middle" className="chart-axis-label">
            {point.label}
          </text>
        ))}

        {clampedHover !== null ? (
          <line
            x1={xFor(clampedHover)}
            x2={xFor(clampedHover)}
            y1={paddingTop}
            y2={paddingTop + innerHeight}
            className="chart-crosshair"
          />
        ) : null}

        {clampedHover !== null
          ? series.map((s) => (
              <circle
                key={s.key}
                cx={xFor(clampedHover)}
                cy={yFor(data[clampedHover].values[s.key] ?? 0)}
                r={4}
                fill={s.color}
                stroke="#ffffff"
                strokeWidth={1.5}
              />
            ))
          : null}
      </svg>

      {clampedHover !== null ? (
        <div
          className="chart-line-tooltip"
          style={{ left: `${(xFor(clampedHover) / width) * 100}%` }}
        >
          <strong>{data[clampedHover].label}</strong>
          {series.map((s) => (
            <p key={s.key}>
              <span className="chart-tooltip-dot" style={{ background: s.color }} />
              {s.label}: {formatValue(data[clampedHover].values[s.key] ?? 0)}
            </p>
          ))}
        </div>
      ) : null}

      <div className="chart-legend">
        {series.map((s) => (
          <span key={s.key} className="chart-legend-item">
            <span className="chart-legend-dot" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export function Donut({
  segments,
  centerLabel,
  centerValue,
}: {
  segments: { label: string; value: number; color: string }[]
  centerLabel: string
  centerValue: string
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1
  let cursor = 0
  const stops = segments.map((s) => {
    const start = (cursor / total) * 360
    cursor += s.value
    const end = (cursor / total) * 360
    return `${s.color} ${start}deg ${end}deg`
  })

  return (
    <div className="chart-donut" style={{ background: `conic-gradient(${stops.join(', ')})` }}>
      <div className="chart-donut-hole">
        <strong>{centerValue}</strong>
        <span>{centerLabel}</span>
      </div>
    </div>
  )
}

export function RankedBars({
  rows,
  formatValue,
}: {
  rows: { label: string; value: number; color: string }[]
  formatValue: (value: number) => string
}) {
  const total = rows.reduce((sum, r) => sum + r.value, 0) || 1
  const max = Math.max(...rows.map((r) => r.value), 1)

  return (
    <div className="chart-ranked-bars">
      {rows.map((row) => {
        const pct = (row.value / total) * 100
        const widthPct = (row.value / max) * 100
        return (
          <div key={row.label} className="chart-ranked-row">
            <span className="chart-ranked-label">
              <span className="chart-ranked-dot" style={{ background: row.color }} />
              {row.label}
            </span>
            <div className="chart-ranked-track">
              <div className="chart-ranked-fill" style={{ width: `${widthPct}%`, background: row.color }} />
            </div>
            <span className="chart-ranked-value">{formatValue(row.value)}</span>
            <span className="chart-ranked-pct">{pct.toFixed(0)}%</span>
          </div>
        )
      })}
    </div>
  )
}
