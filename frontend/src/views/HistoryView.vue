<template>
  <div class="history-view">
    <div class="page-header">
      <div class="title-section">
        <h2 class="page-title">历史记录</h2>
        <p class="page-subtitle">自动化运行轨迹、文件整理与下载留痕</p>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="history-tabs" @tab-change="onTabChange">
      <el-tab-pane label="自动化运行" name="automation">
        <div class="tab-toolbar">
          <el-button :icon="Refresh" @click="loadAutomation" :loading="loadingAuto">
            刷新
          </el-button>
        </div>
        <div class="glass-container">
          <el-table
            :data="automationData"
            v-loading="loadingAuto"
            class="history-table"
            header-cell-class-name="table-header"
          >
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="detail-expand">
                  <div class="detail-label">运行消息:</div>
                  <div class="detail-content" :class="{ 'is-error': row.status === 'fail' }">
                    {{ row.message || '无详细信息' }}
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="任务名称" min-width="160">
              <template #default="{ row }">
                <span class="task-name">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)" size="small" effect="dark">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="100">
              <template #default="{ row }">
                <span class="duration-text">{{ formatDuration(row.duration) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="170">
              <template #default="{ row }">
                <span class="time-text">{{ formatTime(row.start_time) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="结果简述" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="message-text" :class="{ 'is-error': row.status === 'fail' }">
                  {{ row.message }}
                </span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!automationData.length && !loadingAuto" class="empty-state">
            <el-empty description="暂无运行历史" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="整理历史" name="transfers">
        <div class="tab-toolbar">
          <el-select v-model="transferFilter" style="width: 140px" @change="loadTransfers(1)">
            <el-option label="全部" value="all" />
            <el-option label="仅成功" value="ok" />
            <el-option label="仅失败" value="fail" />
          </el-select>
          <el-button :icon="Refresh" @click="loadTransfers(transferPage)" :loading="loadingTransfer">刷新</el-button>
        </div>
        <div class="glass-container">
          <el-table :data="transferData" v-loading="loadingTransfer" class="history-table">
            <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
            <el-table-column label="成功" width="70">
              <template #default="{ row }">
                <el-tag :type="row.success ? 'success' : 'danger'" size="small">{{ row.success ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="mode" label="模式" width="90" />
            <el-table-column prop="dest" label="目标路径" min-width="200" show-overflow-tooltip />
            <el-table-column prop="errmsg" label="失败原因" min-width="120" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>
          <el-pagination
            v-if="transferTotal > 0"
            class="pager"
            layout="total, prev, pager, next"
            :total="transferTotal"
            :page-size="pageSize"
            :current-page="transferPage"
            @current-change="loadTransfers"
          />
          <div v-if="!transferData.length && !loadingTransfer" class="empty-state">
            <el-empty description="暂无整理记录" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="下载历史" name="downloads">
        <div class="tab-toolbar">
          <el-button :icon="Refresh" @click="loadDownloads(downloadPage)" :loading="loadingDownload">刷新</el-button>
        </div>
        <div class="glass-container">
          <el-table :data="downloadData" v-loading="loadingDownload" class="history-table">
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">{{ formatBytes(row.size) }}</template>
            </el-table-column>
            <el-table-column prop="site_id" label="站点ID" width="90" />
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>
          <el-pagination
            v-if="downloadTotal > 0"
            class="pager"
            layout="total, prev, pager, next"
            :total="downloadTotal"
            :page-size="pageSize"
            :current-page="downloadPage"
            @current-change="loadDownloads"
          />
          <div v-if="!downloadData.length && !loadingDownload" class="empty-state">
            <el-empty description="暂无下载记录" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { automationApi, historyApi } from '@/api'
import { ElMessage } from 'element-plus'

const activeTab = ref('automation')
const pageSize = 20

const loadingAuto = ref(false)
const automationData = ref([])

const loadingTransfer = ref(false)
const transferData = ref([])
const transferTotal = ref(0)
const transferPage = ref(1)
const transferFilter = ref('all')
const transfersTabLoaded = ref(false)
const downloadsTabLoaded = ref(false)

const loadingDownload = ref(false)
const downloadData = ref([])
const downloadTotal = ref(0)
const downloadPage = ref(1)

async function loadAutomation() {
  loadingAuto.value = true
  try {
    const res = await automationApi.history()
    if (res.code === 0) {
      automationData.value = res.data || []
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载自动化历史失败')
  } finally {
    loadingAuto.value = false
  }
}

async function loadTransfers(page = 1) {
  transferPage.value = page
  loadingTransfer.value = true
  try {
    const params = { page, page_size: pageSize }
    if (transferFilter.value === 'ok') params.success = true
    if (transferFilter.value === 'fail') params.success = false
    const res = await historyApi.transfers(params)
    if (res.code === 0) {
      transferData.value = res.data || []
      transferTotal.value = res.total || 0
    }
  } catch (e) {
    ElMessage.error('加载整理历史失败')
  } finally {
    loadingTransfer.value = false
  }
}

async function loadDownloads(page = 1) {
  downloadPage.value = page
  loadingDownload.value = true
  try {
    const res = await historyApi.downloads({ page, page_size: pageSize })
    if (res.code === 0) {
      downloadData.value = res.data || []
      downloadTotal.value = res.total || 0
    }
  } catch (e) {
    ElMessage.error('加载下载历史失败')
  } finally {
    loadingDownload.value = false
  }
}

function onTabChange(name) {
  if (name === 'transfers' && !transfersTabLoaded.value) {
    transfersTabLoaded.value = true
    loadTransfers(1)
  }
  if (name === 'downloads' && !downloadsTabLoaded.value) {
    downloadsTabLoaded.value = true
    loadDownloads(1)
  }
}

function getStatusTagType(status) {
  switch (status) {
    case 'success': return 'success'
    case 'fail': return 'danger'
    case 'running': return 'primary'
    default: return 'info'
  }
}

function getStatusText(status) {
  switch (status) {
    case 'success': return '执行成功'
    case 'fail': return '执行失败'
    case 'running': return '进行中'
    default: return status || '-'
  }
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '-'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

function formatBytes(n) {
  if (n == null || n === 0) return '-'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(n) / Math.log(k))
  return `${parseFloat((n / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

onMounted(() => {
  loadAutomation()
})
</script>

<style lang="scss" scoped>
.history-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  .page-title {
    margin: 0;
    font-size: 24px;
    background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.7) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .page-subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255,255,255,0.45);
  }
}

.history-tabs {
  :deep(.el-tabs__item) {
    color: rgba(255,255,255,0.55);
    &.is-active { color: var(--primary); font-weight: 600; }
  }
  :deep(.el-tabs__active-bar) { background: var(--primary); }
}

.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.glass-container {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  overflow: hidden;
}

.pager {
  padding: 12px 16px;
  justify-content: flex-end;
}

.history-table {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: rgba(255, 255, 255, 0.05);
  --el-table-text-color: rgba(255, 255, 255, 0.85);

  :deep(.table-header) {
    color: rgba(255, 255, 255, 0.45);
    font-weight: 600;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
  }

  .task-name { font-weight: 500; }
  .duration-text, .time-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
  }
  .message-text {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.45);
    &.is-error { color: #f87171; }
  }
}

.detail-expand {
  padding: 16px 48px;
  background: rgba(0, 0, 0, 0.2);

  .detail-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.3);
    margin-bottom: 8px;
  }

  .detail-content {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.8;
    color: var(--text-primary);
    white-space: pre-wrap;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 4px;
    border-left: 3px solid var(--primary);

    &.is-error {
      color: #fca5a5;
      border-left-color: var(--danger);
    }
  }
}

.empty-state {
  padding: 60px 0;
}
</style>
