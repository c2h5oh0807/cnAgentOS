<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import { errorMessage } from '@/utils/display'

const router = useRouter()
const session = useSessionStore()
const loading = ref(false)
const credentials = reactive({ username: '', password: '' })

async function submit(): Promise<void> {
  if (!credentials.username || !credentials.password) {
    ElMessage.warning('请输入登录名和密码')
    return
  }
  loading.value = true
  try {
    await session.login(credentials)
    await router.replace('/qa')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-screen">
    <div class="login-bg">
      <div class="login-bg-circle c1" />
      <div class="login-bg-circle c2" />
      <div class="login-bg-circle c3" />
    </div>
    <div class="login-container">
      <div class="login-header">
        <div class="login-logo">
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <rect width="36" height="36" rx="8" fill="#07C160"/>
            <path d="M10 18L16 24L26 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>cnAgentOS</h1>
        <p class="login-subtitle">AI 智能瞭望与问数系统</p>
      </div>
      <div class="login-form">
        <div class="input-group">
          <div class="input-field">
            <input v-model="credentials.username" type="text" autocomplete="username" placeholder="登录名" @keyup.enter="submit" />
            <span class="input-icon">👤</span>
          </div>
          <div class="input-field">
            <input v-model="credentials.password" type="password" autocomplete="current-password" placeholder="密码" @keyup.enter="submit" />
            <span class="input-icon">🔒</span>
          </div>
        </div>
        <button class="login-btn" :class="{ loading }" :disabled="loading" @click="submit">
          <span v-if="loading" class="btn-loading" />
          <span v-else>登 录</span>
        </button>
        <div class="login-footer">
          <router-link to="/register" class="register-link">注册账号</router-link>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.login-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F7F7F7;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-bg-circle {
  position: absolute;
  border-radius: 50%;
}

.login-bg-circle.c1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(7, 193, 96, 0.08), transparent 70%);
  top: -150px; right: -100px;
}

.login-bg-circle.c2 {
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(7, 193, 96, 0.06), transparent 70%);
  bottom: -80px; left: -60px;
}

.login-bg-circle.c3 {
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(7, 193, 96, 0.04), transparent 70%);
  bottom: 30%; right: 10%;
}

.login-container {
  position: relative;
  width: 380px;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 40px 32px 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-logo {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 6px;
  color: #1A1A1A;
  letter-spacing: -0.02em;
}

.login-subtitle {
  margin: 0;
  font-size: 14px;
  color: #999;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.input-field {
  position: relative;
}

.input-field input {
  width: 100%;
  height: 48px;
  padding: 0 16px 0 44px;
  border: 1.5px solid #E5E5E5;
  border-radius: 10px;
  font-size: 15px;
  color: #1A1A1A;
  background: #FAFAFA;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
  box-sizing: border-box;
}

.input-field input:focus {
  border-color: #07C160;
  background: #FFFFFF;
}

.input-field input::placeholder {
  color: #B2B2B2;
}

.input-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  line-height: 1;
  pointer-events: none;
}

.login-btn {
  height: 48px;
  border: none;
  border-radius: 10px;
  background: #07C160;
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.1em;
}

.login-btn:hover {
  background: #06AD56;
}

.login-btn:active {
  transform: scale(0.98);
}

.login-btn.loading {
  background: #B2E6C4;
  cursor: not-allowed;
}

.login-btn:disabled {
  cursor: not-allowed;
}

.btn-loading {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  text-align: center;
}

.register-link {
  color: #999;
  font-size: 13px;
  text-decoration: none;
  transition: color 0.2s;
}

.register-link:hover {
  color: #07C160;
}
</style>
