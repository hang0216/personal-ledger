/**
 * CSV 导出工具（选做功能 3）。
 * 使用 UTF-8 BOM + 标准单元格转义，Excel 双击打开不乱码、不串列。
 */

const BOM = '\ufeff'

/** 单元格转义：包含逗号 / 引号 / 换行时用双引号包裹，内部引号加倍 */
function escapeCell(value) {
  const text = value === null || value === undefined ? '' : String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/** 生成 CSV 文本（表头 + 数据行，CRLF 换行） */
export function toCsv(headers, rows) {
  const lines = [headers.map(escapeCell).join(',')]
  rows.forEach((row) => lines.push(row.map(escapeCell).join(',')))
  return BOM + lines.join('\r\n')
}

/** 触发浏览器下载 */
export function downloadCsv(filename, content) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
