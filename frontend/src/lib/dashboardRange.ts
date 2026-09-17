// Shared date-range filter for the Sales and Expenses dashboards.
//
// The backend endpoints take a `days` window. "All-time" is expressed as a very
// large window (ALL_TIME_DAYS). For the fixed ranges we request DOUBLE the
// window so the dashboard can also show the immediately-preceding period for
// the growth / comparison figures.

export type RangeKey = '7' | '30' | '90' | 'all'

export const RANGE_OPTIONS: { key: RangeKey; label: string }[] = [
  { key: '7', label: '7 days' },
  { key: '30', label: '30 days' },
  { key: '90', label: '90 days' },
  { key: 'all', label: 'All-time' },
]

export const ALL_TIME_DAYS = 36500

/** History window (in days) to REQUEST from the API for a given range. */
export function fetchWindowDays(range: RangeKey): number {
  return range === 'all' ? ALL_TIME_DAYS : Number(range) * 2
}

/** Local YYYY-MM-DD for `n` days before today. */
export function daysAgoISO(n: number): string {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - n)
  return d.toLocaleDateString('en-CA')
}

/** Split date-keyed rows into the current period and the one before it. */
export function splitByRange<T extends { date: string }>(
  rows: T[],
  range: RangeKey,
): { current: T[]; previous: T[] } {
  if (range === 'all') return { current: [...rows], previous: [] }
  const span = Number(range)
  const currentStart = daysAgoISO(span)
  const previousStart = daysAgoISO(span * 2)
  return {
    current: rows.filter((r) => r.date >= currentStart),
    previous: rows.filter((r) => r.date >= previousStart && r.date < currentStart),
  }
}

export function rangeLabel(range: RangeKey): string {
  return range === 'all' ? 'All-time' : `Last ${range} days`
}

// Shared by the Sales and Expenses dashboards' "All Months / Jan..Dec" filter.

export const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export const MONTH_SHORT_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export type MonthFilter = number | 'all' | 'today'

/** ISO since/until covering the whole of `monthIndex` (0-11) in `year`. */
export function monthRangeISO(year: number, monthIndex: number): { since: string; until: string } {
  const since = new Date(Date.UTC(year, monthIndex, 1)).toISOString().slice(0, 10)
  const until = new Date(Date.UTC(year, monthIndex + 1, 0)).toISOString().slice(0, 10)
  return { since, until }
}

/** Local YYYY-MM-DD for today — used by the "Today" quick filter so it scopes
 * strictly to today's date instead of summing in every prior day. */
export function todayISO(): string {
  return new Date().toLocaleDateString('en-CA')
}
