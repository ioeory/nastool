<template>
  <div class="explore-view">
    <!-- 顶层标签系统 -->
    <div class="tabs-container">
      <div class="tab-item active">TheMovieDb</div>
      <div class="tab-item">Douban</div>
      <div class="tab-item">Bangumi</div>
      <div class="flex-spacer"></div>
      <el-icon class="grid-icon"><Grid /></el-icon>
    </div>

    <!-- 过滤器面板 -->
    <div class="filters-panel">
      <!-- 类别过滤 -->
      <div class="filter-row">
        <span class="filter-label">Type</span>
        <div class="filter-options">
          <div class="filter-btn" :class="{active: filterParams.media_type === 'movie'}" @click="setMediaType('movie')">
            <el-icon v-if="filterParams.media_type === 'movie'"><Check /></el-icon> Movie
          </div>
          <div class="filter-btn" :class="{active: filterParams.media_type === 'tv'}" @click="setMediaType('tv')">
            <el-icon v-if="filterParams.media_type === 'tv'"><Check /></el-icon> TV Show
          </div>
        </div>
      </div>

      <!-- 排序过滤 -->
      <div class="filter-row">
        <span class="filter-label">Sort</span>
        <div class="filter-options">
          <div class="filter-btn" :class="{active: filterParams.sort_by === 'popularity.desc'}" @click="setSort('popularity.desc')">
             <el-icon v-if="filterParams.sort_by === 'popularity.desc'"><Check /></el-icon> Popularity Descending
          </div>
          <div class="filter-btn" :class="{active: filterParams.sort_by === 'primary_release_date.desc'}" @click="setSort('primary_release_date.desc')">
             <el-icon v-if="filterParams.sort_by === 'primary_release_date.desc'"><Check /></el-icon> Release Date Descending
          </div>
          <div class="filter-btn" :class="{active: filterParams.sort_by === 'vote_average.desc'}" @click="setSort('vote_average.desc')">
             <el-icon v-if="filterParams.sort_by === 'vote_average.desc'"><Check /></el-icon> Vote Average Descending
          </div>
        </div>
      </div>

      <!-- 流派 (Genres) 过滤 -->
      <div class="filter-row scrollable-row">
        <span class="filter-label">Genre</span>
        <div class="filter-options">
          <div v-for="g in genres" :key="g.id" class="filter-btn" :class="{active: filterParams.with_genres === g.id}" @click="setGenre(g.id)">
             <el-icon v-if="filterParams.with_genres === g.id"><Check /></el-icon> {{g.name}}
          </div>
        </div>
      </div>

      <!-- 语言过滤 -->
      <div class="filter-row scrollable-row">
        <span class="filter-label">Language</span>
        <div class="filter-options">
          <div v-for="lang in languages" :key="lang.id" class="filter-btn" :class="{active: filterParams.with_original_language === lang.id}" @click="setLanguage(lang.id)">
             <el-icon v-if="filterParams.with_original_language === lang.id"><Check /></el-icon> {{lang.name}}
          </div>
        </div>
      </div>
    </div>

    <!-- 瀑布流展示 (无限加载) -->
    <div class="media-grid" v-infinite-scroll="loadMore" :infinite-scroll-disabled="loading || reachedEnd">
      <MediaCard v-for="item in mediaList" :key="item.id" :item="item" :type="filterParams.media_type" @click="openDetail(item)" />
    </div>

    <div v-if="loading" class="loading-spinner">
      <el-icon class="is-loading"><Loading /></el-icon> Loading more...
    </div>

    <!-- 详情侧弹窗/Modal -->
    <MediaDetailModal ref="detailModal" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { Check, Grid, Loading } from '@element-plus/icons-vue'
import { tmdbApi } from '@/api'
import MediaCard from '@/components/MediaCard.vue'
import MediaDetailModal from '@/components/MediaDetailModal.vue'

const detailModal = ref(null)

const filterParams = reactive({
  media_type: 'movie',
  sort_by: 'popularity.desc',
  with_genres: '',
  with_original_language: '',
  page: 1
})

const genres = ref([])
const mediaList = ref([])
const loading = ref(false)
const reachedEnd = ref(false)

const languages = [
  { id: '', name: 'All' },
  { id: 'zh', name: 'Chinese' },
  { id: 'en', name: 'English' },
  { id: 'ja', name: 'Japanese' },
  { id: 'ko', name: 'Korean' },
  { id: 'fr', name: 'French' },
  { id: 'de', name: 'German' },
]

async function fetchGenres() {
  try {
    const res = await tmdbApi.getGenres(filterParams.media_type)
    genres.value = [{ id: '', name: 'All' }, ...res.data]
  } catch (e) {
    console.error('Failed to load genres', e)
  }
}

async function fetchMedia(reset = false) {
  if (loading.value || reachedEnd.value) return
  
  if (reset) {
    filterParams.page = 1
    mediaList.value = []
    reachedEnd.value = false
  }

  loading.value = true
  try {
    const res = await tmdbApi.discover({
      media_type: filterParams.media_type,
      sort_by: filterParams.sort_by,
      with_genres: filterParams.with_genres,
      with_original_language: filterParams.with_original_language,
      page: filterParams.page
    })
    
    if (res.data && res.data.results) {
      if (res.data.results.length === 0) {
        reachedEnd.value = true
      } else {
        mediaList.value.push(...res.data.results.filter(i => i.poster_path))
        filterParams.page++
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 事件切换
function setMediaType(t) { filterParams.media_type = t; filterParams.with_genres = ''; fetchGenres(); fetchMedia(true) }
function setSort(s) { filterParams.sort_by = s; fetchMedia(true) }
function setGenre(g) { filterParams.with_genres = g; fetchMedia(true) }
function setLanguage(l) { filterParams.with_original_language = l; fetchMedia(true) }

function loadMore() {
  if (mediaList.value.length > 0) {
    fetchMedia(false)
  }
}

function openDetail(item) {
  detailModal.value.open(item.id, filterParams.media_type)
}

onMounted(() => {
  fetchGenres()
  fetchMedia(true)
})

</script>

<style lang="scss" scoped>
.explore-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tabs-container {
  display: flex;
  align-items: center;
  gap: 24px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding-bottom: 15px;
  margin-bottom: 20px;
  .tab-item {
    font-size: 16px;
    font-weight: 600;
    color: #9ca3af;
    cursor: pointer;
    transition: all 0.3s ease;
    &.active {
      color: #8b5cf6;
      border-bottom: 2px solid #8b5cf6;
    }
    &:hover { color: #fff; }
  }
  .flex-spacer { flex: 1; }
  .grid-icon { font-size: 20px; color: #9ca3af; cursor: pointer; }
}

.filters-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
  
  .filter-label {
    min-width: 70px;
    font-size: 14px;
    color: #9ca3af;
    font-weight: 500;
  }
  
  .filter-options {
    display: flex;
    gap: 8px;
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    &::-webkit-scrollbar { display: none; }
    
    .filter-btn {
      padding: 6px 16px;
      font-size: 13px;
      color: #cbd5e1;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      transition: all 0.2s ease;
      
      &:hover {
        background: rgba(255,255,255,0.1);
      }
      
      &.active {
        background: rgba(139, 92, 246, 0.15);
        color: #a78bfa;
        border-color: rgba(139, 92, 246, 0.5);
      }
    }
  }
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
  padding-bottom: 40px;
}

.loading-spinner {
  text-align: center;
  padding: 20px;
  color: #8b5cf6;
  font-size: 14px;
}
</style>
