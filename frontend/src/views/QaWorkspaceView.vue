<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { get, getEnvelope, patch, post, postStream } from '@/api/client'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { QaCitationItem, QaMessageItem, QaSessionItem } from '@/types'
import { errorMessage, shortTime } from '@/utils/display'
import { applyQaStreamEvent, inlineQaCitations } from '@/utils/qa'

const loadingSessions = ref(false)
const loadingMessages = ref(false)
const streaming = ref(false)
const sessions = ref<QaSessionItem[]>([])
const messages = ref<QaMessageItem[]>([])
const selectedSession = ref<QaSessionItem | null>(null)
const question = ref('')
const sessionQuery = ref('')
const messagePane = ref<HTMLElement>()
const citationVisible = ref(false)
const citationLoading = ref(false)
const activeCitations = ref<QaCitationItem[]>([])
const sessionPagination = reactive({ page: 1, page_size: 20, total: 0 })
let sessionSearchTimer: number | undefined

const askDisabled = computed(() => streaming.value || !question.value.trim())
const selectedTitle = computed(() => selectedSession.value?.title || '未命名会话')

function buildSessionQuery(): string {
  const params = new URLSearchParams()
  params.set('page', String(sessionPagination.page))
  params.set('page_size', String(sessionPagination.page_size))
  if (sessionQuery.value.trim()) params.set('q', sessionQuery.value.trim())
  return `?${params}`
}

function applySessionPagination(meta?: { page?: number; page_size?: number; total?: number }): void {
  sessionPagination.page = Number(meta?.page ?? sessionPagination.page)
  sessionPagination.page_size = Number(meta?.page_size ?? sessionPagination.page_size)
  sessionPagination.total = Number(meta?.total ?? sessions.value.length)
}

function localId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function citationStatus(citation: QaCitationItem): string | null | undefined {
  return citation.current_status ?? citation.status
}

function autoResize(e: Event): void {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function scrollToBottom(): Promise<void> {
  await nextTick()
  if (messagePane.value) messagePane.value.scrollTop = messagePane.value.scrollHeight
}

async function loadSessions(keepSelection = true): Promise<void> {
  loadingSessions.value = true
  try {
    const payload = await getEnvelope<QaSessionItem[]>(`/api/v1/qa/sessions${buildSessionQuery()}`)
    sessions.value = payload.data
    applySessionPagination(payload.meta ?? payload)
    if (keepSelection && selectedSession.value) {
      selectedSession.value = sessions.value.find((item) => item.id === selectedSession.value?.id) ?? selectedSession.value
    } else if (!selectedSession.value && sessions.value.length) {
      await openSession(sessions.value[0])
    }
  } catch (error) {
    ElMessage.warning(errorMessage(error))
  } finally {
    loadingSessions.value = false
  }
}

async function loadMessages(sessionId: string): Promise<void> {
  loadingMessages.value = true
  try {
    messages.value = await get<QaMessageItem[]>(`/api/v1/qa/sessions/${sessionId}/messages`)
    await scrollToBottom()
  } catch (error) {
    ElMessage.warning(errorMessage(error))
  } finally {
    loadingMessages.value = false
  }
}

async function openSession(session: QaSessionItem): Promise<void> {
  selectedSession.value = session
  await loadMessages(session.id)
}

function searchSessions(): void {
  sessionPagination.page = 1
  void loadSessions(false)
}

function queueSearchSessions(): void {
  if (sessionSearchTimer) window.clearTimeout(sessionSearchTimer)
  sessionSearchTimer = window.setTimeout(searchSessions, 300)
}

function changeSessionPage(page: number): void {
  sessionPagination.page = page
  void loadSessions()
}

async function createSession(title = ''): Promise<QaSessionItem | null> {
  try {
    const session = await post<QaSessionItem>('/api/v1/qa/sessions', { title: title || null })
    selectedSession.value = session
    messages.value = []
    await loadSessions()
    return session
  } catch (error) {
    ElMessage.error(errorMessage(error))
    return null
  }
}

async function promptCreateSession(): Promise<void> {
  const result = await ElMessageBox.prompt('给新会话起一个标题，也可以留空。', '新建问数会话', {
    inputPlaceholder: '例如：本周农业信息摘要',
  }).catch(() => null)
  if (result) await createSession(result.value)
}

async function renameSession(): Promise<void> {
  if (!selectedSession.value) return
  const result = await ElMessageBox.prompt('修改当前会话标题。', '重命名会话', {
    inputValue: selectedSession.value.title ?? '',
  }).catch(() => null)
  if (!result) return
  try {
    selectedSession.value = await patch<QaSessionItem>(`/api/v1/qa/sessions/${selectedSession.value.id}`, { title: result.value || null })
    await loadSessions()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

async function archiveSession(): Promise<void> {
  if (!selectedSession.value) return
  try {
    await ElMessageBox.confirm(`确认归档会话「${selectedTitle.value}」？`, '归档会话', { type: 'warning' })
    await patch<QaSessionItem>(`/api/v1/qa/sessions/${selectedSession.value.id}`, { status: 'archived' })
    selectedSession.value = null
    messages.value = []
    await loadSessions(false)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(errorMessage(error))
  }
}

async function askQuestion(): Promise<void> {
  const text = question.value.trim()
  if (!text || streaming.value) return
  let active = selectedSession.value
  if (!active) active = await createSession(text.slice(0, 30))
  if (!active) return

  question.value = ''
  const userMessage: QaMessageItem = {
    id: localId('question'),
    session_id: active.id,
    role: 'user',
    content: text,
    status: 'completed',
  }
  const answerMessage: QaMessageItem = {
    id: localId('answer'),
    session_id: active.id,
    role: 'assistant',
    content: '',
    status: 'streaming',
    citations: [],
  }
  messages.value.push(userMessage, answerMessage)
  await scrollToBottom()

  streaming.value = true
  try {
    await postStream(`/api/v1/qa/sessions/${active.id}/questions/stream`, { question: text }, ({ event, data }) => {
      applyQaStreamEvent(answerMessage, event, data)
      if (event === 'delta') {
        void scrollToBottom()
      }
    })
    if (answerMessage.status === 'streaming') answerMessage.status = 'completed'
    await loadMessages(active.id).catch(() => undefined)
    await loadSessions()
  } catch (error) {
    answerMessage.status = 'failed'
    answerMessage.error_summary = errorMessage(error)
    if (!answerMessage.content) answerMessage.content = answerMessage.error_summary
    ElMessage.error(answerMessage.error_summary)
  } finally {
    streaming.value = false
    await scrollToBottom()
  }
}

async function openCitations(message: QaMessageItem): Promise<void> {
  citationVisible.value = true
  citationLoading.value = true
  activeCitations.value = inlineQaCitations(message)
  try {
    if (!activeCitations.value.length) {
      activeCitations.value = await get<QaCitationItem[]>(`/api/v1/qa/messages/${message.id}/citations`)
    }
  } catch (error) {
    ElMessage.warning(errorMessage(error))
  } finally {
    citationLoading.value = false
  }
}

onMounted(() => {
  void loadSessions()
})

onBeforeUnmount(() => {
  if (sessionSearchTimer) window.clearTimeout(sessionSearchTimer)
})
</script>

<template>
  <div class="wx-qa">
    <!-- Sidebar: session list -->
    <aside class="wx-qa-sidebar">
      <div class="wx-qa-sidebar-head">
        <h1>智能问数</h1>
        <button class="wx-qa-new-btn" @click="promptCreateSession">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建
        </button>
      </div>
      <div class="wx-qa-search">
        <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input v-model="sessionQuery" placeholder="搜索会话" @input="queueSearchSessions" @keyup.enter="searchSessions" />
      </div>
      <div v-loading="loadingSessions" class="wx-qa-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          class="wx-qa-item"
          :class="{ active: session.id === selectedSession?.id }"
          type="button"
          @click="openSession(session)"
        >
          <div class="wx-qa-item-icon">{{ (session.title || '未') [0] }}</div>
          <div class="wx-qa-item-info">
            <strong class="wx-qa-item-title">{{ session.title || '未命名会话' }}</strong>
            <span class="wx-qa-item-time">{{ shortTime(session.updated_at) }}</span>
          </div>
          <status-tag :value="session.status" />
        </button>
        <div v-if="!sessions.length && !loadingSessions" class="wx-qa-empty">暂无会话</div>
      </div>
      <div v-if="sessionPagination.total > sessionPagination.page_size" class="wx-qa-pagination">
        <el-pagination
          small
          layout="prev, pager, next"
          :current-page="sessionPagination.page"
          :page-size="sessionPagination.page_size"
          :total="sessionPagination.total"
          @current-change="changeSessionPage"
        />
      </div>
    </aside>

    <!-- Main chat panel -->
    <main class="wx-qa-panel">
      <!-- Header -->
      <header v-if="selectedSession" class="wx-qa-panel-head">
        <div class="wx-qa-panel-info">
          <h2>{{ selectedTitle }}</h2>
          <span class="wx-qa-panel-desc">回答只使用已治理为 available 的内容</span>
        </div>
        <div class="wx-qa-panel-actions">
          <button class="wx-panel-btn" @click="renameSession">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            重命名
          </button>
          <button class="wx-panel-btn" @click="archiveSession">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
            归档
          </button>
        </div>
      </header>

      <!-- Messages -->
      <section ref="messagePane" v-loading="loadingMessages" class="wx-qa-messages">
        <template v-if="messages.length">
          <div
            v-for="message in messages"
            :key="message.id"
            class="wx-qa-msg"
            :class="message.role === 'user' ? 'own' : 'other'"
          >
            <div class="wx-qa-msg-avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
            <div class="wx-qa-msg-body">
              <div class="wx-qa-msg-meta">
                <span class="wx-qa-msg-role">{{ message.role === 'user' ? '你' : '智能问数' }}</span>
                <status-tag v-if="message.role === 'assistant'" :value="message.status" />
              </div>
              <div class="wx-qa-msg-bubble" :class="{ loading: message.status === 'streaming' }">
                <template v-if="message.role === 'assistant' && message.content">
                  <MarkdownRenderer :content="message.content" />
                  <div v-if="message.status === 'streaming'" class="typing-cursor" />
                </template>
                <template v-else>{{ message.content || (message.status === 'streaming' ? '正在生成回答...' : '-') }}</template>
              </div>
              <p v-if="message.error_summary" class="wx-qa-msg-error">{{ message.error_summary }}</p>
              <div v-if="message.role === 'assistant' && message.citations?.length" class="wx-qa-citations">
                <button v-for="citation in message.citations" :key="`${message.id}-${citation.knowledge_item_id}`" type="button" class="wx-qa-cite" @click="openCitations(message)">
                  <span class="cite-num">{{ citation.rank }}</span>
                  <span class="cite-text">{{ citation.title || citation.knowledge_item_id }}</span>
                </button>
              </div>
              <button v-if="message.role === 'assistant' && message.status === 'completed'" class="wx-qa-ref-link" @click="openCitations(message)">
                查看引用 →
              </button>
            </div>
          </div>
        </template>
        <div v-else-if="!selectedSession" class="wx-qa-msg-empty">
          <div class="wx-qa-empty-icon">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <p>新建会话或直接输入问题开始问数</p>
        </div>
      </section>

      <!-- Composer -->
      <footer class="wx-qa-composer">
        <div class="wx-qa-composer-row">
          <div class="wx-qa-composer-input">
            <textarea
              v-model="question"
              placeholder="输入问题，系统会基于可用数据生成带引用的回答"
              rows="1"
              @keydown.enter.prevent="askQuestion"
              @input="autoResize"
            />
          </div>
          <button class="wx-composer-btn" :disabled="askDisabled" @click="askQuestion">
            <span v-if="streaming" class="wx-spinner-sm" />
            <template v-else>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </template>
            发送
          </button>
        </div>
      </footer>
    </main>

    <!-- Citation drawer -->
    <el-drawer v-model="citationVisible" title="回答引用" size="560px">
      <el-skeleton v-if="citationLoading" :rows="6" animated />
      <div v-else class="wx-citation-list">
        <article v-for="citation in activeCitations" :key="`${citation.rank}-${citation.knowledge_item_id}`" class="wx-citation-card">
          <div class="wx-citation-head">
            <strong>#{{ citation.rank }} {{ citation.title || citation.knowledge_item_id }}</strong>
            <status-tag v-if="citationStatus(citation)" :value="citationStatus(citation)" />
          </div>
          <p class="wx-citation-source">{{ citation.source_name || '未知来源' }}</p>
          <blockquote class="wx-citation-excerpt">{{ citation.excerpt }}</blockquote>
        </article>
        <el-empty v-if="!activeCitations.length" description="当前回答没有引用" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
/* ── Layout ────────────────────────────────────────────────────────────── */
.wx-qa {
  display: flex;
  height: calc(100vh - 52px);
  background: var(--bg-page);
  overflow: hidden;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
.wx-qa-sidebar {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
}

.wx-qa-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border-light);
}

.wx-qa-sidebar-head h1 {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}

.wx-qa-new-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: none;
  border-radius: 8px;
  background: var(--wx-green);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.wx-qa-new-btn:hover { background: var(--wx-green-hover); }

.wx-qa-search {
  position: relative;
  padding: 10px 14px;
}

.wx-qa-search .search-icon {
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-placeholder);
  pointer-events: none;
}

.wx-qa-search input {
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

.wx-qa-search input::placeholder { color: var(--text-placeholder); }

.wx-qa-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.wx-qa-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
  border-bottom: 1px solid var(--border-light);
}

.wx-qa-item:last-child { border-bottom: none; }
.wx-qa-item:hover { background: var(--bg-hover); }
.wx-qa-item.active { background: var(--wx-green-bg); }

.wx-qa-item-icon {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: var(--wx-green-light);
  color: var(--wx-green);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
  flex-shrink: 0;
}

.wx-qa-item-info {
  flex: 1;
  min-width: 0;
}

.wx-qa-item-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wx-qa-item-time {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.wx-qa-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.wx-qa-pagination {
  padding: 10px 14px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: center;
}

/* ── Q&A Panel ────────────────────────────────────────────────────────── */
.wx-qa-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-page);
}

.wx-qa-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.wx-qa-panel-info h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.wx-qa-panel-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  display: block;
}

.wx-qa-panel-actions {
  display: flex;
  gap: 8px;
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

.wx-panel-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Messages ─────────────────────────────────────────────────────────── */
.wx-qa-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.wx-qa-msg {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.wx-qa-msg.own {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.wx-qa-msg.other {
  align-self: flex-start;
}

.wx-qa-msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  flex-shrink: 0;
}

.wx-qa-msg.own .wx-qa-msg-avatar {
  background: var(--wx-green);
  color: #FFFFFF;
}

.wx-qa-msg.other .wx-qa-msg-avatar {
  background: #5B8FF9;
  color: #FFFFFF;
}

.wx-qa-msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.wx-qa-msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wx-qa-msg-role {
  font-size: 12px;
  color: var(--text-muted);
}

.wx-qa-msg-bubble {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.wx-qa-msg.own .wx-qa-msg-bubble {
  background: #95EC69;
  color: #1A1A1A;
  border-radius: 8px 2px 8px 8px;
}

.wx-qa-msg.other .wx-qa-msg-bubble {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-light);
  border-radius: 2px 8px 8px 8px;
}

.wx-qa-msg-bubble.loading {
  opacity: 0.85;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: var(--wx-green);
  margin-left: 2px;
  animation: blink 0.8s step-end infinite;
  vertical-align: text-bottom;
}

@keyframes blink {
  50% { opacity: 0; }
}

.wx-qa-msg-error {
  font-size: 12px;
  color: var(--wx-red);
  margin: 4px 0 0;
}

/* Citations inline */
.wx-qa-citations {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.wx-qa-cite {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px 3px 6px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  background: var(--bg-card);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.wx-qa-cite:hover {
  border-color: var(--wx-green);
  color: var(--wx-green);
}

.cite-num {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: var(--wx-green-light);
  color: var(--wx-green);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}

.cite-text {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wx-qa-ref-link {
  background: none;
  border: none;
  color: var(--wx-green);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
  text-align: left;
  transition: color 0.15s;
}

.wx-qa-ref-link:hover {
  color: var(--wx-green-hover);
}

/* Empty state */
.wx-qa-msg-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-placeholder);
  font-size: 14px;
}

.wx-qa-empty-icon { opacity: 0.4; }

/* ── Composer ─────────────────────────────────────────────────────────── */
.wx-qa-composer {
  padding: 12px 24px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-light);
  flex-shrink: 0;
}

.wx-qa-composer-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  width: 100%;
}

.wx-qa-composer-input {
  flex: 1;
}

.wx-qa-composer-input textarea {
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

.wx-qa-composer-input textarea:focus {
  border-color: var(--wx-green);
  background: var(--bg-card);
}

.wx-qa-composer-input textarea::placeholder {
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

.wx-composer-btn:hover { background: var(--wx-green-hover); }
.wx-composer-btn:active { transform: scale(0.97); }
.wx-composer-btn:disabled { background: var(--wx-green); opacity: 0.35; cursor: not-allowed; transform: none; }

.wx-spinner-sm {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: wx-spin 0.6s linear infinite;
}

@keyframes wx-spin { to { transform: rotate(360deg); } }

/* ── Citation Drawer ──────────────────────────────────────────────────── */
.wx-citation-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wx-citation-card {
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.wx-citation-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 6px;
}

.wx-citation-head strong {
  font-size: 14px;
  color: var(--text-primary);
}

.wx-citation-source {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 0 10px;
}

.wx-citation-excerpt {
  margin: 0;
  padding: 10px 12px;
  border-left: 3px solid var(--wx-green);
  background: var(--wx-green-bg);
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
}
</style>
