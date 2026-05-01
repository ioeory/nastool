import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/views/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' },
      },
      {
        path: 'site',
        name: 'Site',
        component: () => import('@/views/SiteView.vue'),
        meta: { title: '站点管理', icon: 'Monitor' },
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/SearchView.vue'),
        meta: { title: '搜索', icon: 'Search' },
      },
      {
        path: 'subscribe',
        name: 'Subscribe',
        component: () => import('@/views/SubscribeView.vue'),
        meta: { title: '订阅', icon: 'Bell' },
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryView.vue'),
        meta: { title: '历史记录', icon: 'List' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: '系统设置', icon: 'Setting' },
      },
      {
        path: 'downloader',
        name: 'Downloader',
        component: () => import('@/views/DownloaderView.vue'),
        meta: { title: '下载器与节点', icon: 'Connection' },
      },
      {
        path: 'explore',
        name: 'Explore',
        component: () => import('@/views/ExploreView.vue'),
        meta: { title: '探索', icon: 'Compass' },
      },
      {
        path: 'workflow',
        name: 'Workflow',
        component: () => import('@/views/WorkflowView.vue'),
        meta: { title: '自动化任务', icon: 'Operation' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局导航守卫
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth !== false && !authStore.token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.token) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
