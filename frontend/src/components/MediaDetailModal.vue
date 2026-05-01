<template>
  <el-dialog
    v-model="visible"
    :show-close="true"
    width="85%"
    top="5vh"
    custom-class="hero-modal"
    destroy-on-close
    append-to-body
    :before-close="handleClose"
  >
    <div class="detail-container" v-loading="loading">
      <template v-if="detail">
        <!-- 巨型 Backdrop 主视觉 -->
        <div class="hero-section" :style="heroStyle">
          <div class="hero-gradient"></div>
          <div class="hero-content">
            <div class="poster-wrap">
              <img v-if="detail.poster_path" :src="`/api/v1/tmdb/image?path=${detail.poster_path}&size=w500`" class="main-poster" />
            </div>
            <div class="info-wrap">
              <h1 class="title">{{ detail.title || detail.name }}</h1>
              <div class="year-line">({{ releaseYear }})</div>
              <div class="meta-line">
                <span v-if="detail.runtime">{{ detail.runtime }} minutes | </span>
                <span class="genres">{{ genresText }}</span>
              </div>
              
              <div class="actions">
                <el-button type="primary" class="cta-btn search-btn" @click="goSearch">
                  <el-icon><Search /></el-icon> SEARCH RESOURCE
                </el-button>
                <el-button type="warning" class="cta-btn sub-btn" @click="subscribe">
                  <el-icon><Star /></el-icon> SUBSCRIBE
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 详细信息区 -->
        <div class="content-section">
          <!-- 概览与演职员摘要 -->
          <div class="overview-grid">
            <div class="left-col">
              <h3 class="section-title">Overview</h3>
              <p class="overview-text">{{ detail.overview || '暂无简介' }}</p>
              
              <div class="crew-summary" v-if="featuredCrew.length > 0">
                <div v-for="c in featuredCrew" :key="c.id" class="crew-item">
                  <div class="crew-job">{{ c.job }}</div>
                  <div class="crew-name">{{ c.name }}</div>
                </div>
              </div>
            </div>
            
            <!-- 右侧核心参数区域 -->
            <div class="right-col details-table">
              <div class="d-row">
                <span class="d-label">ID</span>
                <span class="d-val">{{ detail.id }}</span>
              </div>
              <div class="d-row">
                <span class="d-label">Original Title</span>
                <span class="d-val">{{ detail.original_title || detail.original_name }}</span>
              </div>
              <div class="d-row">
                <span class="d-label">Status</span>
                <span class="d-val">{{ detail.status }}</span>
              </div>
              <div class="d-row">
                <span class="d-label">Release Date</span>
                <span class="d-val">{{ detail.release_date || detail.first_air_date }}</span>
              </div>
              <div class="d-row border-none">
                <span class="d-label">Production Countries</span>
                <span class="d-val right-align">{{ countriesText }}</span>
              </div>
            </div>
          </div>

          <!-- 卡司阵容 (Cast) -->
          <div class="carousel-section" v-if="castList.length > 0">
            <div class="section-header">
              <h3>Cast & Crew</h3>
              <el-button link type="primary">更多 <el-icon><ArrowRight /></el-icon></el-button>
            </div>
            <div class="cast-carousel">
              <div v-for="c in castList" :key="c.id" class="cast-card">
                <img v-if="c.profile_path" :src="`/api/v1/tmdb/image?path=${c.profile_path}&size=w185`" class="avatar" />
                <div v-else class="avatar no-avatar"><el-icon><User /></el-icon></div>
                <div class="c-name">{{ c.name }}</div>
                <div class="c-char">{{ c.character }}</div>
              </div>
            </div>
          </div>

          <!-- 推荐与相似 -->
          <div class="carousel-section" v-if="recommendations.length > 0">
            <div class="section-header">
              <h3 style="border-left-color: #8b5cf6;">Recommendations</h3>
            </div>
            <div class="media-carousel">
               <MediaCard v-for="m in recommendations" :key="m.id" :item="m" :type="mediaType" @click="loadDetail(m.id)" style="width: 140px; flex-shrink: 0;" />
            </div>
          </div>

        </div>
      </template>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { tmdbApi } from '@/api'
import { Search, Star, ArrowRight, User } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import MediaCard from './MediaCard.vue'

const visible = ref(false)
const loading = ref(false)
const detail = ref(null)
const mediaType = ref('movie')
const router = useRouter()

const heroStyle = computed(() => {
  if (!detail.value || !detail.value.backdrop_path) return {}
  return {
    backgroundImage: `url(/api/v1/tmdb/image?path=${detail.value.backdrop_path}&size=original)`
  }
})

const releaseYear = computed(() => {
  const d = detail.value?.release_date || detail.value?.first_air_date
  return d ? d.split('-')[0] : 'N/A'
})

const genresText = computed(() => {
  return (detail.value?.genres || []).map(g => g.name).join('、')
})

const countriesText = computed(() => {
  return (detail.value?.production_countries || []).map(c => c.name).join(', ')
})

const featuredCrew = computed(() => {
  if (!detail.value?.credits?.crew) return []
  // 取出 Director, Producer, 等前 6 个
  const core = detail.value.credits.crew.filter(c => ['Director', 'Producer', 'Editor', 'Writer'].includes(c.job))
  return core.slice(0, 6)
})

const castList = computed(() => {
  return (detail.value?.credits?.cast || []).slice(0, 10)
})

const recommendations = computed(() => {
  return (detail.value?.recommendations?.results || []).slice(0, 10)
})

async function open(id, type) {
  mediaType.value = type
  visible.value = true
  await loadDetail(id)
}

async function loadDetail(id) {
  loading.value = true
  detail.value = null
  try {
    const res = await tmdbApi.getFullDetails(mediaType.value, id)
    if (res.data) detail.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleClose(done) {
  detail.value = null
  done()
}

function goSearch() {
  const title = detail.value?.name || detail.value?.title
  visible.value = false
  router.push({ path: '/search', query: { w: title } })
}

function subscribe() {
  visible.value = false
  // 简易路由跳转，可以带入名字也可以带 TMDB ID
  router.push({ path: '/subscribe', query: { w: detail.value?.title || detail.value?.name } })
}

defineExpose({ open })
</script>

<style lang="scss">
/* 覆盖 ElDialog 默认样式使之沉浸化 */
.hero-modal {
  background: #111827 !important;
  border-radius: 16px !important;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
  padding: 0 !important;
  
  .el-dialog__header { display: none; }
  .el-dialog__body { padding: 0; }
  .el-dialog__headerbtn {
    z-index: 50;
    top: 20px;
    right: 20px;
    background: rgba(0,0,0,0.5);
    border-radius: 50%;
    width: 36px;
    height: 36px;
    .el-dialog__close { color: #fff; font-size: 20px;}
  }
}
</style>

<style lang="scss" scoped>
.detail-container {
  min-height: 500px;
  color: #e5e7eb;
}

.hero-section {
  position: relative;
  width: 100%;
  height: 65vh; /* 巨幅海报 */
  min-height: 400px;
  background-size: cover;
  background-position: center 20%;
  background-repeat: no-repeat;
  background-color: #1f2937;
  
  .hero-gradient {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      to bottom,
      rgba(17, 24, 39, 0.1) 0%,
      rgba(17, 24, 39, 0.6) 50%,
      rgba(17, 24, 39, 1) 100%
    );
  }
}

.hero-content {
  position: absolute;
  bottom: -40px;
  left: 5%;
  right: 5%;
  display: flex;
  align-items: flex-end;
  gap: 40px;
  z-index: 10;
}

.poster-wrap {
  width: 240px;
  flex-shrink: 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255,255,255,0.1);
  background: #000;
  
  .main-poster {
    width: 100%;
    display: block;
  }
}

.info-wrap {
  flex: 1;
  padding-bottom: 50px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  text-align: center;
  margin-left: -280px; /* offset poster wrap */
  
  .title {
    font-size: 42px;
    font-weight: 800;
    color: #fff;
    margin: 0 0 5px 0;
    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    letter-spacing: 1px;
  }
  
  .year-line {
    font-size: 24px;
    font-weight: 600;
    color: #d1d5db;
    margin-bottom: 20px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
  }
  
  .meta-line {
    font-size: 15px;
    color: #f3f4f6;
    margin-bottom: 30px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.8);
  }
  
  .actions {
    display: flex;
    gap: 16px;
    
    .cta-btn {
      padding: 12px 24px;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 1px;
      border-radius: 8px;
    }
    .search-btn {
      background: rgba(30, 58, 138, 0.6);
      border-color: rgba(59, 130, 246, 0.5);
      backdrop-filter: blur(8px);
      &:hover { background: rgba(30, 58, 138, 0.9); }
    }
    .sub-btn {
      background: rgba(146, 64, 14, 0.6);
      border-color: rgba(217, 119, 6, 0.5);
      backdrop-filter: blur(8px);
      color: #fff;
      &:hover { background: rgba(146, 64, 14, 0.9); border-color: rgba(245, 158, 11, 0.8);}
    }
  }
}

.content-section {
  padding: 60px 5% 40px 5%;
  background: #111827;
}

.overview-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 40px;
  margin-bottom: 40px;
}

.section-title {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 16px;
  margin-top: 0;
}

.overview-text {
  font-size: 15px;
  line-height: 1.7;
  color: #d1d5db;
  margin-bottom: 30px;
}

.crew-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  
  .crew-item {
    .crew-job { font-weight: 700; font-size: 14px; color: #fff; margin-bottom: 4px; }
    .crew-name { font-size: 14px; color: #9ca3af; }
  }
}

.details-table {
  background: rgba(255,255,255,0.03);
  border-radius: 12px;
  padding: 10px 20px;
  border: 1px solid rgba(255,255,255,0.05);
  
  .d-row {
    display: flex;
    justify-content: space-between;
    padding: 16px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    
    &.border-none { border-bottom: none; }
    
    .d-label { font-size: 14px; font-weight: 700; color: #fff; width: 40%; flex-shrink: 0;}
    .d-val { font-size: 14px; color: #9ca3af; text-align: right; }
    .right-align { text-align: right; }
  }
}

.carousel-section {
  margin-bottom: 40px;
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h3 {
      font-size: 20px;
      color: #fff;
      margin: 0;
      padding-left: 10px;
      border-left: 4px solid #3b82f6;
    }
  }
}

.cast-carousel {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 10px;
  scrollbar-width: thin;
  
  &::-webkit-scrollbar { height: 6px; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
  
  .cast-card {
    width: 140px;
    flex-shrink: 0;
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
    overflow: hidden;
    padding-bottom: 10px;
    text-align: center;
    
    .avatar {
      width: 100%;
      height: 175px;
      object-fit: cover;
      margin-bottom: 10px;
    }
    
    .no-avatar {
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1f2937;
      font-size: 40px;
      color: #4b5563;
    }
    
    .c-name {
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      margin: 0 8px 4px 8px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    
    .c-char {
      font-size: 12px;
      color: #9ca3af;
      margin: 0 8px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.media-carousel {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 15px;
  
  &::-webkit-scrollbar { height: 6px; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
}

@media screen and (max-width: 1024px) {
  .hero-content {
    flex-direction: column;
    align-items: center;
    bottom: -80px;
  }
  .info-wrap {
    margin-left: 0;
    padding-bottom: 0;
  }
  .overview-grid {
    grid-template-columns: 1fr;
    margin-top: 60px;
  }
}
</style>
