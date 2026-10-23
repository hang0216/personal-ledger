import axios from 'axios'

/**
 * 统一 axios 实例（front-ui §1.2）。
 * 约定：所有接口返回 { code, message, data }（api-design §2.1）。
 * - code === 0  → 直接交付 data 给业务层
 * - code !== 0  → 抛出带 code / message 的 ApiError，由页面决定展示位置
 * - 网络异常/超时 → 抛出 code=-1 的 ApiError："网络异常，请重试"（E-15）
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      return Promise.reject(new ApiError(body.code, body.message || '请求失败'))
    }
    return response.data
  },
  (error) => {
    const body = error.response?.data
    if (body && typeof body === 'object' && 'code' in body) {
      return Promise.reject(new ApiError(body.code, body.message || '请求失败'))
    }
    return Promise.reject(new ApiError(-1, '网络异常，请重试'))
  },
)

export default http