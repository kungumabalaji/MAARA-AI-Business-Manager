import { apiFetch } from './client'
import type {
  DailyProfitSummary,
  DailyReportOut,
  DailyReportSavePayload,
  DailySalesRow,
  ExpenseCategoryRow,
  MeResponse,
  MonthlyExpenseRow,
  MonthlyProfitRow,
  MonthlySalesRow,
  RecentExpenseRow,
} from './types'

export function fetchMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>('/me')
}

export function fetchDailyReport(organizationId: string, date: string): Promise<DailyReportOut | null> {
  return apiFetch<DailyReportOut | null>(`/organizations/${organizationId}/daily-reports/by-date/${date}`)
}

export function saveDailyReport(
  organizationId: string,
  date: string,
  payload: DailyReportSavePayload,
): Promise<DailyReportOut> {
  return apiFetch<DailyReportOut>(`/organizations/${organizationId}/daily-reports/by-date/${date}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function fetchSalesDaily(organizationId: string, days = 21): Promise<DailySalesRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/sales/daily?days=${days}`)
}

export function fetchSalesMonthly(organizationId: string, months = 7): Promise<MonthlySalesRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/sales/monthly?months=${months}`)
}

export function fetchExpensesMonthly(organizationId: string, months = 7): Promise<MonthlyExpenseRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/monthly?months=${months}`)
}

export function fetchExpensesByCategory(
  organizationId: string,
  since: string,
  until: string,
): Promise<ExpenseCategoryRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/by-category?since=${since}&until=${until}`)
}

export function fetchExpensesRecent(organizationId: string, limit = 20): Promise<RecentExpenseRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/recent?limit=${limit}`)
}

export function fetchProfitMonthly(organizationId: string, months = 7): Promise<MonthlyProfitRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/profit/monthly?months=${months}`)
}

export function fetchProfitDailySummary(organizationId: string, date?: string): Promise<DailyProfitSummary | null> {
  const query = date ? `?date=${date}` : ''
  return apiFetch(`/organizations/${organizationId}/dashboard/profit/daily-summary${query}`)
}
