<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  riskLevel?: string | null            // '低' | '中' | '高' | null
  collectionHealth?: number            // 0-100 success rate
  modelErrorRate?: number              // 0-100 percentage
  loading?: boolean
}>()

const maxRisk = computed<'high' | 'medium' | 'low' | 'none'>(() => {
  if (props.riskLevel === '高') return 'high'
  if (props.riskLevel === '中') return 'medium'
  if (props.collectionHealth != null && props.collectionHealth < 80) return 'medium'
  if (props.modelErrorRate != null && props.modelErrorRate > 10) return 'medium'
  if (props.riskLevel === '低') return 'low'
  return 'none'
})

const barClass = computed(() => 'health-bar--' + maxRisk.value)

const barLabel = computed(() => {
  switch (maxRisk.value) {
    case 'high': return '系统告警'
    case 'medium': return '系统注意'
    case 'low': return '系统良好'
    default: return '系统健康'
  }
})

const barIcon = computed(() => {
  switch (maxRisk.value) {
    case 'high': return '⚠️'
    case 'medium': return '⚡'
    case 'low': return '✅'
    default: return '🟢'
  }
})
</script>

<template>
  <div v-if="loading" class="health-bar health-bar--loading">
    <div class="health-bar-placeholder" />
  </div>
  <div v-else class="health-bar" :class="barClass">
    <div class="health-bar-left">
      <span class="health-bar-icon">{{ barIcon }}</span>
      <span class="health-bar-label">{{ barLabel }}</span>
      <span v-if="riskLevel" class="health-bar-tag">舆情风险：{{ riskLevel }}</span>
      <span v-if="collectionHealth != null" class="health-bar-tag">采集健康：{{ collectionHealth }}%</span>
      <span v-if="modelErrorRate != null" class="health-bar-tag">模型错误率：{{ modelErrorRate }}%</span>
    </div>
  </div>
</template>

<style scoped>
.health-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  transition: background 0.3s;
}
.health-bar--high {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  color: #F56C6C;
}
.health-bar--medium {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  color: #E6A23C;
}
.health-bar--low {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67C23A;
}
.health-bar--none {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67C23A;
}
.health-bar--loading {
  background: #fafafa;
  border: 1px solid #eee;
}
.health-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.health-bar-icon {
  font-size: 18px;
}
.health-bar-label {
  font-weight: 600;
  font-size: 14px;
}
.health-bar-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.7);
}
.health-bar-placeholder {
  width: 40%;
  height: 20px;
  background: linear-gradient(90deg, #f0f2f5 25%, #e8eaed 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
