<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { post } from '@/api/client'
import { errorMessage } from '@/utils/display'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  username: '',
  display_name: '',
  password: '',
  password_confirm: '',
})

async function submit(): Promise<void> {
  if (!form.username || !form.display_name || !form.password || !form.password_confirm) {
    ElMessage.warning('请填写所有字段')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码至少 6 个字符')
    return
  }
  if (form.password !== form.password_confirm) {
    ElMessage.warning('两次密码输入不一致')
    return
  }
  loading.value = true
  try {
    await post('/api/v1/auth/register', {
      username: form.username,
      display_name: form.display_name,
      password: form.password,
    })
    ElMessage.success('注册成功，请登录')
    await router.replace('/login')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="register-screen">
    <div class="register-bg">
      <div class="register-bg-circle c1" />
      <div class="register-bg-circle c2" />
    </div>
    <div class="register-container">
      <div class="register-header">
        <router-link to="/login" class="back-link">← 返回登录</router-link>
        <h1>创建账号</h1>
        <p class="register-subtitle">注册后即可使用智能问数和聊天功能</p>
      </div>
      <div class="register-form">
        <div class="input-field">
          <label>用户名</label>
          <input v-model="form.username" type="text" autocomplete="username" placeholder="4-30 字符，字母开头" />
        </div>
        <div class="input-field">
          <label>显示名</label>
          <input v-model="form.display_name" type="text" placeholder="你的显示名称" />
        </div>
        <div class="input-field">
          <label>密码</label>
          <input v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 6 个字符" />
        </div>
        <div class="input-field">
          <label>确认密码</label>
          <input v-model="form.password_confirm" type="password" autocomplete="new-password" placeholder="再次输入密码" @keyup.enter="submit" />
        </div>
        <button class="register-btn" :class="{ loading }" :disabled="loading" @click="submit">
          <span v-if="loading" class="btn-loading" />
          <span v-else>注 册</span>
        </button>
      </div>
    </div>
  </main>
</template>

<style scoped>
.register-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F7F7F7;
  position: relative;
  overflow: hidden;
}

.register-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.register-bg-circle {
  position: absolute;
  border-radius: 50%;
}

.register-bg-circle.c1 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(7, 193, 96, 0.08), transparent 70%);
  top: -100px; left: -120px;
}

.register-bg-circle.c2 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(7, 193, 96, 0.06), transparent 70%);
  bottom: -60px; right: -80px;
}

.register-container {
  position: relative;
  width: 400px;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  z-index: 1;
}

.register-header {
  margin-bottom: 28px;
}

.back-link {
  display: inline-block;
  font-size: 13px;
  color: #999;
  text-decoration: none;
  margin-bottom: 16px;
  transition: color 0.2s;
}

.back-link:hover {
  color: #07C160;
}

.register-header h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 6px;
  color: #1A1A1A;
}

.register-subtitle {
  margin: 0;
  font-size: 14px;
  color: #999;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-field label {
  font-size: 13px;
  font-weight: 600;
  color: #666;
}

.input-field input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1.5px solid #E5E5E5;
  border-radius: 10px;
  font-size: 14px;
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

.register-btn {
  height: 46px;
  border: none;
  border-radius: 10px;
  background: #07C160;
  color: #FFFFFF;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.1em;
  margin-top: 8px;
}

.register-btn:hover {
  background: #06AD56;
}

.register-btn:active {
  transform: scale(0.98);
}

.register-btn.loading {
  background: #B2E6C4;
  cursor: not-allowed;
}

.register-btn:disabled {
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
</style>
