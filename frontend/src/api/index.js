import http from './http'

// ---- 认证 ----
export const authApi = {
  login: (username, password) => {
    const form = new FormData()
    form.append('username', username)
    form.append('password', password)
    return http.post('/auth/login', form)
  },
  me: () => http.get('/auth/me'),
}

// ---- 站点管理 ----
export const siteApi = {
  list: (activeOnly = false) => http.get('/site/', { params: { active_only: activeOnly } }),
  get: (id) => http.get(`/site/${id}`),
  add: (data) => http.post('/site/', data),
  update: (id, data) => http.patch(`/site/${id}`, data),
  delete: (id) => http.delete(`/site/${id}`),
  test: (id) => http.post(`/site/${id}/test`),
  registryList: () => http.get('/site/registry/list'),
  syncCookieCloud: () => http.post('/site/cookiecloud/sync'),
  checkin: (id) => http.post(`/site/${id}/checkin`),
  checkinAll: () => http.post('/site/checkin/all'),
}

// ---- 系统 ----
export const systemApi = {
  info: () => http.get('/system/info'),
  health: () => http.get('/system/health'),
  getSettings: () => http.get('/system/settings'),
  saveSettings: (data) => http.post('/system/settings', data),
  getStats: () => http.get('/system/stats'),
  testQb: (data) => http.post('/system/test_qb', data),
  testNotification: (data) => http.post('/system/test_notification', data),
}

// ---- 搜索与下载 ----
export const searchApi = {
  search: (keyword, page = 1) => http.post('/search/', { keyword, page }),
  download: (item, savePath, category) => http.post('/search/download', { item, save_path: savePath, category }),
}
// ---- 下载器 ----
export const downloaderApi = {
  list: (activeOnly = false) => http.get('/downloader/', { params: { active_only: activeOnly } }),
  add: (data) => http.post('/downloader/', data),
  update: (id, data) => http.patch(`/downloader/${id}`, data),
  delete: (id) => http.delete(`/downloader/${id}`),
  test: (id) => http.post(`/downloader/${id}/test`),
  getSpeed: () => http.get('/downloader/speed'),
}

// ---- 订阅 ----
export const subscribeApi = {
  list: () => http.get('/subscribe/'),
  add: (data) => http.post('/subscribe/', data),
  update: (id, data) => http.patch(`/subscribe/${id}`, data),
  delete: (id) => http.delete(`/subscribe/${id}`),
}
export const automationApi = {
  list: () => http.get('/automation/'),
  history: (id) => http.get('/automation/history', { params: { automation_id: id } }),
  add: (data) => http.post('/automation/', data),
  run: (id) => http.post(`/automation/${id}/run`),
  toggle: (id) => http.post(`/automation/${id}/toggle`),
  update: (id, data) => http.patch(`/automation/${id}`, data),
  delete: (id) => http.delete(`/automation/${id}`),
}

export { tmdbApi } from './tmdb'
