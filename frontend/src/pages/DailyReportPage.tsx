import { useEffect, useMemo, useRef, useState } from 'react'
import SalesDashboard from './SalesDashboard'
import ExpenseDashboard from './ExpenseDashboard'
import ProfitTracker from './ProfitTracker'
import { fetchDailyReport, fetchDailyReportById, fetchMe, saveDailyReport, updateDailyReport } from '../api/reportsApi'
import type { DailyReportOut } from '../api/types'
import { isAcceptableNumberInput, parseAmount } from '../lib/validation'

type DailyReportPageProps = {
  userEmail?: string
  onSignOut: () => void
}

type ExpenseItem = {
  id: number
  description: string
  amount: string
}

// "Total Sales" and "Total Expenses" are computed, not typed in — they aren't
// part of this list, they're rendered as their own read-only row instead.
// Tips/Payout are recorded but deliberately excluded from Total Sales —
// they're cash-handling figures, not revenue (see dashboard_service.py).
const salesRowsBeforeTotal = [
  { key: 'openingCash', label: 'Opening Cash' },
  { key: 'cardSalesMachine', label: 'Card Sales (Machine)' },
  { key: 'cashSales', label: 'Cash Sales' },
  { key: 'uberEatsSales', label: 'Uber Eats Sales' },
  { key: 'justEatSales', label: 'Just Eat Sales' },
  { key: 'deliverooSales', label: 'Deliveroo Sales' },
  { key: 'otherSales', label: 'Other Sales' },
  { key: 'tipsOnCard', label: 'Tips on Card' },
  { key: 'payout', label: 'Payout' },
] as const

const salesRowsAfterTotal = [{ key: 'miscIncome', label: 'Misc Income' }] as const

// The channels that make up Total Sales — matches the real backend rule
// (calculation_rules "total_sales": SUM of exactly these). Opening Cash,
// Tips, Payout, and Misc Income are deliberately excluded, same as the
// seeded template.
const SALES_CHANNEL_KEYS = ['cardSalesMachine', 'cashSales', 'uberEatsSales', 'justEatSales', 'deliverooSales', 'otherSales'] as const

const sidebarItems = [
  'Daily Sales Report',
  'Sales Dashboard',
  'Expenses Dashboard',
  'Profit Track',
] as const

type SalesKey =
  | (typeof salesRowsBeforeTotal)[number]['key']
  | (typeof salesRowsAfterTotal)[number]['key']
  | (typeof SALES_CHANNEL_KEYS)[number]
type SidebarItem = (typeof sidebarItems)[number]

// Frontend field keys <-> the report_fields.key values the backend actually
// stores (see the seeded Dosa n Chutney template — Phase 3 of the backend work).
const FIELD_KEY_MAP: Record<SalesKey, string> = {
  openingCash: 'opening_cash',
  cardSalesMachine: 'card_sales_machine',
  cashSales: 'cash_sales',
  uberEatsSales: 'uber_eats',
  justEatSales: 'just_eat',
  deliverooSales: 'deliveroo',
  otherSales: 'other_sales',
  tipsOnCard: 'tips_on_card',
  payout: 'payout',
  miscIncome: 'misc_income',
}

const SUMMARY_FIELD_KEY_MAP = {
  nextDayOpenCash: 'next_day_open_cash',
  cashBalance: 'cash_balance',
} as const

const EMPTY_SALES: Record<SalesKey, string> = {
  openingCash: '',
  cardSalesMachine: '',
  cashSales: '',
  uberEatsSales: '',
  justEatSales: '',
  deliverooSales: '',
  otherSales: '',
  tipsOnCard: '',
  payout: '',
  miscIncome: '',
}

const EMPTY_SUMMARY = { nextDayOpenCash: '', cashBalance: '' }

const DEFAULT_EXPENSES: ExpenseItem[] = [
  { id: 1, description: '', amount: '' },
  { id: 2, description: '', amount: '' },
  { id: 3, description: '', amount: '' },
  { id: 4, description: '', amount: '' },
]

function formatAmount(value: number): string {
  return `£ ${value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function DailyReportPage({ userEmail, onSignOut }: DailyReportPageProps) {
  const [activeSection, setActiveSection] = useState<SidebarItem>('Daily Sales Report')
  const [reportDate, setReportDate] = useState(
    () => new Date().toLocaleDateString('en-CA')
  )
  const [sales, setSales] = useState<Record<SalesKey, string>>(EMPTY_SALES)
  const [expenses, setExpenses] = useState<ExpenseItem[]>(DEFAULT_EXPENSES)
  const [summary, setSummary] = useState(EMPTY_SUMMARY)

  const [organizationId, setOrganizationId] = useState<string | null>(null)
  const [orgError, setOrgError] = useState<string | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)

  // The saved report for the selected date, if any. Fetched for an EXISTENCE
  // CHECK ONLY — its values are never copied into the form automatically.
  const [existingReport, setExistingReport] = useState<DailyReportOut | null>(null)
  // True only after the user explicitly clicks "View / Edit Existing Report",
  // or after a successful save. Gates the overwrite warning.
  const [existingReportInForm, setExistingReportInForm] = useState(false)

  // Set when editing one specific past entry (via the Sales Dashboard's Edit
  // action) instead of adding a new one. Save then updates that report in
  // place rather than inserting a fresh row.
  const [editingReportId, setEditingReportId] = useState<string | null>(null)
  const [editLoadError, setEditLoadError] = useState<string | null>(null)
  // The date-change effect below normally blanks the form — set true right
  // before programmatically changing reportDate while loading an edit, so
  // that reset is skipped for that one run.
  const skipResetRef = useRef(false)

  const displayDate = useMemo(() => {
    const [year, month, day] = reportDate.split('-')
    return `${day}/${month}/${year}`
  }, [reportDate])

  const totalSales = useMemo(
    () => SALES_CHANNEL_KEYS.reduce((sum, key) => sum + parseAmount(sales[key]), 0),
    [sales],
  )

  const totalExpenses = useMemo(
    () => expenses.reduce((sum, expense) => sum + parseAmount(expense.amount), 0),
    [expenses],
  )

  // Resolve which organization this account belongs to, once, on mount.
  useEffect(() => {
    let cancelled = false
    fetchMe()
      .then((me) => {
        if (cancelled) return
        const org = me.organizations.find((o) => o.organization_slug === 'dosa-n-chutney') ?? me.organizations[0]
        if (org) {
          setOrganizationId(org.organization_id)
        } else {
          setOrgError('Your account isn’t attached to an organization yet — ask an admin to add you.')
        }
      })
      .catch((err) => {
        if (!cancelled) setOrgError(err instanceof Error ? err.message : 'Failed to load your account.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Check whether a report already exists for this date. This NEVER populates
  // the entry form — it only records the saved report so we can warn the user
  // and offer an explicit "View / Edit Existing Report" action. The form always
  // starts blank, and values from a previously selected date never leak in.
  useEffect(() => {
    if (!organizationId) return
    if (skipResetRef.current) {
      // This date change was triggered by startEditingReport, which already
      // populated the form — don't blank it back out.
      skipResetRef.current = false
      return
    }

    let cancelled = false

    // Fresh date => fresh blank form.
    setEditingReportId(null)
    setEditLoadError(null)
    setSales(EMPTY_SALES)
    setSummary(EMPTY_SUMMARY)
    setExpenses(DEFAULT_EXPENSES)
    setExistingReport(null)
    setExistingReportInForm(false)
    setLoadingReport(true)
    setLoadError(null)
    setSavedMessage(null)

    fetchDailyReport(organizationId, reportDate)
      .then((report) => {
        if (cancelled) return
        setExistingReport(report ?? null)
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Failed to check this date.')
      })
      .finally(() => {
        if (!cancelled) setLoadingReport(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId, reportDate])

  // Explicit, user-initiated: copy the saved report's values into the form.
  // This is the ONLY place saved data enters the entry form.
  function loadExistingReportIntoForm() {
    if (!existingReport) return

    const nextSales = { ...EMPTY_SALES }
    for (const key of Object.keys(FIELD_KEY_MAP) as SalesKey[]) {
      nextSales[key] = existingReport.values[FIELD_KEY_MAP[key]] ?? ''
    }
    setSales(nextSales)
    setSummary({
      nextDayOpenCash: existingReport.values[SUMMARY_FIELD_KEY_MAP.nextDayOpenCash] ?? '',
      cashBalance: existingReport.values[SUMMARY_FIELD_KEY_MAP.cashBalance] ?? '',
    })
    setExpenses(
      existingReport.expenses.length > 0
        ? existingReport.expenses.map((expense, index) => ({
            id: index + 1,
            description: expense.description,
            amount: expense.amount,
          }))
        : DEFAULT_EXPENSES,
    )
    setExistingReportInForm(true)
    setSavedMessage(null)
  }

  // Loads one specific saved report into the form for in-place editing —
  // reached from the Sales Dashboard's records table Edit action.
  async function startEditingReport(reportId: string) {
    if (!organizationId) return
    setActiveSection('Daily Sales Report')
    setEditLoadError(null)
    setLoadingReport(true)
    try {
      const report = await fetchDailyReportById(organizationId, reportId)
      skipResetRef.current = true
      setReportDate(report.report_date)
      setEditingReportId(report.id)

      const nextSales = { ...EMPTY_SALES }
      for (const key of Object.keys(FIELD_KEY_MAP) as SalesKey[]) {
        nextSales[key] = report.values[FIELD_KEY_MAP[key]] ?? ''
      }
      setSales(nextSales)
      setSummary({
        nextDayOpenCash: report.values[SUMMARY_FIELD_KEY_MAP.nextDayOpenCash] ?? '',
        cashBalance: report.values[SUMMARY_FIELD_KEY_MAP.cashBalance] ?? '',
      })
      setExpenses(
        report.expenses.length > 0
          ? report.expenses.map((expense, index) => ({ id: index + 1, description: expense.description, amount: expense.amount }))
          : DEFAULT_EXPENSES,
      )
      setExistingReport(report)
      setExistingReportInForm(true)
      setSavedMessage(null)
    } catch (err) {
      setEditLoadError(err instanceof Error ? err.message : 'Failed to load that entry for editing.')
    } finally {
      setLoadingReport(false)
    }
  }

  function cancelEditing() {
    setEditingReportId(null)
    setEditLoadError(null)
    setSales(EMPTY_SALES)
    setSummary(EMPTY_SUMMARY)
    setExpenses(DEFAULT_EXPENSES)
    setExistingReport(null)
    setExistingReportInForm(false)
    setSavedMessage(null)
  }

  function updateSales(key: SalesKey, value: string) {
    // Reject any keystroke that would put a non-numeric character in the box.
    if (!isAcceptableNumberInput(value)) return
    setSales((current) => ({ ...current, [key]: value }))
  }

  function updateExpense(id: number, field: 'description' | 'amount', value: string) {
    // The amount column is numeric-only; the description column is free text.
    if (field === 'amount' && !isAcceptableNumberInput(value)) return
    setExpenses((current) =>
      current.map((item) => (item.id === id ? { ...item, [field]: value } : item)),
    )
  }

  function updateSummary(key: keyof typeof EMPTY_SUMMARY, value: string) {
    if (!isAcceptableNumberInput(value)) return
    setSummary((current) => ({ ...current, [key]: value }))
  }

  function addExpenseRow() {
    setExpenses((current) => [...current, { id: Date.now(), description: '', amount: '' }])
  }

  async function handleSave() {
    if (!organizationId) return

    setSaving(true)
    setSaveError(null)
    setSavedMessage(null)

    try {
      const values: Record<string, string> = {}
      for (const key of Object.keys(FIELD_KEY_MAP) as SalesKey[]) {
        values[FIELD_KEY_MAP[key]] = sales[key]
      }
      values[SUMMARY_FIELD_KEY_MAP.nextDayOpenCash] = summary.nextDayOpenCash
      values[SUMMARY_FIELD_KEY_MAP.cashBalance] = summary.cashBalance

      const payload = {
        values,
        expenses: expenses
          .filter((expense) => expense.description.trim() && parseAmount(expense.amount) !== 0)
          .map((expense) => ({ description: expense.description, amount: expense.amount })),
      }

      const saved = editingReportId
        ? await updateDailyReport(organizationId, editingReportId, payload)
        : await saveDailyReport(organizationId, reportDate, payload)

      setExistingReport(saved)
      setExistingReportInForm(true)
      setSavedMessage(
        editingReportId
          ? `Entry for ${displayDate} updated.`
          : `Entry for ${displayDate} saved. It adds to that day's totals on the dashboards.`,
      )
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="report-shell">
      <div className="report-backdrop" />
      <div className="report-app-layout">
        <aside className="report-sidebar">
          <div className="report-sidebar-brand">
            <img className="report-sidebar-mark" src="/logo-mark.png" alt="MAARA" />
            <div>
              <p className="report-sidebar-name">MAARA AI</p>
              <p className="report-sidebar-subtitle">Business Manager</p>
            </div>
          </div>

          <nav className="report-sidebar-nav">
            {sidebarItems.map((item) => (
              <button
                key={item}
                type="button"
                className={`report-sidebar-link ${activeSection === item ? 'is-active' : ''}`}
                onClick={() => setActiveSection(item)}
              >
                <span>{item}</span>
              </button>
            ))}
          </nav>
        </aside>

        <div className="report-page">
          <header className="report-topbar">
            <div className="report-brand">
              <img className="report-brand-mark" src="/logo-mark.png" alt="MAARA" />
              <div>
                <p className="report-brand-name">MAARA</p>
                <p className="report-brand-subtitle">Dosa n Chutney Operations</p>
              </div>
            </div>

            <div className="report-topbar-actions">
              {userEmail ? <p className="report-user">{userEmail}</p> : null}
              <button type="button" className="report-signout" onClick={onSignOut}>
                Sign out
              </button>
            </div>
          </header>

          {activeSection === 'Daily Sales Report' ? (
            <main className="report-card report-card-dashboard">
              <div className="report-card-header report-card-header-compact">
                <div>
                  <p className="report-kicker">Daily Operations Ledger</p>
                  <h1>Dosa n Chutney</h1>
                  <p className="report-subheading">
                    {loadingReport ? 'Loading…' : 'Daily Sales & Expenses Report'}
                  </p>
                </div>

                <label className="report-date">
                  <span>Date</span>
                  <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} />
                </label>
              </div>

              {orgError ? <p className="feedback error">{orgError}</p> : null}
              {loadError ? <p className="feedback error">{loadError}</p> : null}
              {editLoadError ? <p className="feedback error">{editLoadError}</p> : null}

              {editingReportId ? (
                <div className="report-existing-banner" role="status">
                  <span>Editing the entry saved for {displayDate}. Saving updates it in place.</span>
                  <button type="button" className="report-existing-banner-btn" onClick={cancelEditing}>
                    Cancel — start a new entry instead
                  </button>
                </div>
              ) : null}

              {existingReport && !existingReportInForm ? (
                <div className="report-existing-banner" role="status">
                  <span>
                    An entry was already saved for this date. Saving again adds a new
                    entry — it won&rsquo;t overwrite. Dashboards add every entry together.
                  </span>
                  <button
                    type="button"
                    className="report-existing-banner-btn"
                    onClick={loadExistingReportIntoForm}
                  >
                    Load last entry
                  </button>
                </div>
              ) : null}

              <section className="report-two-column">
                <div className="report-panel-block report-panel-income">
                  <div className="report-panel-title">Income / Sales</div>
                  <div className="report-mini-table">
                    <div className="report-mini-head">Description</div>
                    <div className="report-mini-head">Amount</div>

                    {salesRowsBeforeTotal.map((row) => (
                      <div key={row.key} className="report-mini-row">
                        <div className="report-mini-label">{row.label}</div>
                        <input
                          className="report-mini-input"
                          type="text"
                          inputMode="decimal"
                          placeholder="£ 0.00"
                          value={sales[row.key]}
                          onChange={(event) => updateSales(row.key, event.target.value)}
                        />
                      </div>
                    ))}

                    <div className="report-mini-row is-strong">
                      <div className="report-mini-label">Total Sales</div>
                      <div className="report-mini-input report-mini-computed">{formatAmount(totalSales)}</div>
                    </div>

                    {salesRowsAfterTotal.map((row) => (
                      <div key={row.key} className="report-mini-row">
                        <div className="report-mini-label">{row.label}</div>
                        <input
                          className="report-mini-input"
                          type="text"
                          inputMode="decimal"
                          placeholder="£ 0.00"
                          value={sales[row.key]}
                          onChange={(event) => updateSales(row.key, event.target.value)}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="report-panel-block report-panel-expense">
                  <div className="report-panel-title">Expenses</div>
                  <div className="report-mini-table">
                    <div className="report-mini-head">Description</div>
                    <div className="report-mini-head">Amount</div>

                    {expenses.map((expense, index) => (
                      <div key={expense.id} className="report-mini-row">
                        <input
                          className="report-mini-input"
                          type="text"
                          placeholder={`Expense ${index + 1}`}
                          value={expense.description}
                          onChange={(event) => updateExpense(expense.id, 'description', event.target.value)}
                        />
                        <input
                          className="report-mini-input"
                          type="text"
                          inputMode="decimal"
                          placeholder="£ 0.00"
                          value={expense.amount}
                          onChange={(event) => updateExpense(expense.id, 'amount', event.target.value)}
                        />
                      </div>
                    ))}

                    <button type="button" className="report-add-expense" onClick={addExpenseRow}>
                      + Add Expense
                    </button>

                    <div className="report-mini-row is-strong">
                      <div className="report-mini-label">Total Expenses</div>
                      <div className="report-mini-input report-mini-computed">{formatAmount(totalExpenses)}</div>
                    </div>

                    <div className="report-mini-row is-strong">
                      <div className="report-mini-label">Next-Day Open Cash</div>
                      <input
                        className="report-mini-input"
                        type="text"
                        inputMode="decimal"
                        placeholder="£ 0.00"
                        value={summary.nextDayOpenCash}
                        onChange={(event) => updateSummary('nextDayOpenCash', event.target.value)}
                      />
                    </div>

                    <div className="report-mini-row is-strong">
                      <div className="report-mini-label">Cash Balance</div>
                      <input
                        className="report-mini-input"
                        type="text"
                        inputMode="decimal"
                        placeholder="£ 0.00"
                        value={summary.cashBalance}
                        onChange={(event) => updateSummary('cashBalance', event.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </section>

              <section className="report-footer-grid">
                <div className="report-actions report-actions-compact">
                  <button type="button" className="report-save" onClick={handleSave} disabled={saving || !organizationId}>
                    {saving ? 'Saving…' : editingReportId ? 'Update Entry' : 'Save Daily Report'}
                  </button>
                  {savedMessage ? <p className="report-saved-message">{savedMessage}</p> : null}
                  {saveError ? <p className="feedback error">{saveError}</p> : null}
                </div>
              </section>
            </main>
          ) : null}

          {activeSection === 'Sales Dashboard' ? (
            <SalesDashboard organizationId={organizationId} onEditReport={startEditingReport} />
          ) : null}

          {activeSection === 'Expenses Dashboard' ? <ExpenseDashboard organizationId={organizationId} /> : null}

          {activeSection === 'Profit Track' ? (
            <ProfitTracker organizationId={organizationId} defaultDate={reportDate} />
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default DailyReportPage
