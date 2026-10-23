/** 日期 / 月份工具（spec §5.1、§5.3；格式严格 YYYY-MM-DD / YYYY-MM） */

const pad = (n) => String(n).padStart(2, '0')

/** 业务最小日期（spec R-24） */
export const MIN_DATE = '2000-01-01'

/** 今天（本地时区）YYYY-MM-DD，作为日期上限 */
export function today() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 当前月 YYYY-MM（UI 默认值，仅用于人工操作体验，不作为测试依据） */
export function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
}

/** 月份 ±delta，跨年自动进位（front-ui §2.3） */
export function shiftMonth(month, delta) {
  const [y, m] = month.split('-').map(Number)
  const total = y * 12 + (m - 1) + delta
  const year = Math.floor(total / 12)
  const mon = (total % 12 + 12) % 12 + 1
  return `${year}-${pad(mon)}`
}

/** 日期是否超出 [2000-01-01, 今天] */
export function isDateOutOfRange(dateText) {
  return dateText < MIN_DATE || dateText > today()
}

/** Unicode 码点长度（spec R-06） */
export function codePointLength(text) {
  return [...(text || '')].length
}