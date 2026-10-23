/**
 * 错误码 → 前端提示位置映射（严格对齐 api-design §2.2 与 front-ui §1.3）。
 * 返回 { field, message }：field 为表单字段名（null 表示顶部/全局提示）。
 */
export function resolveFieldError(err) {
  const message = err?.message || '操作失败'
  switch (err?.code) {
    case 1001:
      if (message.includes('备注')) return { field: 'note', message }
      if (message.includes('分类名称')) return { field: 'name', message }
      return { field: null, message }
    case 1002:
    case 1003:
      return { field: 'amount', message }
    case 1004:
      return { field: 'date', message }
    case 1005:
      return { field: 'month', message }
    case 1006:
    case 1007:
      return { field: 'category_id', message }
    case 1009:
      return { field: 'name', message }
    case 1008:
      return { field: null, message, refresh: true, close: true }
    case 1010:
      return { field: null, message, refresh: true }
    default:
      return { field: null, message }
  }
}