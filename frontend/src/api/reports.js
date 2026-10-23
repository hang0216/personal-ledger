import http from './http'

/**
 * GET /api/reports/monthly?month=YYYY-MM（api-design §3.8）
 * data: { month, total_income, total_expense, balance, expense_by_category[] }
 * percentage 由后端唯一计算，前端不重算（spec §6.3、AC-12）。
 */
export function getMonthlyReport(month) {
  return http.get('/reports/monthly', { params: { month } })
}