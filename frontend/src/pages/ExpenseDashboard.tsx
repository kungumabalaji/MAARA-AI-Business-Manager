import { useEffect, useMemo, useState } from 'react'
import { BarTrend, Donut, RankedBars } from '../components/charts/Charts'
import { fetchExpenseCategories, fetchExpensesByCategory, fetchExpensesMonthly, fetchExpensesRecent } from '../api/reportsApi'
import type { ExpenseCategoryDef, ExpenseCategoryRow, MonthlyExpenseRow, RecentExpenseRow } from '../api/types'
import { formatGBP, monthLabel, parseAmount } from '../data/reportData'
import { MONTH_NAMES, MONTH_SHORT_NAMES, monthRangeISO, todayISO, type MonthFilter } from '../lib/dashboardRange'
import { downloadCsv } from '../lib/csvExport'

const categoryPalette = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#7a5cf0', '#c04851', '#3aa7a0']

type ExpenseDashboardProps = {
  organizationId: string | null
}

const RECORDS_PAGE_SIZE = 15
// Wide enough to cover a full calendar year either side of today, so the
// year's worth of monthly data (which can include past AND future-dated
// months relative to "today") is never silently cut off.
const MONTHLY_FETCH_MONTHS = 24
const RECENT_FETCH_LIMIT = 500

const sumMonthly = (rows: MonthlyExpenseRow[]) => rows.reduce((total, row) => total + parseAmount(row.total), 0)

function ExpenseDashboard({ organizationId }: ExpenseDashboardProps) {
  const year = new Date().getFullYear()

  const [monthFilter, setMonthFilter] = useState<MonthFilter>('all')

  const [monthlyRows, setMonthlyRows] = useState<MonthlyExpenseRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [categories, setCategories] = useState<ExpenseCategoryRow[]>([])
  const [allCategoryDefs, setAllCategoryDefs] = useState<ExpenseCategoryDef[]>([])
  const [recent, setRecent] = useState<RecentExpenseRow[]>([])
  const [scopeLoading, setScopeLoading] = useState(true)
  const [recordsPage, setRecordsPage] = useState(1)

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([fetchExpensesMonthly(organizationId, MONTHLY_FETCH_MONTHS), fetchExpenseCategories(organizationId)])
      .then(([rows, categoryDefs]) => {
        if (cancelled) return
        setMonthlyRows(rows)
        setAllCategoryDefs(categoryDefs)
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

  useEffect(() => {
    setRecordsPage(1)
  }, [monthFilter])

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setScopeLoading(true)

    const scopedSince =
      monthFilter === 'all' ? `${year}-01-01` : monthFilter === 'today' ? todayISO() : monthRangeISO(year, monthFilter).since
    const scopedUntil =
      monthFilter === 'all' ? `${year}-12-31` : monthFilter === 'today' ? todayISO() : monthRangeISO(year, monthFilter).until

    Promise.all([
      fetchExpensesByCategory(organizationId, scopedSince, scopedUntil),
      fetchExpensesRecent(organizationId, RECENT_FETCH_LIMIT, scopedSince, scopedUntil),
    ])
      .then(([categoryRows, recentRows]) => {
        if (cancelled) return
        setCategories(categoryRows)
        setRecent(recentRows)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load expense data.')
      })
      .finally(() => {
        if (!cancelled) setScopeLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId, monthFilter, year])

  const monthlyByKey = useMemo(() => {
    const map = new Map<string, number>()
    for (const row of monthlyRows) map.set(row.month, parseAmount(row.total))
    return map
  }, [monthlyRows])

  const selectedMonthKey = typeof monthFilter === 'number' ? `${year}-${String(monthFilter + 1).padStart(2, '0')}` : null

  const grandTotal = sumMonthly(monthlyRows.filter((r) => r.month.startsWith(String(year))))
  // Fixed /12 denominator — a month with nothing recorded yet must not pull
  // the average up, same reasoning as the Sales Dashboard's days-in-month fix.
  const avgPerMonth = grandTotal / 12

  // "Today" has no precomputed monthly row to look up — sum the already
  // today-scoped category totals instead (fetched by the effect above).
  const scopedCategoryTotal = categories.reduce((sum, row) => sum + parseAmount(row.total), 0)

  const totalExpenses =
    monthFilter === 'all' ? grandTotal : monthFilter === 'today' ? scopedCategoryTotal : monthlyByKey.get(selectedMonthKey!) ?? 0

  const monthlyChartData = monthlyRows
    .filter((r) => r.month.startsWith(String(year)))
    .sort((a, b) => (a.month < b.month ? -1 : 1))
    .map((row) => ({ label: monthLabel(row.month), value: parseAmount(row.total) }))

  const donutSegments = categories.map((row, i) => ({
    label: row.category,
    value: parseAmount(row.total),
    color: categoryPalette[i % categoryPalette.length],
  }))
  const topCategories = [...donutSegments].sort((a, b) => b.value - a.value).slice(0, 8)

  const rangeLabelText = monthFilter === 'all' ? `${year} (All Months)` : monthFilter === 'today' ? 'Today' : `${MONTH_NAMES[monthFilter]} ${year}`

  const recordsTotalPages = Math.max(1, Math.ceil(recent.length / RECORDS_PAGE_SIZE))
  const pagedRecords = recent.slice((recordsPage - 1) * RECORDS_PAGE_SIZE, recordsPage * RECORDS_PAGE_SIZE)

  function handleExportCsv() {
    const headers = ['Date', 'Description', 'Category', 'Amount']
    const rows = recent.map((row) => [row.date, row.description, row.category, parseAmount(row.amount)])
    const fileScope = monthFilter === 'all' ? 'all-months' : monthFilter === 'today' ? `today-${todayISO()}` : MONTH_NAMES[monthFilter].toLowerCase()
    downloadCsv(`expenses-${fileScope}-${year}.csv`, headers, rows)
  }

  const kpis = [
    {
      label: monthFilter === 'all' ? 'Grand Total' : monthFilter === 'today' ? 'Today Total' : `${MONTH_NAMES[monthFilter]} Total`,
      value: formatGBP(totalExpenses, { decimals: false }),
      hint: rangeLabelText,
    },
    { label: 'Grand Total (All Months)', value: formatGBP(grandTotal, { decimals: false }), hint: `${year}` },
    { label: 'Monthly Average', value: formatGBP(avgPerMonth, { decimals: false }), hint: `${year}, 12 months` },
    { label: 'Expense Categories', value: String(allCategoryDefs.length), hint: 'defined for this org' },
  ]

  const header = (
    <div className="report-card-header">
      <div>
        <p className="report-kicker">Expenses Dashboard</p>
        <h1>Dosa n Chutney</h1>
        <p className="report-subheading">Where the money is going, and which costs are rising</p>
      </div>
      <div className="dashboard-header-actions">
        <button
          type="button"
          className={`dashboard-today-btn ${monthFilter === 'today' ? 'is-active' : ''}`}
          aria-pressed={monthFilter === 'today'}
          onClick={() => setMonthFilter((current) => (current === 'today' ? 'all' : 'today'))}
        >
          Today
        </button>
        <button type="button" className="dashboard-export-btn" onClick={handleExportCsv}>
          Export CSV
        </button>
      </div>
    </div>
  )

  const monthPills = (
    <div className="report-panel-block dashboard-month-pill-panel">
      <div className="dashboard-month-pills" role="group" aria-label="Filter by month">
        {MONTH_SHORT_NAMES.map((short, index) => (
          <button
            key={short}
            type="button"
            className={`dashboard-month-pill ${monthFilter === index ? 'is-active' : ''}`}
            aria-pressed={monthFilter === index}
            onClick={() => setMonthFilter((current) => (current === index ? 'all' : index))}
          >
            {short}
          </button>
        ))}
      </div>
    </div>
  )

  if (!organizationId || loading) {
    return (
      <main className="report-card report-card-simple">
        {header}
        <p className="report-subheading">Loading…</p>
      </main>
    )
  }

  if (monthlyRows.length === 0) {
    return (
      <main className="report-card report-card-simple">
        {header}
        <p className="report-subheading">No expenses logged yet — add expense rows to a Daily Sales Report to see them here.</p>
      </main>
    )
  }

  return (
    <main className="report-card report-card-simple">
      {header}

      {error ? <p className="feedback error">{error}</p> : null}

      <section className="dashboard-scroll">
        <div className="report-dashboard-strip">
          {kpis.map((card) => (
            <div key={card.label} className="report-dashboard-card">
              <p>{card.label}</p>
              <strong>{card.value}</strong>
              <span className="dashboard-card-hint">{card.hint}</span>
            </div>
          ))}
        </div>

        {monthPills}

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block report-panel-expense">
            <div className="report-panel-title">Monthly Expenses — {year}</div>
            <div className="dashboard-panel-body">
              {monthlyChartData.length ? (
                <BarTrend data={monthlyChartData} color="var(--accent-expense)" formatValue={(v) => formatGBP(v, { decimals: false })} />
              ) : (
                <p className="dashboard-footnote">No monthly data yet.</p>
              )}
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">
              {monthFilter === 'all' ? `Expense by Category — ${rangeLabelText}` : `${rangeLabelText} Breakdown`}
            </div>
            {monthFilter !== 'all' ? <p className="dashboard-footnote">Expenses by category for {monthFilter === 'today' ? 'today' : 'this month'}</p> : null}
            <div className="dashboard-panel-body dashboard-donut-body">
              {scopeLoading ? (
                <p className="dashboard-footnote">Loading…</p>
              ) : donutSegments.length ? (
                <>
                  <Donut segments={donutSegments} centerLabel={rangeLabelText} centerValue={formatGBP(totalExpenses, { decimals: false })} />
                  <RankedBars rows={donutSegments} formatValue={(v) => formatGBP(v, { decimals: false })} />
                </>
              ) : (
                <p className="dashboard-footnote">No categorised expenses in this range yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="report-panel-block">
          <div className="report-panel-title">Top Categories — {rangeLabelText}</div>
          <div className="dashboard-panel-body">
            {topCategories.length ? (
              <RankedBars rows={topCategories} formatValue={(v) => formatGBP(v, { decimals: false })} />
            ) : (
              <p className="dashboard-footnote">No categorised expenses in this range yet.</p>
            )}
          </div>
        </div>

        <div className="report-panel-block">
          <div className="report-panel-title">Expense Records — {rangeLabelText}</div>
          <div className="dashboard-panel-body dashboard-recent-body">
            {scopeLoading ? (
              <p className="dashboard-footnote">Loading records…</p>
            ) : pagedRecords.length ? (
              <>
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
                    {pagedRecords.map((row, index) => (
                      <tr key={`${row.date}-${row.description}-${index}`}>
                        <td>{new Date(`${row.date}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                        <td>{row.description}</td>
                        <td>{row.category}</td>
                        <td>{formatGBP(parseAmount(row.amount), { decimals: false })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {recordsTotalPages > 1 ? (
                  <div className="dashboard-pagination">
                    <span>
                      Showing {(recordsPage - 1) * RECORDS_PAGE_SIZE + 1}–{Math.min(recordsPage * RECORDS_PAGE_SIZE, recent.length)} of {recent.length}
                    </span>
                    <div className="dashboard-pagination-controls">
                      <button type="button" disabled={recordsPage <= 1} onClick={() => setRecordsPage((p) => p - 1)}>
                        ‹
                      </button>
                      <span>
                        Page {recordsPage} of {recordsTotalPages}
                      </span>
                      <button type="button" disabled={recordsPage >= recordsTotalPages} onClick={() => setRecordsPage((p) => p + 1)}>
                        ›
                      </button>
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <p className="dashboard-footnote">No expenses logged for {rangeLabelText.toLowerCase()}.</p>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}

export default ExpenseDashboard
