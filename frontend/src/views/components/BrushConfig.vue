<template>
  <div class="brush-config-container">
    <el-tabs v-model="activeTab" class="brush-tabs">

      <!-- =============== 基本配置 =============== -->
      <el-tab-pane label="基本配置" name="basic">
        <div class="tab-content">

          <!-- 下载器绑定（最重要，放首位） -->
          <div class="downloader-bind-section">
            <div class="section-label">
              <span class="required-star">*</span> 绑定下载器节点
            </div>
            <div class="downloader-options">
              <div
                v-for="dl in downloaders"
                :key="dl.id"
                class="downloader-card"
                :class="{ selected: config.downloader_id === dl.id }"
                @click="config.downloader_id = dl.id"
              >
                <div class="dl-icon">
                  <span v-if="dl.client_type === 'qbittorrent'" class="dl-type qb">qB</span>
                  <span v-else class="dl-type tr">TR</span>
                </div>
                <div class="dl-info">
                  <div class="dl-name">{{ dl.name }}</div>
                  <div class="dl-host">{{ dl.host }}</div>
                </div>
                <el-icon v-if="config.downloader_id === dl.id" class="check-icon"><Select /></el-icon>
              </div>
              <div v-if="!downloaders.length" class="no-downloader">
                暂无下载器，请先在「下载器管理」中添加节点
              </div>
            </div>
          </div>

          <!-- 刷流站点 -->
          <el-form-item label="刷流站点" required style="margin-top: 20px">
            <el-select
              v-model="config.sites"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择要刷流的站点（可多选）"
              style="width: 100%"
            >
              <el-option
                v-for="site in sites"
                :key="site.id"
                :label="site.name"
                :value="site.id"
              />
            </el-select>
          </el-form-item>

          <!-- 并发与分类 -->
          <div class="form-grid-3" style="margin-top: 4px">
            <el-form-item label="同时下载任务数">
              <el-input-number v-model="config.max_tasks" :min="1" :max="20" style="width:100%" />
            </el-form-item>
            <el-form-item label="保种体积上限 (GB)">
              <el-input-number v-model="config.keep_volume" :min="0" style="width:100%" />
            </el-form-item>
            <el-form-item label="种子分类标签">
              <el-input v-model="config.category" placeholder="Brushing" />
            </el-form-item>
          </div>
        </div>
      </el-tab-pane>

      <!-- =============== 选种规则 =============== -->
      <el-tab-pane label="选种规则" name="selection">
        <div class="tab-content">
          <div class="form-row">
            <el-form-item label="排除 H&R" style="flex: 1">
              <el-select v-model="config.selection_rules.exclude_hr" style="width:100%">
                <el-option label="是（推荐）" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
            <el-form-item label="优惠类型筛选" style="flex: 1">
              <el-select v-model="config.selection_rules.promotion" style="width:100%">
                <el-option label="所有（不限）" value="" />
                <el-option label="仅 免费 (FREE)" value="FREE" />
                <el-option label="仅 2X免费 (2XFREE)" value="2XFREE" />
                <el-option label="仅 50% (半价)" value="50%" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-grid-3">
            <el-form-item label="最小体积 (GB)">
              <el-input-number
                v-model="config.selection_rules.min_size_gb"
                :min="0" :precision="1" :step="0.5"
                style="width:100%"
              />
            </el-form-item>
            <el-form-item label="最大做种人数">
              <el-input-number
                v-model="config.selection_rules.max_seeders"
                :min="0" placeholder="0=不限"
                style="width:100%"
              />
            </el-form-item>
            <el-form-item label="发布时间 (分钟内)">
              <el-input-number
                v-model="config.selection_rules.max_pub_time"
                :min="0" placeholder="0=不限"
                style="width:100%"
              />
            </el-form-item>
          </div>
          <div class="tip-box">
            <el-icon><InfoFilled /></el-icon>
            <span>建议：优先选 <strong>仅FREE</strong> + <strong>排除H&R</strong>，可最大化刷流安全性与收益比</span>
          </div>
        </div>
      </el-tab-pane>

      <!-- =============== 删除规则 =============== -->
      <el-tab-pane label="删除规则" name="deletion">
        <div class="tab-content">
          <div class="form-row">
            <el-form-item label="最低做种时间 (小时)" style="flex: 1">
              <el-input-number
                v-model="config.delete_rules.min_seeding_hours"
                :min="0" :precision="1"
                style="width:100%"
              />
            </el-form-item>
            <el-form-item label="最低分享率" style="flex: 1">
              <el-input-number
                v-model="config.delete_rules.min_ratio"
                :min="0" :precision="2" :step="0.1"
                style="width:100%"
              />
            </el-form-item>
          </div>
          <el-form-item label="排除标签 (逗号分隔)">
            <el-input v-model="config.delete_rules.exclude_labels" placeholder="H&R,MOVIEPILOT" />
          </el-form-item>
          <el-form-item label="删种时删除本地文件">
            <el-switch v-model="config.delete_rules.delete_files" />
            <span class="switch-hint">开启后，满足删种规则时会在 qBittorrent 中勾选「删除文件」，释放磁盘空间</span>
          </el-form-item>
          <div class="tip-box warning">
            <el-icon><WarningFilled /></el-icon>
            <span>满足「做种时间」<strong>AND</strong>「分享率」双条件时才会删种，两者均 0 则不自动删</span>
          </div>
        </div>
      </el-tab-pane>

      <!-- =============== 更多配置 =============== -->
      <el-tab-pane label="更多配置" name="more">
        <div class="tab-content">
          <div class="switch-grid">
            <el-form-item label="使用 RSS 优先">
              <el-switch v-model="config.use_rss" />
            </el-form-item>
            <el-form-item label="动态删种">
              <el-switch v-model="config.dynamic_delete" />
            </el-form-item>
            <el-form-item label="站点顺序刷流">
              <el-switch v-model="config.sequential" />
            </el-form-item>
            <el-form-item label="站点独立配置">
              <el-switch v-model="config.site_independent" />
            </el-form-item>
          </div>
        </div>
      </el-tab-pane>

    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Select, InfoFilled, WarningFilled } from '@element-plus/icons-vue'
import { siteApi, downloaderApi } from '@/api'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['update:modelValue'])

const activeTab = ref('basic')
const sites = ref([])
const downloaders = ref([])

// 深度合并配置结构，保证嵌套对象完整
const defaultConfig = {
  sites: [],
  downloader_id: null,
  max_tasks: 3,
  keep_volume: 100,
  category: 'Brushing',
  selection_rules: {
    exclude_hr: true,
    promotion: 'FREE',
    min_size_gb: 0,
    max_seeders: 100,
    max_pub_time: 60,
  },
  delete_rules: {
    min_seeding_hours: 2,
    min_ratio: 1.0,
    exclude_labels: 'H&R',
    delete_files: false,
  },
  use_rss: true,
  dynamic_delete: true,
  sequential: false,
  site_independent: false,
}

const config = ref(JSON.parse(JSON.stringify(defaultConfig)))

// 同步外部变更 (仅当外部值与内部值不一致时更新，防止循环)
watch(() => props.modelValue, (newVal) => {
  if (!newVal) return
  
  const merged = {
    ...defaultConfig,
    ...newVal,
    selection_rules: { ...defaultConfig.selection_rules, ...(newVal?.selection_rules || {}) },
    delete_rules: { ...defaultConfig.delete_rules, ...(newVal?.delete_rules || {}) },
  }
  
  // 只有当合并后的结果与当前 local config 不一致时才更新
  // 使用 JSON 字符串对比是深度对比最简单有效的方式
  if (JSON.stringify(merged) !== JSON.stringify(config.value)) {
    config.value = JSON.parse(JSON.stringify(merged))
  }
}, { immediate: true, deep: true })

// 同步内部变更到父组件
watch(config, (newVal) => {
  // 只有当内部变更与外部 prop 不一致时才发射
  if (JSON.stringify(newVal) !== JSON.stringify(props.modelValue)) {
    emit('update:modelValue', JSON.parse(JSON.stringify(newVal)))
  }
}, { deep: true })

async function loadData() {
  try {
    const [siteRes, dlRes] = await Promise.all([
      siteApi.list(true),       // active_only=true
      downloaderApi.list(true), // active_only=true
    ])
    sites.value = siteRes.data || []
    downloaders.value = dlRes.data || []
  } catch (e) {
    console.error('BrushConfig: 加载数据失败', e)
  }
}

watch(config, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

onMounted(loadData)
</script>

<style lang="scss" scoped>
.brush-config-container { margin-top: -10px; }

.tab-content { padding-top: 16px; min-height: 280px; }

.form-row { display: flex; gap: 16px; }

.form-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

/* 下载器绑定区域 */
.downloader-bind-section {
  margin-bottom: 4px;
}
.section-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  .required-star { color: var(--danger); margin-right: 4px; }
}
.downloader-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.downloader-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  cursor: pointer;
  transition: all 0.2s;
  min-width: 220px;
  position: relative;

  &:hover {
    border-color: var(--primary);
    background: rgba(99, 102, 241, 0.05);
  }
  &.selected {
    border-color: var(--primary);
    background: rgba(99, 102, 241, 0.12);
  }
}
.dl-icon {
  flex-shrink: 0;
  .dl-type {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px; height: 32px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 700;
    &.qb { background: rgba(29,155,240,0.2); color: #1d9bf0; }
    &.tr { background: rgba(239,68,68,0.2); color: #ef4444; }
  }
}
.dl-info {
  flex: 1;
  .dl-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .dl-host { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
}
.check-icon {
  color: var(--primary);
  font-size: 18px;
}
.no-downloader {
  color: var(--text-muted);
  font-size: 13px;
  padding: 12px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  width: 100%;
  text-align: center;
}

/* Tabs 样式 */
.brush-tabs {
  :deep(.el-tabs__item) { color: var(--text-secondary); }
  :deep(.el-tabs__item.is-active) { color: var(--primary); font-weight: 600; }
  :deep(.el-tabs__active-bar) { background-color: var(--primary); }
}

/* Switch 网格 */
.switch-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  :deep(.el-form-item) {
    background: var(--bg-surface);
    padding: 10px 14px;
    border-radius: 8px;
    border: 1px solid var(--border);
    .el-form-item__label { flex: 1; color: var(--text-secondary); }
  }
}

/* 提示框 */
.tip-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.15);
  color: var(--text-secondary);
  font-size: 12px;
  .el-icon { color: var(--primary); flex-shrink: 0; }
  &.warning {
    background: rgba(245,158,11,0.08);
    border-color: rgba(245,158,11,0.15);
    .el-icon { color: var(--warning); }
  }
}

.switch-hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}
</style>
