import { useMemo } from 'react'
import { BarTrend, RankedBars } from '../components/charts/Charts'
import {
  channelTotal,
  currentMonth,
  dailySalesLedger,
  formatGBP,
  formatPct,
  lastNDays,
  monthlySalesLedger,
  pctChange,
  previousMonth,
  previousNDays,
  salesChannelMeta,
  weekdayLabel,
} from '../data/reportData'

function SalesDashboard() {
  const currentMonthRow = monthlySalesLedger.find((row) => row.month === currentMonth)!
  const previousMonthRow = monthlySalesLedger.find((row) => row.month === previousMonth)!

  const monthTotal = channelTotal(currentMonthRow)
  const prevMonthTotal = channelTotal(previousMonthRow)
  const monthGrowth = pctChange(monthTotal, prevMonthTotal)

  const last7 = useMemo(() => lastNDays(dailySalesLedger, 7), [])
  const prev7 = useMemo(() => previousNDays(dailySalesLedger, 7), [])

  const today = last7[last7.length - 1]
  const yesterday = last7[last7.length - 2]
  const todayTotal = channelTotal(today)
  const yesterdayTotal = channelTotal(yesterday)

  const thisWeekTotal = last7.reduce((sum, day) => sum + channelTotal(day), 0)
  const lastWeekTotal = prev7.reduce((sum, day) => sum + channelTotal(day), 0)

  const avgDailySales = thisWeekTotal / last7.length

  const channelRows = salesChannelMeta.map((meta) => ({
    label: meta.label,
    value: currentMonthRow[meta.key],
    color: meta.color,
  }))

  const trendData = last7.map((day) => ({ label: weekdayLabel(day.date), value: channelTotal(day) }))

  const deliverySales = currentMonthRow.uberEatsSales + currentMonthRow.justEatSales + currentMonthRow.deliverooSales
  const deliveryShare = (deliverySales / monthTotal) * 100

  const kpis = [
    { label: 'Total Sales', value: formatGBP(monthTotal), hint: currentMonth },
    { label: 'Today Sales', value: formatGBP(todayTotal), hint: weekdayLabel(today.date) },
    { label: 'Avg Daily Sales', value: formatGBP(avgDailySales), hint: 'last 7 days' },
    { label: 'Sales Growth', value: formatPct(monthGrowth), hint: `vs ${previousMonth}`, positive: monthGrowth >= 0 },
  ]

  const comparisons = [
    { label: 'Today vs Yesterday', current: todayTotal, previous: yesterdayTotal },
    { label: 'This Week vs Last Week', current: thisWeekTotal, previous: lastWeekTotal },
    { label: 'This Month vs Last Month', current: monthTotal, previous: prevMonthTotal },
  ]

  return (
    <main className="report-card report-card-simple">
      <div className="report-card-header">
        <div>
          <p className="report-kicker">Sales Dashboard</p>
          <h1>Dosa n Chutney</h1>
          <p className="report-subheading">Where the money is coming from, and how sales are moving</p>
        </div>
      </div>

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
              <RankedBars rows={channelRows} formatValue={(v) => formatGBP(v, { decimals: false })} />
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Sales Trend — Last 7 Days</div>
            <div className="dashboard-panel-body">
              <BarTrend data={trendData} color="var(--brand-violet)" formatValue={(v) => formatGBP(v, { decimals: false })} />
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
                  <strong>{formatGBP(currentMonthRow.uberEatsSales, { decimals: false })}</strong>
                </li>
                <li>
                  <span>Just Eat</span>
                  <strong>{formatGBP(currentMonthRow.justEatSales, { decimals: false })}</strong>
                </li>
                <li>
                  <span>Deliveroo</span>
                  <strong>{formatGBP(currentMonthRow.deliverooSales, { decimals: false })}</strong>
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
