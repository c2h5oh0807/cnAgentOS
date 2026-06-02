<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import { get, post, postFormData } from '@/api/client'
import EmojiPicker from '@/components/EmojiPicker.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { errorMessage } from '@/utils/display'
import type { AdminFileItem, ConversationMemberItem, ConversationItem, DigitalEmployeeItem } from '@/types'

const session = useSessionStore()
const chat = useChatStore()

// --- Tab state ---
const activeTab = ref<'chats' | 'contacts'>('chats')
const chatSearch = ref('')
const contactSearch = ref('')
const employees = ref<DigitalEmployeeItem[]>([])
const loadingEmployees = ref(false)

// --- Dialogs ---
const showAddFriend = ref(false)
const friendSearch = ref('')
const searchResults = ref<{ user_id: string; username: string; display_name: string }[]>([])
const showFriendRequests = ref(false)
const showMembers = ref(false)
const memberList = ref<ConversationMemberItem[]>([])
const showCreateGroup = ref(false)
const groupName = ref('')
const groupMembers = ref('')

// --- Composer ---
const newMessage = ref('')
const messagePane = ref<HTMLElement | null>(null)

// --- File upload ---
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const fileMetaCache = ref<Map<string, AdminFileItem>>(new Map())

// --- Helpers ---
function getFileMeta(fileId: string): AdminFileItem | undefined {
  return fileMetaCache.value.get(fileId)
}

function formatFileSize(bytes?: number): string {
  if (bytes == null) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getPreviewText(content?: string, contentType?: string): string {
  if (!content) return ''
  if (contentType === 'image') return '[图片]'
  if (contentType === 'file') return '[文件]'
  return content
}

async function fetchFileMeta(fileId: string): Promise<void> {
  if (fileMetaCache.value.has(fileId)) return
  try {
    const meta = await get<AdminFileItem>('/api/v1/chat/files/' + fileId)
    fileMetaCache.value = new Map(fileMetaCache.value).set(fileId, meta)
  } catch {
    // Silently ignore — metadata unavailable
  }
}

// --- Computed ---
const activeConversation = computed(() =>
  chat.conversations.find(c => c.id === chat.activeConversationId)
)

const conversationTitle = computed(() => {
  const conv = activeConversation.value
  if (!conv) return ''
  if (conv.type === 'group') return conv.name || '群聊'
  return conv.name || '私聊'
})

const filteredConversations = computed(() => {
  if (!chatSearch.value) return chat.conversations
  const q = chatSearch.value.toLowerCase()
  return chat.conversations.filter(c => (c.name || '').toLowerCase().includes(q))
})

const filteredContacts = computed(() => {
  if (!contactSearch.value) return chat.contacts
  const q = contactSearch.value.toLowerCase()
  return chat.contacts.filter(
    c => c.display_name.toLowerCase().includes(q) || c.username.toLowerCase().includes(q)
  )
})

// --- Methods ---

function openConversation(conv: ConversationItem): void {
  chat.setActiveConversation(conv.id)
  conv.unread_count = 0
}

async function startPrivateChat(contact: { user_id: string }): Promise<void> {
  const existing = chat.conversations.find(
    c => c.type === 'private' && c.other_user_id === contact.user_id
  )
  if (existing) {
    openConversation(existing)
    return
  }
  try {
    const conv = await chat.createPrivateConversation(contact.user_id)
    openConversation(conv)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function handleActionCommand(command: string): void {
  if (command === 'addFriend') showAddFriend.value = true
  else if (command === 'createGroup') showCreateGroup.value = true
}

async function doSearchUsers(): Promise<void> {
  if (!friendSearch.value) return
  try {
    const data = await get<{ user_id: string; username: string; display_name: string }[]>(
      '/api/v1/chat/users/search?q=' + encodeURIComponent(friendSearch.value) + '&page_size=20'
    )
    searchResults.value = data
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function doSendRequest(username: string): Promise<void> {
  try {
    await chat.sendFriendRequest(username)
    ElMessage.success('好友请求已发送')
    showAddFriend.value = false
    friendSearch.value = ''
    searchResults.value = []
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function handleFriendReq(requestId: string, action: 'accept' | 'reject'): Promise<void> {
  try {
    await chat.handleFriendRequest(requestId, action)
    ElMessage.success(action === 'accept' ? '已添加好友' : '已拒绝')
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function loadMembers(): Promise<void> {
  if (!chat.activeConversationId) return
  try {
    memberList.value = await get<ConversationMemberItem[]>(
      '/api/v1/chat/conversations/' + chat.activeConversationId + '/members'
    )
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function showMemberDialog(): void {
  showMembers.value = true
  loadMembers()
}

async function confirmLeaveGroup(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定退出群聊？', '退出群聊')
    await chat.leaveGroup(chat.activeConversationId!)
    ElMessage.success('已退出群聊')
    showMembers.value = false
  } catch (error) {
    if (!errorMessage(error).includes('cancel')) {
      ElMessage.error(errorMessage(error))
    }
  }
}

async function createGroup(): Promise<void> {
  if (!groupMembers.value.trim()) {
    ElMessage.warning('请输入群成员用户名')
    return
  }
  const usernames = groupMembers.value.split(/[,，\s]+/).filter(Boolean)
  try {
    await chat.createGroup(groupName.value || null, usernames)
    ElMessage.success('群聊已创建')
    showCreateGroup.value = false
    groupName.value = ''
    groupMembers.value = ''
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function loadEmployees(): Promise<void> {
  loadingEmployees.value = true
  try {
    const data = await get<DigitalEmployeeItem[]>('/api/v1/chat/employees')
    employees.value = data
  } catch (error) {
    employees.value = []
  } finally {
    loadingEmployees.value = false
  }
}

// --- @Mention ---
const showMention = ref(false)
const mentionFilter = ref('')
const mentionStart = ref(-1)
const mentionCursorPos = ref(-1)
const mentionActiveIndex = ref(0)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const filteredMentionEmployees = computed(() => {
  if (!mentionFilter.value) return employees.value.filter(e => e.status === 'active')
  const q = mentionFilter.value.toLowerCase()
  return employees.value.filter(
    e => e.status === 'active' && (e.name.toLowerCase().includes(q) || e.code.toLowerCase().includes(q))
  )
})

function checkMention(cursorPos: number, text: string): void {
  // @mention is only available in group conversations
  if (activeConversation.value?.type !== 'group') {
    showMention.value = false
    return
  }
  let pos = cursorPos - 1
  while (pos >= 0 && text[pos] !== '@' && text[pos] !== ' ' && text[pos] !== '\n') {
    pos--
  }
  if (pos >= 0 && text[pos] === '@') {
    const afterAt = text.substring(pos + 1, cursorPos)
    if (pos === 0 || text[pos - 1] === ' ' || text[pos - 1] === '\n') {
      showMention.value = true
      mentionFilter.value = afterAt
      mentionStart.value = pos
      mentionCursorPos.value = cursorPos
      mentionActiveIndex.value = 0
      return
    }
  }
  showMention.value = false
}

function handleInput(e: Event): void {
  autoResize(e)
  const el = e.target as HTMLTextAreaElement
  checkMention(el.selectionStart, el.value)
}

function selectEmployee(emp: DigitalEmployeeItem): void {
  const before = newMessage.value.substring(0, mentionStart.value)
  const after = newMessage.value.substring(mentionCursorPos.value)
  newMessage.value = before + '@' + emp.code + ' ' + after
  showMention.value = false
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return
    const newPos = before.length + emp.code.length + 2
    el.focus()
    el.selectionStart = el.selectionEnd = newPos
  })
}

function handleMentionKeydown(e: KeyboardEvent): void {
  if (!showMention.value) return
  const items = filteredMentionEmployees.value
  if (!items.length) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    mentionActiveIndex.value = (mentionActiveIndex.value + 1) % items.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    mentionActiveIndex.value = (mentionActiveIndex.value - 1 + items.length) % items.length
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    e.preventDefault()
    selectEmployee(items[mentionActiveIndex.value])
  } else if (e.key === 'Escape') {
    e.preventDefault()
    showMention.value = false
  }
}

function closeMention(): void {
  setTimeout(() => { showMention.value = false }, 200)
}

async function handleSend(): Promise<void> {
  const content = newMessage.value.trim()
  if (!content || !chat.activeConversationId) return
  newMessage.value = ''
  if (chat.wsConnected) {
    chat.wsSend('send_message', {
      conversation_id: chat.activeConversationId,
      content,
    })
  } else {
    try {
      await post('/api/v1/chat/messages', {
        conversation_id: chat.activeConversationId,
        content,
        content_type: 'text',
      })
      await chat.loadMessages(chat.activeConversationId)
    } catch (error) {
      ElMessage.error(errorMessage(error))
    }
  }
}

function onEmojiSelect(emoji: string): void {
  const el = textareaRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const text = newMessage.value
  newMessage.value = text.substring(0, start) + emoji + text.substring(end)
  nextTick(() => {
    el.focus()
    const newPos = start + emoji.length
    el.selectionStart = el.selectionEnd = newPos
  })
}

function triggerFileUpload(): void {
  fileInputRef.value?.click()
}

async function handleFileSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !chat.activeConversationId) return

  // Frontend validation: 10 MB limit
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 10MB')
    input.value = ''
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const result = await postFormData<AdminFileItem>('/api/v1/chat/files/upload', formData)

    // Cache metadata
    fileMetaCache.value = new Map(fileMetaCache.value).set(result.id, result)

    const isImage = result.mime_type?.startsWith('image/')
    const contentType = isImage ? 'image' : 'file'

    if (chat.wsConnected) {
      chat.wsSend('send_message', {
        conversation_id: chat.activeConversationId,
        content: result.id,
        content_type: contentType,
      })
    } else {
      await post('/api/v1/chat/messages', {
        conversation_id: chat.activeConversationId,
        content: result.id,
        content_type: contentType,
      })
      await chat.loadMessages(chat.activeConversationId)
    }
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    uploading.value = false
    input.value = '' // Allow re-selecting the same file
  }
}

function downloadFile(fileId: string): void {
  window.open('/api/v1/chat/files/' + fileId + '/download', '_blank')
}

function autoResize(e: Event): void {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function formatTime(ts?: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function formatConversationTime(ts?: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// Auto-scroll on new messages
watch(() => chat.messages.length, async () => {
  await nextTick()
  if (messagePane.value) {
    messagePane.value.scrollTop = messagePane.value.scrollHeight
  }
})

// Fetch file metadata for new file/image messages
watch(() => chat.messages, (messages) => {
  const needed = messages.filter(
    m => (m.content_type === 'file' || m.content_type === 'image') && !fileMetaCache.value.has(m.content),
  )
  if (!needed.length) return
  // Fire-and-forget — each call handles its own dedup
  needed.forEach(m => fetchFileMeta(m.content))
}, { deep: true })

// Lifecycle
onMounted(() => {
  chat.init()
  loadEmployees()
})

onUnmounted(() => {
  chat.destroy()
})
</script>

<template>
  <section class="wx-chat">
    <!-- Left: conversation list -->
    <aside class="wx-chat-sidebar">
      <div class="wx-chat-sidebar-head">
        <div class="wx-chat-tabs">
          <button :class="{ active: activeTab === 'chats' }" @click="activeTab = 'chats'">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            聊天
          </button>
          <button :class="{ active: activeTab === 'contacts' }" @click="activeTab = 'contacts'">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            通讯录
          </button>
        </div>
        <div class="wx-chat-actions">
          <button class="wx-action-btn" title="好友请求" @click="showFriendRequests = true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            <span v-if="chat.incomingRequests.length" class="wx-badge-dot" />
          </button>
          <el-dropdown trigger="click" placement="bottom-end" @command="handleActionCommand">
            <button class="wx-action-btn" title="更多">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="addFriend">添加好友</el-dropdown-item>
                <el-dropdown-item command="createGroup">创建群聊</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- Chats tab -->
      <div v-show="activeTab === 'chats'" class="wx-chat-list">
        <div class="wx-chat-search">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="chatSearch" placeholder="搜索聊天" />
        </div>
        <div v-if="filteredConversations.length === 0" class="wx-chat-empty">
          <p>暂无聊天</p>
        </div>
        <div
          v-for="conv in filteredConversations"
          :key="conv.id"
          class="wx-conv-item"
          :class="{ active: conv.id === chat.activeConversationId }"
          @click="openConversation(conv)"
        >
          <div class="wx-conv-avatar" :class="conv.type === 'group' ? 'group' : ''">
            {{ (conv.name || (conv.type === 'group' ? '群' : '私'))[0] }}
          </div>
          <div class="wx-conv-info">
            <div class="wx-conv-top">
              <strong class="wx-conv-name">{{ conv.name || (conv.type === 'group' ? '群聊' : '私聊') }}</strong>
              <span class="wx-conv-time">{{ formatConversationTime(conv.last_message?.created_at) }}</span>
            </div>
            <div class="wx-conv-bottom">
              <span class="wx-conv-preview">{{ getPreviewText(conv.last_message?.content, conv.last_message?.content_type) }}</span>
              <span v-if="conv.unread_count" class="wx-unread-badge">{{ conv.unread_count > 99 ? '99+' : conv.unread_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Contacts tab -->
      <div v-show="activeTab === 'contacts'" class="wx-chat-list">
        <div class="wx-chat-search">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="contactSearch" placeholder="搜索联系人" />
        </div>
        <div v-if="filteredContacts.length === 0" class="wx-chat-empty">
          <p>暂无联系人</p>
        </div>
        <div
          v-for="contact in filteredContacts"
          :key="contact.user_id"
          class="wx-conv-item"
          @click="startPrivateChat(contact)"
        >
          <div class="wx-conv-avatar">{{ (contact.remark || contact.display_name)[0] }}</div>
          <div class="wx-conv-info">
            <strong class="wx-conv-name">{{ contact.remark || contact.display_name }}</strong>
            <span class="wx-conv-username">@{{ contact.username }}</span>
          </div>
        </div>
      </div>

    </aside>

    <!-- Right: Chat panel -->
    <main class="wx-chat-panel">
      <template v-if="activeConversation">
        <!-- Header -->
        <header class="wx-panel-head">
          <h2>{{ conversationTitle }}</h2>
          <div class="wx-panel-actions">
            <span class="wx-ws-status" :class="{ connected: chat.wsConnected }" :title="chat.wsConnected ? '已连接' : '未连接'" />
            <button v-if="activeConversation.type === 'group'" class="wx-panel-btn" @click="showMemberDialog">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
              </svg>
              群成员
            </button>
          </div>
        </header>

        <!-- Messages -->
        <section ref="messagePane" class="wx-panel-messages">
          <div
            v-for="msg in chat.messages"
            :key="msg.id"
            class="wx-msg"
            :class="msg.sender_id === session.user?.id ? 'own' : 'other'"
          >
            <div v-if="activeConversation.type === 'group' && msg.sender_id !== session.user?.id" class="wx-msg-sender">
              {{ msg.sender_name }}
            </div>
            <div class="wx-msg-content">
              <div class="wx-msg-bubble" :class="{ 'is-image': msg.content_type === 'image' }">
                <template v-if="msg.content_type === 'image'">
                  <img
                    :src="'/api/v1/chat/files/' + msg.content + '/download'"
                    class="wx-msg-image"
                    alt="图片"
                    @click="downloadFile(msg.content)"
                  />
                  <span v-if="getFileMeta(msg.content)?.filename" class="wx-msg-image-name">
                    {{ getFileMeta(msg.content)?.filename }}
                  </span>
                </template>
                <template v-else-if="msg.content_type === 'file'">
                  <div class="wx-msg-file" @click="downloadFile(msg.content)">
                    <div class="wx-file-icon">📎</div>
                    <div class="wx-file-info">
                      <span class="wx-file-name">{{ getFileMeta(msg.content)?.filename || '文件' }}</span>
                      <span class="wx-file-size">{{ formatFileSize(getFileMeta(msg.content)?.size_bytes) }}</span>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <MarkdownRenderer :content="msg.content" />
                </template>
              </div>
              <div class="wx-msg-time">{{ formatTime(msg.created_at) }}</div>
            </div>
          </div>
        </section>

        <!-- Composer -->
        <footer class="wx-panel-composer">
          <!-- @Mention panel (group chat only) -->
          <div v-if="showMention && filteredMentionEmployees.length && activeConversation?.type === 'group'" class="wx-mention-panel">
            <div
              v-for="(emp, idx) in filteredMentionEmployees"
              :key="emp.id"
              class="wx-mention-item"
              :class="{ active: idx === mentionActiveIndex }"
              @click="selectEmployee(emp)"
              @mouseenter="mentionActiveIndex = idx"
            >
              <span class="wx-mention-avatar">🤖</span>
              <div class="wx-mention-info">
                <span class="wx-mention-name">{{ emp.name }}</span>
                <span class="wx-mention-code">@{{ emp.code }}</span>
              </div>
            </div>
          </div>
          <div class="wx-composer-row">
            <div class="wx-composer-toolbar">
              <EmojiPicker @select="onEmojiSelect" />
              <button class="wx-toolbar-btn" :disabled="uploading" title="上传文件" @click="triggerFileUpload">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                </svg>
              </button>
              <input ref="fileInputRef" type="file" style="display:none" @change="handleFileSelected" />
            </div>
            <div class="wx-composer-input">
              <textarea
                ref="textareaRef"
                v-model="newMessage"
                placeholder="输入消息..."
                rows="1"
                @keyup.enter.prevent="handleSend"
                @keydown="handleMentionKeydown"
                @input="handleInput"
                @blur="closeMention"
              />
            </div>
            <button v-if="uploading" class="wx-composer-btn" disabled>
              <span class="wx-loading-spinner" />
              上传中
            </button>
            <button v-else class="wx-composer-btn" :disabled="!newMessage.trim()" @click="handleSend">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
              发送
            </button>
          </div>
        </footer>
      </template>

      <!-- Empty state -->
      <div v-else class="wx-panel-empty">
        <div class="wx-empty-icon">
          <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <p>选择一个聊天开始对话</p>
      </div>
    </main>
  </section>

  <!-- Dialogs -->
  <el-dialog v-model="showAddFriend" title="添加好友" width="400px">
    <div class="wx-dialog-body">
      <div class="wx-dialog-search">
        <input v-model="friendSearch" placeholder="搜索用户名" @keyup.enter="doSearchUsers" />
        <button class="wx-dialog-search-btn" @click="doSearchUsers">搜索</button>
      </div>
      <div v-for="user in searchResults" :key="user.user_id" class="wx-dialog-item">
        <span>{{ user.display_name }} (@{{ user.username }})</span>
        <button class="wx-add-btn" @click="doSendRequest(user.username)">添加</button>
      </div>
      <div v-if="searchResults.length === 0 && friendSearch" class="wx-dialog-empty">
        未找到用户
      </div>
    </div>
  </el-dialog>

  <el-dialog v-model="showFriendRequests" title="好友请求" width="400px">
    <div class="wx-dialog-body">
      <div v-if="chat.incomingRequests.length === 0" class="wx-dialog-empty">暂无待处理请求</div>
      <div v-for="req in chat.incomingRequests" :key="req.id" class="wx-dialog-item column">
        <div class="wx-request-info">
          <strong>{{ req.from_user_name }}</strong>
          <p v-if="req.message">{{ req.message }}</p>
        </div>
        <div class="wx-request-actions">
          <button class="wx-btn-accept" @click="handleFriendReq(req.id, 'accept')">接受</button>
          <button class="wx-btn-reject" @click="handleFriendReq(req.id, 'reject')">拒绝</button>
        </div>
      </div>
    </div>
  </el-dialog>

  <el-dialog v-model="showCreateGroup" title="创建群聊" width="400px">
    <div class="wx-dialog-body">
      <div class="wx-form-group">
        <label>群名称</label>
        <input v-model="groupName" placeholder="群聊名称（可选）" />
      </div>
      <div class="wx-form-group">
        <label>群成员</label>
        <textarea v-model="groupMembers" placeholder="输入用户名，用逗号分隔" rows="3" />
        <p class="wx-form-hint">仅限已经是联系人的用户</p>
      </div>
      <div class="wx-dialog-footer">
        <button class="wx-dialog-cancel" @click="showCreateGroup = false">取消</button>
        <button class="wx-dialog-confirm" @click="createGroup">创建</button>
      </div>
    </div>
  </el-dialog>

  <el-dialog v-model="showMembers" title="群成员" width="350px">
    <div class="wx-dialog-body">
      <div v-for="member in memberList" :key="member.user_id" class="wx-dialog-item">
        <span>{{ member.display_name }} (@{{ member.username }})</span>
        <span v-if="member.role === 'owner'" class="wx-tag wx-tag-owner">群主</span>
      </div>
      <div class="wx-dialog-footer">
        <button class="wx-btn-leave" @click="confirmLeaveGroup">退出群聊</button>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────────────────── */
.wx-chat {
  display: flex;
  height: calc(100vh - 52px);
  background: var(--bg-page);
  overflow: hidden;
}

/* ── Chat Sidebar ────────────────────────────────────────────────────────── */
.wx-chat-sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
}

.wx-chat-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.wx-chat-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg-hover);
  border-radius: 8px;
  padding: 2px;
}

.wx-chat-tabs button {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  transition: all 0.15s;
  white-space: nowrap;
}

.wx-chat-tabs button.active {
  background: var(--bg-card);
  color: var(--wx-green);
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.wx-chat-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.wx-action-btn {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}

.wx-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.wx-badge-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wx-red);
  border: 2px solid var(--bg-card);
}

/* ── Conversation Search ─────────────────────────────────────────────────── */
.wx-chat-search {
  position: relative;
  padding: 10px 14px;
}

.wx-chat-search .search-icon {
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-placeholder);
  pointer-events: none;
}

.wx-chat-search input {
  width: 100%;
  height: 34px;
  padding: 0 12px 0 32px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-hover);
  outline: none;
  box-sizing: border-box;
}

.wx-chat-search input::placeholder {
  color: var(--text-placeholder);
}

.wx-chat-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: var(--text-muted);
  font-size: 13px;
}

/* ── Conversation List ───────────────────────────────────────────────────── */
.wx-chat-list {
  flex: 1;
  overflow-y: auto;
}

.wx-conv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid var(--border-light);
}

.wx-conv-item:last-child { border-bottom: none; }

.wx-conv-item:hover {
  background: var(--bg-hover);
}

.wx-conv-item.active {
  background: var(--wx-green-bg);
}

/* ── Conversation Avatar ─────────────────────────────────────────────────── */
.wx-conv-avatar {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: var(--wx-green);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  flex-shrink: 0;
}

.wx-conv-avatar.group {
  background: #5B8FF9;
  border-radius: 8px;
  font-size: 16px;
}

/* ── Conversation Info ───────────────────────────────────────────────────── */
.wx-conv-info {
  flex: 1;
  min-width: 0;
}

.wx-conv-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.wx-conv-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wx-conv-time {
  font-size: 11px;
  color: var(--text-placeholder);
  flex-shrink: 0;
}

.wx-conv-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.wx-conv-preview {
  font-size: 13px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.wx-conv-username {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.wx-unread-badge {
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
  flex-shrink: 0;
}

/* ── Chat Panel ──────────────────────────────────────────────────────────── */
.wx-chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-page);
}

.wx-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.wx-panel-head h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.wx-panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wx-ws-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-placeholder);
  transition: background 0.3s;
}

.wx-ws-status.connected {
  background: var(--wx-green);
}

.wx-panel-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.wx-panel-btn:hover {
  border-color: var(--wx-green);
  color: var(--wx-green);
}

/* ── Messages ────────────────────────────────────────────────────────────── */
.wx-panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--bg-page);
}

.wx-msg {
  display: flex;
  flex-direction: column;
  max-width: 70%;
  gap: 2px;
}

.wx-msg.own {
  align-self: flex-end;
  align-items: flex-end;
}

.wx-msg.other {
  align-self: flex-start;
  align-items: flex-start;
}

.wx-msg-sender {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 2px;
  margin-left: 4px;
}

.wx-msg-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.wx-msg.own .wx-msg-content {
  align-items: flex-end;
}

.wx-msg.other .wx-msg-content {
  align-items: flex-start;
}

.wx-msg-bubble {
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
  position: relative;
}

.wx-msg.own .wx-msg-bubble {
  background: #95EC69;
  color: #1A1A1A;
  border-radius: 8px 2px 8px 8px;
}

.wx-msg.other .wx-msg-bubble {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-light);
  border-radius: 2px 8px 8px 8px;
}

.wx-msg-time {
  font-size: 11px;
  color: var(--text-placeholder);
  padding: 0 4px;
}

/* ── Composer ────────────────────────────────────────────────────────────── */
.wx-panel-composer {
  padding: 12px 20px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.wx-composer-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  width: 100%;
}

.wx-composer-input {
  flex: 1;
}

.wx-composer-input textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: 10px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-hover);
  outline: none;
  resize: none;
  min-height: 42px;
  max-height: 120px;
  line-height: 1.5;
  box-sizing: border-box;
  transition: border-color 0.2s;
  font-family: inherit;
}

.wx-composer-input textarea:focus {
  border-color: var(--wx-green);
  background: var(--bg-card);
}

.wx-composer-input textarea::placeholder {
  color: var(--text-placeholder);
}

.wx-composer-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 18px;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  white-space: nowrap;
  flex-shrink: 0;
}

.wx-composer-btn:hover {
  background: var(--wx-green-hover);
}

.wx-composer-btn:active {
  transform: scale(0.97);
}

.wx-composer-btn:disabled {
  background: var(--wx-green);
  opacity: 0.35;
  cursor: not-allowed;
  transform: none;
}

/* ── @Mention Panel ──────────────────────────────────────────── */
.wx-panel-composer {
  position: relative;
}

.wx-mention-panel {
  position: absolute;
  bottom: 100%;
  left: 20px;
  right: 20px;
  max-height: 200px;
  overflow-y: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: 10px 10px 0 0;
  box-shadow: 0 -4px 12px rgba(0,0,0,0.08);
  z-index: 100;
}

.wx-mention-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.1s;
}

.wx-mention-item:hover,
.wx-mention-item.active {
  background: var(--wx-green-bg);
}

.wx-mention-avatar {
  font-size: 18px;
  flex-shrink: 0;
}

.wx-mention-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.wx-mention-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.wx-mention-code {
  font-size: 12px;
  color: var(--text-muted);
}

/* ── Empty State ─────────────────────────────────────────────────────────── */
.wx-panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-placeholder);
  font-size: 14px;
}

.wx-empty-icon {
  opacity: 0.4;
}

/* ── Dialog Styles ───────────────────────────────────────────────────────── */
.wx-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wx-dialog-search {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.wx-dialog-search input {
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

.wx-dialog-search input:focus {
  border-color: var(--wx-green);
}

.wx-dialog-search-btn {
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.wx-dialog-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
  font-size: 14px;
}

.wx-dialog-item.column {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.wx-dialog-empty {
  text-align: center;
  padding: 20px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.wx-add-btn {
  padding: 4px 14px;
  border: none;
  border-radius: 6px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.wx-add-btn:hover { background: var(--wx-green-hover); }

.wx-request-info strong { font-size: 14px; }
.wx-request-info p { font-size: 13px; color: var(--text-muted); margin: 4px 0 0; }

.wx-request-actions { display: flex; gap: 8px; }

.wx-btn-accept {
  padding: 5px 16px;
  border: none;
  border-radius: 6px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.wx-btn-reject {
  padding: 5px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.wx-form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.wx-form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.wx-form-group input, .wx-form-group textarea {
  padding: 10px 12px;
  border: 1.5px solid var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-input);
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}

.wx-form-group input:focus, .wx-form-group textarea:focus {
  border-color: var(--wx-green);
}

.wx-form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.wx-tag-owner {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(250, 157, 59, 0.12);
  color: var(--wx-orange);
  font-weight: 600;
}

.wx-dialog-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.wx-dialog-confirm {
  padding: 8px 24px;
  border: none;
  border-radius: 8px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.wx-dialog-cancel {
  padding: 8px 24px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
}

.wx-btn-leave {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: var(--wx-red);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

/* ── Composer Toolbar ─────────────────────────────────────────── */
.wx-composer-toolbar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 4px 0 0;
  flex-shrink: 0;
}

.wx-toolbar-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s;
}

.wx-toolbar-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.wx-toolbar-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ── Image Message ────────────────────────────────────────────── */
.wx-msg-bubble.is-image {
  padding: 0;
  overflow: hidden;
  background: transparent !important;
  border: none !important;
  max-width: 280px;
}

.wx-msg-image {
  display: block;
  max-width: 100%;
  max-height: 360px;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.15s;
}

.wx-msg-image:hover {
  opacity: 0.9;
}

.wx-msg-image-name {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 8px 8px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── File Message ─────────────────────────────────────────────── */
.wx-msg-file {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  cursor: pointer;
  min-width: 180px;
}

.wx-msg-file:hover {
  opacity: 0.8;
}

.wx-file-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.wx-file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.wx-file-name {
  font-size: 13px;
  font-weight: 600;
  color: inherit;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wx-file-size {
  font-size: 11px;
  color: var(--text-muted);
}

/* ── Loading Spinner ──────────────────────────────────────────── */
.wx-loading-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: wx-spin 0.6s linear infinite;
}

@keyframes wx-spin {
  to { transform: rotate(360deg); }
}
</style>
