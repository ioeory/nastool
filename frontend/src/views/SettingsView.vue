<template>
  <div class="settings-view">
    <div class="page-card settings-header">
      <div class="settings-title">
        <h2>系统设置</h2>
        <span class="settings-subtitle">配置下载器、基础代理以及系统核心变量参数</span>
      </div>
    </div>

    <div class="settings-content" v-loading="loading">
      <el-form :model="form" label-width="150px" label-position="left">
        

        <el-card shadow="never" class="settings-card">
          <template #header>
            <div class="card-header">目录与辅助设置</div>
          </template>
          

          <el-form-item label="媒体库路径">
            <el-input v-model="form.LIBRARY_PATH" placeholder="/media/library" />
          </el-form-item>
          <el-form-item label="代理地址">
            <el-input v-model="form.PROXY_HOST" placeholder="http://127.0.0.1:7890 (可选)" />
          </el-form-item>
          <el-form-item label="TMDB API Key">
            <el-input v-model="form.TMDB_API_KEY" placeholder="(可选) 用于获取剧情、海报等" />
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="settings-card">
          <template #header>
            <div class="card-header">媒体服务器 (Emby / Jellyfin)</div>
          </template>
          
          <el-form-item label="Emby 地址">
            <el-input v-model="form.EMBY_HOST" placeholder="http://127.0.0.1:8096" />
          </el-form-item>
          <el-form-item label="Emby API Key">
            <el-input v-model="form.EMBY_API_KEY" type="password" show-password />
          </el-form-item>
          <el-divider border-style="dashed" />
          <el-form-item label="Jellyfin 地址">
            <el-input v-model="form.JELLYFIN_HOST" placeholder="http://127.0.0.1:8096" />
          </el-form-item>
          <el-form-item label="Jellyfin API Key">
            <el-input v-model="form.JELLYFIN_API_KEY" type="password" show-password />
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="settings-card">
          <template #header>
            <div class="card-header">消息通知 (Telegram / 企业微信)</div>
          </template>
          
          <el-form-item label="TG Bot Token">
            <el-input v-model="form.TELEGRAM_BOT_TOKEN" placeholder="123456789:AAxx..." type="password" show-password />
          </el-form-item>
          <el-form-item label="TG Chat ID">
            <el-input v-model="form.TELEGRAM_CHAT_ID" placeholder="Your Chat ID" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" size="small" plain @click="testNotification('telegram')">测试 Telegram</el-button>
          </el-form-item>
          
          <el-divider border-style="dashed" />
          
          <el-form-item label="企业微信 CorpID">
            <el-input v-model="form.WECHAT_CORP_ID" />
          </el-form-item>
          <el-form-item label="企业微信 Secret">
            <el-input v-model="form.WECHAT_CORP_SECRET" type="password" show-password />
          </el-form-item>
          <el-form-item label="企业微信 AgentID">
            <el-input v-model="form.WECHAT_AGENT_ID" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" size="small" plain @click="testNotification('wechat')">测试企业微信</el-button>
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="settings-card">
          <template #header>
            <div class="card-header">CookieCloud 自动同步</div>
          </template>
          <el-form-item label="服务地址">
            <el-input v-model="form.COOKIECLOUD_HOST" placeholder="http://127.0.0.1:8088" />
          </el-form-item>
          <el-form-item label="用户 KEY">
            <el-input v-model="form.COOKIECLOUD_KEY" type="password" show-password />
          </el-form-item>
          <el-form-item label="端对端密码">
            <el-input v-model="form.COOKIECLOUD_PASSWORD" type="password" show-password />
          </el-form-item>
        </el-card>

      </el-form>

      <div class="bottom-actions">
        <el-button type="primary" class="save-btn" icon="Check" :loading="saving" @click="saveSettings">
          保存全部配置
        </el-button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { Connection, Check } from '@element-plus/icons-vue'
import { systemApi } from '@/api'

const loading = ref(false)
const saving = ref(false)

const form = ref({
  LIBRARY_PATH: '',
  PROXY_HOST: '',
  USE_PROXY: false,
  TMDB_API_KEY: '',
  EMBY_HOST: '',
  EMBY_API_KEY: '',
  JELLYFIN_HOST: '',
  JELLYFIN_API_KEY: '',
  TELEGRAM_BOT_TOKEN: '',
  TELEGRAM_CHAT_ID: '',
  WECHAT_CORP_ID: '',
  WECHAT_CORP_SECRET: '',
  WECHAT_AGENT_ID: '',
  COOKIECLOUD_HOST: '',
  COOKIECLOUD_KEY: '',
  COOKIECLOUD_PASSWORD: ''
})

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  loading.value = true
  try {
    const res = await systemApi.getSettings()
    if (res.data) {
      // 合并到 form 变量
      for (const k in res.data) {
        if (form.value.hasOwnProperty(k)) {
          form.value[k] = res.data[k]
        }
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const res = await systemApi.saveSettings(form.value)
    ElMessage.success(res.message || '配置保存成功，并且已经热更新！')
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

async function testNotification(channel) {
  const loading = ElLoading.service({ text: `正在发送 ${channel} 测试消息...` })
  try {
    const res = await systemApi.testNotification({
      channel: channel,
      config: form.value
    })
    if (res.code === 0) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('测试组件连接失败，请检查后端状态')
  } finally {
    loading.close()
  }
}

</script>

<style lang="scss" scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-header {
  padding: 30px;
  background: var(--bg-surface);
  box-shadow: var(--shadow);
  border-left: 4px solid #f59e0b;
}

.settings-title {
  h2 { font-size: 24px; color: #fff; margin-bottom: 6px; }
  .settings-subtitle { font-size: 14px; color: var(--text-muted); }
}

.settings-content {
  max-width: 800px;
}

.settings-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  margin-bottom: 20px;
  
  :deep(.el-card__header) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(0, 0, 0, 0.1);
  }
  
  .card-header {
    font-size: 16px;
    font-weight: 600;
    color: #f59e0b;
  }
}

:deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
  
  &.is-focus {
    border-color: #f59e0b;
  }
}

:deep(.el-input__inner) {
  color: #fff;
}

.bottom-actions {
  margin-top: 30px;
  display: flex;
  justify-content: flex-start;
  
  .save-btn {
    padding: 20px 40px;
    font-size: 16px;
    border-radius: 8px;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border: none;
    
    &:hover {
      background: linear-gradient(135deg, #fbbf24, #f59e0b);
      box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
    }
  }
}
</style>
