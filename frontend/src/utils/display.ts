import { ApiError } from '@/api/client'

export function errorMessage(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export function shortTime(value?: string | null): string {
  if (!value) return '-'
  const m = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}/.exec(value)
  return m ? m[0].replace('T', ' ') : value
}

export function statusType(status?: string | null): 'primary' | 'success' | 'info' | 'warning' | 'danger' {
  if (status === 'active' || status === 'available' || status === 'succeeded' || status === 'success') return 'success'
  if (status === 'disabled' || status === 'archived' || status === 'cancelled' || status === 'pending') return 'info'
  if (status === 'excluded' || status === 'partial_failed' || status === 'unhealthy') return 'warning'
  if (status === 'failed' || status === 'error') return 'danger'
  return 'primary'
}

const STATUS_LABELS: Record<string, string> = {
  active: '启用',
  disabled: '停用',
  available: '可用',
  excluded: '排除',
  archived: '归档',
  succeeded: '成功',
  failed: '失败',
  pending: '等待',
  running: '运行中',
  streaming: '生成中',
  completed: '已完成',
  cancelled: '已取消',
  partial_failed: '部分失败',
  unhealthy: '不健康',
  passed: '通过',
  error: '错误',
  success: '成功',
  created: '新增',
  duplicate: '重复',
}

export function statusLabel(status?: string | null): string {
  return status ? (STATUS_LABELS[status] ?? status) : '-'
}

/**
 * ElMessageBox.confirm rejects with the strings 'cancel' or 'close'
 * when the user dismisses the dialog without confirming.
 */
export function isUserCancelled(error: unknown): boolean {
  return error === 'cancel' || error === 'close'
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const size = (bytes / Math.pow(k, i)).toFixed(i > 0 ? 1 : 0)
  return size + ' ' + units[i]
}
