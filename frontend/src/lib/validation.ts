// Numeric-input validation, shared by every money/number field in the app.
//
// Rule: a money field may contain ONLY digits, at most one decimal point, and
// an optional leading minus. No letters, no spaces, no thousands separators,
// no currency symbols.
//
// Why a dedicated file: the old code "cleaned" a field by deleting every
// character that wasn't a digit. That turns a typo like "1842x00" into
// "184200" — a £1,842 entry silently becomes £184,200. We now reject the
// bad character instead of stripping it.

/**
 * Still-being-typed states that are OK to keep in the input box:
 *   ""  "-"  "12"  "12."  "12.34"  ".5"
 * Use this to decide whether to accept a keystroke.
 */
const PARTIAL_NUMBER = /^-?\d*\.?\d*$/

/**
 * A fully-formed, parseable number:
 *   "12"  "-12"  "12.34"  ".5"  "-.5"
 * Use this for save-time validation and before doing math.
 */
const COMPLETE_NUMBER = /^-?(\d+\.?\d*|\.\d+)$/

/**
 * Largest magnitude a money field may hold. The backend columns are
 * NUMERIC(14,2) for expense amounts (abs < 10^12) and NUMERIC(18,4) for
 * report values — anything bigger overflows the database and fails the whole
 * save. 10^11 (£100 billion) is far beyond any real daily figure and stays
 * safely under the stricter limit.
 */
export const MAX_MONEY = 1e11

/** True if `value` is safe to accept into a numeric input as the user types. */
export function isAcceptableNumberInput(value: string): boolean {
  const trimmed = value.trim()
  if (!PARTIAL_NUMBER.test(trimmed)) return false
  const n = Number(trimmed)
  // Number("") is 0 and Number("-") is NaN — both fine to keep typing.
  if (Number.isFinite(n) && Math.abs(n) > MAX_MONEY) return false
  return true
}

/** True only when `value` is a complete number (not "", "-", "3." etc.). */
export function isCompleteNumber(value: string): boolean {
  return COMPLETE_NUMBER.test(value.trim())
}

/**
 * Convert a numeric field to a number for calculations. Anything that is not a
 * complete number (blank, half-typed, or invalid) becomes 0. Characters are
 * never stripped — an invalid entry is 0, not a guess.
 */
export function parseAmount(value: string | undefined | null): number {
  if (value == null) return 0
  const trimmed = value.trim()
  if (!isCompleteNumber(trimmed)) return 0
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : 0
}
