import http from './http'

/**
 * GET /api/transactions（api-design §3.1 + 选做功能 2 搜索）
 * - 普通模式：month + type + category_id
 * - 搜索模式：startDate / endDate / keyword 任一存在时跨月查询，month 不生效
 */
export function listTransactions({
  month,
  type,
  categoryId,
  startDate,
  endDate,
  keyword,
} = {}) {
  const params = {}
  if (month) params.month = month
  if (type) params.type = type
  if (categoryId) params.category_id = categoryId
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  if (keyword) params.keyword = keyword
  return http.get('/transactions', { params })
}

/** POST /api/transactions（api-design §3.2） */
export function createTransaction(payload) {
  return http.post('/transactions', payload)
}

/** PUT /api/transactions/{id}（全量覆盖，api-design §3.3） */
export function updateTransaction(id, payload) {
  return http.put(`/transactions/${id}`, payload)
}

/** DELETE /api/transactions/{id}（api-design §3.4，成功返回 data=null） */
export function deleteTransaction(id) {
  return http.delete(`/transactions/${id}`)
}
