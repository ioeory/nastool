<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">🎬</div>
        <h1 class="login-title">NasTool</h1>
        <p class="login-subtitle">NAS 媒体库自动化管理</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
            autocomplete="username"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="handleLogin"
        >
          登 录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await authStore.login(form.username, form.password)
      const redirect = route.query.redirect || '/dashboard'
      router.push(redirect)
    } catch (e) {
      ElMessage.error('登录失败，请检查用户名和密码')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
}

.login-card {
  width: 380px;
  padding: 48px 40px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-logo {
  font-size: 52px;
  margin-bottom: 12px;
  filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.8));
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 4px;
  letter-spacing: 2px;
}

.login-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.login-form {
  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: none;
    border-radius: 10px;
    &:hover, &.is-focus {
      border-color: #6366f1;
    }
  }
  :deep(.el-input__inner) {
    color: #fff;
    &::placeholder { color: rgba(255,255,255,0.3); }
  }
  :deep(.el-input__prefix-icon) {
    color: rgba(255,255,255,0.4);
  }
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  margin-top: 8px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  letter-spacing: 4px;
  transition: all 0.3s;
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5);
  }
}
</style>
