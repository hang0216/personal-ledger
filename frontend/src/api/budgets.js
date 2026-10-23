import http from './http'

/** GET /api/budgets?month=YYYY-MM（选做功能 1；未设置时 amount=null） */
export function getBudget(month) {
  const params = {}
  if (month) params.month = month
  return http.get('/budgets', { params })
}

/** PUT /api/budgets（设置或覆盖月度预算，金额单位为元） */
export function setBudget(payload) {
  return http.put('/budgets', payload)
}
