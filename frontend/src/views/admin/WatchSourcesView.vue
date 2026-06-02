<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { getEnvelope, patch, post } from '@/api/client'
import AdminPageHeader from '@/components/AdminPageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useSessionStore } from '@/stores/session'
import type { WatchSourceItem } from '@/types'
import { errorMessage, isUserCancelled, statusLabel } from '@/utils/display'

const session = useSessionStore()
const loading = ref(false)
const submitting = ref(false)
const sources = ref<WatchSourceItem[]>([])
const editingSource = ref<WatchSourceItem | null>(null)
const editSourceVisible = ref(false)
const createSourceVisible = ref(false)
const taskVisible = ref(false)
const taskSource = ref<WatchSourceItem | null>(null)
const sourceQuery = reactive({ q: '', status: '', source_type: '' })
const sourcePagination = reactive({ page: 1, page_size: 20, total: 0 })

const emptySourceForm = () => ({
  name: '',
  source_type: 'web_page',
  entry_url: '',
  allowed_hosts_text: '',
  auth_config_text: '',
  description: '',
  // Rule fields
  request_method: 'GET',
  request_headers_text: '{\n  "Accept": "text/html"\n}',
  request_params_text: '{}',
  extractor_type: 'html',
  extractor_config_text: '{\n  "item_selector": ".item",\n  "title_selector": ".title",\n  "content_selector": ".content"\n}',
  // Cron fields
  cron_expression: '',
})

const sourceForm = reactive(emptySourceForm())
const sourceEditForm = reactive(emptySourceForm())
const taskForm = reactive({ variables_text: '{}' })

function resetSourceForm(): void {
  Object.assign(sourceForm, emptySourceForm())
}

const canRunTask = computed(() => session.permissions.includes('watch.tasks.run'))

function buildQuery(): string {
  const params = new URLSearchParams()
  params.set('page', String(sourcePagination.page))
  params.set('page_size', String(sourcePagination.page_size))
  if (sourceQuery.q.trim()) params.set('q', sourceQuery.q.trim())
  if (sourceQuery.status) params.set('status', sourceQuery.status)
  if (sourceQuery.source_type) params.set('source_type', sourceQuery.source_type)
  return params.toString() ? `?${params}` : ''
}

function applySourcePagination(meta?: { page?: number; page_size?: number; total?: number }): void {
  sourcePagination.page = Number(meta?.page ?? sourcePagination.page)
  sourcePagination.page_size = Number(meta?.page_size ?? sourcePagination.page_size)
  sourcePagination.total = Number(meta?.total ?? sources.value.length)
}

async function loadSources(): Promise<void> {
  loading.value = true
  try {
    const payload = await getEnvelope<WatchSourceItem[]>(`/api/v1/admin/watch-sources${buildQuery()}`)
    sources.value = payload.data
    applySourcePagination(payload.meta ?? payload)
  } catch (error) {
    ElMessage.warning(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function searchSources(): void {
  sourcePagination.page = 1
  void loadSources()
}

function changeSourcePage(page: number): void {
  sourcePagination.page = page
  void loadSources()
}

function changeSourcePageSize(pageSize: number): void {
  sourcePagination.page = 1
  sourcePagination.page_size = pageSize
  void loadSources()
}

function parseJsonObject(value: string, field: string): Record<string, unknown> | null {
  if (!value.trim()) return null
  const parsed = JSON.parse(value) as unknown
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error(`${field} 必须是 JSON 对象`)
  return parsed as Record<string, unknown>
}

function parseHosts(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function jsonText(value?: Record<string, unknown> | null): string {
  return JSON.stringify(value ?? {}, null, 2)
}

/** Build payload for source create/update (includes merged rule fields). */
function sourcePayload(form: typeof sourceForm | typeof sourceEditForm): Record<string, unknown> {
  const body: Record<string, unknown> = {
    name: form.name,
    source_type: form.source_type,
    entry_url: form.entry_url,
    allowed_hosts: parseHosts(form.allowed_hosts_text),
    description: form.description || null,
    // Rule fields
    request_method: form.request_method,
    request_headers: parseJsonObject(form.request_headers_text, '请求头') ?? {},
    request_params: parseJsonObject(form.request_params_text, '请求参数') ?? {},
    extractor_type: form.extractor_type,
    extractor_config: parseJsonObject(form.extractor_config_text, '解析配置') ?? {},
  }
  if (form.auth_config_text.trim()) {
    body.auth_config = parseJsonObject(form.auth_config_text, '认证配置') ?? {}
  }
  if (form.cron_expression.trim()) {
    body.cron_expression = form.cron_expression.trim()
  }
  return body
}

// --- Data Source CRUD ---
async function createSource(): Promise<void> {
  submitting.value = true
  try {
    await post<WatchSourceItem>('/api/v1/admin/watch-sources', sourcePayload(sourceForm))
    createSourceVisible.value = false
    resetSourceForm()
    ElMessage.success('数据源已创建')
    await loadSources()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    submitting.value = false
  }
}

function openSourceEdit(source: WatchSourceItem): void {
  editingSource.value = source
  Object.assign(sourceEditForm, {
    name: source.name,
    source_type: source.source_type,
    entry_url: source.entry_url,
    allowed_hosts_text: source.allowed_hosts.join('\n'),
    auth_config_text: '',
    description: source.description ?? '',
    // Rule fields
    request_method: source.request_method || 'GET',
    request_headers_text: jsonText(source.request_headers),
    request_params_text: jsonText(source.request_params),
    extractor_type: source.extractor_type || 'html',
    extractor_config_text: jsonText(source.extractor_config),
    // Cron fields
    cron_expression: source.cron_expression ?? '',
  })
  editSourceVisible.value = true
}

function closeSourceEdit(): void {
  editSourceVisible.value = false
  editingSource.value = null
}

async function saveSource(): Promise<void> {
  if (!editingSource.value) return
  submitting.value = true
  try {
    // Build payload, only sending changed fields
    const payload = sourcePayload(sourceEditForm)
    await patch<WatchSourceItem>(`/api/v1/admin/watch-sources/${editingSource.value.id}`, payload)
    closeSourceEdit()
    ElMessage.success('数据源已更新')
    await loadSources()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function toggleSource(source: WatchSourceItem): Promise<void> {
  const status = source.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(`确认将数据源 ${source.name} 改为 ${statusLabel(status)}？`, '状态确认', { type: 'warning' })
    await patch<WatchSourceItem>(`/api/v1/admin/watch-sources/${source.id}/status`, { status })
    ElMessage.success('数据源状态已更新')
    await loadSources()
  } catch (error) {
    if (!isUserCancelled(error)) ElMessage.error(errorMessage(error))
  }
}

// --- Manual task execution ---
function openTask(source: WatchSourceItem): void {
  if (!canRunTask.value) return
  taskSource.value = source
  taskForm.variables_text = '{}'
  taskVisible.value = true
}

async function runTask(): Promise<void> {
  if (!taskSource.value || !canRunTask.value) return
  submitting.value = true
  try {
    const variables = parseJsonObject(taskForm.variables_text, '任务变量') ?? {}
    const task = await post<{ id: string; status: string; created_at: string }>('/api/v1/admin/collection-tasks', {
      targets: [{ source_id: taskSource.value.id, variables }],
    })
    // Auto-execute the task immediately
    await post<void>(`/api/v1/admin/collection-tasks/${task.id}/execute`)
    taskVisible.value = false
    ElMessage.success(`采集任务已创建并开始执行：${task.id}`)
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    submitting.value = false
  }
}

onMounted(loadSources)
</script>

<template>
  <admin-page-header title="数据源" description="配置受安全边界约束的数据源（含采集规则），支持手动和定时采集。">
    <el-input v-model="sourceQuery.q" class="toolbar-search" clearable placeholder="搜索数据源" @keyup.enter="searchSources" />
    <el-select v-model="sourceQuery.status" clearable placeholder="状态" style="width: 130px"><el-option value="active" label="启用" /><el-option value="disabled" label="停用" /></el-select>
    <el-select v-model="sourceQuery.source_type" clearable placeholder="类型" style="width: 140px"><el-option value="web_page" label="网页" /><el-option value="web_api" label="API" /></el-select>
    <el-button type="primary" @click="createSourceVisible = true">新增数据源</el-button>
    <el-button @click="searchSources">刷新</el-button>
  </admin-page-header>

  <el-card class="resource-card" shadow="never">
    <template #header><strong>数据源</strong></template>
    <el-table v-loading="loading" :data="sources">
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="source_type" label="类型" width="90" />
      <el-table-column prop="entry_url" label="入口 URL" min-width="220" show-overflow-tooltip />
      <el-table-column label="白名单主机" min-width="160"><template #default="{ row }"><el-tag v-for="host in row.allowed_hosts" :key="host" class="value-tag" effect="plain">{{ host }}</el-tag></template></el-table-column>
      <el-table-column prop="request_method" label="方法" width="70" />
      <el-table-column prop="extractor_type" label="解析" width="70" />
      <el-table-column label="状态" width="90"><template #default="{ row }"><status-tag :value="row.status" /></template></el-table-column>
      <el-table-column label="操作" fixed="right" width="220"><template #default="{ row }">
        <el-button link type="primary" @click.stop="openSourceEdit(row)">编辑</el-button>
        <el-button link @click.stop="toggleSource(row)">启停</el-button>
        <el-button link type="success" :disabled="!canRunTask" @click.stop="openTask(row)">运行</el-button>
      </template></el-table-column>
    </el-table>
    <el-pagination
      class="table-pagination"
      layout="total, sizes, prev, pager, next"
      :current-page="sourcePagination.page"
      :page-size="sourcePagination.page_size"
      :page-sizes="[10, 20, 50, 100]"
      :total="sourcePagination.total"
      @current-change="changeSourcePage"
      @size-change="changeSourcePageSize"
    />
  </el-card>

  <!-- Create Source Dialog -->
  <el-dialog v-model="createSourceVisible" title="新增数据源" width="680px" @close="resetSourceForm">
    <el-form label-position="top" :model="sourceForm">
      <el-row :gutter="16">
        <el-col :span="12"><el-form-item label="名称"><el-input v-model="sourceForm.name" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="类型"><el-select v-model="sourceForm.source_type"><el-option value="web_page" label="网页" /><el-option value="web_api" label="API" /></el-select></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="请求方法"><el-select v-model="sourceForm.request_method"><el-option value="GET" label="GET" /><el-option value="POST" label="POST" /></el-select></el-form-item></el-col>
      </el-row>
      <el-form-item label="入口 URL"><el-input v-model="sourceForm.entry_url" /></el-form-item>
      <el-form-item label="允许主机"><el-input v-model="sourceForm.allowed_hosts_text" type="textarea" :rows="2" placeholder="每行或逗号分隔一个 host" /></el-form-item>
      <el-row :gutter="16">
        <el-col :span="12"><el-form-item label="解析类型"><el-select v-model="sourceForm.extractor_type"><el-option value="html" label="HTML" /><el-option value="json" label="JSON" /></el-select></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="定时 Cron"><el-input v-model="sourceForm.cron_expression" placeholder="如：0 9 * * *（每天9点）" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="请求头 JSON"><el-input v-model="sourceForm.request_headers_text" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="请求参数 JSON"><el-input v-model="sourceForm.request_params_text" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="解析配置 JSON"><el-input v-model="sourceForm.extractor_config_text" type="textarea" :rows="4" /></el-form-item>
      <el-form-item label="认证配置 JSON"><el-input v-model="sourceForm.auth_config_text" type="textarea" :rows="3" placeholder='{"headers":{"Authorization":"Bearer test"}}' /></el-form-item>
      <el-form-item label="说明"><el-input v-model="sourceForm.description" type="textarea" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="createSourceVisible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="createSource">创建</el-button></template>
  </el-dialog>

  <!-- Edit Source Dialog -->
  <el-dialog v-model="editSourceVisible" title="编辑数据源" width="680px" @closed="closeSourceEdit">
    <el-form label-position="top" :model="sourceEditForm">
      <el-row :gutter="16">
        <el-col :span="12"><el-form-item label="名称"><el-input v-model="sourceEditForm.name" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="类型"><el-input v-model="sourceEditForm.source_type" disabled /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="请求方法"><el-select v-model="sourceEditForm.request_method"><el-option value="GET" label="GET" /><el-option value="POST" label="POST" /></el-select></el-form-item></el-col>
      </el-row>
      <el-form-item label="入口 URL"><el-input v-model="sourceEditForm.entry_url" /></el-form-item>
      <el-form-item label="允许主机"><el-input v-model="sourceEditForm.allowed_hosts_text" type="textarea" :rows="2" /></el-form-item>
      <el-row :gutter="16">
        <el-col :span="12"><el-form-item label="解析类型"><el-select v-model="sourceEditForm.extractor_type"><el-option value="html" label="HTML" /><el-option value="json" label="JSON" /></el-select></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="定时 Cron"><el-input v-model="sourceEditForm.cron_expression" placeholder="如：0 9 * * *（每天9点）" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="请求头 JSON"><el-input v-model="sourceEditForm.request_headers_text" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="请求参数 JSON"><el-input v-model="sourceEditForm.request_params_text" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="解析配置 JSON"><el-input v-model="sourceEditForm.extractor_config_text" type="textarea" :rows="4" /></el-form-item>
      <el-form-item label="认证配置 JSON（留空保留旧值）"><el-input v-model="sourceEditForm.auth_config_text" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="说明"><el-input v-model="sourceEditForm.description" type="textarea" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="closeSourceEdit">取消</el-button><el-button type="primary" :loading="submitting" @click="saveSource">保存</el-button></template>
  </el-dialog>

  <!-- Run Task Dialog -->
  <el-dialog v-model="taskVisible" title="运行采集任务" width="560px">
    <p class="dialog-hint">将手动采集数据源：{{ taskSource?.name }}</p>
    <el-input v-model="taskForm.variables_text" type="textarea" :rows="6" />
    <template #footer><el-button @click="taskVisible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="runTask">发起任务</el-button></template>
  </el-dialog>
</template>
