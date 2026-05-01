<template>
  <div class="subscribe-view">
    <!-- 工具栏 -->
    <div class="page-card toolbar-card">
      <div class="toolbar">
        <h2 class="toolbar-title">订阅管理</h2>
        <div class="toolbar-actions">
          <el-button :icon="Refresh" @click="loadSubscribes" :loading="loading">刷新</el-button>
          <el-button type="primary" :icon="Plus" @click="openAddDialog">添加订阅</el-button>
        </div>
      </div>
    </div>

    <!-- 列表 -->
    <div class="page-card">
      <el-table
        :data="subscribes"
        v-loading="loading"
        row-key="id"
        class="dl-table"
      >
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }">
            <div class="name-cell">
              <div class="indicator" :class="row.is_active ? 'active' : 'inactive'" />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="keyword" label="搜索关键字" min-width="180">
          <template #default="{ row }">
            <el-tag type="info">{{ row.keyword }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="180">
          <template #default="{ row }">
            <span class="url-text">{{ row.note || '-' }}</span>
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
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button-group size="small">
              <el-button @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" @click="deleteSubscribe(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑订阅' : '添加订阅'"
      width="450px"
      append-to-body
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="起个名字，比如：海贼王" />
        </el-form-item>
        <el-form-item label="关键字" prop="keyword">
          <el-input v-model="form.keyword" placeholder="搜索资源用的关键字" />
        </el-form-item>
        <el-form-item label="备注" prop="note">
          <el-input v-model="form.note" type="textarea" placeholder="可选备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { subscribeApi } from '@/api'

const subscribes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const formRef = ref()

const form = reactive({
  name: '', keyword: '', note: '', is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入订阅名', trigger: 'blur' }],
  keyword: [{ required: true, message: '请输入关键字', trigger: 'blur' }],
}

async function loadSubscribes() {
  loading.value = true
  try {
    const res = await subscribeApi.list()
    subscribes.value = res.data || []
  } catch { ElMessage.error('加载列表失败') }
  finally { loading.value = false }
}

function openAddDialog() {
  editingId.value = null
  Object.assign(form, { name: '', keyword: '', note: '', is_active: true })
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  Object.assign(form, { 
    name: row.name, keyword: row.keyword, note: row.note
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value?.validate()
  submitting.value = true
  try {
    if (editingId.value) {
      await subscribeApi.update(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await subscribeApi.add(form)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadSubscribes()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  }
  finally { submitting.value = false }
}

async function toggleActive(row, val) {
  try {
    await subscribeApi.update(row.id, { is_active: val })
  } catch { row.is_active = !val }
}

async function deleteSubscribe(row) {
  await ElMessageBox.confirm(`确定删除订阅【${row.name}】吗？`, '警告', { type: 'warning' })
  await subscribeApi.delete(row.id)
  ElMessage.success('删除成功')
  await loadSubscribes()
}

const route = useRoute()

onMounted(async () => {
  await loadSubscribes()
  
  // 处理来自详情页的跳转：自动打开添加窗口并预填
  const w = route.query.w
  if (w) {
    openAddDialog()
    form.name = String(w)
    form.keyword = String(w)
  }
})
</script>

<style lang="scss" scoped>
.subscribe-view { display: flex; flex-direction: column; gap: 16px; min-height: 100%;}
.toolbar-card { padding: 16px 24px; }
.toolbar {
  display: flex; align-items: center;
  .toolbar-title { font-size: 18px; font-weight: 600; flex: 1; margin:0;}
  .toolbar-actions { display: flex; gap: 8px; }
}

.name-cell {
  display: flex; align-items: center; gap: 8px; font-weight: 600; color: #fff;
}
.indicator {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  &.active { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
  &.inactive { background: #ef4444; }
}
.url-text {
  color: var(--text-muted); font-size: 13px; font-family: monospace;
}
</style>
