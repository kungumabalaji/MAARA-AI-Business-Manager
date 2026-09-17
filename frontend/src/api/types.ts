export type OrganizationMembership = {
  organization_id: string
  organization_name: string
  organization_slug: string
  role: string
}

export type MeResponse = {
  profile: { id: string; display_name: string | null }
  organizations: OrganizationMembership[]
}

export type DailyReportExpenseOut = {
  id: string
  description: string
  amount: string
  expense_category_id: string | null
  notes: string | null
}

export type DailyReportOut = {
  id: string
  organization_id: string
  report_date: string
  status: string
  values: Record<string, string>
  expenses: DailyReportExpenseOut[]
  prepared_by: string | null
  checked_by: string | null
}

export type DailyReportListOut = {
  items: DailyReportOut[]
  total: number
}

export type SalesMonthSummary = {
  year: number
  month: string
  daysInMonth: number
  totalSales: string
  avgDailySales: string
  bestDay: { date: string; weekday: string; sales: string } | null
  cardTips: string
}

export type DailyReportSavePayload = {
  values: Record<string, string>
  expenses: { description: string; amount: string }[]
  prepared_by?: string | null
  checked_by?: string | null
}

export type DailySalesRow = {
  date: string
  cardSalesMachine: string
  cashSales: string
  uberEatsSales: string
  justEatSales: string
  deliverooSales: string
  otherSales: string
  miscIncome: string
  tips: string
  payout: string
}

export type MonthlySalesRow = {
  month: string
  cardSalesMachine: string
  cashSales: string
  uberEatsSales: string
  justEatSales: string
  deliverooSales: string
  otherSales: string
  miscIncome: string
  tips: string
  payout: string
}

export type MonthlyExpenseRow = { month: string; total: string }

export type DailyExpenseRow = { date: string; total: string }

export type ExpenseCategoryRow = { category: string; total: string }

export type ExpenseCategoryDef = { key: string; label: string; is_fixed_cost: boolean; is_custom: boolean }

export type RecentExpenseRow = { date: string; description: string; category: string; amount: string }

export type MonthlyProfitRow = { month: string; revenue: string; expenses: string; profit: string }

export type DailyProfitSummary = {
  date: string
  revenue: string
  expenses: string
  profit: string
  expectedCash: string
  actualCash: string
  cashVariance: string
  hasActualCash: boolean
}
