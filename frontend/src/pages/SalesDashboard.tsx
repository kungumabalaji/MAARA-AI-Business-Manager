import { useEffect, useMemo, useState } from 'react'
import { BarTrend, RankedBars } from '../components/charts/Charts'
import { fetchSalesDaily, fetchSalesMonthly } from '../api/reportsApi'
import type { DailySalesRow, MonthlySalesRow } from '../api/types'
import {
  channelTotal,
  formatGBP,
  formatPct,
  lastNDays,
  parseAmount,
  pctChange,
  previousNDays,
  salesChannelMeta,
  weekdayLabel,
  type SalesChannels,
} from '../data/reportData'

type SalesDashboardProps = {
  organizationId: string | null
}

function toChannels(row: DailySalesRow | MonthlySalesRow): SalesChannels {
  return {
    cardSales: parseAmount(row.cardSales),
    cashSales: parseAmount(row.cashSales),
    uberEatsSales: parseAmount(row.uberEatsSales),
    justEatSales: parseAmount(row.justEatSales),
    deliverooSales: parseAmount(row.deliverooSales),
    otherSales: parseAmount(row.otherSales),
    miscIncome: parseAmount(row.miscIncome),
  }
}

function SalesDashboard({ organizationId }: SalesDashboardProps) {
  const [daily, setDaily] = useState<DailySalesRow[]>([])
  const [monthly, setMonthly] = useState<MonthlySalesRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([fetchSalesDaily(organizationId, 21), fetchSalesMonthly(organizationId, 7)])
      .then(([dailyRows, monthlyRows]) => {
        if (cancelled) return
        setDaily(dailyRows)
        setMonthly(monthlyRows)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load sales data.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId])

  const currentMonthRow = monthly[monthly.length - 1]
  const previousMonthRow = monthly[monthly.length - 2]

  const monthTotal = currentMonthRow ? channelTotal(toChannels(currentMonthRow)) : 0
  const prevMonthTotal = previousMonthRow ? channelTotal(toChannels(previousMonthRow)) : 0
  const monthGrowth = pctChange(monthTotal, prevMonthTotal)

  const last7 = useMemo(() => lastNDays(daily, 7), [daily])
  const prev7 = useMemo(() => previousNDays(daily, 7), [daily])

  const today = last7[last7.length - 1]
  const yesterday = last7[last7.length - 2]
  const todayTotal = today ? channelTotal(toChannels(today)) : 0
  const yesterdayTotal = yesterday ? channelTotal(toChannels(yesterday)) : 0

  const thisWeekTotal = last7.reduce((sum, day) => sum + channelTotal(toChannels(day)), 0)
  const lastWeekTotal = prev7.reduce((sum, day) => sum + channelTotal(toChannels(day)), 0)
  const avgDailySales = last7.length ? thisWeekTotal / last7.length : 0

  const channelRows = currentMonthRow
    ? salesChannelMeta.map((meta) => ({
        label: meta.label,
        value: toChannels(currentMonthRow)[meta.key],
        color: meta.color,
      }))
    : []

  const trendData = last7.map((day) => ({ label: weekdayLabel(day.date), value: channelTotal(toChannels(day)) }))

  const deliverySales = currentMonthRow
    ? toChannels(currentMonthRow).uberEatsSales + toChannels(currentMonthRow).justEatSales + toChannels(currentMonthRow).deliverooSales
    : 0
  const deliveryShare = monthTotal ? (deliverySales / monthTotal) * 100 : 0

  const kpis = [
    { label: 'Total Sales', value: formatGBP(monthTotal), hint: currentMonthRow?.month ?? 'This month' },
    { label: 'Today Sales', value: formatGBP(todayTotal), hint: today ? weekdayLabel(today.date) : 'No entry yet' },
    { label: 'Avg Daily Sales', value: formatGBP(avgDailySales), hint: 'last 7 days with entries' },
    { label: 'Sales Growth', value: formatPct(monthGrowth), hint: 'vs previous month', positive: monthGrowth >= 0 },
  ]

  const comparisons = [
    { label: 'Today vs Yesterday', current: todayTotal, previous: yesterdayTotal },
    { label: 'This Week vs Last Week', current: thisWeekTotal, previous: lastWeekTotal },
    { label: 'This Month vs Last Month', current: monthTotal, previous: prevMonthTotal },
  ]

  if (!organizationId || loading) {
    return (
      <main className="report-card report-card-simple">
        <div className="report-card-header">
          <div>
            <p className="report-kicker">Sales Dashboard</p>
            <h1>Dosa n Chutney</h1>
          </div>
        </div>
        <p className="report-subheading">Loading…</p>
      </main>
    )
  }

  if (daily.length === 0 && monthly.length === 0) {
    return (
      <main className="report-card report-card-simple">
        <div className="report-card-header">
          <div>
            <p className="report-kicker">Sales Dashboard</p>
            <h1>Dosa n Chutney</h1>
            <p className="report-subheading">Where the money is coming from, and how sales are moving</p>
          </div>
        </div>
        <p className="report-subheading">
          No sales data yet — fill in and save a Daily Sales Report to see it here.
        </p>
      </main>
    )
  }

  return (
    <main className="report-card report-card-simple">
      <div className="report-card-header">
        <div>
          <p className="report-kicker">Sales Dashboard</p>
          <h1>Dosa n Chutney</h1>
          <p className="report-subheading">Where the money is coming from, and how sales are moving</p>
        </div>
      </div>

      {error ? <p className="feedback error">{error}</p> : null}

      <section className="dashboard-scroll">
        <div className="report-dashboard-strip">
          {kpis.map((card) => (
            <div key={card.label} className="report-dashboard-card">
              <p>{card.label}</p>
              <strong className={card.positive === false ? 'is-negative' : card.positive ? 'is-positive' : ''}>
                {card.value}
              </strong>
              <span className="dashboard-card-hint">{card.hint}</span>
            </div>
          ))}
        </div>

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block report-panel-income">
            <div className="report-panel-title">Sales by Channel</div>
            <div className="dashboard-panel-body">
              {channelRows.length ? (
                <RankedBars rows={channelRows} formatValue={(v) => formatGBP(v, { decimals: false })} />
              ) : (
                <p className="dashboard-footnote">No channel data for this month yet.</p>
              )}
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Sales Trend — Last 7 Entries</div>
            <div className="dashboard-panel-body">
              {trendData.length ? (
                <BarTrend data={trendData} color="var(--brand-violet)" formatValue={(v) => formatGBP(v, { decimals: false })} />
              ) : (
                <p className="dashboard-footnote">No daily entries yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Delivery Platform Performance</div>
            <div className="dashboard-panel-body dashboard-delivery-body">
              <ul className="dashboard-simple-list">
                <li>
                  <span>Uber Eats</span>
                  <strong>{formatGBP(currentMonthRow ? toChannels(currentMonthRow).uberEatsSales : 0, { decimals: false })}</strong>
                </li>
                <li>
                  <span>Just Eat</span>
                  <strong>{formatGBP(currentMonthRow ? toChannels(currentMonthRow).justEatSales : 0, { decimals: false })}</strong>
                </li>
                <li>
                  <span>Deliveroo</span>
                  <strong>{formatGBP(currentMonthRow ? toChannels(currentMonthRow).deliverooSales : 0, { decimals: false })}</strong>
                </li>
              </ul>
              <div className="dashboard-delivery-summary">
                <div>
                  <p>Total Delivery Sales</p>
                  <strong>{formatGBP(deliverySales, { decimals: false })}</strong>
                </div>
                <div>
                  <p>Delivery % of Sales</p>
                  <strong>{deliveryShare.toFixed(0)}%</strong>
                </div>
              </div>
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Period Comparisons</div>
            <div className="dashboard-panel-body">
              <div className="dashboard-comparison-list">
                {comparisons.map((row) => {
                  const change = pctChange(row.current, row.previous)
                  return (
                    <div key={row.label} className="dashboard-comparison-row">
                      <span className="dashboard-comparison-label">{row.label}</span>
                      <span className="dashboard-comparison-values">
                        {formatGBP(row.current, { decimals: false })}
                        <span className="dashboard-comparison-prev"> vs {formatGBP(row.previous, { decimals: false })}</span>
                      </span>
                      <span className={`dashboard-delta ${change >= 0 ? 'is-positive' : 'is-negative'}`}>
                        {change >= 0 ? '▲' : '▼'} {formatPct(change)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

export default SalesDashboard
