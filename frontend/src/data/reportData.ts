export const expenseMonths = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const

export type ExpenseMonth = (typeof expenseMonths)[number]

export const expenseCategories = [
  'Scottish Power (Gas & Electric)',
  'Groceries',
  'Cash & Carry',
  'Beer Purchases',
  'Meat Bills',
  'Frozen Food Bills',
  'Biffa Waste',
  'Internet & Phone',
  'Marketing',
  'Accountant Fees',
  'Deliveroo Commission',
  'Just Eat Commission',
  'Uber Eats Commission',
  'Everyday Spending',
  'Rent',
  'Council Tax',
  'Staff Wages',
  'Water Bills',
]

// Categories whose cost is contractually fixed month to month.
export const fixedCategories = ['Rent', 'Council Tax', 'Internet & Phone', 'Accountant Fees']

export const deliveryCommissionCategories = ['Deliveroo Commission', 'Just Eat Commission', 'Uber Eats Commission']

export const initialExpenseMatrix: Record<string, Record<string, string>> = {
  'Scottish Power (Gas & Electric)': {
    January: '£2,627.89',
    February: '£2,569.88',
    March: '£2,257.60',
    April: '£2,489.89',
    May: '£2,438.94',
    June: '£2,510.20',
  },
  Groceries: {
    March: '£2,592.30',
    April: '£3,544.35',
    May: '£3,548.97',
    June: '£3,120.55',
  },
  'Cash & Carry': {
    April: '£1,884.29',
    May: '£820.14',
    June: '£950.30',
  },
  'Beer Purchases': {
    January: '£415.18',
    February: '£429.58',
    March: '£429.58',
    April: '£429.58',
    May: '£429.58',
    June: '£429.58',
  },
  'Meat Bills': {
    April: '£1,453.00',
    May: '£1,984.00',
    June: '£1,760.00',
  },
  'Frozen Food Bills': {
    April: '£435.74',
    May: '£609.92',
    June: '£588.40',
  },
  'Biffa Waste': {
    January: '£369.83',
    February: '£316.46',
    March: '£298.10',
    April: '£310.00',
    May: '£325.40',
    June: '£299.75',
  },
  'Internet & Phone': {
    January: '£49.89',
    February: '£54.08',
    March: '£40.76',
    April: '£35.76',
    May: '£48.99',
    June: '£43.80',
  },
  Marketing: {
    May: '£180.00',
    June: '£220.00',
  },
  'Accountant Fees': {
    June: '£350.00',
  },
  'Deliveroo Commission': {
    May: '£410.00',
    June: '£460.00',
  },
  'Just Eat Commission': {
    May: '£520.00',
    June: '£560.00',
  },
  'Uber Eats Commission': {
    May: '£610.00',
    June: '£680.00',
  },
  'Everyday Spending': {
    March: '£601.88',
    April: '£385.61',
    May: '£654.35',
    June: '£602.10',
  },
  Rent: {
    January: '£4,166.00',
    February: '£4,166.00',
    March: '£4,166.00',
    April: '£4,166.00',
    May: '£4,166.00',
    June: '£4,166.00',
    July: '£4,166.00',
    August: '£4,166.00',
    September: '£4,166.00',
    October: '£4,166.00',
    November: '£4,166.00',
    December: '£7,166.00',
  },
  'Council Tax': {
    January: '£917.00',
    February: '£1,059.38',
    March: '£1,059.38',
    April: '£1,059.38',
    May: '£1,059.38',
    June: '£1,059.38',
    July: '£1,059.38',
    August: '£1,059.38',
    September: '£1,059.38',
    October: '£1,059.38',
    November: '£1,059.38',
    December: '£1,059.38',
  },
  'Staff Wages': {
    January: '£3,420.00',
    February: '£3,460.00',
    March: '£3,510.00',
    April: '£3,580.00',
    May: '£3,650.00',
    June: '£3,800.00',
  },
  'Water Bills': {
    January: '£88.20',
    February: '£90.10',
    March: '£91.40',
    April: '£93.80',
    May: '£96.40',
    June: '£101.20',
  },
}

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

// Two trading weeks ending on the daily-report default date (2026-08-07) — supports
// both the "last 7 days" trend chart and a real week-over-week comparison.
export const dailySalesLedger: ({ date: string } & SalesChannels)[] = [
  { date: '2026-07-25', cardSales: 2360, cashSales: 1170, uberEatsSales: 870, justEatSales: 570, deliverooSales: 365, otherSales: 55, miscIncome: 0 },
  { date: '2026-07-26', cardSales: 2120, cashSales: 1050, uberEatsSales: 765, justEatSales: 500, deliverooSales: 320, otherSales: 35, miscIncome: 0 },
  { date: '2026-07-27', cardSales: 1470, cashSales: 695, uberEatsSales: 480, justEatSales: 340, deliverooSales: 215, otherSales: 20, miscIncome: 0 },
  { date: '2026-07-28', cardSales: 1530, cashSales: 730, uberEatsSales: 515, justEatSales: 355, deliverooSales: 220, otherSales: 25, miscIncome: 0 },
  { date: '2026-07-29', cardSales: 1760, cashSales: 835, uberEatsSales: 615, justEatSales: 410, deliverooSales: 260, otherSales: 30, miscIncome: 0 },
  { date: '2026-07-30', cardSales: 1965, cashSales: 925, uberEatsSales: 675, justEatSales: 455, deliverooSales: 285, otherSales: 40, miscIncome: 0 },
  { date: '2026-07-31', cardSales: 2260, cashSales: 1075, uberEatsSales: 780, justEatSales: 525, deliverooSales: 330, otherSales: 50, miscIncome: 0 },
  { date: '2026-08-01', cardSales: 2650, cashSales: 1320, uberEatsSales: 980, justEatSales: 640, deliverooSales: 410, otherSales: 60, miscIncome: 0 },
  { date: '2026-08-02', cardSales: 2380, cashSales: 1180, uberEatsSales: 860, justEatSales: 560, deliverooSales: 360, otherSales: 40, miscIncome: 0 },
  { date: '2026-08-03', cardSales: 1650, cashSales: 780, uberEatsSales: 540, justEatSales: 380, deliverooSales: 240, otherSales: 20, miscIncome: 0 },
  { date: '2026-08-04', cardSales: 1720, cashSales: 820, uberEatsSales: 580, justEatSales: 400, deliverooSales: 250, otherSales: 30, miscIncome: 0 },
  { date: '2026-08-05', cardSales: 1980, cashSales: 940, uberEatsSales: 690, justEatSales: 460, deliverooSales: 290, otherSales: 35, miscIncome: 0 },
  { date: '2026-08-06', cardSales: 2210, cashSales: 1040, uberEatsSales: 760, justEatSales: 510, deliverooSales: 320, otherSales: 45, miscIncome: 0 },
  { date: '2026-08-07', cardSales: 2540, cashSales: 1210, uberEatsSales: 880, justEatSales: 590, deliverooSales: 370, otherSales: 55, miscIncome: 210 },
]

// Monthly sales ledger, channel totals for each trading month of 2026.
export const monthlySalesLedger: ({ month: ExpenseMonth } & SalesChannels)[] = [
  { month: 'January', cardSales: 14200, cashSales: 7200, uberEatsSales: 5100, justEatSales: 3600, deliverooSales: 2100, otherSales: 380, miscIncome: 150 },
  { month: 'February', cardSales: 14800, cashSales: 7450, uberEatsSales: 5300, justEatSales: 3750, deliverooSales: 2200, otherSales: 400, miscIncome: 120 },
  { month: 'March', cardSales: 15600, cashSales: 7800, uberEatsSales: 5600, justEatSales: 3950, deliverooSales: 2350, otherSales: 420, miscIncome: 200 },
  { month: 'April', cardSales: 16400, cashSales: 8100, uberEatsSales: 5850, justEatSales: 4150, deliverooSales: 2500, otherSales: 450, miscIncome: 180 },
  { month: 'May', cardSales: 16200, cashSales: 8450, uberEatsSales: 6050, justEatSales: 4200, deliverooSales: 2450, otherSales: 430, miscIncome: 190 },
  { month: 'June', cardSales: 18420, cashSales: 9850, uberEatsSales: 6940, justEatSales: 4820, deliverooSales: 2810, otherSales: 500, miscIncome: 260 },
]

// The month treated as "current" for KPI cards / comparisons across all three dashboards.
export const currentMonth: ExpenseMonth = 'June'
export const previousMonth: ExpenseMonth = 'May'

export type RecentExpense = {
  date: string
  description: string
  category: string
  amount: number
  paymentMethod: string
}

export const recentExpenses: RecentExpense[] = [
  { date: '2026-08-07', description: 'Weekly grocery top-up', category: 'Groceries', amount: 245.6, paymentMethod: 'Card' },
  { date: '2026-08-07', description: 'Gas & electric standing charge', category: 'Scottish Power (Gas & Electric)', amount: 90.2, paymentMethod: 'Direct Debit' },
  { date: '2026-08-06', description: 'Butcher order', category: 'Meat Bills', amount: 380.0, paymentMethod: 'Card' },
  { date: '2026-08-06', description: 'Takeaway packaging restock', category: 'Everyday Spending', amount: 76.4, paymentMethod: 'Cash' },
  { date: '2026-08-05', description: 'Cash & Carry run', category: 'Cash & Carry', amount: 214.9, paymentMethod: 'Card' },
  { date: '2026-08-05', description: 'Social media ad spend', category: 'Marketing', amount: 60.0, paymentMethod: 'Card' },
  { date: '2026-08-04', description: 'Frozen supplier delivery', category: 'Frozen Food Bills', amount: 142.3, paymentMethod: 'Card' },
  { date: '2026-08-03', description: 'Waste collection', category: 'Biffa Waste', amount: 74.5, paymentMethod: 'Direct Debit' },
]

export function parseAmount(raw: string | undefined): number {
  if (!raw) return 0
  const numeric = Number(raw.replace(/[^\d.-]/g, ''))
  return Number.isFinite(numeric) ? numeric : 0
}

export function categoryMonthTotal(
  matrix: Record<string, Record<string, string>>,
  category: string,
  month: string,
): number {
  return parseAmount(matrix[category]?.[month])
}

export function monthExpenseTotal(matrix: Record<string, Record<string, string>>, month: string): number {
  return expenseCategories.reduce((sum, category) => sum + categoryMonthTotal(matrix, category, month), 0)
}

export function categoryTotalAllMonths(matrix: Record<string, Record<string, string>>, category: string): number {
  return expenseMonths.reduce((sum, month) => sum + categoryMonthTotal(matrix, category, month), 0)
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
