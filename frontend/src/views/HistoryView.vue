<template>
  <div class="history-view">
    <div class="page-header">
      <div class="title-section">
        <h2 class="page-title">自动化历史</h2>
        <p class="page-subtitle">监控所有自动化工作流的运行轨迹</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="loadHistory" :loading="loading">
          刷新记录
        </el-button>
      </div>
    </div>

    <!-- 历史记录表格 -->
    <div class="glass-container">
      <el-table
        :data="historyData"
        style="width: 100%"
        v-loading="loading"
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

        <el-table-column label="任务名称" min-width="180">
          <template #default="{ row }">
            <span class="task-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="getStatusTagType(row.status)"
              size="small"
              class="status-tag"
              effect="dark"
            >
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="耗时" width="120">
          <template #default="{ row }">
            <span class="duration-text">{{ formatDuration(row.duration) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="开始时间" width="180">
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
      
      <div v-if="!historyData.length && !loading" class="empty-state">
        <el-empty description="暂无运行历史" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { automationApi } from '@/api'
import { ElMessage } from 'element-plus'

const historyData = ref([])
const loading = ref(false)

async function loadHistory() {
  loading.value = true
  try {
    const res = await automationApi.history()
    if (res.code === 0) {
      historyData.value = res.data || []
    }
  } catch (e) {
    console.error('加载历史记录失败:', e)
    ElMessage.error('加载历史数据失败')
  } finally {
    loading.value = false
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
    default: return status
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

onMounted(loadHistory)
</script>

<style lang="scss" scoped>
.history-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
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

.glass-container {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  overflow: hidden;
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

  .task-name {
    font-weight: 500;
  }

  .duration-text, .time-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
  }

  .status-tag {
    border-radius: 4px;
    border: none;
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

:deep(.el-table__expand-icon) {
  color: rgba(255, 255, 255, 0.4);
}
</style>
