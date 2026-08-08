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

export type DailyReportSavePayload = {
  values: Record<string, string>
  expenses: { description: string; amount: string }[]
  prepared_by?: string | null
  checked_by?: string | null
}

export type DailySalesRow = {
  date: string
  cardSales: string
  cashSales: string
  uberEatsSales: string
  justEatSales: string
  deliverooSales: string
  otherSales: string
  miscIncome: string
}

export type MonthlySalesRow = {
  month: string
  cardSales: string
  cashSales: string
  uberEatsSales: string
  justEatSales: string
  deliverooSales: string
  otherSales: string
  miscIncome: string
}

export type MonthlyExpenseRow = { month: string; total: string }

export type ExpenseCategoryRow = { category: string; total: string }

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
