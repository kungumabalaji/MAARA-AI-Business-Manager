import { useEffect, useState } from 'react'
import { Donut, BarTrend, RankedBars } from '../components/charts/Charts'
import { fetchExpensesByCategory, fetchExpensesMonthly, fetchExpensesRecent } from '../api/reportsApi'
import type { ExpenseCategoryRow, MonthlyExpenseRow, RecentExpenseRow } from '../api/types'
import { formatGBP, formatPct, monthLabel, parseAmount, pctChange } from '../data/reportData'

const categoryPalette = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7']

type ExpenseDashboardProps = {
  organizationId: string | null
}

function monthBounds(monthKey: string): { since: string; until: string } {
  const [year, month] = monthKey.split('-').map(Number)
  const since = `${monthKey}-01`
  const untilDate = new Date(year, month, 0) // last day of the month
  const until = untilDate.toISOString().slice(0, 10)
  return { since, until }
}

function ExpenseDashboard({ organizationId }: ExpenseDashboardProps) {
  const [monthly, setMonthly] = useState<MonthlyExpenseRow[]>([])
  const [categories, setCategories] = useState<ExpenseCategoryRow[]>([])
  const [recent, setRecent] = useState<RecentExpenseRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchExpensesMonthly(organizationId, 7)
      .then(async (monthlyRows) => {
        if (cancelled) return
        setMonthly(monthlyRows)

        const currentMonthKey = monthlyRows[monthlyRows.length - 1]?.month
        const [categoryRows, recentRows] = await Promise.all([
          currentMonthKey
            ? fetchExpensesByCategory(organizationId, monthBounds(currentMonthKey).since, monthBounds(currentMonthKey).until)
            : Promise.resolve([]),
          fetchExpensesRecent(organizationId, 15),
        ])
        if (cancelled) return
        setCategories(categoryRows)
        setRecent(recentRows)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load expense data.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId])

  const thisMonthRow = monthly[monthly.length - 1]
  const lastMonthRow = monthly[monthly.length - 2]
  const thisMonthTotal = thisMonthRow ? parseAmount(thisMonthRow.total) : 0
  const lastMonthTotal = lastMonthRow ? parseAmount(lastMonthRow.total) : 0
  const totalExpenses = monthly.reduce((sum, row) => sum + parseAmount(row.total), 0)
  const avgDailyExpense = thisMonthTotal / 30
  const expenseChange = pctChange(thisMonthTotal, lastMonthTotal)
  const largestCategory = categories[0]

  const donutSegments = categories.map((row, i) => ({
    label: row.category,
    value: parseAmount(row.total),
    color: categoryPalette[i % categoryPalette.length],
  }))

  const trendData = monthly.map((row) => ({ label: monthLabel(row.month), value: parseAmount(row.total) }))

  const kpis = [
    { label: 'Total Expenses', value: formatGBP(totalExpenses, { decimals: false }), hint: 'across loaded months' },
    { label: 'This Month', value: formatGBP(thisMonthTotal, { decimals: false }), hint: thisMonthRow ? monthLabel(thisMonthRow.month) : '—' },
    { label: 'Avg Daily Expense', value: formatGBP(avgDailyExpense, { decimals: false }), hint: 'this month / 30' },
    { label: 'Largest Category', value: largestCategory?.category ?? '—', hint: largestCategory ? formatGBP(parseAmount(largestCategory.total), { decimals: false }) : '' },
    { label: 'Expense Change', value: formatPct(expenseChange), hint: 'vs previous month', positive: expenseChange <= 0 },
  ]

  if (!organizationId || loading) {
    return (
      <main className="report-card report-card-simple">
        <div className="report-card-header">
          <div>
            <p className="report-kicker">Expenses Dashboard</p>
            <h1>Dosa n Chutney</h1>
          </div>
        </div>
        <p className="report-subheading">Loading…</p>
      </main>
    )
  }

  if (monthly.length === 0) {
    return (
      <main className="report-card report-card-simple">
        <div className="report-card-header">
          <div>
            <p className="report-kicker">Expenses Dashboard</p>
            <h1>Dosa n Chutney</h1>
            <p className="report-subheading">Where the money is going, and which costs are rising</p>
          </div>
        </div>
        <p className="report-subheading">No expenses logged yet — add expense rows to a Daily Sales Report to see them here.</p>
      </main>
    )
  }

  return (
    <main className="report-card report-card-simple">
      <div className="report-card-header">
        <div>
          <p className="report-kicker">Expenses Dashboard</p>
          <h1>Dosa n Chutney</h1>
          <p className="report-subheading">Where the money is going, and which costs are rising</p>
        </div>
      </div>

      {error ? <p className="feedback error">{error}</p> : null}

      <section className="dashboard-scroll">
        <div className="report-dashboard-strip dashboard-strip-five">
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

        <div className="report-panel-block report-panel-expense">
          <div className="report-panel-title">Expense Trend</div>
          <div className="dashboard-panel-body">
            <BarTrend data={trendData} color="var(--accent-expense)" formatValue={(v) => formatGBP(v, { decimals: false })} />
          </div>
        </div>

        <div className="report-panel-block">
          <div className="report-panel-title">Expense by Category{thisMonthRow ? ` — ${monthLabel(thisMonthRow.month)}` : ''}</div>
          <div className="dashboard-panel-body dashboard-donut-body">
            {donutSegments.length ? (
              <>
                <Donut segments={donutSegments} centerLabel="this month" centerValue={formatGBP(thisMonthTotal, { decimals: false })} />
                <RankedBars rows={donutSegments} formatValue={(v) => formatGBP(v, { decimals: false })} />
              </>
            ) : (
              <p className="dashboard-footnote">No expense rows for this month yet.</p>
            )}
          </div>
        </div>

        <div className="report-panel-block">
          <div className="report-panel-title">Recent Expenses</div>
          <div className="dashboard-panel-body dashboard-recent-body">
            {recent.length ? (
              <table className="dashboard-recent-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((row, index) => (
                    <tr key={`${row.date}-${row.description}-${index}`}>
                      <td>{new Date(`${row.date}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}</td>
                      <td>{row.description}</td>
                      <td>{row.category}</td>
                      <td>{formatGBP(parseAmount(row.amount), { decimals: false })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="dashboard-footnote">No expenses logged yet.</p>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}

export default ExpenseDashboard
