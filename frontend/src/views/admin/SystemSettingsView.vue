<script setup lang="ts">
import { Check, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { get, post } from '@/api/client'
import AdminPageHeader from '@/components/AdminPageHeader.vue'
import type { DatabaseConfig, DatabaseStatus } from '@/types'
import { errorMessage } from '@/utils/display'

const loading = ref(false)
const testing = ref(false)
const switching = ref(false)
const status = ref<DatabaseStatus | null>(null)
const config = ref<DatabaseConfig | null>(null)
const switchVisible = ref(false)

const form = reactive({
  type: 'sqlite' as 'sqlite' | 'mysql',
  mysql: {
    host: '127.0.0.1',
    port: 3306,
    user: 'cnagentos',
    password: '',
    database: 'cnagentos',
  },
})

async function loadStatus(): Promise<void> {
  loading.value = true
  try {
    const [s, c] = await Promise.all([
      get<DatabaseStatus>('/api/v1/admin/database/status'),
      get<DatabaseConfig>('/api/v1/admin/database/config'),
    ])
    status.value = s
    config.value = c
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

function openSwitchDialog(): void {
  // Pre-fill form from current config
  if (config.value) {
    form.type = config.value.active_database
    form.mysql.host = config.value.mysql.host
    form.mysql.port = config.value.mysql.port
    form.mysql.user = config.value.mysql.user
    form.mysql.password = ''
    form.mysql.database = config.value.mysql.database
  }
  switchVisible.value = true
}

async function testConnection(): Promise<void> {
  testing.value = true
  try {
    const result = await post<{ success: boolean; latency_ms: number }>(
      '/api/v1/admin/database/test',
      form.mysql,
    )
    ElMessage.success(`连接成功 (${result.latency_ms}ms)`)
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    testing.value = false
  }
}

async function doSwitch(): Promise<void> {
  if (form.type === 'mysql') {
    // Require at least host + password for MySQL switch
    if (!form.mysql.host || !form.mysql.password) {
      ElMessage.warning('请填写 MySQL 主机地址和密码')
      return
    }
  }

  try {
    await ElMessageBox.confirm(
      '切换数据库不会迁移已有数据，请确保已做好备份。确定要执行切换吗？',
      '确认切换',
      { confirmButtonText: '确定切换', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return // User cancelled
  }

  switching.value = true
  try {
    const payload: Record<string, unknown> = { type: form.type }
    if (form.type === 'mysql') {
      payload.mysql = { ...form.mysql }
    }
    await post('/api/v1/admin/database/switch', payload)
    ElMessage.success('数据库切换成功')
    switchVisible.value = false
    await loadStatus()
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    switching.value = false
  }
}

onMounted(loadStatus)
</script>

<template>
  <AdminPageHeader title="系统设置" description="管理系统数据库与全局配置" />

  <!-- Database Status Card -->
  <el-card shadow="never" class="db-card">
    <template #header>
      <div class="card-header">
        <span>数据库配置</span>
        <el-button type="primary" size="small" @click="openSwitchDialog">
          切换数据库
        </el-button>
      </div>
    </template>

    <div v-loading="loading" class="status-grid">
      <div class="status-item">
        <span class="label">当前数据库</span>
        <el-tag :type="status?.type === 'mysql' ? 'success' : 'info'" effect="plain" size="large">
          {{ status?.type === 'mysql' ? 'MySQL' : 'SQLite' }}
        </el-tag>
      </div>
      <div class="status-item">
        <span class="label">连接状态</span>
        <span class="value">
          <el-icon v-if="status?.connected" color="#67c23a" size="16"><Check /></el-icon>
          <el-icon v-else color="#f56c6c" size="16"><Close /></el-icon>
          {{ status?.connected ? '已连接' : '未连接' }}
        </span>
      </div>
      <div class="status-item">
        <span class="label">表数量</span>
        <span class="value">{{ status?.table_count ?? '-' }}</span>
      </div>
    </div>
  </el-card>

  <!-- Switch Database Dialog -->
  <el-dialog v-model="switchVisible" title="切换数据库" width="560px" :close-on-click-modal="false">
    <el-alert
      type="warning"
      title="切换数据库不会迁移已有数据，请确保已做好备份"
      :closable="false"
      show-icon
      style="margin-bottom: 20px"
    />

    <el-form label-width="120px">
      <el-form-item label="数据库类型">
        <el-radio-group v-model="form.type">
          <el-radio value="sqlite">SQLite（默认）</el-radio>
          <el-radio value="mysql">MySQL</el-radio>
        </el-radio-group>
      </el-form-item>

      <template v-if="form.type === 'mysql'">
        <el-form-item label="主机地址" required>
          <el-input v-model="form.mysql.host" placeholder="127.0.0.1" />
        </el-form-item>
        <el-form-item label="端口" required>
          <el-input-number v-model="form.mysql.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="form.mysql.user" placeholder="cnagentos" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input
            v-model="form.mysql.password"
            type="password"
            placeholder="MySQL 密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="数据库名" required>
          <el-input v-model="form.mysql.database" placeholder="cnagentos" />
        </el-form-item>
        <el-form-item>
          <el-button :loading="testing" @click="testConnection">
            测试连接
          </el-button>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="switchVisible = false">取消</el-button>
      <el-button type="primary" :loading="switching" @click="doSwitch">
        保存并切换
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.db-card {
  max-width: 720px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-grid {
  display: flex;
  gap: 40px;
  min-height: 60px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-item .label {
  font-size: 13px;
  color: var(--text-muted);
}

.status-item .value {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}
</style>
