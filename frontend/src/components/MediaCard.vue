<template>
  <div class="media-card" @click="$emit('click')">
    <div class="poster-container">
      <img v-if="item.poster_path" :src="posterUrl" class="poster-img" />
      <div v-else class="no-poster">NO POSTER</div>
      
      <!-- 渐变遮罩 -->
      <div class="gradient-overlay"></div>
      
      <!-- 顶部标签栏 -->
      <div class="top-tags">
        <div class="type-tag" :class="type">{{ type === 'movie' ? 'Movie' : 'TV Show' }}</div>
        <div class="rating-tag" v-if="item.vote_average > 0">{{ item.vote_average.toFixed(1) }}</div>
      </div>
      
      
    </div>
    
    <!-- 标题面板 (原截图有的只有底部的标题) -> 但实际上由于海报自带所以我们可以隐藏底部纯文字，但为了无字幕海报这里保留 -->
    <div class="title-panel">
      <div class="title-text">{{ item.title || item.name }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true },
  type: { type: String, default: 'movie' }
})

const posterUrl = computed(() => {
  return `/api/v1/tmdb/image?path=${props.item.poster_path}`
})
</script>

<style lang="scss" scoped>
.media-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgba(255,255,255,0.02);
  
  &:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 15px 30px rgba(139, 92, 246, 0.15);
    
    .poster-img {
      filter: brightness(1.1);
    }
  }
}

.poster-container {
  width: 100%;
  aspect-ratio: 2 / 3;
  position: relative;
  background: #1e1e1e;
  
  .poster-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: filter 0.3s ease;
  }
  
  .no-poster {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    font-weight: bold;
    letter-spacing: 2px;
  }
  
  .gradient-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.3) 100%);
    pointer-events: none;
  }
}

.top-tags {
  position: absolute;
  top: 10px;
  left: 10px;
  right: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 2;
  
  .type-tag {
    background: rgba(59, 130, 246, 0.85); /* 胶囊型分类标签 (如果是剧集可以是另一种颜色) */
    backdrop-filter: blur(4px);
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 12px;
    letter-spacing: 0.5px;
    
    &.tv { background: rgba(16, 185, 129, 0.85); }
  }
  
  .rating-tag {
    background: rgba(139, 92, 246, 0.9);
    backdrop-filter: blur(4px);
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 12px;
  }
}

.bottom-badges {
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 2;
  
  .tmdb-icon {
    width: 24px;
    height: 24px;
    opacity: 0.8;
  }
}

.title-panel {
  padding: 12px 10px;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 2;
  
  .title-text {
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
  }
}
</style>
