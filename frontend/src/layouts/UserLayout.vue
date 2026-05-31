<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import { errorMessage } from '@/utils/display'

const router = useRouter()
const session = useSessionStore()

async function logout(): Promise<void> {
  try {
    await session.logout()
  } catch (error) {
    ElMessage.warning(errorMessage(error))
  } finally {
    await router.replace('/login')
  }
}
</script>

<template>
  <div class="console-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-monogram">CN</span>
        <span><strong>cnAgentOS</strong><small>智能平台</small></span>
      </div>
      <p class="sidebar-label">用户功能</p>
      <nav class="sidebar-navigation">
        <router-link to="/qa" class="nav-link">
          <span class="nav-icon sparkles" />
          <span>智能问数</span>
        </router-link>
        <router-link to="/chat" class="nav-link">
          <span class="nav-icon chat" />
          <span>智能聊天</span>
        </router-link>
      </nav>
    </aside>
    <section class="workspace">
      <header class="topbar">
        <div class="environment-pill"><span /> 用户工作区</div>
        <div class="account-actions">
          <span class="account-name">{{ session.user?.display_name }} · {{ session.user?.username }}</span>
          <el-button plain @click="logout">退出</el-button>
        </div>
      </header>
      <main class="page-content">
        <router-view />
      </main>
    </section>
  </div>
</template>
