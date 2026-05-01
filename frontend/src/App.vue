<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  // 恢复登录状态
  if (authStore.token) {
    await authStore.fetchMe()
  }
})
</script>
