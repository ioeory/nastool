<template>
  <div class="dashboard">
    <div v-if="sysInfo" class="sys-info-strip">
      <span class="app">{{ sysInfo.app_name }}</span>
      <span class="meta">v{{ sysInfo.version }} · {{ sysInfo.db_type }}</span>
      <span class="meta platform" :title="sysInfo.platform">{{ shortPlatform }}</span>
    </div>

    <!-- 实时看板 -->
    <div class="stat-grid speed-grid">
      <div class="stat-card speed-card down">
        <div class="speed-info">
          <div class="label">当前下载</div>
          <div class="value">{{ formatSpeed(speed.dl) }}</div>
        </div>
        <el-icon class="speed-bg-icon"><Download /></el-icon>
      </div>
      <div class="stat-card speed-card up">
        <div class="speed-info">
          <div class="label">当前上传</div>
          <div class="value">{{ formatSpeed(speed.ul) }}</div>
        </div>
        <el-icon class="speed-bg-icon"><Upload /></el-icon>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-icon" :style="{ background: stat.color }">
          <el-icon :size="22"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- 中下部内容 -->
    <div class="section-grid">
      <!-- 站点状态 -->
      <div class="page-card">
        <div class="page-header">
          <h2>站点状态</h2>
          <el-button link type="primary" @click="$router.push('/site')">查看详情</el-button>
        </div>
        <div v-if="sites.length === 0" class="empty-tip">
          <el-empty description="暂无站点" :image-size="60" />
        </div>
        <div v-else class="site-status-list">
          <div class="site-status-item" v-for="site in sites.slice(0, 6)" :key="site.id">
            <div class="site-dot" :class="site.is_active ? 'active' : 'inactive'" />
            <span class="site-name">{{ site.name }}</span>
            <span class="checkin-time">{{ site.last_checkin ? site.last_checkin.split(' ')[0] : '从未签到' }}</span>
          </div>
        </div>
      </div>

      <!-- 最近活动 -->
      <div class="page-card">
        <div class="page-header">
          <h2>最近活动</h2>
          <el-button link type="primary" @click="$router.push('/history')">所有记录</el-button>
        </div>
        <div v-if="recentHistory.length === 0" class="empty-tip">
          <el-empty description="暂无记录" :image-size="60" />
        </div>
        <div v-else class="history-list">
          <div class="history-item" v-for="h in recentHistory.slice(0, 6)" :key="h.id">
            <div class="h-main">
              <span class="h-name">{{ h.name }}</span>
              <el-tag :type="activityTagType(h.status)" size="small">
                {{ activityStatusText(h.status) }}
              </el-tag>
            </div>
            <div class="h-time">{{ formatActivityTime(h) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Monitor, Bell, List,
  Download, Upload, Timer, Clock
} from '@element-plus/icons-vue'
import { siteApi, systemApi, downloaderApi, automationApi } from '@/api'

const loading = ref(false)
const sites = ref([])
const recentHistory = ref([])
const speed = ref({ dl: 0, ul: 0 })
const sysInfo = ref(null)

const shortPlatform = computed(() => {
  const p = sysInfo.value?.platform || ''
  return p.length > 48 ? `${p.slice(0, 48)}…` : p
})

const stats = ref([
  { key: 'active_sites', label: '活跃站点', value: 0, icon: 'Monitor', color: 'linear-gradient(135deg,#6366f1,#8b5cf6)' },
  { key: 'total_subscribes', label: '全部规则', value: 0, icon: 'Bell', color: 'linear-gradient(135deg,#f59e0b,#ef4444)' },
  { key: 'today_transfers', label: '今日整理', value: 0, icon: 'Clock', color: 'linear-gradient(135deg,#22c55e,#16a34a)' },
  { key: 'total_transfers', label: '累计整理', value: 0, icon: 'List', color: 'linear-gradient(135deg,#14b8a6,#0d9488)' },
  { key: 'total_downloads', label: '累计下载', value: 0, icon: 'Download', color: 'linear-gradient(135deg,#3b82f6,#2563eb)' },
])

let timer = null

onMounted(async () => {
  fetchData()
  // 3秒轮询一次速度和基础状态
  timer = setInterval(() => {
    fetchSpeed()
  }, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

async function fetchData() {
  // 1. 基础统计
  try {
    const res = await systemApi.getStats()
    if (res.data) {
      stats.value.forEach(s => {
        if (res.data[s.key] !== undefined) s.value = res.data[s.key]
      })
    }
  } catch {}

  try {
    const infoRes = await systemApi.info()
    if (infoRes.data) sysInfo.value = infoRes.data
  } catch {}

  // 2. 站点列表
  try {
    const res = await siteApi.list()
    sites.value = res.data || []
  } catch {}

  // 3. 最近历史
  try {
    const res = await automationApi.history()
    recentHistory.value = res.data || []
  } catch {}

  fetchSpeed()
}

async function fetchSpeed() {
  try {
    const res = await downloaderApi.getSpeed()
    if (res.data) {
      speed.value.dl = res.data.dl_speed
      speed.value.ul = res.data.ul_speed
    }
  } catch {}
}

function formatSpeed(bps) {
  if (!bps) return '0 B/s'
  const k = 1024
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  const i = Math.floor(Math.log(bps) / Math.log(k))
  return parseFloat((bps / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatTime(t) {
  if (!t) return ''
  const date = new Date(t)
  return `${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')}:${date.getSeconds().toString().padStart(2,'0')}`
}

function activityTagType(status) {
  if (status === 'success') return 'success'
  if (status === 'fail') return 'danger'
  if (status === 'running') return 'primary'
  return 'info'
}

function activityStatusText(status) {
  if (status === 'success') return '完成'
  if (status === 'fail') return '失败'
  if (status === 'running') return '进行中'
  return status || '-'
}

function formatActivityTime(h) {
  const t = h.end_time || h.start_time
  return formatTime(t)
}
</script>

<style lang="scss" scoped>
.dashboard { display: flex; flex-direction: column; gap: 24px; }

.sys-info-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 16px;
  padding: 10px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 13px;
  color: var(--text-secondary);
  .app { font-weight: 600; color: var(--text-primary); }
  .meta { color: var(--text-muted); }
  .platform { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  @media (max-width: 1200px) { grid-template-columns: repeat(3, 1fr); }
  @media (max-width: 800px) { grid-template-columns: repeat(2, 1fr); }
}

.speed-grid {
  grid-template-columns: repeat(2, 1fr);
}

.speed-card {
  height: 100px;
  padding: 0 30px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  border: none;
  
  &.down { background: linear-gradient(135deg, #10b981, #059669); }
  &.up { background: linear-gradient(135deg, #3b82f6, #2563eb); }

  .speed-info {
    z-index: 2;
    .label { font-size: 14px; color: rgba(255,255,255,0.8); margin-bottom: 4px; }
    .value { font-size: 28px; font-weight: 800; color: #fff; font-family: 'Inter', sans-serif; }
  }

  .speed-bg-icon {
    position: absolute;
    right: -10px;
    bottom: -10px;
    font-size: 80px;
    color: rgba(255,255,255,0.15);
    transform: rotate(-15deg);
  }
}

.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
  &:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
}

.stat-icon {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0;
}

.stat-value { font-size: 26px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

.section-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  @media (max-width: 900px) { grid-template-columns: 1fr; }
}

.page-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
  h2 { font-size: 18px; color: #fff; margin: 0; }
}

.site-status-list, .history-list { display: flex; flex-direction: column; gap: 8px; }

.site-status-item, .history-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 10px;
  transition: background 0.2s;
  &:hover { background: rgba(255,255,255,0.05); }
}

.site-dot {
  width: 8px; height: 8px; border-radius: 50%; 
  &.active { background: #10b981; box-shadow: 0 0 8px #10b981; }
  &.inactive { background: #ef4444; }
}

.site-name, .h-name { flex: 1; color: var(--text-secondary); font-size: 13px; font-weight: 500; }
.checkin-time, .h-time { font-size: 12px; color: var(--text-muted); }

.history-item {
  flex-direction: column; align-items: flex-start; gap: 4px;
  .h-main { display: flex; width: 100%; justify-content: space-between; align-items: center; }
}
</style>
