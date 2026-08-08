import { useMemo, useState } from 'react'
import SalesDashboard from './SalesDashboard'
import ExpenseDashboard from './ExpenseDashboard'
import ProfitTracker from './ProfitTracker'
import { initialExpenseMatrix } from '../data/reportData'

type DailyReportPageProps = {
  userEmail?: string
  onSignOut: () => void
}

type ExpenseItem = {
  id: number
  description: string
  amount: string
}

const salesRows = [
  { key: 'openingCash', label: 'Opening Cash' },
  { key: 'cardSales', label: 'Card Sales' },
  { key: 'cashSales', label: 'Cash Sales' },
  { key: 'uberEatsSales', label: 'Uber Eats Sales' },
  { key: 'justEatSales', label: 'Just Eat Sales' },
  { key: 'deliverooSales', label: 'Deliveroo Sales' },
  { key: 'otherSales', label: 'Other Sales' },
  { key: 'totalSales', label: 'Total Sales', strong: true },
  { key: 'miscIncome', label: 'Misc Income' },
] as const

const sidebarItems = [
  'Daily Sales Report',
  'Sales Dashboard',
  'Expenses Dashboard',
  'Profit Track',
] as const

type SalesKey = (typeof salesRows)[number]['key']
type SidebarItem = (typeof sidebarItems)[number]

function DailyReportPage({ userEmail, onSignOut }: DailyReportPageProps) {
  const [activeSection, setActiveSection] = useState<SidebarItem>('Daily Sales Report')
  const [reportDate, setReportDate] = useState('2026-08-07')
  const [preparedBy, setPreparedBy] = useState('')
  const [checkedBy, setCheckedBy] = useState('')
  const [sales, setSales] = useState<Record<SalesKey, string>>({
    openingCash: '',
    cardSales: '',
    cashSales: '',
    uberEatsSales: '',
    justEatSales: '',
    deliverooSales: '',
    otherSales: '',
    totalSales: '',
    miscIncome: '',
  })
  const [expenses, setExpenses] = useState<ExpenseItem[]>([
    { id: 1, description: '', amount: '' },
    { id: 2, description: '', amount: '' },
    { id: 3, description: '', amount: '' },
    { id: 4, description: '', amount: '' },
  ])
  const [summary, setSummary] = useState({
    totalExpenses: '',
    nextDayOpenCash: '',
    cashBalance: '',
  })
  const [savedMessage, setSavedMessage] = useState<string | null>(null)
  const [expenseMatrix, setExpenseMatrix] = useState(initialExpenseMatrix)

  const displayDate = useMemo(() => {
    const [year, month, day] = reportDate.split('-')
    return `${day}/${month}/${year}`
  }, [reportDate])

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

  function updateExpenseMatrix(category: string, month: string, value: string) {
    setExpenseMatrix((current) => ({
      ...current,
      [category]: {
        ...(current[category] || {}),
        [month]: value,
      },
    }))
  }

  function handleSave() {
    setSavedMessage(`Daily report for ${displayDate} saved successfully.`)
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
                  <p className="report-subheading">Daily Sales &amp; Expenses Report</p>
                </div>

                <label className="report-date">
                  <span>Date</span>
                  <input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} />
                </label>
              </div>

              <section className="report-two-column">
                <div className="report-panel-block report-panel-income">
                  <div className="report-panel-title">Income / Sales</div>
                  <div className="report-mini-table">
                    <div className="report-mini-head">Description</div>
                    <div className="report-mini-head">Amount</div>

                    {salesRows.map((row) => (
                      <div key={row.key} className={`report-mini-row ${'strong' in row && row.strong ? 'is-strong' : ''}`}>
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
                      <input
                        className="report-mini-input"
                        type="text"
                        inputMode="decimal"
                        placeholder="£ 0.00"
                        value={summary.totalExpenses}
                        onChange={(event) => setSummary((current) => ({ ...current, totalExpenses: event.target.value }))}
                      />
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
                  <button type="button" className="report-save" onClick={handleSave}>
                    Save Daily Report
                  </button>
                  {savedMessage ? <p className="report-saved-message">{savedMessage}</p> : null}
                </div>
              </section>
            </main>
          ) : null}

          {activeSection === 'Sales Dashboard' ? <SalesDashboard /> : null}

          {activeSection === 'Expenses Dashboard' ? (
            <ExpenseDashboard expenseMatrix={expenseMatrix} onUpdateCell={updateExpenseMatrix} />
          ) : null}

          {activeSection === 'Profit Track' ? <ProfitTracker expenseMatrix={expenseMatrix} /> : null}
        </div>
      </div>
    </div>
  )
}

export default DailyReportPage
