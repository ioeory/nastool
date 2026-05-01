<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="sidebar-header">
        <span class="logo-icon">🎬</span>
        <span v-show="!collapsed" class="logo-text">NasTool</span>
      </div>

      <el-menu
        :default-active="$route.path"
        router
        :collapse="collapsed"
        class="sidebar-menu"
        background-color="transparent"
        text-color="rgba(255,255,255,0.7)"
        active-text-color="#fff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-menu-item index="/site">
          <el-icon><Monitor /></el-icon>
          <template #title>站点管理</template>
        </el-menu-item>
        <el-menu-item index="/explore">
          <el-icon><Compass /></el-icon>
          <template #title>发现与探索</template>
        </el-menu-item>
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <template #title>搜索资源</template>
        </el-menu-item>
        <el-menu-item index="/subscribe">
          <el-icon><Bell /></el-icon>
          <template #title>订阅追剧</template>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><List /></el-icon>
          <template #title>整理历史</template>
        </el-menu-item>
        <el-menu-item index="/workflow">
          <el-icon><Operation /></el-icon>
          <template #title>自动化任务</template>
        </el-menu-item>
        <div class="sidebar-spacer" />
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
        <el-menu-item index="/downloader">
          <el-icon><Connection /></el-icon>
          <template #title>下载器与节点</template>
        </el-menu-item>
      </el-menu>

      <!-- 用户信息 -->
      <div class="sidebar-footer" v-show="!collapsed">
        <el-avatar :size="32" class="user-avatar">
          {{ authStore.user?.name?.charAt(0).toUpperCase() }}
        </el-avatar>
        <span class="user-name">{{ authStore.user?.name }}</span>
        <el-button
          :icon="SwitchButton"
          circle
          size="small"
          class="logout-btn"
          @click="handleLogout"
        />
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶栏 -->
      <el-header class="main-header">
        <el-button :icon="collapsed ? Expand : Fold" circle @click="collapsed = !collapsed" />
        <div class="header-title">{{ $route.meta.title }}</div>
        <div class="header-right">
          <el-tag type="success" size="small">在线</el-tag>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Odometer, Monitor, Search, Bell, List, Setting, Connection, Compass,
  SwitchButton, Expand, Fold, Operation
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

async function handleLogout() {
  await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
  authStore.logout()
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  border-right: 1px solid rgba(255,255,255,0.06);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}

.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;

  .logo-icon { font-size: 28px; }
  .logo-text {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 2px;
    white-space: nowrap;
  }
}

.sidebar-menu {
  flex: 1;
  border: none;
  padding: 12px 8px;
  overflow-y: auto;

  :deep(.el-menu-item) {
    border-radius: 10px;
    margin: 2px 0;
    height: 46px;
    &.is-active {
      background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
      color: #fff !important;
      box-shadow: 0 4px 15px rgba(99,102,241,0.4);
    }
    &:hover:not(.is-active) {
      background: rgba(255,255,255,0.08) !important;
      color: #fff !important;
    }
  }
}

.sidebar-spacer { flex: 1; }

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;

  .user-avatar {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .user-name {
    color: rgba(255,255,255,0.8);
    font-size: 13px;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .logout-btn {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.5);
    flex-shrink: 0;
    &:hover { color: #f87171; border-color: #f87171; }
  }
}

.main-container {
  background: #0d1117;
  overflow: hidden;
}

.main-header {
  height: 64px;
  background: #0d1117;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  flex-shrink: 0;

  .header-title {
    font-size: 16px;
    font-weight: 600;
    color: rgba(255,255,255,0.9);
    flex: 1;
  }
}

.main-content {
  overflow-y: auto;
  padding: 24px;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
