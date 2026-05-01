<template>
  <div class="downloader-view">
    <!-- 工具栏 -->
    <div class="page-card toolbar-card">
      <div class="toolbar">
        <h2 class="toolbar-title">下载器管理</h2>
        <div class="toolbar-actions">
          <el-button :icon="Refresh" @click="loadDownloaders" :loading="loading">刷新</el-button>
          <el-button type="primary" :icon="Plus" @click="openAddDialog">添加下载器</el-button>
        </div>
      </div>
    </div>

    <!-- 列表 -->
    <div class="page-card">
      <el-table
        :data="downloaders"
        v-loading="loading"
        row-key="id"
        class="dl-table"
      >
        <el-table-column label="节点名称" min-width="120">
          <template #default="{ row }">
            <div class="name-cell">
              <div class="indicator" :class="row.is_active ? 'active' : 'inactive'" />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="客户端类型" min-width="120">
          <template #default="{ row }">
            <el-tag :type="row.client_type === 'qbittorrent' ? 'success' : 'danger'" size="small">
              {{ row.client_type === 'qbittorrent' ? 'qBittorrent' : 'Transmission' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="连接地址" min-width="180">
          <template #default="{ row }">
            <span class="url-text">{{ row.host }}</span>
          </template>
        </el-table-column>
        <el-table-column label="高级配置" min-width="180">
          <template #default="{ row }">
            <div class="tags-container" style="gap:5px;">
              <el-tag v-if="row.sequential_download" type="warning" size="small">顺序下载</el-tag>
              <el-tag v-if="row.force_resume" type="danger" size="small">强制恢复</el-tag>
              <el-tag v-if="JSON.parse(row.path_mapping || '[]').length > 0" type="success" size="small">路径映射已开</el-tag>
              <span v-else class="url-text" style="font-size:12px;opacity:0.5;">默认设置</span>
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
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button-group size="small">
              <el-button @click="testDownloader(row)" :loading="testingIds.has(row.id)">测试</el-button>
              <el-button @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" @click="deleteDownloader(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? 'Configuration / ' + form.name : 'Configuration'"
      width="600px"
      append-to-body
      custom-class="dark-modal"
      destroy-on-close
    >
      <div class="form-container">
        <!-- 基础配置与开关 -->
        <div class="form-grid switch-grid">
          <div class="switch-item">
            <el-switch v-model="form.is_active" />
            <span class="switch-label">Enabled</span>
          </div>
        </div>

        <div class="form-grid input-grid">
          <div class="input-item">
            <label>Name</label>
            <el-input v-model="form.name" placeholder="Name" />
          </div>
          <div class="input-item">
            <label>Host</label>
            <el-input v-model="form.host" placeholder="http(s)://ip:port" />
          </div>
          <div class="input-item">
            <label>Username</label>
            <el-input v-model="form.username" placeholder="Username" />
          </div>
          <div class="input-item">
            <label>Password</label>
            <el-input v-model="form.password" type="password" show-password placeholder="Password" />
          </div>
          <div class="input-item">
             <label>Client Type</label>
             <el-select v-model="form.client_type" style="width: 100%;">
                <el-option label="qBittorrent" value="qbittorrent" />
                <el-option label="Transmission" value="transmission" />
             </el-select>
          </div>
        </div>

        <!-- 进阶控制 -->
        <div class="form-grid switch-grid" style="margin-top: 20px;">
          <div class="switch-item">
            <el-switch v-model="form.auto_category_management" />
            <span class="switch-label">Auto Category Management</span>
          </div>
          <div class="switch-item">
            <el-switch v-model="form.sequential_download" />
            <span class="switch-label">Sequential Download</span>
          </div>
          <div class="switch-item">
            <el-switch v-model="form.force_resume" />
            <span class="switch-label">Force Resume</span>
          </div>
          <div class="switch-item">
            <el-switch v-model="form.first_last_piece_priority" />
            <span class="switch-label">First/Last Piece Priority</span>
          </div>
        </div>

        <el-divider><span style="color:#6b7280; font-size:14px;">Path Mapping</span></el-divider>

        <!-- 路径映射列表 -->
        <div class="path-mappings">
          <div v-for="(mapping, index) in parsedPathMapping" :key="index" class="mapping-card">
            <div class="mapping-content">
              <div class="input-group">
                <div class="label-with-icon"><el-icon><Folder /></el-icon> Storage Path</div>
                <div style="display:flex;">
                  <el-button style="border-right:none; border-top-right-radius:0; border-bottom-right-radius:0; background:rgba(255,255,255,0.05)" disabled>Local</el-button>
                  <el-input v-model="mapping.storage_path" placeholder="/path/to/storage" style="border-top-left-radius:0; border-bottom-left-radius:0"/>
                </div>
              </div>
              <div class="mapping-arrow"><el-icon><ArrowDown /></el-icon></div>
              <div class="input-group">
                <div class="label-with-icon" style="color:#22c55e;"><el-icon><Download /></el-icon> Download Path</div>
                <div style="display:flex; align-items:center;">
                  <el-input v-model="mapping.download_path" placeholder="/path/to/download" />
                  <el-button type="danger" link style="margin-left:8px;" @click="removePathMapping(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <el-button link type="primary" class="add-mapping-btn" @click="addPathMapping">
            <el-icon><Plus /></el-icon> ADD PATH MAPPING
          </el-button>
        </div>

      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          Save
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Refresh, Folder, ArrowDown, Download, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { downloaderApi } from '@/api'

const downloaders = ref([])
const loading = ref(false)
const testingIds = ref(new Set())
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)

const parsedPathMapping = ref([])

const form = reactive({
  name: '', client_type: 'qbittorrent', host: '', 
  username: '', password: '', category: '', 
  save_path: '', priority: 100, is_active: true,
  auto_category_management: false, sequential_download: false,
  force_resume: false, first_last_piece_priority: false,
  path_mapping: '[]'
})

async function loadDownloaders() {
  loading.value = true
  try {
    const res = await downloaderApi.list()
    downloaders.value = res.data || []
  } catch { ElMessage.error('加载列表失败') }
  finally { loading.value = false }
}

function openAddDialog() {
  editingId.value = null
  Object.assign(form, { 
    name: '', client_type: 'qbittorrent', host: '', username: '', password: '', 
    category: '', save_path: '', priority: 100, is_active: true,
    auto_category_management: false, sequential_download: false,
    force_resume: false, first_last_piece_priority: false, path_mapping: '[]'
  })
  parsedPathMapping.value = []
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  Object.assign(form, { 
    name: row.name, client_type: row.client_type, host: row.host, 
    username: row.username, password: row.password, category: row.category, 
    save_path: row.save_path, priority: row.priority, is_active: row.is_active,
    auto_category_management: row.auto_category_management, 
    sequential_download: row.sequential_download,
    force_resume: row.force_resume, 
    first_last_piece_priority: row.first_last_piece_priority, 
    path_mapping: row.path_mapping || '[]'
  })
  try {
    parsedPathMapping.value = JSON.parse(form.path_mapping || '[]')
  } catch (e) {
    parsedPathMapping.value = []
  }
  dialogVisible.value = true
}

function addPathMapping() {
  parsedPathMapping.value.push({ storage_path: '', download_path: '' })
}

function removePathMapping(index) {
  parsedPathMapping.value.splice(index, 1)
}

async function submitForm() {
  if (!form.name || !form.host) {
    ElMessage.warning('名称和地址不能为空')
    return
  }
  
  // 序列化 path_mapping
  // 过滤掉空的映射
  const validMappings = parsedPathMapping.value.filter(m => m.storage_path && m.download_path)
  form.path_mapping = JSON.stringify(validMappings)

  submitting.value = true
  try {
    if (editingId.value) {
      await downloaderApi.update(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await downloaderApi.add(form)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadDownloaders()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  }
  finally { submitting.value = false }
}

async function testDownloader(row) {
  testingIds.value.add(row.id)
  try {
    const res = await downloaderApi.test(row.id)
    ElMessage.success(res.message || '测试通过')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '测试失败')
  }
  finally { testingIds.value.delete(row.id) }
}

async function toggleActive(row, val) {
  try {
    await downloaderApi.update(row.id, { is_active: val })
  } catch { row.is_active = !val }
}

async function deleteDownloader(row) {
  await ElMessageBox.confirm(`确定删除下载器【${row.name}】吗？`, '警告', { type: 'warning' })
  await downloaderApi.delete(row.id)
  ElMessage.success('删除成功')
  await loadDownloaders()
}

onMounted(loadDownloaders)
</script>

<style lang="scss" scoped>
.downloader-view { display: flex; flex-direction: column; gap: 16px; min-height: 100%;}
.toolbar-card { padding: 16px 24px; }
.toolbar {
  display: flex; align-items: center;
  .toolbar-title { font-size: 18px; font-weight: 600; flex: 1; margin:0;}
  .toolbar-actions { display: flex; gap: 8px; }
}

.name-cell {
  display: flex; align-items: center; gap: 8px; font-weight: 600;
  color: var(--text-primary);
}
.indicator {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  &.active { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
  &.inactive { background: #ef4444; }
}
.url-text {
  color: var(--text-primary); font-size: 13px; font-family: monospace;
}
:deep(.el-table__row) {
  background-color: var(--bg-surface) !important;
}
.tags-container { display: flex; gap: 4px; flex-wrap: wrap; }

/* 模态框自定义样式 */
.form-container {
  padding: 0 10px;
}

.form-grid {
  display: grid;
  gap: 20px;
}
.input-grid {
  grid-template-columns: 1fr 1fr;
  margin-top: 15px;
}

.switch-grid {
  grid-template-columns: 1fr 1fr;
}

.input-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  label {
    font-size: 12px;
    color: #9ca3af;
  }
}

.switch-item {
  display: flex;
  align-items: center;
  gap: 12px;
  .switch-label {
    color: #cbd5e1;
    font-size: 14px;
    font-weight: 500;
  }
}

.path-mappings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mapping-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 16px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label-with-icon {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #9ca3af;
}

.mapping-arrow {
  text-align: center;
  color: #6b7280;
  margin: 8px 0;
}

.add-mapping-btn {
  margin-top: 8px;
  align-self: flex-start;
  font-weight: 600;
}

:deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.05);
  box-shadow: none;
  border: 1px solid rgba(255,255,255,0.1);
  &.is-focus { border-color: #3b82f6;}
}
:deep(.el-input__inner) {
  color: #fff;
}
</style>
