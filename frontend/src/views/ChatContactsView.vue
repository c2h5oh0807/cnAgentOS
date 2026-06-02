<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { get, patch, post } from '@/api/client'
import { useChatStore } from '@/stores/chat'
import { errorMessage } from '@/utils/display'
import type { ContactItem } from '@/types'

const router = useRouter()
const chat = useChatStore()

const activeTab = ref<'contacts' | 'requests' | 'search'>('contacts')
const searchQuery = ref('')
const searchResults = ref<{ user_id: string; username: string; display_name: string }[]>([])
const loading = ref(false)

async function doSearch(): Promise<void> {
  if (!searchQuery.value) return
  loading.value = true
  try {
    const data = await get<{ user_id: string; username: string; display_name: string }[]>(
      '/api/v1/chat/users/search?q=' + encodeURIComponent(searchQuery.value) + '&page_size=20'
    )
    searchResults.value = data
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

async function doSendRequest(username: string): Promise<void> {
  try {
    await post('/api/v1/chat/friend-requests', { username })
    ElMessage.success('好友请求已发送')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function handleReq(requestId: string, action: 'accept' | 'reject'): Promise<void> {
  try {
    await patch('/api/v1/chat/friend-requests/' + requestId, { action })
    await chat.loadFriendRequests()
    if (action === 'accept') await chat.loadContacts()
    ElMessage.success(action === 'accept' ? '已添加好友' : '已拒绝')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function chatWith(_contact: ContactItem): void {
  router.push('/chat')
}

onMounted(() => {
  chat.loadContacts()
  chat.loadFriendRequests()
})
</script>

<template>
  <div class="wx-contacts-page">
    <div class="wx-contacts-tabs">
      <button :class="{ active: activeTab === 'contacts' }" @click="activeTab = 'contacts'">
        联系人
        <span class="wx-contacts-count">{{ chat.contacts.length }}</span>
      </button>
      <button :class="{ active: activeTab === 'requests' }" @click="activeTab = 'requests'">
        请求
        <span v-if="chat.incomingRequests.length" class="wx-badge">{{ chat.incomingRequests.length }}</span>
      </button>
      <button :class="{ active: activeTab === 'search' }" @click="activeTab = 'search'">查找用户</button>
    </div>

    <!-- Contacts list -->
    <div v-if="activeTab === 'contacts'" class="wx-contacts-list">
      <div v-if="chat.contacts.length === 0" class="wx-contacts-empty">暂无联系人</div>
      <div
        v-for="c in chat.contacts"
        :key="c.user_id"
        class="wx-contact-item"
        @click="chatWith(c)"
      >
        <div class="wx-contact-avatar">{{ (c.remark || c.display_name)[0] }}</div>
        <div class="wx-contact-body">
          <strong>{{ c.remark || c.display_name }}</strong>
          <span class="wx-contact-username">@{{ c.username }}</span>
        </div>
      </div>
    </div>

    <!-- Requests -->
    <div v-else-if="activeTab === 'requests'" class="wx-contacts-list">
      <div v-if="chat.incomingRequests.length === 0" class="wx-contacts-empty">暂无待处理请求</div>
      <div v-for="req in chat.incomingRequests" :key="req.id" class="wx-contact-item request">
        <div class="wx-contact-avatar">{{ req.from_user_name[0] }}</div>
        <div class="wx-contact-body">
          <strong>{{ req.from_user_name }}</strong>
          <p v-if="req.message" class="wx-contact-msg">{{ req.message }}</p>
        </div>
        <div class="wx-contact-actions">
          <button class="wx-action-accept" @click="handleReq(req.id, 'accept')">接受</button>
          <button class="wx-action-reject" @click="handleReq(req.id, 'reject')">拒绝</button>
        </div>
      </div>
    </div>

    <!-- Search -->
    <div v-else class="wx-contacts-list">
      <div class="wx-search-bar">
        <input v-model="searchQuery" placeholder="输入用户名搜索" @keyup.enter="doSearch" />
        <button class="wx-search-btn" :disabled="loading" @click="doSearch">{{ loading ? '搜索中...' : '搜索' }}</button>
      </div>
      <div v-if="searchResults.length > 0" class="wx-search-results">
        <div v-for="u in searchResults" :key="u.user_id" class="wx-contact-item">
          <div class="wx-contact-avatar">{{ u.display_name[0] }}</div>
          <div class="wx-contact-body">
            <strong>{{ u.display_name }}</strong>
            <span class="wx-contact-username">@{{ u.username }}</span>
          </div>
          <button class="wx-add-contact-btn" @click="doSendRequest(u.username)">添加</button>
        </div>
      </div>
      <div v-else-if="searchQuery && !loading" class="wx-contacts-empty">未找到用户</div>
    </div>
  </div>
</template>

<style scoped>
.wx-contacts-page {
  padding: 0;
  max-width: 640px;
  margin: 0 auto;
}

.wx-contacts-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg-hover);
  border-radius: 8px;
  padding: 2px;
  margin-bottom: 16px;
}

.wx-contacts-tabs button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  transition: all 0.15s;
}

.wx-contacts-tabs button.active {
  background: var(--bg-card);
  color: var(--text-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.wx-contacts-count {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 400;
}

.wx-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--wx-red);
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.wx-contacts-list {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  overflow: hidden;
}

.wx-contacts-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.wx-contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background 0.12s;
}

.wx-contact-item:last-child { border-bottom: none; }
.wx-contact-item:hover { background: var(--bg-hover); }
.wx-contact-item.request { cursor: default; }

.wx-contact-avatar {
  width: 42px;
  height: 42px;
  border-radius: 6px;
  background: var(--wx-green);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}

.wx-contact-body {
  flex: 1;
  min-width: 0;
}

.wx-contact-body strong {
  display: block;
  font-size: 15px;
  color: var(--text-primary);
}

.wx-contact-username {
  display: block;
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 2px;
}

.wx-contact-msg {
  font-size: 13px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.wx-contact-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.wx-action-accept, .wx-add-contact-btn {
  padding: 5px 14px;
  border: none;
  border-radius: 6px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.wx-action-accept:hover, .wx-add-contact-btn:hover { background: var(--wx-green-hover); }

.wx-action-reject {
  padding: 5px 14px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
}

.wx-search-bar {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
}

.wx-search-bar input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1.5px solid var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-input);
  outline: none;
  box-sizing: border-box;
}

.wx-search-bar input:focus { border-color: var(--wx-green); }

.wx-search-btn {
  padding: 0 18px;
  border: none;
  border-radius: 8px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.wx-search-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.wx-search-results {
  display: flex;
  flex-direction: column;
}
</style>
