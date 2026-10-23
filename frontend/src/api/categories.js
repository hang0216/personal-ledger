import http from './http'

/** GET /api/categories?type=（api-design §3.5，排序：type 升序、id 升序） */
export function listCategories(type) {
  const params = type ? { type } : {}
  return http.get('/categories', { params })
}

/** POST /api/categories（api-design §3.6） */
export function createCategory(payload) {
  return http.post('/categories', payload)
}

/** DELETE /api/categories/{id}（api-design §3.7，成功返回 data=null） */
export function deleteCategory(id) {
  return http.delete(`/categories/${id}`)
}