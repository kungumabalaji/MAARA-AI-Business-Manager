import { apiFetch } from './client'
import type {
  DailyExpenseRow,
  DailyProfitSummary,
  DailyReportListOut,
  DailyReportOut,
  DailyReportSavePayload,
  DailySalesRow,
  ExpenseCategoryDef,
  ExpenseCategoryRow,
  MeResponse,
  MonthlyExpenseRow,
  MonthlyProfitRow,
  MonthlySalesRow,
  RecentExpenseRow,
  SalesMonthSummary,
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

export function fetchSalesMonthSummary(organizationId: string, year: number, month: number): Promise<SalesMonthSummary> {
  return apiFetch(`/organizations/${organizationId}/dashboard/sales/monthly-summary?year=${year}&month=${month}`)
}

export function fetchDailyReports(
  organizationId: string,
  params: { since?: string; until?: string; page?: number; pageSize?: number } = {},
): Promise<DailyReportListOut> {
  const query = new URLSearchParams()
  if (params.since) query.set('since', params.since)
  if (params.until) query.set('until', params.until)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.pageSize ?? 20))
  return apiFetch(`/organizations/${organizationId}/daily-reports?${query.toString()}`)
}

export function fetchDailyReportById(organizationId: string, reportId: string): Promise<DailyReportOut> {
  return apiFetch(`/organizations/${organizationId}/daily-reports/${reportId}`)
}

export function updateDailyReport(
  organizationId: string,
  reportId: string,
  payload: DailyReportSavePayload,
): Promise<DailyReportOut> {
  return apiFetch<DailyReportOut>(`/organizations/${organizationId}/daily-reports/${reportId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteDailyReport(organizationId: string, reportId: string): Promise<void> {
  return apiFetch<void>(`/organizations/${organizationId}/daily-reports/${reportId}`, {
    method: 'DELETE',
  })
}

export function fetchExpensesMonthly(organizationId: string, months = 7): Promise<MonthlyExpenseRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/monthly?months=${months}`)
}

export function fetchExpensesDaily(organizationId: string, days = 90): Promise<DailyExpenseRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/daily?days=${days}`)
}

export function fetchExpenseCategories(organizationId: string): Promise<ExpenseCategoryDef[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/categories`)
}

export function fetchExpensesByCategory(
  organizationId: string,
  since: string,
  until: string,
): Promise<ExpenseCategoryRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/by-category?since=${since}&until=${until}`)
}

export function fetchExpensesRecent(
  organizationId: string,
  limit = 20,
  since?: string,
  until?: string,
): Promise<RecentExpenseRow[]> {
  const query = new URLSearchParams({ limit: String(limit) })
  if (since) query.set('since', since)
  if (until) query.set('until', until)
  return apiFetch(`/organizations/${organizationId}/dashboard/expenses/recent?${query.toString()}`)
}

export function fetchProfitMonthly(organizationId: string, months = 7): Promise<MonthlyProfitRow[]> {
  return apiFetch(`/organizations/${organizationId}/dashboard/profit/monthly?months=${months}`)
}

export function fetchProfitDailySummary(organizationId: string, date?: string): Promise<DailyProfitSummary | null> {
  const query = date ? `?date=${date}` : ''
  return apiFetch(`/organizations/${organizationId}/dashboard/profit/daily-summary${query}`)
}
