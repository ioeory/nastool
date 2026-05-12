<template>
  <div class="workflow-container">
    <div class="header">
      <div class="title-section">
        <h2 class="view-title">自动化任务</h2>
        <p class="subtitle">管理系统的定时任务与后台工作流</p>
      </div>
      <div class="actions">
        <el-button type="primary" :icon="Plus" @click="handleAdd">添加任务</el-button>
        <el-button :icon="Refresh" circle @click="fetchData" />
      </div>
    </div>

    <!-- 任务卡片网格 -->
    <el-row :gutter="20" class="workflow-grid">
      <el-col v-for="auto in automations" :key="auto.id" :xs="24" :sm="12" :md="8" :lg="8" :xl="6">
        <el-card class="workflow-card" :body-style="{ padding: '0px' }">
          <div class="card-content">
            <div class="card-header">
              <div class="type-icon" :class="auto.type">
                <el-icon v-if="auto.type === 'transfer'"><Switch /></el-icon>
                <el-icon v-else-if="auto.type === 'subscribe'"><Bell /></el-icon>
                <el-icon v-else-if="auto.type === 'brush'"><Connection /></el-icon>
                <el-icon v-else-if="auto.type === 'site_checkin' || auto.type === 'site_check'"><Calendar /></el-icon>
                <el-icon v-else><Operation /></el-icon>
              </div>
              <div class="header-info">
                <h3>{{ auto.name }}</h3>
                <el-tag :type="auto.is_active ? 'success' : 'info'" size="small" effect="dark">
                  {{ auto.is_active ? '已启用' : '已停用' }}
                </el-tag>
              </div>
              <el-switch v-model="auto.is_active" @change="handleToggle(auto)" />
            </div>

            <p class="description">{{ auto.description || '暂无描述' }}</p>

            <div class="stats">
              <div class="stat-item">
                <span class="label">执行周期</span>
                <span class="value">{{ formatTrigger(auto) }}</span>
              </div>
              <div class="stat-item">
                <span class="label">上次运行</span>
                <span class="value">{{ formatTime(auto.last_run) }}</span>
              </div>
              <div class="stat-item">
                <span class="label">下次运行</span>
                <span class="value accent">{{ formatTime(auto.next_run) }}</span>
              </div>
            </div>

            <div class="card-actions">
              <el-button type="primary" size="small" :icon="CaretRight" @click="handleRun(auto)">运行</el-button>
              <el-button size="small" :icon="Setting" @click="handleEdit(auto)">配置</el-button>
              <el-button size="small" :icon="Timer" @click="showHistory(auto)">历史</el-button>
              <el-button type="danger" size="small" plain :icon="Delete" @click="handleDelete(auto)" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行历史抽屉 -->
    <el-drawer v-model="historyVisible" :title="selectedTaskName ? `【${selectedTaskName}】运行历史` : '任务运行历史'" size="45%">
      <el-table :data="history" style="width: 100%" class="history-mini-table">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="mini-detail">
              <div class="detail-label">执行详情:</div>
              <div class="detail-content">{{ row.message || '无' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="任务名称" width="120" />
        <el-table-column prop="start_time" label="开始时间" width="160">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small" effect="dark">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="简述" show-overflow-tooltip />
      </el-table>
    </el-drawer>

<!-- 任务配置对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑任务' : '创建新任务'"
      :width="form.type === 'brush' ? '680px' : '480px'"
      append-to-body
      destroy-on-close
    >
      <el-form :model="form" label-width="80px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="14">
            <el-form-item label="任务名称" required>
              <el-input v-model="form.name" placeholder="起个名字" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="任务类型" required>
              <el-select v-model="form.type">
                <el-option label="文件整理" value="transfer" />
                <el-option label="订阅检查" value="subscribe" />
                <el-option label="站点刷流" value="brush" />
                <el-option label="站点签到" value="site_checkin" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="任务描述">
          <el-input v-model="form.description" type="textarea" placeholder="该任务负责什么工作..." />
        </el-form-item>

        <el-divider content-position="left">调度配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="触发方式" required>
              <el-select v-model="form.trigger">
                <el-option label="间隔执行" value="interval" />
                <el-option label="Cron定时" value="cron" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item v-if="form.trigger === 'interval'" label="间隔时间" required>
              <div style="display: flex; gap: 8px; width: 100%;">
                <el-input-number v-model="form.trigger_config.interval_value" :min="1" style="flex: 1;" />
                <el-select v-model="form.trigger_config.interval_unit" style="width: 120px;">
                  <el-option label="分钟" value="minutes" />
                  <el-option label="小时" value="hours" />
                  <el-option label="秒" value="seconds" />
                </el-select>
              </div>
            </el-form-item>
            <el-form-item v-if="form.trigger === 'cron'" label="Cron 表达式" required>
              <el-input v-model="form.trigger_config.cron" placeholder="0 0 * * *" />
            </el-form-item>
          </el-col>
        </el-row>

        <template v-if="form.type === 'site_checkin'">
          <el-divider content-position="left">签到任务配置</el-divider>
          <el-form-item label="目标站点（留空表示全部启用站点）">
            <el-select
              v-model="form.task_config.sites"
              multiple
              filterable
              clearable
              collapse-tags
              collapse-tags-tooltip
              placeholder="可选：指定签到站点"
              style="width: 100%;"
            >
              <el-option
                v-for="site in siteOptions"
                :key="site.id"
                :label="`${site.name} (${site.domain})`"
                :value="site.id"
              />
            </el-select>
          </el-form-item>
        </template>

        <!-- 针对刷流任务的特殊配置 -->
        <template v-if="form.type === 'brush'">
          <el-divider content-position="left">刷流业务配置</el-divider>
          <BrushConfig 
            :key="editingId || 'new'"
            v-model="form.task_config" 
          />
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Refresh, CaretRight, Setting, Switch, Bell, Operation, Timer, Delete, Connection } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { automationApi, siteApi } from '@/api'
import dayjs from 'dayjs'
import BrushConfig from './components/BrushConfig.vue'

const automations = ref([])
const history = ref([])
const historyVisible = ref(false)
const selectedTaskName = ref('')
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const siteOptions = ref([])

const form = reactive({
  name: '',
  description: '',
  type: 'transfer',
  trigger: 'interval',
  trigger_config: { interval_value: 30, interval_unit: 'minutes', cron: '0 0 * * *' },
  task_config: {},
  is_active: true
})

async function fetchData() {
  try {
    const res = await automationApi.list()
    automations.value = res.data
  } catch (err) {
    ElMessage.error('加载任务列表失败')
  }
}

async function loadSiteOptions() {
  try {
    const res = await siteApi.list(true)
    siteOptions.value = res.data || []
  } catch {
    siteOptions.value = []
  }
}

function normalizeTriggerConfig(trigger, triggerConfig) {
  const base = triggerConfig || {}
  if (trigger !== 'interval') {
    return {
      interval_value: 30,
      interval_unit: 'minutes',
      cron: base.cron || '0 0 * * *',
    }
  }
  if (Number(base.minutes) > 0) {
    return {
      interval_value: Number(base.minutes),
      interval_unit: 'minutes',
      cron: base.cron || '0 0 * * *',
    }
  }
  if (Number(base.hours) > 0) {
    return {
      interval_value: Number(base.hours),
      interval_unit: 'hours',
      cron: base.cron || '0 0 * * *',
    }
  }
  if (Number(base.seconds) > 0) {
    return {
      interval_value: Number(base.seconds),
      interval_unit: 'seconds',
      cron: base.cron || '0 0 * * *',
    }
  }
  return {
    interval_value: 30,
    interval_unit: 'minutes',
    cron: base.cron || '0 0 * * *',
  }
}

function handleAdd() {
  editingId.value = null
  Object.assign(form, {
    name: '', description: '', type: 'transfer', trigger: 'interval',
    trigger_config: { interval_value: 30, interval_unit: 'minutes', cron: '0 0 * * *' },
    task_config: {}, is_active: true
  })
  dialogVisible.value = true
}

function handleEdit(auto) {
  editingId.value = auto.id
  Object.assign(form, {
    name: auto.name,
    description: auto.description,
    type: auto.type,
    trigger: auto.trigger,
    trigger_config: normalizeTriggerConfig(auto.trigger, JSON.parse(JSON.stringify(auto.trigger_config || {}))),
    task_config: JSON.parse(JSON.stringify(auto.task_config || {})),
    is_active: auto.is_active
  })
  if (form.type === 'site_checkin') {
    form.task_config = {
      ...(form.task_config || {}),
      sites: Array.isArray(form.task_config?.sites) ? form.task_config.sites : [],
    }
  }
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.name) return ElMessage.warning('名称必填')
  
  submitting.value = true
  try {
    // 深度克隆并清理配置，防止参数冲突
    const payload = JSON.parse(JSON.stringify(form))
    if (payload.trigger === 'interval') {
      const unit = payload.trigger_config?.interval_unit || 'minutes'
      const value = Number(payload.trigger_config?.interval_value || 0)
      payload.trigger_config = {
        [unit]: value > 0 ? value : 30,
      }
    } else if (payload.trigger === 'cron') {
      payload.trigger_config = { cron: payload.trigger_config.cron }
    }

    // 刷流：确保 task_config.feed_source 写入后端（避免单选未绑定导致永远走搜索 API）
    if (payload.type === 'brush' && payload.task_config) {
      const tc = payload.task_config
      if (tc.feed_source !== 'rss' && tc.feed_source !== 'search') {
        tc.feed_source = ((tc.rss_url || '').trim() || tc.use_rss) ? 'rss' : 'search'
      }
    }

    if (payload.type === 'site_checkin') {
      payload.task_config = payload.task_config || {}
      payload.task_config.sites = Array.isArray(payload.task_config.sites)
        ? payload.task_config.sites.map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
        : []
    }

    if (editingId.value) {
      await automationApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await automationApi.add(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(auto) {
  try {
    await ElMessageBox.confirm(`确定删除任务【${auto.name}】吗？`, '警告', { type: 'warning' })
    await automationApi.delete(auto.id)
    ElMessage.success('已删除')
    fetchData()
  } catch {}
}

async function handleToggle(auto) {
  try {
    await automationApi.toggle(auto.id)
    ElMessage.success('状态已更新')
    await fetchData()
  } catch {
    auto.is_active = !auto.is_active
    ElMessage.error('操作失败')
  }
}

async function handleRun(auto) {
  try {
    const res = await automationApi.run(auto.id)
    ElMessage.success(res.message || '任务启动成功')
  } catch {
    ElMessage.error('任务启动失败')
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
    case 'success': return '成功'
    case 'fail': return '失败'
    case 'running': return '执行中'
    default: return status
  }
}

async function showHistory(auto) {
  try {
    selectedTaskName.value = auto.name
    const res = await automationApi.history(auto.id)
    history.value = res.data
    historyVisible.value = true
  } catch {
    ElMessage.error('获取历史记录失败')
  }
}

function formatTrigger(auto) {
  if (auto.trigger === 'interval') {
    if (auto.trigger_config?.hours) return `每 ${auto.trigger_config.hours} 小时`
    if (auto.trigger_config?.seconds) return `每 ${auto.trigger_config.seconds} 秒`
    return `每 ${auto.trigger_config?.minutes || 30} 分钟`
  }
  if (auto.trigger === 'cron') return `Cron: ${auto.trigger_config?.cron}`
  return '手动'
}

function formatTime(val) {
  return val ? dayjs(val).format('MM-DD HH:mm:ss') : '-'
}

onMounted(async () => {
  await Promise.all([fetchData(), loadSiteOptions()])
})
</script>

<style lang="scss" scoped>
.workflow-container { max-width: 1400px; margin: 0 auto; }
.header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;
  .view-title { font-size: 28px; font-weight: 700; margin: 0; color: #fff; }
  .subtitle { color: rgba(255,255,255,0.5); font-size: 14px; margin-top: 5px; }
}

.workflow-grid { margin-top: 20px; }

.workflow-card {
  background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px;
  margin-bottom: 20px; transition: all 0.3s;
  &:hover { transform: translateY(-5px); border-color: #6366f1; }
  .card-content { padding: 20px; }
}

.card-header {
  display: flex; align-items: flex-start; gap: 12px; margin-bottom: 15px;
  .type-icon {
    width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px;
    &.transfer { background: rgba(99, 102, 241, 0.2); color: #818cf8; }
    &.subscribe { background: rgba(236, 72, 153, 0.2); color: #f472b6; }
    &.brush { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
  }
  .header-info { flex: 1; h3 { margin: 0 0 5px 0; font-size: 16px; color: #fff; } .page-subtitle {
    font-size: 14px;
    color: var(--text-muted);
  }
}

/* 历史抽屉详情样式 */
.mini-detail {
  padding: 16px 24px;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
  border-left: 4px solid var(--primary);
  margin: 4px 0;
  border-radius: 0 8px 8px 0;

  .detail-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
    opacity: 0.8;
    
    &::after {
      content: 'INFO';
      font-size: 9px;
      padding: 1px 4px;
      background: rgba(99, 102, 241, 0.2);
      border-radius: 3px;
    }
  }
  .detail-content {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-primary);
    white-space: pre-wrap;
    letter-spacing: 0.2px;
  }
}
}

.description { color: rgba(255,255,255,0.4); font-size: 13px; margin-bottom: 20px; height: 36px; overflow: hidden; }

.stats {
  background: rgba(0, 0, 0, 0.2); border-radius: 8px; padding: 12px; margin-bottom: 20px;
  .stat-item {
    display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;
    .label { color: rgba(255,255,255,0.3); }
    .value { color: #fff; &.accent { color: #818cf8; font-weight: 600; } }
  }
}

.card-actions { display: flex; gap: 6px; }
</style>
