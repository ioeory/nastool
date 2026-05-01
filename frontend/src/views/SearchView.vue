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
        />
      </div>
      
    </div>
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
</style>
