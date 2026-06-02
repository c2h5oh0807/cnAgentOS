<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import AppNavigation from '@/components/AppNavigation.vue'
import type { NavigationItem } from '@/types'
import { useSessionStore } from '@/stores/session'
import { useTheme } from '@/composables/useTheme'
import { errorMessage } from '@/utils/display'

const router = useRouter()
const session = useSessionStore()
const { isDark, toggle: toggleTheme } = useTheme()

/** Admin sidebar only shows cluster parents and /admin/* routes — filter out standalone user links like "智能问数". */
const adminNavigation = computed<NavigationItem[]>(() =>
  session.navigation.filter(n => n.children?.length || n.route_path?.startsWith('/admin')),
)

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
  <div class="admin-app">
    <!-- Sidebar -->
    <aside class="admin-sidebar">
      <div class="admin-sidebar-header">
        <div class="admin-logo">
          <svg width="32" height="32" viewBox="0 0 36 36" fill="none">
            <rect width="36" height="36" rx="8" fill="#07C160"/>
            <path d="M10 18L16 24L26 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="admin-brand">
          <strong>cnAgentOS</strong>
          <small>管理控制台</small>
        </div>
      </div>

      <nav class="admin-nav">
        <app-navigation :nodes="adminNavigation" class="admin-nav-tree" />
      </nav>

      <div class="admin-sidebar-footer">
        <button class="admin-logout-btn" @click="logout">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          退出登录
        </button>
      </div>
    </aside>

    <!-- Main area -->
    <section class="admin-main">
      <header class="admin-topbar">
        <div class="admin-topbar-left">
          <span class="admin-breadcrumb">管理控制台</span>
        </div>
        <div class="admin-topbar-right">
          <button class="admin-theme-btn" :title="isDark ? '切换到亮色' : '切换到暗色'" @click="toggleTheme">
            <!-- sun icon (light) -->
            <svg v-if="!isDark" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <!-- moon icon (dark) -->
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
          <span class="admin-topbar-user">{{ session.user?.display_name || '管理员' }}</span>
          <span class="admin-topbar-divider" />
          <router-link to="/qa" class="admin-goto-user" title="前往用户端">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            用户端
          </router-link>
        </div>
      </header>
      <main class="admin-content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<style scoped>
.admin-app {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-page);
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
.admin-sidebar {
  width: 240px;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.admin-sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 14px;
  border-bottom: 1px solid var(--border-light);
}

.admin-logo {
  flex-shrink: 0;
}

.admin-brand strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.admin-brand small {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}

/* ── Navigation ──────────────────────────────────────────────────────────── */
.admin-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.admin-nav-tree :deep(.nav-cluster-title) {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 12px 16px 6px;
  margin: 0;
}

.admin-nav-tree :deep(.nav-link) {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin: 2px 6px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.15s;
}

.admin-nav-tree :deep(.nav-link:hover) {
  background: var(--wx-green-bg);
  color: var(--wx-green);
}

.admin-nav-tree :deep(.nav-link.router-link-active) {
  background: var(--wx-green-light);
  color: var(--wx-green);
  font-weight: 600;
}

.admin-nav-tree :deep(.nav-link .el-icon) {
  font-size: 18px;
}

/* ── Sidebar footer ────────────────────────────────────────────────────── */
.admin-sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-light);
}

.admin-logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  border-radius: 8px;
  width: 100%;
  transition: all 0.15s;
}

.admin-logout-btn:hover {
  background: rgba(250, 81, 81, 0.06);
  color: var(--wx-red);
}

/* ── Main area ──────────────────────────────────────────────────────────── */
.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.admin-breadcrumb {
  font-size: 14px;
  color: var(--text-muted);
}

.admin-topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-topbar-user {
  font-size: 13px;
  color: var(--text-muted);
}

.admin-topbar-divider {
  width: 1px;
  height: 16px;
  background: var(--border-color);
}

.admin-theme-btn {
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

.admin-theme-btn:hover {
  background: var(--wx-green-light);
  color: var(--wx-green);
}

.admin-goto-user {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 8px;
  transition: all 0.15s;
}

.admin-goto-user:hover {
  background: var(--wx-green-light);
  color: var(--wx-green);
}

.admin-content {
  flex: 1;
  overflow: auto;
  padding: 24px;
  min-height: 0;
}
</style>
