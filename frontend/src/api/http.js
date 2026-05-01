import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截：自动附加 Token
http.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截：统一错误处理
http.interceptors.response.use(
  (response) => {
    const data = response.data
    // 内部业务错误
    if (data.code && data.code !== 0) {
      ElMessage.error(data.message || '操作失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (error.response?.status === 403) {
      ElMessage.error('权限不足')
    } else {
      ElMessage.error(error.response?.data?.detail || '网络请求失败')
    }
    return Promise.reject(error)
  }
)

export default http
