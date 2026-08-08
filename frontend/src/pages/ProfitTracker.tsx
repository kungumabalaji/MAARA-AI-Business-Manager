import { useEffect, useState } from 'react'
import { MultiLineTrend } from '../components/charts/Charts'
import { fetchProfitDailySummary, fetchProfitMonthly } from '../api/reportsApi'
import type { DailyProfitSummary, MonthlyProfitRow } from '../api/types'
import { formatGBP, formatPct, monthLabel, parseAmount, pctChange } from '../data/reportData'

type ProfitTrackerProps = {
  organizationId: string | null
  defaultDate: string
}

function ProfitTracker({ organizationId, defaultDate }: ProfitTrackerProps) {
  const [monthly, setMonthly] = useState<MonthlyProfitRow[]>([])
  const [dailySummary, setDailySummary] = useState<DailyProfitSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([fetchProfitMonthly(organizationId, 7), fetchProfitDailySummary(organizationId, defaultDate)])
      .then(([monthlyRows, summary]) => {
        if (cancelled) return
        setMonthly(monthlyRows)
        setDailySummary(summary)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load profit data.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId, defaultDate])

  const thisMonthRow = monthly[monthly.length - 1]
  const lastMonthRow = monthly[monthly.length - 2]

  const revenue = thisMonthRow ? parseAmount(thisMonthRow.revenue) : 0
  const expenses = thisMonthRow ? parseAmount(thisMonthRow.expenses) : 0
  const profit = revenue - expenses
  const margin = revenue ? (profit / revenue) * 100 : 0

  const lastRevenue = lastMonthRow ? parseAmount(lastMonthRow.revenue) : 0
  const lastExpenses = lastMonthRow ? parseAmount(lastMonthRow.expenses) : 0
  const lastProfit = lastRevenue - lastExpenses
  const lastMargin = lastRevenue ? (lastProfit / lastRevenue) * 100 : 0

  const revenueChange = pctChange(revenue, lastRevenue)
  const expenseChange = pctChange(expenses, lastExpenses)
  const profitChange = pctChange(profit, lastProfit)

  const trendData = monthly.map((row) => {
    const rev = parseAmount(row.revenue)
    const exp = parseAmount(row.expenses)
    return { label: monthLabel(row.month), values: { revenue: rev, expenses: exp, profit: rev - exp } }
  })

  const cashVariance = dailySummary ? parseAmount(dailySummary.cashVariance) : 0
  const cashOk = Math.abs(cashVariance) < 1

  const insights = [
    thisMonthRow
      ? {
          icon: revenueChange >= 0 ? '↗' : '↘',
          tone: revenueChange >= 0 ? 'good' : 'bad',
          text: `Revenue ${revenueChange >= 0 ? 'increased' : 'decreased'} ${formatPct(Math.abs(revenueChange)).replace('+', '')} compared with last month.`,
        }
      : null,
    thisMonthRow
      ? {
          icon: profitChange >= 0 ? '↗' : '↘',
          tone: profitChange >= 0 ? 'good' : 'bad',
          text: `Operating profit ${profitChange >= 0 ? 'increased' : 'decreased'} ${formatPct(Math.abs(profitChange)).replace('+', '')} compared with last month.`,
        }
      : null,
    dailySummary && dailySummary.hasActualCash
      ? {
          icon: cashOk ? '✓' : '⚠',
          tone: cashOk ? 'good' : 'warn',
          text: cashOk
            ? `Cash reconciled for ${dailySummary.date} — expected and actual cash match.`
            : `Cash variance of ${formatGBP(Math.abs(cashVariance), { decimals: false })} on ${dailySummary.date} — ${cashVariance > 0 ? 'more' : 'less'} cash than expected.`,
        }
      : null,
  ].filter((insight): insight is NonNullable<typeof insight> => insight !== null)

  if (!organizationId || loading) {
    return (
      <main className="report-card report-card-simple">
        <div className="report-card-header">
          <div>
            <p className="report-kicker">Profit &amp; Performance</p>
            <h1>Are we actually making money?</h1>
          </div>
        </div>
        <p className="report-subheading">Loading…</p>
      </main>
    )
  }

  if (monthly.length === 0 && !dailySummary) {
    return (
      <main className="report-card report-card-simple">
        <div className="report-card-header">
          <div>
            <p className="report-kicker">Profit &amp; Performance</p>
            <h1>Are we actually making money?</h1>
            <p className="report-subheading">Revenue, expenses, and the operating profit they produce</p>
          </div>
        </div>
        <p className="report-subheading">No reports saved yet — this fills in once you save a Daily Sales Report.</p>
      </main>
    )
  }

  return (
    <main className="report-card report-card-simple">
      <div className="report-card-header">
        <div>
          <p className="report-kicker">Profit &amp; Performance</p>
          <h1>Are we actually making money?</h1>
          <p className="report-subheading">Revenue, expenses, and the operating profit they produce</p>
        </div>
      </div>

      {error ? <p className="feedback error">{error}</p> : null}

      <section className="dashboard-scroll">
        <div className="report-dashboard-strip">
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Total Revenue</p>
            <strong>{formatGBP(revenue, { decimals: false })}</strong>
            {lastMonthRow ? (
              <span className={`dashboard-delta ${revenueChange >= 0 ? 'is-positive' : 'is-negative'}`}>
                {revenueChange >= 0 ? '▲' : '▼'} {formatPct(revenueChange)}
              </span>
            ) : null}
          </div>
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Total Expenses</p>
            <strong>{formatGBP(expenses, { decimals: false })}</strong>
            {lastMonthRow ? (
              <span className={`dashboard-delta ${expenseChange <= 0 ? 'is-positive' : 'is-negative'}`}>
                {expenseChange >= 0 ? '▲' : '▼'} {formatPct(expenseChange)}
              </span>
            ) : null}
          </div>
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Operating Profit</p>
            <strong>{formatGBP(profit, { decimals: false })}</strong>
            {lastMonthRow ? (
              <span className={`dashboard-delta ${profitChange >= 0 ? 'is-positive' : 'is-negative'}`}>
                {profitChange >= 0 ? '▲' : '▼'} {formatPct(profitChange)}
              </span>
            ) : null}
          </div>
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Profit Margin</p>
            <strong>{margin.toFixed(1)}%</strong>
            {lastMonthRow ? (
              <span className={`dashboard-delta ${margin >= lastMargin ? 'is-positive' : 'is-negative'}`}>
                {margin >= lastMargin ? '▲' : '▼'} {formatPct(margin - lastMargin)}pt
              </span>
            ) : null}
          </div>
        </div>

        {trendData.length > 1 ? (
          <div className="report-panel-block">
            <div className="report-panel-title">Revenue vs Expenses vs Operating Profit</div>
            <div className="dashboard-panel-body">
              <MultiLineTrend
                data={trendData}
                series={[
                  { key: 'revenue', label: 'Revenue', color: '#2a78d6' },
                  { key: 'expenses', label: 'Expenses', color: '#eb6834' },
                  { key: 'profit', label: 'Profit', color: '#199e70' },
                ]}
                formatValue={(v) => formatGBP(v, { decimals: false })}
              />
            </div>
          </div>
        ) : null}

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Daily Profit / Loss{dailySummary ? ` — ${dailySummary.date}` : ''}</div>
            <div className="dashboard-panel-body">
              {dailySummary ? (
                <div className="profit-breakdown">
                  <div className="profit-breakdown-row"><span>Revenue</span><span>{formatGBP(parseAmount(dailySummary.revenue), { decimals: false })}</span></div>
                  <div className="profit-breakdown-row"><span>Expenses</span><span>{formatGBP(parseAmount(dailySummary.expenses), { decimals: false })}</span></div>
                  <div className={`profit-breakdown-row is-profit ${parseAmount(dailySummary.profit) < 0 ? 'is-loss' : ''}`}>
                    <span>{parseAmount(dailySummary.profit) >= 0 ? 'Profit' : 'Loss'}</span>
                    <span>{formatGBP(Math.abs(parseAmount(dailySummary.profit)), { decimals: false })}</span>
                  </div>
                </div>
              ) : (
                <p className="dashboard-footnote">No report saved for this date yet.</p>
              )}
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Expected Cash vs Actual Cash</div>
            <div className="dashboard-panel-body">
              {dailySummary ? (
                <div className="profit-breakdown">
                  <div className="profit-breakdown-row">
                    <span>Expected (Opening + Cash Sales − Expenses)</span>
                    <span>{formatGBP(parseAmount(dailySummary.expectedCash), { decimals: false })}</span>
                  </div>
                  <div className="profit-breakdown-row">
                    <span>Actual (counted Cash Balance)</span>
                    <span>{dailySummary.hasActualCash ? formatGBP(parseAmount(dailySummary.actualCash), { decimals: false }) : '— not entered —'}</span>
                  </div>
                  <div className={`profit-breakdown-row is-profit ${cashOk ? '' : 'is-loss'}`}>
                    <span>Variance</span>
                    <span>{dailySummary.hasActualCash ? formatGBP(cashVariance, { decimals: false }) : '—'}</span>
                  </div>
                  <p className="dashboard-footnote">
                    Expected cash assumes expenses were paid out of the till in cash — a simplification until expenses track payment method.
                  </p>
                </div>
              ) : (
                <p className="dashboard-footnote">No report saved for this date yet.</p>
              )}
            </div>
          </div>
        </div>

        {monthly.length > 0 ? (
          <div className="report-panel-block">
            <div className="report-panel-title">Monthly Profit Performance</div>
            <div className="dashboard-panel-body dashboard-recent-body">
              <table className="dashboard-recent-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Revenue</th>
                    <th>Expenses</th>
                    <th>Profit</th>
                    <th>Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {monthly.map((row) => {
                    const rev = parseAmount(row.revenue)
                    const exp = parseAmount(row.expenses)
                    const prof = rev - exp
                    return (
                      <tr key={row.month}>
                        <td>{monthLabel(row.month)}</td>
                        <td>{formatGBP(rev, { decimals: false })}</td>
                        <td>{formatGBP(exp, { decimals: false })}</td>
                        <td>{formatGBP(prof, { decimals: false })}</td>
                        <td>{rev ? ((prof / rev) * 100).toFixed(1) : '0.0'}%</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {insights.length > 0 ? (
          <div className="report-panel-block">
            <div className="report-panel-title">Business Insights</div>
            <div className="dashboard-panel-body">
              <ul className="profit-insights">
                {insights.map((insight) => (
                  <li key={insight.text} className={`profit-insight is-${insight.tone}`}>
                    <span className="profit-insight-icon" aria-hidden="true">{insight.icon}</span>
                    <span>{insight.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  )
}

export default ProfitTracker
