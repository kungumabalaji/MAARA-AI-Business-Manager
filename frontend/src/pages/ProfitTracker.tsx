import { useMemo, useState } from 'react'
import { MultiLineTrend } from '../components/charts/Charts'
import {
  categoryMonthTotal,
  channelTotal,
  currentMonth,
  deliveryCommissionCategories,
  formatGBP,
  formatPct,
  monthExpenseTotal,
  monthlySalesLedger,
  pctChange,
  previousMonth,
} from '../data/reportData'

const foodAndStockCategories = ['Groceries', 'Cash & Carry', 'Meat Bills', 'Frozen Food Bills', 'Beer Purchases']
const utilitiesCategories = ['Scottish Power (Gas & Electric)', 'Water Bills']
const otherCategories = ['Biffa Waste', 'Internet & Phone', 'Marketing', 'Accountant Fees', 'Everyday Spending', 'Council Tax']

function monthRevenue(matrixMonth: (typeof monthlySalesLedger)[number]) {
  return channelTotal(matrixMonth) + matrixMonth.miscIncome
}

function bucketTotal(matrix: Record<string, Record<string, string>>, categories: string[], month: string) {
  return categories.reduce((sum, category) => sum + categoryMonthTotal(matrix, category, month), 0)
}

type ProfitTrackerProps = {
  expenseMatrix: Record<string, Record<string, string>>
}

function ProfitTracker({ expenseMatrix }: ProfitTrackerProps) {
  const [period, setPeriod] = useState<'This Month' | 'This Year'>('This Month')

  const currentRow = monthlySalesLedger.find((row) => row.month === currentMonth)!
  const previousRow = monthlySalesLedger.find((row) => row.month === previousMonth)!

  const thisMonthRevenue = monthRevenue(currentRow)
  const lastMonthRevenue = monthRevenue(previousRow)
  const thisMonthExpenses = monthExpenseTotal(expenseMatrix, currentMonth)
  const lastMonthExpenses = monthExpenseTotal(expenseMatrix, previousMonth)

  const ytdRevenue = useMemo(() => monthlySalesLedger.reduce((sum, row) => sum + monthRevenue(row), 0), [])
  const ytdExpenses = useMemo(
    () => monthlySalesLedger.reduce((sum, row) => sum + monthExpenseTotal(expenseMatrix, row.month), 0),
    [expenseMatrix],
  )

  const revenue = period === 'This Month' ? thisMonthRevenue : ytdRevenue
  const expenses = period === 'This Month' ? thisMonthExpenses : ytdExpenses
  const profit = revenue - expenses
  const margin = revenue ? (profit / revenue) * 100 : 0

  const revenueChange = pctChange(thisMonthRevenue, lastMonthRevenue)
  const expenseChange = pctChange(thisMonthExpenses, lastMonthExpenses)
  const lastMonthProfit = lastMonthRevenue - lastMonthExpenses
  const profitChange = pctChange(profit, lastMonthProfit)
  const lastMonthMargin = lastMonthRevenue ? (lastMonthProfit / lastMonthRevenue) * 100 : 0

  const trendData = monthlySalesLedger.map((row) => {
    const rev = monthRevenue(row)
    const exp = monthExpenseTotal(expenseMatrix, row.month)
    return { label: row.month.slice(0, 3), values: { revenue: rev, expenses: exp, profit: rev - exp } }
  })

  const foodStock = bucketTotal(expenseMatrix, foodAndStockCategories, currentMonth)
  const utilities = bucketTotal(expenseMatrix, utilitiesCategories, currentMonth)
  const rent = categoryMonthTotal(expenseMatrix, 'Rent', currentMonth)
  const staffWages = categoryMonthTotal(expenseMatrix, 'Staff Wages', currentMonth)
  const commissions = deliveryCommissionCategories.reduce(
    (sum, category) => sum + categoryMonthTotal(expenseMatrix, category, currentMonth),
    0,
  )
  const other = bucketTotal(expenseMatrix, otherCategories, currentMonth)
  const breakdownExpenseTotal = foodStock + utilities + rent + staffWages + commissions + other
  const breakdownProfit = thisMonthRevenue - breakdownExpenseTotal

  const monthlyPerformance = monthlySalesLedger.map((row, index) => {
    const rev = monthRevenue(row)
    const exp = monthExpenseTotal(expenseMatrix, row.month)
    const prof = rev - exp
    const prior = index > 0 ? monthlySalesLedger[index - 1] : null
    const priorProfit = prior ? monthRevenue(prior) - monthExpenseTotal(expenseMatrix, prior.month) : null
    return {
      month: row.month,
      revenue: rev,
      expenses: exp,
      profit: prof,
      margin: rev ? (prof / rev) * 100 : 0,
      change: priorProfit !== null ? pctChange(prof, priorProfit) : null,
    }
  })

  const deliveryChannels = [
    { label: 'Uber Eats', sales: currentRow.uberEatsSales, category: 'Uber Eats Commission' },
    { label: 'Just Eat', sales: currentRow.justEatSales, category: 'Just Eat Commission' },
    { label: 'Deliveroo', sales: currentRow.deliverooSales, category: 'Deliveroo Commission' },
  ].map((row) => {
    const commission = categoryMonthTotal(expenseMatrix, row.category, currentMonth)
    return { ...row, commission, afterCommission: row.sales - commission }
  })

  const utilitiesChange = pctChange(
    bucketTotal(expenseMatrix, utilitiesCategories, currentMonth),
    bucketTotal(expenseMatrix, utilitiesCategories, previousMonth),
  )
  const commissionShare = (commissions / thisMonthExpenses) * 100

  const insights = [
    {
      icon: revenueChange >= 0 ? '↗' : '↘',
      tone: revenueChange >= 0 ? 'good' : 'bad',
      text: `Revenue ${revenueChange >= 0 ? 'increased' : 'decreased'} ${formatPct(Math.abs(revenueChange)).replace('+', '')} compared with ${previousMonth}.`,
    },
    {
      icon: profitChange >= 0 ? '↗' : '↘',
      tone: profitChange >= 0 ? 'good' : 'bad',
      text: `Operating profit ${profitChange >= 0 ? 'increased' : 'decreased'} ${formatPct(Math.abs(profitChange)).replace('+', '')} compared with ${previousMonth}.`,
    },
    {
      icon: utilitiesChange <= 0 ? '↘' : '↗',
      tone: utilitiesChange <= 0 ? 'good' : 'warn',
      text: `Utilities ${utilitiesChange <= 0 ? 'decreased' : 'increased'} ${formatPct(Math.abs(utilitiesChange)).replace('+', '')} compared with ${previousMonth}.`,
    },
    {
      icon: '⚠',
      tone: commissionShare > 5 ? 'warn' : 'good',
      text: `Delivery commissions now represent ${commissionShare.toFixed(1)}% of ${currentMonth} expenses.`,
    },
  ]

  return (
    <main className="report-card report-card-simple">
      <div className="report-card-header">
        <div>
          <p className="report-kicker">Profit &amp; Performance</p>
          <h1>Are we actually making money?</h1>
          <p className="report-subheading">Revenue, expenses, and the operating profit they produce</p>
        </div>

        <div className="profit-period-tabs" role="tablist" aria-label="Reporting period">
          {(['Today', '7 Days', 'This Month', 'This Year', 'Custom'] as const).map((label) => {
            const enabled = label === 'This Month' || label === 'This Year'
            return (
              <button
                key={label}
                type="button"
                role="tab"
                aria-selected={period === label}
                disabled={!enabled}
                className={`profit-period-tab ${period === label ? 'is-active' : ''} ${!enabled ? 'is-disabled' : ''}`}
                onClick={() => enabled && setPeriod(label as 'This Month' | 'This Year')}
              >
                {label}
              </button>
            )
          })}
        </div>
      </div>

      <section className="dashboard-scroll">
        <div className="report-dashboard-strip">
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Total Revenue</p>
            <strong>{formatGBP(revenue, { decimals: false })}</strong>
            {period === 'This Month' ? (
              <span className={`dashboard-delta ${revenueChange >= 0 ? 'is-positive' : 'is-negative'}`}>
                {revenueChange >= 0 ? '▲' : '▼'} {formatPct(revenueChange)}
              </span>
            ) : null}
          </div>
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Total Expenses</p>
            <strong>{formatGBP(expenses, { decimals: false })}</strong>
            {period === 'This Month' ? (
              <span className={`dashboard-delta ${expenseChange <= 0 ? 'is-positive' : 'is-negative'}`}>
                {expenseChange >= 0 ? '▲' : '▼'} {formatPct(expenseChange)}
              </span>
            ) : null}
          </div>
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Operating Profit</p>
            <strong>{formatGBP(profit, { decimals: false })}</strong>
            {period === 'This Month' ? (
              <span className={`dashboard-delta ${profitChange >= 0 ? 'is-positive' : 'is-negative'}`}>
                {profitChange >= 0 ? '▲' : '▼'} {formatPct(profitChange)}
              </span>
            ) : null}
          </div>
          <div className="report-dashboard-card report-dashboard-card-large">
            <p>Profit Margin</p>
            <strong>{margin.toFixed(1)}%</strong>
            {period === 'This Month' ? (
              <span className={`dashboard-delta ${margin >= lastMonthMargin ? 'is-positive' : 'is-negative'}`}>
                {margin >= lastMonthMargin ? '▲' : '▼'} {formatPct(margin - lastMonthMargin)}pt
              </span>
            ) : null}
          </div>
        </div>

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

        <div className="report-two-column dashboard-two-column">
          <div className="report-panel-block">
            <div className="report-panel-title">Profit Breakdown — {currentMonth}</div>
            <div className="dashboard-panel-body">
              <div className="profit-breakdown">
                <p className="profit-breakdown-heading">Income</p>
                <div className="profit-breakdown-row"><span>Card + Cash + Delivery Sales</span><span>{formatGBP(channelTotal(currentRow), { decimals: false })}</span></div>
                <div className="profit-breakdown-row"><span>Misc Income</span><span>{formatGBP(currentRow.miscIncome, { decimals: false })}</span></div>
                <div className="profit-breakdown-row is-total"><span>Total Income</span><span>{formatGBP(thisMonthRevenue, { decimals: false })}</span></div>

                <p className="profit-breakdown-heading">Expenses</p>
                <div className="profit-breakdown-row"><span>Food &amp; Stock</span><span>{formatGBP(foodStock, { decimals: false })}</span></div>
                <div className="profit-breakdown-row"><span>Utilities</span><span>{formatGBP(utilities, { decimals: false })}</span></div>
                <div className="profit-breakdown-row"><span>Rent</span><span>{formatGBP(rent, { decimals: false })}</span></div>
                <div className="profit-breakdown-row"><span>Staff Wages</span><span>{formatGBP(staffWages, { decimals: false })}</span></div>
                <div className="profit-breakdown-row"><span>Delivery Commissions</span><span>{formatGBP(commissions, { decimals: false })}</span></div>
                <div className="profit-breakdown-row"><span>Other</span><span>{formatGBP(other, { decimals: false })}</span></div>
                <div className="profit-breakdown-row is-total"><span>Total Expenses</span><span>{formatGBP(breakdownExpenseTotal, { decimals: false })}</span></div>

                <div className="profit-breakdown-row is-profit"><span>Operating Profit</span><span>{formatGBP(breakdownProfit, { decimals: false })}</span></div>
                <p className="dashboard-footnote">Opening Cash is excluded — it's a cash reconciliation figure, not income.</p>
              </div>
            </div>
          </div>

          <div className="report-panel-block">
            <div className="report-panel-title">Delivery Channel Performance</div>
            <div className="dashboard-panel-body">
              <table className="dashboard-recent-table">
                <thead>
                  <tr>
                    <th>Channel</th>
                    <th>Sales</th>
                    <th>Commission</th>
                    <th>After Commission</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveryChannels.map((row) => (
                    <tr key={row.label}>
                      <td>{row.label}</td>
                      <td>{formatGBP(row.sales, { decimals: false })}</td>
                      <td>{formatGBP(row.commission, { decimals: false })}</td>
                      <td>{formatGBP(row.afterCommission, { decimals: false })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="dashboard-footnote">
                "After commission" is revenue net of platform fees — not full channel profit, since food cost, packaging and labour aren't allocated per channel.
              </p>
            </div>
          </div>
        </div>

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
                  <th>vs Prior Month</th>
                </tr>
              </thead>
              <tbody>
                {monthlyPerformance.map((row) => (
                  <tr key={row.month}>
                    <td>{row.month}</td>
                    <td>{formatGBP(row.revenue, { decimals: false })}</td>
                    <td>{formatGBP(row.expenses, { decimals: false })}</td>
                    <td>{formatGBP(row.profit, { decimals: false })}</td>
                    <td>{row.margin.toFixed(1)}%</td>
                    <td>
                      {row.change === null ? (
                        '—'
                      ) : (
                        <span className={`dashboard-delta ${row.change >= 0 ? 'is-positive' : 'is-negative'}`}>
                          {row.change >= 0 ? '▲' : '▼'} {formatPct(row.change)}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

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
      </section>
    </main>
  )
}

export default ProfitTracker
