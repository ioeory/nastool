<template>
  <div class="site-view">
    <!-- 工具栏 -->
    <div class="page-card toolbar-card">
      <div class="toolbar">
        <h2 class="toolbar-title">站点管理</h2>
        <div class="toolbar-actions">
          <el-button :icon="Refresh" @click="loadSites" :loading="loading">刷新</el-button>
          <el-button :icon="Connection" @click="syncCookieCloud">同步 CookieCloud</el-button>
          <el-button :icon="Calendar" @click="checkinAll" :loading="checkinAllLoading">一键签到</el-button>
          <el-button type="primary" :icon="Plus" @click="openAddDialog">添加站点</el-button>
        </div>
      </div>
    </div>

    <!-- 站点列表 -->
    <div class="page-card">
      <el-table
        :data="sites"
        v-loading="loading"
        row-key="id"
        class="site-table"
      >
        <el-table-column label="站点名" min-width="140">
          <template #default="{ row }">
            <div class="site-name-cell">
              <div class="site-indicator" :class="row.is_active ? 'active' : 'inactive'" />
              <span>{{ row.name }}</span>
              <el-tag v-if="row.public" type="info" size="small">公开</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="domain" label="域名" min-width="180">
          <template #default="{ row }">
            <a :href="row.url" target="_blank" class="domain-link">{{ row.domain }}</a>
          </template>
        </el-table-column>
        <el-table-column label="配置" width="140">
          <template #default="{ row }">
            <div class="config-tags">
              <el-tag v-if="row.proxy" type="warning" size="small">代理</el-tag>
              <el-tag v-if="row.render" type="danger" size="small">渲染</el-tag>
              <el-tag size="small" type="info">优先级 {{ row.pri }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="(val) => toggleActive(row, val)"
              size="small"
            />
          </template>
        </el-table-column>
        <el-table-column label="上次签到" width="140">
          <template #default="{ row }">
            <span v-if="row.last_checkin" class="checkin-time">{{ row.last_checkin }}</span>
            <span v-else class="no-checkin">未签到</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button-group size="small">
              <el-button @click="checkinSite(row)" :loading="checkinIds.has(row.id)">签到</el-button>
              <el-button @click="testSite(row)" :loading="testingIds.has(row.id)">测试</el-button>
              <el-button @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" @click="deleteSite(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑站点对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑站点' : '添加站点'"
      width="520px"
      class="site-dialog"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="站点地址" prop="url">
          <el-input v-model="form.url" placeholder="https://pt.example.com" />
        </el-form-item>
        <el-form-item label="Cookie">
          <el-input
            v-model="form.cookie"
            type="textarea"
            :rows="3"
            :placeholder="editingId ? '留空表示保留当前 Cookie，不修改' : '粘贴站点 Cookie（与 API Key 二选一）'"
          />
          <span v-if="editingId" class="form-tip">出于安全，编辑时不显示已保存的 Cookie；留空提交不会清空。</span>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="form.apikey"
            :placeholder="editingId ? '留空表示保留当前 API Key' : 'M-Team 等支持 API Key 的站点'"
          />
          <span v-if="editingId" class="form-tip">留空提交不会清空已保存的 Key。</span>
        </el-form-item>
        <el-form-item label="User-Agent">
          <el-input v-model="form.ua" placeholder="留空使用默认" />
        </el-form-item>
        <el-form-item label="RSS 地址">
          <el-input v-model="form.rss" placeholder="自动获取，一般无需填写" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.pri" :min="1" :max="100" />
          <span class="form-tip">数字越小搜索优先级越高</span>
        </el-form-item>
        <el-form-item label="代理">
          <el-switch v-model="form.proxy" />
        </el-form-item>
        <el-form-item label="浏览器渲染">
          <el-switch v-model="form.render" />
          <span class="form-tip">Cloudflare 站点需要开启</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" placeholder="可选备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ editingId ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Refresh, Connection, Calendar } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { siteApi } from '@/api'

const sites = ref([])
const loading = ref(false)
const testingIds = ref(new Set())
const checkinIds = ref(new Set())
const checkinAllLoading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const formRef = ref()

const form = reactive({
  url: '', cookie: '', apikey: '', ua: '', rss: '',
  pri: 50, proxy: false, render: false, note: '',
})

const rules = {
  url: [{ required: true, message: '请输入站点地址', trigger: 'blur' }],
}

async function loadSites() {
  loading.value = true
  try {
    const res = await siteApi.list()
    sites.value = res.data || []
  } catch { ElMessage.error('加载站点列表失败') }
  finally { loading.value = false }
}

function openAddDialog() {
  editingId.value = null
  Object.assign(form, { url: '', cookie: '', apikey: '', ua: '', rss: '', pri: 50, proxy: false, render: false, note: '' })
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  Object.assign(form, { url: row.url, cookie: '', apikey: '', ua: row.ua || '', rss: row.rss || '', pri: row.pri, proxy: row.proxy, render: row.render, note: row.note || '' })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value?.validate()
  submitting.value = true
  try {
    if (editingId.value) {
      const payload = { ...form }
      if (!String(payload.cookie || '').trim()) delete payload.cookie
      if (!String(payload.apikey || '').trim()) delete payload.apikey
      await siteApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await siteApi.add(form)
      ElMessage.success('站点添加成功')
    }
    dialogVisible.value = false
    await loadSites()
  } catch {}
  finally { submitting.value = false }
}

async function testSite(row) {
  testingIds.value.add(row.id)
  try {
    const res = await siteApi.test(row.id)
    const result = res.data
    if (result.success) {
      ElMessage.success(`${row.name} 连接成功（${result.latency_ms}ms）`)
    } else {
      ElMessage.error(`${row.name} 连接失败: ${result.message}`)
    }
  } catch {}
  finally { testingIds.value.delete(row.id) }
}

async function toggleActive(row, val) {
  try {
    await siteApi.update(row.id, { is_active: val })
  } catch { row.is_active = !val }
}

async function deleteSite(row) {
  await ElMessageBox.confirm(`确定删除站点【${row.name}】吗？`, '警告', { type: 'warning' })
  await siteApi.delete(row.id)
  ElMessage.success('删除成功')
  await loadSites()
}

async function syncCookieCloud() {
  try {
    await siteApi.syncCookieCloud()
    ElMessage.success('CookieCloud 同步已在后台启动')
  } catch {}
}

async function checkinSite(row) {
  checkinIds.value.add(row.id)
  try {
    const res = await siteApi.checkin(row.id)
    const result = res.data
    if (result?.success) {
      ElMessage.success(`${row.name} 签到成功: ${result.message}`)
      row.last_checkin = new Date().toLocaleString('zh-CN', { hour12: false })
    } else {
      ElMessage.warning(`${row.name} 签到失败: ${result?.message || '未知原因'}`)
    }
  } catch (e) {
    ElMessage.error(`${row.name} 签到异常`)
  } finally {
    checkinIds.value.delete(row.id)
  }
}

async function checkinAll() {
  checkinAllLoading.value = true
  try {
    await siteApi.checkinAll()
    ElMessage.success('批量签到已在后台启动，请查看日志')
    // 稍候刷新列表获取签到时间
    setTimeout(loadSites, 3000)
  } catch {} finally {
    checkinAllLoading.value = false
  }
}

onMounted(loadSites)
</script>

<style lang="scss" scoped>
.site-view { display: flex; flex-direction: column; gap: 16px; }

.toolbar-card { padding: 16px 24px; }
.toolbar {
  display: flex; align-items: center;
  .toolbar-title { font-size: 18px; font-weight: 600; flex: 1; }
  .toolbar-actions { display: flex; gap: 8px; }
}

.site-name-cell {
  display: flex; align-items: center; gap: 8px;
}
.site-indicator {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  &.active { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
  &.inactive { background: #ef4444; }
}
.domain-link {
  color: #6366f1; text-decoration: none;
  &:hover { text-decoration: underline; }
}
.config-tags { display: flex; gap: 4px; flex-wrap: wrap; }

.form-tip { margin-left: 8px; color: var(--text-muted); font-size: 12px; }

.checkin-time { font-size: 12px; color: #22c55e; }
.no-checkin { font-size: 12px; color: rgba(255,255,255,0.25); font-style: italic; }

:deep(.site-table) {
  .el-table__row { cursor: default; }
}

:deep(.site-dialog) {
  .el-dialog { background: var(--bg-surface); border: 1px solid var(--border); }
  .el-dialog__title { color: var(--text-primary); }
}
</style>
