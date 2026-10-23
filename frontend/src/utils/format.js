/** 展示格式化工具（front-ui §1.4）。前端只做展示格式化，不做任何金额重算。 */

/** 金额：¥ + 千分位 + 2 位小数；负数输出 -¥1,234.56（用于 balance） */
export function formatMoney(value) {
  const num = Number(value ?? 0)
  const text = Math.abs(num).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return num < 0 ? `-¥${text}` : `¥${text}`
}

/** 占比：2 位小数 + %（直接使用后端 percentage） */
export function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`
}

/** 类型中文标签 */
export function typeLabel(type) {
  return type === 'income' ? '收入' : '支出'
}

/** 备注为空显示 — ，不显示 null（front-ui §1.1） */
export function noteText(note) {
  return note ? note : '—'
}

/** 饼图与图例明细共用的分类配色（front-ui §2 两区颜色需一致） */
export const PIE_COLORS = [
  '#409EFF',
  '#67C23A',
  '#E6A23C',
  '#F56C6C',
  '#909399',
  '#9B59B6',
  '#1ABC9C',
  '#3498DB',
  '#E67E22',
  '#7F8C8D',
]

/** 按索引取色，超出后循环 */
export function pieColor(index) {
  return PIE_COLORS[index % PIE_COLORS.length]
}