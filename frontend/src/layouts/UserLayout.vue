<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import { useTheme } from '@/composables/useTheme'
import { errorMessage } from '@/utils/display'

const router = useRouter()
const session = useSessionStore()
const { isDark, toggle: toggleTheme } = useTheme()

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
  <div class="wx-app">
    <!-- Compact sidebar (WeChat Desktop-style) -->
    <aside class="wx-nav">
      <div class="wx-nav-avatar">
        <div class="nav-avatar-circle">
          {{ (session.user?.display_name || 'U')[0] }}
        </div>
      </div>
      <nav class="wx-nav-items">
        <router-link to="/qa" class="wx-nav-item" :class="{ active: $route.path === '/qa' }" title="智能问数">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span>问数</span>
        </router-link>
        <router-link to="/chat" class="wx-nav-item" :class="{ active: $route.path.startsWith('/chat') }" title="智能聊天">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span>聊天</span>
        </router-link>
      </nav>
      <div class="wx-nav-bottom">
        <button class="wx-nav-item logout-btn" title="退出登录" @click="logout">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>

    <!-- Main workspace -->
    <section class="wx-main">
      <header class="wx-topbar">
        <div class="wx-topbar-left">
          <span class="wx-topbar-title">
            <template v-if="$route.path === '/qa'">智能问数</template>
            <template v-else-if="$route.path.startsWith('/chat')">智能聊天</template>
            <template v-else>cnAgentOS</template>
          </span>
        </div>
        <div class="wx-topbar-right">
          <button class="wx-theme-btn" :title="isDark ? '切换到亮色' : '切换到暗色'" @click="toggleTheme">
            <svg v-if="!isDark" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
          <span class="wx-topbar-user">{{ session.user?.display_name }}</span>
        </div>
      </header>
      <main class="wx-content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<style scoped>
.wx-app {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-page);
}

/* ── Left compact nav (WeChat Desktop style) ──────────────────────────── */
.wx-nav {
  width: 68px;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0 12px;
  flex-shrink: 0;
  border-right: 1px solid rgba(255,255,255,0.06);
}

.wx-nav-avatar {
  margin-bottom: 20px;
}

.nav-avatar-circle {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--wx-green);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
  transition: border-radius 0.2s;
}

.nav-avatar-circle:hover {
  border-radius: 12px;
}

.wx-nav-items {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 0 10px;
}

.wx-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 0;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
  background: transparent;
  font-size: 10px;
}

.wx-nav-item span {
  font-size: 10px;
  line-height: 1;
}

.wx-nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}

.wx-nav-item.active {
  color: var(--wx-green);
  background: rgba(7, 193, 96, 0.12);
}

.wx-nav-item.logout-btn {
  margin-top: auto;
  padding: 10px;
  width: 100%;
}

.wx-nav-item.logout-btn:hover {
  color: var(--wx-red);
  background: rgba(250, 81, 81, 0.1);
}

.wx-nav-bottom {
  width: 100%;
  padding: 0 10px;
  margin-top: auto;
}

/* ── Main area ──────────────────────────────────────────────────────────── */
.wx-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.wx-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.wx-topbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.wx-topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wx-topbar-user {
  font-size: 13px;
  color: var(--text-muted);
}

.wx-theme-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.wx-theme-btn:hover {
  background: var(--wx-green-light);
  color: var(--wx-green);
}

.wx-content {
  flex: 1;
  overflow: auto;
  min-height: 0;
}
</style>
