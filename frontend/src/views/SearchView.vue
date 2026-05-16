<template>
  <div class="search-view">
    <!-- 搜索顶栏 -->
    <div class="page-card search-header">
      <div class="search-title">
        <h2>全局搜索</h2>
        <span class="search-subtitle">支持多站点聚合搜索与一键下载推送到 qBittorrent</span>
      </div>
      <div class="search-bar">
        <el-input
          v-model="keyword"
          placeholder="输入你想看的电影 / 剧集 / 动漫名称"
          class="search-input"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" class="search-btn" :loading="loading" @click="handleSearch">
          索 搜
        </el-button>
      </div>
    </div>

    <!-- 搜索结果区 -->
    <div class="search-results page-card" v-loading="loading">
      
      <!-- 结果控制栏 -->
      <div class="results-ctrl" v-if="results.length > 0">
        <div class="results-stat">
          找到 <span>{{ results.length }}</span> 个与 <span class="highlight">"{{ lastKeyword }}"</span> 相关的结果
        </div>
      </div>
      
      <!-- 空状态 -->
      <el-empty 
        v-if="!loading && results.length === 0 && hasSearched" 
        description="未在已启用的站点中找到相关资源" 
        :image-size="120" 
      />

      <!-- 卡片网格分布 -->
      <div class="torrent-grid" v-if="results.length > 0">
        <ResourceCard 
          v-for="(item, index) in results" 
          :key="index"
          :item="item"
          :downloading="downloadingIds.has(item.enclosure)"
          @download="handleDownload(item)"
          @open="openUrl(item.detail_url)"
          @view-sources="openSources(item)"
        />
      </div>
      
    </div>

    <!-- 多站聚合来源弹窗 -->
    <el-dialog
      v-model="sourcesVisible"
      :title="sourcesTitle"
      width="720px"
      class="sources-dialog"
      append-to-body
    >
      <div class="sources-list" v-if="activeSources.length">
        <div class="source-row" v-for="(s, i) in activeSources" :key="i">
          <div class="source-main">
            <div class="source-head">
              <span class="site-pill">{{ s.site_name || `站点 #${s.site_id}` }}</span>
              <span v-if="s.free" class="free-pill">{{ s.free }}</span>
            </div>
            <div class="source-title" :title="s.title">{{ s.title }}</div>
            <div class="source-meta">
              <span><el-icon><DataLine /></el-icon> {{ formatSize(s.size) }}</span>
              <span class="seeders"><el-icon><CaretTop /></el-icon> {{ s.seeders || 0 }}</span>
            </div>
          </div>
          <div class="source-actions">
            <el-button
              type="primary"
              :icon="Download"
              :loading="downloadingIds.has(s.enclosure)"
              @click="handleSourceDownload(s)"
            >推送下载</el-button>
            <el-button :icon="Link" @click="openUrl(s.detail_url)">详情页</el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="此条目仅有一个来源" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Search, Download, Link, DataLine, CaretTop, Bottom } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { searchApi } from '@/api'
import ResourceCard from '@/components/ResourceCard.vue'

const route = useRoute()
const keyword = ref('')
const lastKeyword = ref('')
const loading = ref(false)
const hasSearched = ref(false)
const results = ref([])
const downloadingIds = ref(new Set())

// 多站聚合来源弹窗
const sourcesVisible = ref(false)
const activeItem = ref(null)
const activeSources = ref([])
const sourcesTitle = ref('')

function openSources(item) {
  activeItem.value = item
  activeSources.value = item.sources || []
  sourcesTitle.value = `聚合来源 · 共 ${activeSources.value.length} 个站点`
  sourcesVisible.value = true
}

async function handleSourceDownload(source) {
  if (!activeItem.value) return
  // 用聚合主条目作模板，覆盖该来源独有字段，转成后端 TorrentItem
  const base = activeItem.value
  const payload = {
    site_id: source.site_id,
    site_name: source.site_name,
    title: source.title || base.title,
    description: base.description,
    enclosure: source.enclosure,
    detail_url: source.detail_url,
    seeders: source.seeders ?? 0,
    leechers: 0,
    downloads: 0,
    size: source.size ?? 0,
    pubdate: base.pubdate,
    free: source.free,
    hr: false,
    labels: [],
    imdb_id: base.imdb_id,
    sources: []
  }
  downloadingIds.value.add(source.enclosure)
  try {
    await searchApi.download(payload)
    ElMessage.success(`✅ 已推送来自 ${source.site_name || '该站点'} 的资源`)
  } catch (e) {
    console.error(e)
  } finally {
    downloadingIds.value.delete(source.enclosure)
  }
}

// 处理来自 URL 参数的自动搜索
function checkQuery() {
  const w = route.query.w
  if (w && w !== lastKeyword.value) {
    keyword.value = String(w)
    handleSearch()
  }
}

onMounted(() => {
  checkQuery()
})

// 监听路由变化，处理连续跳转
watch(() => route.query.w, () => {
  checkQuery()
})

async function handleSearch() {
  if (!keyword.value.trim()) {
    ElMessage.warning('搜索关键词不能为空')
    return
  }
  
  loading.value = true
  hasSearched.value = true
  lastKeyword.value = keyword.value
  
  try {
    const res = await searchApi.search(keyword.value, 1)
    results.value = res.data || []
  } catch (e) {
    results.value = []
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleDownload(item) {
  downloadingIds.value.add(item.enclosure)
  try {
    // 调用 API 触发下载链
    await searchApi.download(item)
    ElMessage.success(`✅ 已推送到下载器: ${item.title.slice(0,20)}...`)
  } catch (e) {
    console.error(e)
  } finally {
    downloadingIds.value.delete(item.enclosure)
  }
}

function openUrl(url) {
  if(url) window.open(url, '_blank')
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style lang="scss" scoped>
.search-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-header {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 30px;
  background: var(--bg-surface);
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 100%; height: 3px;
    background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
  }
}

.search-title {
  text-align: left;
  h2 { font-size: 24px; color: #fff; margin-bottom: 6px; }
  .search-subtitle { font-size: 14px; color: var(--text-muted); }
}

.search-bar {
  display: flex;
  gap: 12px;
  max-width: 800px;
  width: 100%;

  :deep(.el-input__wrapper) {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: none;
    height: 50px;
    border-radius: 12px;
    font-size: 16px;
    transition: all 0.3s;
    &:hover, &.is-focus {
      border-color: #6366f1;
      background: rgba(255,255,255,0.08);
    }
  }
  
  :deep(.el-input__inner) {
    color: #fff;
    &::placeholder { color: rgba(255, 255, 255, 0.3); }
  }

  .search-btn {
    height: 50px;
    padding: 0 40px;
    font-size: 16px;
    border-radius: 12px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border: none;
    font-weight: 600;
    letter-spacing: 2px;
    &:hover {
      box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
      transform: translateY(-2px);
    }
  }
}

.search-results {
  min-height: 400px;
  padding: 24px 30px;
}

.results-ctrl {
  margin-bottom: 24px;
  .results-stat {
    font-size: 14px;
    color: var(--text-secondary);
    span { color: #fff; font-weight: 600; }
    .highlight { color: #8b5cf6; }
  }
}

.torrent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.sources-dialog {
  :deep(.el-dialog) {
    background: #1a1a2e;
    border: 1px solid rgba(255,255,255,0.08);
  }
  :deep(.el-dialog__title) { color: #fff; }
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
}

.source-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  transition: all .2s ease;

  &:hover {
    background: rgba(255,255,255,0.06);
    border-color: rgba(139, 92, 246, 0.4);
  }

  .source-main {
    flex: 1;
    min-width: 0;
  }
  .source-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;

    .site-pill {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      color: #fff;
      background: linear-gradient(135deg, #4f46e5, #7c3aed);
    }
    .free-pill {
      font-size: 10px;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      color: #fff;
      background: linear-gradient(135deg, #10b981, #059669);
    }
  }
  .source-title {
    font-size: 13px;
    color: #fff;
    word-break: break-all;
    line-height: 1.5;
    margin-bottom: 6px;
  }
  .source-meta {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: rgba(255,255,255,0.5);
    span { display: inline-flex; align-items: center; gap: 4px; }
    .seeders { color: #10b981; }
  }
  .source-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  }
}
</style>
