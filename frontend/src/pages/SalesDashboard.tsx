import { useEffect, useMemo, useState } from 'react'
import { BarTrend, MultiLineTrend, RankedBars } from '../components/charts/Charts'
import { deleteDailyReport, fetchDailyReports, fetchSalesDaily, fetchSalesMonthSummary, fetchSalesMonthly } from '../api/reportsApi'
import type { DailyReportOut, DailySalesRow, MonthlySalesRow, SalesMonthSummary } from '../api/types'
import {
  channelTotal,
  formatGBP,
  monthLabel,
  parseAmount,
  salesChannelMeta,
  shortDateLabel,
  weekdayLabel,
  type SalesChannels,
} from '../data/reportData'
import { downloadCsv } from '../lib/csvExport'
import { MONTH_NAMES, monthRangeISO, todayISO, type MonthFilter } from '../lib/dashboardRange'

type SalesDashboardProps = {
  organizationId: string | null
  onEditReport: (reportId: string) => void
}

const WEEKDAY_ORDER = [1, 2, 3, 4, 5, 6, 0] // Monday-first
const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const RECORDS_PAGE_SIZE = 15
// Wide enough to cover a full calendar year of daily entries for the month
// filter and weekday/trend charts, without paging.
const DAILY_FETCH_DAYS = 400

function toChannels(row: {
  cardSalesMachine: string
  cashSales: string
  uberEatsSales: string
  justEatSales: string
  deliverooSales: string
  otherSales: string
  miscIncome: string
  tips: string
  payout: string
}): SalesChannels {
  return {
    cardSalesMachine: parseAmount(row.cardSalesMachine),
    cashSales: parseAmount(row.cashSales),
    uberEatsSales: parseAmount(row.uberEatsSales),
    justEatSales: parseAmount(row.justEatSales),
    deliverooSales: parseAmount(row.deliverooSales),
    otherSales: parseAmount(row.otherSales),
    miscIncome: parseAmount(row.miscIncome),
    tips: parseAmount(row.tips),
    payout: parseAmount(row.payout),
  }
}

const sumBy = (rows: DailySalesRow[], pick: (c: SalesChannels) => number) =>
  rows.reduce((total, row) => total + pick(toChannels(row)), 0)

function weekdayAverages(rows: DailySalesRow[]): { label: string; value: number }[] {
  const sums = new Array(7).fill(0)
  const counts = new Array(7).fill(0)
  for (const row of rows) {
    const day = new Date(`${row.date}T00:00:00`).getDay()
    sums[day] += channelTotal(toChannels(row))
    counts[day] += 1
  }
  return WEEKDAY_ORDER.map((day, i) => ({
    label: WEEKDAY_LABELS[i],
    value: counts[day] ? sums[day] / counts[day] : 0,
  }))
}

function reportValue(report: DailyReportOut, key: string): number {
  return parseAmount(report.values[key])
}

function SalesDashboard({ organizationId, onEditReport }: SalesDashboardProps) {
  const year = new Date().getFullYear()

  const [monthFilter, setMonthFilter] = useState<MonthFilter>('all')

  const [dailyRows, setDailyRows] = useState<DailySalesRow[]>([])
  const [dailyLoading, setDailyLoading] = useState(true)
  const [dailyError, setDailyError] = useState<string | null>(null)

  const [monthlyRows, setMonthlyRows] = useState<MonthlySalesRow[]>([])

  const [records, setRecords] = useState<DailyReportOut[]>([])
  const [recordsTotal, setRecordsTotal] = useState(0)
  const [recordsPage, setRecordsPage] = useState(1)
  const [recordsLoading, setRecordsLoading] = useState(true)
  const [recordsError, setRecordsError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // The four headline KPIs for a single selected month come straight from
  // the backend (GET .../sales/monthly-summary) — it averages by calendar
  // days in the month, not by how many days happen to have a saved entry,
  // so a sparsely-filled month doesn't look artificially high-average.
  const [monthSummary, setMonthSummary] = useState<SalesMonthSummary | null>(null)
  const [monthSummaryLoading, setMonthSummaryLoading] = useState(false)

  const [reloadTick, setReloadTick] = useState(0)

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setDailyLoading(true)
    setDailyError(null)

    Promise.all([fetchSalesDaily(organizationId, DAILY_FETCH_DAYS), fetchSalesMonthly(organizationId, 12)])
      .then(([daily, monthly]) => {
        if (cancelled) return
        setDailyRows(daily)
        setMonthlyRows(monthly)
      })
      .catch((err) => {
        if (!cancelled) setDailyError(err instanceof Error ? err.message : 'Failed to load sales data.')
      })
      .finally(() => {
        if (!cancelled) setDailyLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId, reloadTick])

  useEffect(() => {
    setRecordsPage(1)
  }, [monthFilter])

  useEffect(() => {
    if (!organizationId || typeof monthFilter !== 'number') {
      setMonthSummary(null)
      return
    }
    let cancelled = false
    setMonthSummaryLoading(true)

    fetchSalesMonthSummary(organizationId, year, monthFilter + 1)
      .then((summary) => {
        if (!cancelled) setMonthSummary(summary)
      })
      .catch(() => {
        if (!cancelled) setMonthSummary(null)
      })
      .finally(() => {
        if (!cancelled) setMonthSummaryLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId, monthFilter, year, reloadTick])

  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setRecordsLoading(true)
    setRecordsError(null)

    const { since, until } =
      monthFilter === 'all' ? {} : monthFilter === 'today' ? { since: todayISO(), until: todayISO() } : monthRangeISO(year, monthFilter)

    fetchDailyReports(organizationId, { since, until, page: recordsPage, pageSize: RECORDS_PAGE_SIZE })
      .then((result) => {
        if (cancelled) return
        setRecords(result.items)
        setRecordsTotal(result.total)
      })
      .catch((err) => {
        if (!cancelled) setRecordsError(err instanceof Error ? err.message : 'Failed to load records.')
      })
      .finally(() => {
        if (!cancelled) setRecordsLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, monthFilter, recordsPage, reloadTick])

  const filtered = useMemo(() => {
    if (monthFilter === 'all') return dailyRows
    if (monthFilter === 'today') return dailyRows.filter((row) => row.date === todayISO())
    return dailyRows.filter((row) => new Date(`${row.date}T00:00:00`).getMonth() === monthFilter)
  }, [dailyRows, monthFilter])
  const sorted = useMemo(() => [...filtered].sort((a, b) => (a.date < b.date ? -1 : 1)), [filtered])

  // KPI cards for a single selected month use the backend's monthly-summary
  // figures (correct calendar-day average, month scoped strictly by date) —
  // client-side sums below are the fallback for "All Months", where there's
  // no single calendar-day count to average against.
  const clientTotalSales = sumBy(filtered, channelTotal)
  const clientTipsTotal = sumBy(filtered, (c) => c.tips)
  const clientAvgDaily = filtered.length ? clientTotalSales / filtered.length : 0
  const clientBestDay = sorted.reduce<{ date: string; total: number } | null>((best, row) => {
    const total = channelTotal(toChannels(row))
    return !best || total > best.total ? { date: row.date, total } : best
  }, null)

  const usingMonthSummary = typeof monthFilter === 'number' && monthSummary !== null
  const totalSales = usingMonthSummary ? parseAmount(monthSummary.totalSales) : clientTotalSales
  const tipsTotal = usingMonthSummary ? parseAmount(monthSummary.cardTips) : clientTipsTotal
  const avgDaily = usingMonthSummary ? parseAmount(monthSummary.avgDailySales) : clientAvgDaily
  const bestDay = usingMonthSummary
    ? monthSummary.bestDay
      ? { date: monthSummary.bestDay.date, total: parseAmount(monthSummary.bestDay.sales), weekday: monthSummary.bestDay.weekday }
      : null
    : clientBestDay

  const channelRows = salesChannelMeta.map((meta) => ({
    label: meta.label,
    value: sumBy(filtered, (c) => c[meta.key]),
    color: meta.color,
  }))

  const trendSeries = [{ key: 'value', label: 'Daily Sales', color: 'var(--brand-violet)' }]
  const trendData = sorted.map((day) => ({
    label: shortDateLabel(day.date),
    values: { value: channelTotal(toChannels(day)) },
  }))

  const monthlyData = monthlyRows.map((row) => ({ label: monthLabel(row.month), value: channelTotal(toChannels(row)) }))
  const weekdayData = weekdayAverages(filtered)

  const recordsTotalPages = Math.max(1, Math.ceil(recordsTotal / RECORDS_PAGE_SIZE))
  const rangeLabel = monthFilter === 'all' ? 'All Months' : monthFilter === 'today' ? 'Today' : `${MONTH_NAMES[monthFilter]} ${year}`

  async function handleDelete(report: DailyReportOut) {
    if (!organizationId) return
    if (!window.confirm(`Delete the entry for ${report.report_date}? This can't be undone.`)) return
    setDeletingId(report.id)
    try {
      await deleteDailyReport(organizationId, report.id)
      setReloadTick((t) => t + 1)
    } catch (err) {
      setRecordsError(err instanceof Error ? err.message : 'Failed to delete that entry.')
    } finally {
      setDeletingId(null)
    }
  }

  async function handleExportCsv() {
    if (!organizationId) return
    const { since, until } =
      monthFilter === 'all' ? {} : monthFilter === 'today' ? { since: todayISO(), until: todayISO() } : monthRangeISO(year, monthFilter)
    const result = await fetchDailyReports(organizationId, { since, until, page: 1, pageSize: 1000 })
    const headers = ['Date', 'Day', 'Card (Machine)', 'Cash', 'Uber Eats', 'Just Eats', 'Deliveroo', 'Other Sales', 'Total Sales', 'Payout', 'Tips']
    const rows = result.items.map((report) => [
      report.report_date,
      weekdayLabel(report.report_date),
      reportValue(report, 'card_sales_machine'),
      reportValue(report, 'cash_sales'),
      reportValue(report, 'uber_eats'),
      reportValue(report, 'just_eat'),
      reportValue(report, 'deliveroo'),
      reportValue(report, 'other_sales'),
      reportValue(report, 'total_sales'),
      reportValue(report, 'payout'),
      reportValue(report, 'tips_on_card'),
    ])
    const fileScope = monthFilter === 'all' ? 'all-months' : monthFilter === 'today' ? `today-${todayISO()}` : MONTH_NAMES[monthFilter].toLowerCase()
    downloadCsv(`sales-${fileScope}-${year}.csv`, headers, rows)
  }

  const kpis = [
    { label: 'Total Sales', value: formatGBP(totalSales), hint: rangeLabel },
    { label: 'Avg / Day', value: formatGBP(avgDaily), hint: `${filtered.length} day${filtered.length === 1 ? '' : 's'} with entries` },
    {
      label: 'Best Day',
      value: bestDay ? formatGBP(bestDay.total) : '—',
      hint: bestDay
        ? 'weekday' in bestDay
          ? `${bestDay.weekday}, ${shortDateLabel(bestDay.date)}`
          : shortDateLabel(bestDay.date)
        : 'No entries yet',
    },
    { label: 'Tips', value: formatGBP(tipsTotal), hint: rangeLabel },
  ]

  const header = (
    <div className="report-card-header">
      <div>
        <p className="report-kicker">Sales Dashboard</p>
        <h1>Dosa n Chutney</h1>
        <p className="report-subheading">Where the money is coming from, and how sales are moving</p>
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
        <select
          className="dashboard-month-select"
          value={typeof monthFilter === 'number' ? monthFilter : 'all'}
          onChange={(event) => setMonthFilter(event.target.value === 'all' ? 'all' : Number(event.target.value))}
          aria-label="Filter by month"
        >
          <option value="all">All Months</option>
          {MONTH_NAMES.map((name, index) => (
            <option key={name} value={index}>
              {name}
            </option>
          ))}
        </select>
        <button type="button" className="dashboard-export-btn" onClick={handleExportCsv}>
          Export CSV
        </button>
      </div>
    </div>
  )

  if (!organizationId || dailyLoading) {
    return (
      <main className="report-card report-card-simple">
        {header}
        <p className="report-subheading">Loading…</p>
      </main>
    )
  }

  if (dailyRows.length === 0) {
    return (
      <main className="report-card report-card-simple">
        {header}
        <p className="report-subheading">
          No sales data yet — fill in and save a Daily Sales Report to see it here.
        </p>
      </main>
    )
  }

  return (
    <main className="report-card report-card-simple">
      {header}

      {dailyError ? <p className="feedback error">{dailyError}</p> : null}

      <section className="dashboard-scroll">
        <div className="report-dashboard-strip">
          {kpis.map((card) => (
            <div key={card.label} className="report-dashboard-card">
              <p>{card.label}</p>
              <strong className={monthSummaryLoading && monthFilter !== 'all' ? 'is-refreshing' : ''}>{card.value}</strong>
              <span className="dashboard-card-hint">{card.hint}</span>
            </div>
          ))}
        </div>

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Daily Sales Trend — {rangeLabel}</div>
            <div className="dashboard-panel-body">
              {trendData.length ? (
                <MultiLineTrend data={trendData} series={trendSeries} formatValue={(v) => formatGBP(v, { decimals: false })} />
              ) : (
                <p className="dashboard-footnote">No daily entries in this range yet.</p>
              )}
            </div>
          </div>

          <div className="report-panel-block report-panel-income">
            <div className="report-panel-title">Sales by Channel — {rangeLabel}</div>
            <div className="dashboard-panel-body">
              {totalSales > 0 ? (
                <RankedBars rows={channelRows} formatValue={(v) => formatGBP(v, { decimals: false })} />
              ) : (
                <p className="dashboard-footnote">No channel data in this range yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Monthly Sales Comparison</div>
            <div className="dashboard-panel-body">
              {monthlyData.length ? (
                <BarTrend data={monthlyData} color="var(--accent-income)" formatValue={(v) => formatGBP(v, { decimals: false })} />
              ) : (
                <p className="dashboard-footnote">Not enough history yet.</p>
              )}
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Avg Sales by Day of Week — {rangeLabel}</div>
            <div className="dashboard-panel-body">
              <BarTrend data={weekdayData} color="var(--brand-violet)" formatValue={(v) => formatGBP(v, { decimals: false })} />
            </div>
          </div>
        </div>

        <div className="report-panel-block">
          <div className="report-panel-title">Daily Sales Records — {rangeLabel}</div>
          <div className="dashboard-panel-body dashboard-recent-body">
            {recordsError ? <p className="feedback error">{recordsError}</p> : null}
            {recordsLoading ? (
              <p className="dashboard-footnote">Loading records…</p>
            ) : records.length ? (
              <>
                <table className="dashboard-recent-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Day</th>
                      <th>Card (Mach)</th>
                      <th>Cash</th>
                      <th>Uber</th>
                      <th>Just Eats</th>
                      <th>Deliveroo</th>
                      <th>Other</th>
                      <th>Total</th>
                      <th>Payout</th>
                      <th>Tips</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((report) => (
                      <tr key={report.id}>
                        <td>{shortDateLabel(report.report_date)}</td>
                        <td>{weekdayLabel(report.report_date)}</td>
                        <td>{formatGBP(reportValue(report, 'card_sales_machine'), { decimals: false })}</td>
                        <td>{formatGBP(reportValue(report, 'cash_sales'), { decimals: false })}</td>
                        <td>{formatGBP(reportValue(report, 'uber_eats'), { decimals: false })}</td>
                        <td>{formatGBP(reportValue(report, 'just_eat'), { decimals: false })}</td>
                        <td>{formatGBP(reportValue(report, 'deliveroo'), { decimals: false })}</td>
                        <td>{formatGBP(reportValue(report, 'other_sales'), { decimals: false })}</td>
                        <td>
                          <strong>{formatGBP(reportValue(report, 'total_sales'), { decimals: false })}</strong>
                        </td>
                        <td>{formatGBP(reportValue(report, 'payout'), { decimals: false })}</td>
                        <td>{formatGBP(reportValue(report, 'tips_on_card'), { decimals: false })}</td>
                        <td>
                          <div className="dashboard-row-actions">
                            <button
                              type="button"
                              className="dashboard-row-action-btn"
                              aria-label={`Edit entry for ${report.report_date}`}
                              onClick={() => onEditReport(report.id)}
                            >
                              ✎
                            </button>
                            <button
                              type="button"
                              className="dashboard-row-action-btn is-danger"
                              aria-label={`Delete entry for ${report.report_date}`}
                              disabled={deletingId === report.id}
                              onClick={() => handleDelete(report)}
                            >
                              🗑
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="dashboard-pagination">
                  <span>
                    Showing {(recordsPage - 1) * RECORDS_PAGE_SIZE + 1}–{Math.min(recordsPage * RECORDS_PAGE_SIZE, recordsTotal)} of {recordsTotal}
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
              </>
            ) : (
              <p className="dashboard-footnote">No records for {rangeLabel.toLowerCase()} yet.</p>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}

export default SalesDashboard
