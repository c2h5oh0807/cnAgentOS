<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  delta?: number | null        // percentage change, e.g. 12.5
  deltaLabel?: string          // optional label like "较上周"
  subtitle?: string            // secondary text like "今日新增 5"
  color?: string               // accent color
  loading?: boolean
}>()
</script>

<template>
  <el-card shadow="hover" class="kpi-card">
    <div class="kpi-body" :style="color ? { borderTop: `3px solid ${color}` } : {}">
      <div class="kpi-title">{{ title }}</div>
      <div v-if="loading" class="kpi-loading">
        <div class="kpi-placeholder" />
      </div>
      <template v-else>
        <div class="kpi-value" :style="color ? { color } : {}">{{ value }}</div>
        <div class="kpi-footer">
          <span v-if="delta != null" :class="['kpi-delta', delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat']">
            <template v-if="delta > 0">↑</template>
            <template v-else-if="delta < 0">↓</template>
            {{ delta > 0 ? '+' : '' }}{{ delta }}%
          </span>
          <span v-if="deltaLabel" class="kpi-delta-label">{{ deltaLabel }}</span>
          <span v-if="subtitle" class="kpi-subtitle">{{ subtitle }}</span>
        </div>
      </template>
    </div>
  </el-card>
</template>

<style scoped>
.kpi-card {
  border-radius: 8px;
  margin-bottom: 0;
}
.kpi-body {
  padding: 4px 0;
  text-align: center;
}
.kpi-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1.2;
  margin-bottom: 6px;
}
.kpi-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
}
.kpi-delta {
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}
.kpi-delta.up {
  color: #67C23A;
  background: #f0f9eb;
}
.kpi-delta.down {
  color: #F56C6C;
  background: #fef0f0;
}
.kpi-delta.flat {
  color: #909399;
  background: #f4f4f5;
}
.kpi-delta-label {
  color: #909399;
}
.kpi-subtitle {
  color: #909399;
}
.kpi-loading {
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kpi-placeholder {
  width: 60%;
  height: 18px;
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
