// Generic formatting/derivation helpers shared by the three dashboards. This
// file used to also hold a hand-built mock dataset (daily/monthly sales
// ledgers, an expense category matrix) — that's gone now that all three
// dashboards read from the real backend API (see src/api/reportsApi.ts).

export type SalesChannels = {
  cardSales: number
  cashSales: number
  uberEatsSales: number
  justEatSales: number
  deliverooSales: number
  otherSales: number
  miscIncome: number
}

export const salesChannelMeta: { key: keyof Omit<SalesChannels, 'miscIncome'>; label: string; color: string }[] = [
  { key: 'cardSales', label: 'Card Sales', color: '#2a78d6' },
  { key: 'cashSales', label: 'Cash Sales', color: '#1baf7a' },
  { key: 'uberEatsSales', label: 'Uber Eats', color: '#eda100' },
  { key: 'justEatSales', label: 'Just Eat', color: '#e87ba4' },
  { key: 'deliverooSales', label: 'Deliveroo', color: '#008300' },
  { key: 'otherSales', label: 'Other Sales', color: '#4a3aa7' },
]

export function channelTotal(entry: SalesChannels): number {
  return (
    entry.cardSales +
    entry.cashSales +
    entry.uberEatsSales +
    entry.justEatSales +
    entry.deliverooSales +
    entry.otherSales
  )
}

export function parseAmount(raw: string | undefined): number {
  if (!raw) return 0
  const numeric = Number(raw.replace(/[^\d.-]/g, ''))
  return Number.isFinite(numeric) ? numeric : 0
}

export function formatGBP(value: number, options?: { decimals?: boolean }): string {
  const decimals = options?.decimals ?? true
  return `£${value.toLocaleString('en-GB', {
    minimumFractionDigits: decimals ? 2 : 0,
    maximumFractionDigits: decimals ? 2 : 0,
  })}`
}

export function pctChange(current: number, previous: number): number {
  if (previous === 0) return current === 0 ? 0 : 100
  return ((current - previous) / previous) * 100
}

export function formatPct(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function lastNDays<T>(list: T[], n: number): T[] {
  return list.slice(-n)
}

export function previousNDays<T>(list: T[], n: number): T[] {
  return list.slice(-2 * n, -n)
}

export function weekdayLabel(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString('en-GB', { weekday: 'short' })
}

export function shortDateLabel(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

export function monthLabel(monthKey: string): string {
  const [year, month] = monthKey.split('-')
  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })
}
