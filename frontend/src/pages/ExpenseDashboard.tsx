import { useMemo } from 'react'
import { Donut, BarTrend, RankedBars } from '../components/charts/Charts'
import {
  categoryMonthTotal,
  categoryTotalAllMonths,
  currentMonth,
  deliveryCommissionCategories,
  expenseCategories,
  expenseMonths,
  fixedCategories,
  formatGBP,
  formatPct,
  monthExpenseTotal,
  pctChange,
  previousMonth,
  recentExpenses,
} from '../data/reportData'

const categoryPalette = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7']

const monthsWithData = expenseMonths.slice(0, 7)

type ExpenseDashboardProps = {
  expenseMatrix: Record<string, Record<string, string>>
  onUpdateCell: (category: string, month: string, value: string) => void
}

function ExpenseDashboard({ expenseMatrix, onUpdateCell }: ExpenseDashboardProps) {
  const thisMonthTotal = monthExpenseTotal(expenseMatrix, currentMonth)
  const lastMonthTotal = monthExpenseTotal(expenseMatrix, previousMonth)
  const totalExpenses = useMemo(
    () => expenseMonths.reduce((sum, month) => sum + monthExpenseTotal(expenseMatrix, month), 0),
    [expenseMatrix],
  )

  const categoryThisMonth = expenseCategories
    .map((category) => ({ category, value: categoryMonthTotal(expenseMatrix, category, currentMonth) }))
    .filter((row) => row.value > 0)
    .sort((a, b) => b.value - a.value)

  const largestCategory = categoryThisMonth[0]

  const topCategories = categoryThisMonth.slice(0, 6)
  const otherTotal = categoryThisMonth.slice(6).reduce((sum, row) => sum + row.value, 0)
  const donutSegments = topCategories.map((row, i) => ({
    label: row.category,
    value: row.value,
    color: categoryPalette[i % categoryPalette.length],
  }))
  if (otherTotal > 0) {
    donutSegments.push({ label: 'Other', value: otherTotal, color: '#e34948' })
  }

  const fixedTotal = fixedCategories.reduce((sum, category) => sum + categoryMonthTotal(expenseMatrix, category, currentMonth), 0)
  const variableTotal = thisMonthTotal - fixedTotal

  const commissionRows = deliveryCommissionCategories.map((category) => ({
    category,
    value: categoryMonthTotal(expenseMatrix, category, currentMonth),
  }))
  const commissionTotal = commissionRows.reduce((sum, row) => sum + row.value, 0)

  const trendData = monthsWithData.map((month) => ({ label: month.slice(0, 3), value: monthExpenseTotal(expenseMatrix, month) }))

  const avgDailyExpense = thisMonthTotal / 30
  const expenseChange = pctChange(thisMonthTotal, lastMonthTotal)

  const kpis = [
    { label: 'Total Expenses', value: formatGBP(totalExpenses, { decimals: false }), hint: 'year to date' },
    { label: `This Month (${currentMonth})`, value: formatGBP(thisMonthTotal, { decimals: false }), hint: currentMonth },
    { label: 'Avg Daily Expense', value: formatGBP(avgDailyExpense, { decimals: false }), hint: 'this month / 30' },
    { label: 'Largest Category', value: largestCategory?.category ?? '—', hint: largestCategory ? formatGBP(largestCategory.value, { decimals: false }) : '' },
    {
      label: 'Expense Change',
      value: formatPct(expenseChange),
      hint: `vs ${previousMonth}`,
      positive: expenseChange <= 0,
    },
  ]

  return (
    <main className="report-card report-card-simple">
      <div className="report-card-header">
        <div>
          <p className="report-kicker">Expenses Dashboard</p>
          <h1>Dosa n Chutney</h1>
          <p className="report-subheading">Where the money is going, and which costs are rising</p>
        </div>
      </div>

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

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Expense by Category — {currentMonth}</div>
            <div className="dashboard-panel-body dashboard-donut-body">
              <Donut
                segments={donutSegments}
                centerLabel={currentMonth}
                centerValue={formatGBP(thisMonthTotal, { decimals: false })}
              />
              <RankedBars
                rows={donutSegments}
                formatValue={(v) => formatGBP(v, { decimals: false })}
              />
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Fixed vs Variable Costs</div>
            <div className="dashboard-panel-body">
              <RankedBars
                rows={[
                  { label: 'Fixed Costs', value: fixedTotal, color: '#4a3aa7' },
                  { label: 'Variable Costs', value: variableTotal, color: '#eb6834' },
                ]}
                formatValue={(v) => formatGBP(v, { decimals: false })}
              />
              <p className="dashboard-footnote">
                Fixed: Rent, Council Tax, Internet &amp; Phone, Accountant Fees. Everything else is variable.
              </p>
            </div>
          </div>
        </div>

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Delivery Commissions — {currentMonth}</div>
            <div className="dashboard-panel-body">
              <ul className="dashboard-simple-list">
                {commissionRows.map((row) => (
                  <li key={row.category}>
                    <span>{row.category.replace(' Commission', '')}</span>
                    <strong>{formatGBP(row.value, { decimals: false })}</strong>
                  </li>
                ))}
              </ul>
              <div className="dashboard-delivery-summary">
                <div>
                  <p>Total Commission</p>
                  <strong>{formatGBP(commissionTotal, { decimals: false })}</strong>
                </div>
                <div>
                  <p>% of Expenses</p>
                  <strong>{((commissionTotal / thisMonthTotal) * 100).toFixed(1)}%</strong>
                </div>
              </div>
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Recent Expenses</div>
            <div className="dashboard-panel-body dashboard-recent-body">
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
                  {recentExpenses.map((row) => (
                    <tr key={`${row.date}-${row.description}`}>
                      <td>{new Date(`${row.date}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}</td>
                      <td>{row.description}</td>
                      <td>{row.category}</td>
                      <td>{formatGBP(row.amount, { decimals: false })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="report-panel-block">
          <div className="report-panel-title">Monthly Expense Entry — by Category</div>
          <div className="expenses-matrix-wrap dashboard-matrix-wrap">
            <div className="expenses-matrix">
              <div className="expenses-cell expenses-cell-head expenses-cell-category">Category</div>
              {expenseMonths.map((month) => (
                <div key={month} className="expenses-cell expenses-cell-head">
                  {month}
                </div>
              ))}
              <div className="expenses-cell expenses-cell-head">Total</div>

              {expenseCategories.map((category) => {
                const total = categoryTotalAllMonths(expenseMatrix, category)
                return (
                  <div key={category} className="expenses-row">
                    <div className="expenses-cell expenses-cell-category">{category}</div>
                    {expenseMonths.map((month) => (
                      <input
                        key={`${category}-${month}`}
                        className="expenses-cell expenses-input"
                        type="text"
                        placeholder="£ 0.00"
                        value={expenseMatrix[category]?.[month] || ''}
                        onChange={(event) => onUpdateCell(category, month, event.target.value)}
                      />
                    ))}
                    <div className="expenses-cell expenses-total">{total ? formatGBP(total) : formatGBP(0)}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

export default ExpenseDashboard
