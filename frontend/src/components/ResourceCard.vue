<template>
  <div class="resource-card" @click="$emit('click')">
    <!-- 顶部徽章 -->
    <div class="card-badges">
      <span v-if="item.sources && item.sources.length > 1" class="badge multi-site">
        聚合 {{ item.sources.length }} 站
      </span>
      <span v-if="item.free" class="badge free">{{ item.free }}</span>
      <span v-if="meta.season" class="badge season">{{ meta.season }}</span>
    </div>

    <!-- 站点标识 -->
    <div class="site-info">
      <div class="site-stack" v-if="item.sources && item.sources.length > 1">
        <div class="site-avatar stack-1">{{ item.sources[0].site_name.charAt(0) }}</div>
        <div class="site-avatar stack-2" v-if="item.sources[1]">{{ item.sources[1].site_name.charAt(0) }}</div>
      </div>
      <div class="site-avatar" v-else>{{ item.site_name.charAt(0) }}</div>
      <span class="site-name">
        <template v-if="item.sources && item.sources.length > 1">多站聚合</template>
        <template v-else>{{ item.site_name }}</template>
      </span>
    </div>

    <!-- 标题区 -->
    <div class="title-area">
      <h3 class="main-title" :title="item.title">{{ item.title }}</h3>
      <p v-if="item.description" class="sub-title">{{ item.description }}</p>
    </div>

    <!-- 标签网格 -->
    <div class="tags-row">
      <el-tag v-if="meta.resolution" size="small" :type="getTagColor('resolution', meta.resolution)" effect="dark">
        {{ meta.resolution }}
      </el-tag>
      <el-tag v-if="meta.source" size="small" :type="getTagColor('source', meta.source)" effect="plain">
        {{ meta.source }}
      </el-tag>
      <el-tag v-if="meta.codec" size="small" type="info" effect="plain">
        {{ meta.codec }}
      </el-tag>
      <el-tag v-for="h in meta.hdr" :key="h" size="small" type="warning" effect="dark">
        {{ h }}
      </el-tag>
    </div>

    <!-- 底部属性 -->
    <div class="meta-footer">
      <div class="meta-item">
        <el-icon><DataLine /></el-icon>
        {{ formatSize(item.size) }}
      </div>
      <div class="meta-item seeders">
        <el-icon><CaretTop /></el-icon>
        {{ item.seeders }}
      </div>
      <div class="meta-item">
        <el-icon><Bottom /></el-icon>
        {{ item.downloads || 0 }}
      </div>
    </div>

    <!-- 操作浮层 (Hover) -->
    <div class="action-overlay">
      <el-button 
        type="primary" 
        circle 
        :icon="Download" 
        :loading="downloading"
        @click.stop="$emit('download')"
      />
      <el-button 
        circle 
        :icon="Link" 
        @click.stop="$emit('open')"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DataLine, CaretTop, Bottom, Download, Link } from '@element-plus/icons-vue'
import { parseTorrentTitle, getTagColor } from '@/utils/torrentParser'

const props = defineProps({
  item: { type: Object, required: true },
  downloading: { type: Boolean, default: false }
})

defineEmits(['download', 'open', 'click'])

const meta = computed(() => parseTorrentTitle(props.item.title))

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style lang="scss" scoped>
.resource-card {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  cursor: pointer;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(99, 102, 241, 0.5);
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);

    .action-overlay {
      opacity: 1;
      transform: translateY(0);
    }
  }
}

.card-badges {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  gap: 1px;
  z-index: 2;

  .badge {
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    border-bottom-left-radius: 8px;
    
    &.free {
      background: linear-gradient(135deg, #10b981, #059669);
      color: #fff;
    }
    &.multi-site {
      background: linear-gradient(135deg, #8b5cf6, #d946ef);
      color: #fff;
    }
    &.season {
      background: #6366f1;
      color: #fff;
    }
  }
}

.site-info {
  display: flex;
  align-items: center;
  gap: 8px;

  .site-stack {
    position: relative;
    width: 30px;
    height: 20px;
    
    .site-avatar {
      position: absolute;
      top: 0;
      &.stack-1 { left: 0; z-index: 2; }
      &.stack-2 { 
        left: 10px; 
        z-index: 1; 
        opacity: 0.6;
        filter: grayscale(0.5);
      }
    }
  }
  
  .site-avatar {
    width: 20px;
    height: 20px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    color: #fff;
  }
  
  .site-name {
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.title-area {
  flex: 1;
  .main-title {
    font-size: 14px;
    font-weight: 600;
    color: #fff;
    line-height: 1.4;
    margin-bottom: 4px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-all;
  }
  
  .sub-title {
    font-size: 12px;
    color: rgba(255,255,255,0.4);
    display: -webkit-box;
    -webkit-line-clamp: 1;
    line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;

  :deep(.el-tag) {
    border: none;
    height: 18px;
    padding: 0 6px;
    font-size: 10px;
    font-weight: 700;
  }
}

.meta-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.05);
  
  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    font-weight: 600;
    
    &.seeders {
      color: #10b981;
    }
  }
}

.action-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.3s ease;
  z-index: 5;
  
  .el-button {
    width: 40px;
    height: 40px;
    border: none;
    background: #6366f1;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    
    &:last-child {
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(4px);
      box-shadow: none;
    }
  }
}
</style>
