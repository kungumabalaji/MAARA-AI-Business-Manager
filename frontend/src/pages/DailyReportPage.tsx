import { useEffect, useMemo, useState } from 'react'
import SalesDashboard from './SalesDashboard'
import ExpenseDashboard from './ExpenseDashboard'
import ProfitTracker from './ProfitTracker'
import { fetchDailyReport, fetchMe, saveDailyReport } from '../api/reportsApi'

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
const salesRowsBeforeTotal = [
  { key: 'openingCash', label: 'Opening Cash' },
  { key: 'cardSales', label: 'Card Sales' },
  { key: 'cashSales', label: 'Cash Sales' },
  { key: 'uberEatsSales', label: 'Uber Eats Sales' },
  { key: 'justEatSales', label: 'Just Eat Sales' },
  { key: 'deliverooSales', label: 'Deliveroo Sales' },
  { key: 'otherSales', label: 'Other Sales' },
] as const

const salesRowsAfterTotal = [{ key: 'miscIncome', label: 'Misc Income' }] as const

// The channels that make up Total Sales — matches the real backend rule
// (calculation_rules "total_sales": SUM of exactly these). Opening Cash and
// Misc Income are deliberately excluded, same as the seeded template.
const SALES_CHANNEL_KEYS = ['cardSales', 'cashSales', 'uberEatsSales', 'justEatSales', 'deliverooSales', 'otherSales'] as const

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
  cardSales: 'card_sales',
  cashSales: 'cash_sales',
  uberEatsSales: 'uber_eats',
  justEatSales: 'just_eat',
  deliverooSales: 'deliveroo',
  otherSales: 'other_sales',
  miscIncome: 'misc_income',
}

const SUMMARY_FIELD_KEY_MAP = {
  nextDayOpenCash: 'next_day_open_cash',
  cashBalance: 'cash_balance',
} as const

const EMPTY_SALES: Record<SalesKey, string> = {
  openingCash: '',
  cardSales: '',
  cashSales: '',
  uberEatsSales: '',
  justEatSales: '',
  deliverooSales: '',
  otherSales: '',
  miscIncome: '',
}

const EMPTY_SUMMARY = { nextDayOpenCash: '', cashBalance: '' }

const DEFAULT_EXPENSES: ExpenseItem[] = [
  { id: 1, description: '', amount: '' },
  { id: 2, description: '', amount: '' },
  { id: 3, description: '', amount: '' },
  { id: 4, description: '', amount: '' },
]

function parseAmount(value: string): number {
  const cleaned = value.replace(/[^0-9.-]/g, '')
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? parsed : 0
}

function formatAmount(value: number): string {
  return `£ ${value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function DailyReportPage({ userEmail, onSignOut }: DailyReportPageProps) {
  const [activeSection, setActiveSection] = useState<SidebarItem>('Daily Sales Report')
  const [reportDate, setReportDate] = useState('2026-08-07')
  const [preparedBy, setPreparedBy] = useState('')
  const [checkedBy, setCheckedBy] = useState('')
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

  // Load whatever was already saved for this date, every time the date (or
  // the resolved organization) changes.
  useEffect(() => {
    if (!organizationId) return
    let cancelled = false
    setLoadingReport(true)
    setLoadError(null)
    setSavedMessage(null)

    fetchDailyReport(organizationId, reportDate)
      .then((report) => {
        if (cancelled) return
        if (report) {
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
              ? report.expenses.map((expense, index) => ({
                  id: index + 1,
                  description: expense.description,
                  amount: expense.amount,
                }))
              : DEFAULT_EXPENSES,
          )
        } else {
          setSales(EMPTY_SALES)
          setSummary(EMPTY_SUMMARY)
          setExpenses(DEFAULT_EXPENSES)
        }
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Failed to load this report.')
      })
      .finally(() => {
        if (!cancelled) setLoadingReport(false)
      })

    return () => {
      cancelled = true
    }
  }, [organizationId, reportDate])

  function updateSales(key: SalesKey, value: string) {
    setSales((current) => ({ ...current, [key]: value }))
  }

  function updateExpense(id: number, field: 'description' | 'amount', value: string) {
    setExpenses((current) =>
      current.map((item) => (item.id === id ? { ...item, [field]: value } : item)),
    )
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

      await saveDailyReport(organizationId, reportDate, {
        values,
        expenses: expenses
          .filter((expense) => expense.description.trim() && parseAmount(expense.amount) !== 0)
          .map((expense) => ({ description: expense.description, amount: expense.amount })),
      })

      setSavedMessage(`Daily report for ${displayDate} saved successfully.`)
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
                        onChange={(event) => setSummary((current) => ({ ...current, nextDayOpenCash: event.target.value }))}
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
                        onChange={(event) => setSummary((current) => ({ ...current, cashBalance: event.target.value }))}
                      />
                    </div>
                  </div>
                </div>
              </section>

              <section className="report-footer-grid">
                <label className="report-signoff-field">
                  <span>Prepared By</span>
                  <select value={preparedBy} onChange={(event) => setPreparedBy(event.target.value)}>
                    <option value="">Select staff</option>
                    <option value="Asha">Asha</option>
                    <option value="Kumar">Kumar</option>
                    <option value="Meena">Meena</option>
                  </select>
                </label>

                <label className="report-signoff-field">
                  <span>Checked By</span>
                  <select value={checkedBy} onChange={(event) => setCheckedBy(event.target.value)}>
                    <option value="">Select manager</option>
                    <option value="Manager Arun">Manager Arun</option>
                    <option value="Manager Devi">Manager Devi</option>
                    <option value="Manager Priya">Manager Priya</option>
                  </select>
                </label>

                <div className="report-actions report-actions-compact">
                  <button type="button" className="report-save" onClick={handleSave} disabled={saving || !organizationId}>
                    {saving ? 'Saving…' : 'Save Daily Report'}
                  </button>
                  {savedMessage ? <p className="report-saved-message">{savedMessage}</p> : null}
                  {saveError ? <p className="feedback error">{saveError}</p> : null}
                </div>
              </section>
            </main>
          ) : null}

          {activeSection === 'Sales Dashboard' ? <SalesDashboard organizationId={organizationId} /> : null}

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
