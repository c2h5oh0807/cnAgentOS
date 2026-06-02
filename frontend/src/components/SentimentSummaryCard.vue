<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  taskName?: string
  riskLevel?: string | null    // '低' | '中' | '高' | null
  summarySnippet?: string
  completedAt?: string
  loading?: boolean
}>()

const router = useRouter()

const riskTagType = computed<'success' | 'warning' | 'danger' | 'info'>(() => {
  switch (props.riskLevel) {
    case '低': return 'success'
    case '中': return 'warning'
    case '高': return 'danger'
    default: return 'info'
  }
})

function goToSentiment(): void {
  router.push('/admin/sentiment')
}
</script>

<template>
  <div v-if="loading" class="sentiment-placeholder">
    <div class="sp-line" />
    <div class="sp-line sp-line--short" />
  </div>
  <div v-else-if="!taskName" class="sentiment-empty">
    <el-empty description="暂无舆情分析数据" :image-size="60">
      <el-button size="small" type="primary" @click="goToSentiment">创建分析任务</el-button>
    </el-empty>
  </div>
  <div v-else class="sentiment-card">
    <div class="sentiment-header">
      <span class="sentiment-title">{{ taskName }}</span>
      <el-tag v-if="riskLevel" :type="riskTagType" size="small" effect="dark">
        风险：{{ riskLevel }}
      </el-tag>
    </div>
    <div v-if="summarySnippet" class="sentiment-body">
      {{ summarySnippet }}<span v-if="summarySnippet.length >= 300">…</span>
    </div>
    <div class="sentiment-footer">
      <span v-if="completedAt" class="sentiment-time">{{ completedAt }}</span>
      <el-button size="small" type="primary" link @click="goToSentiment">
        查看详情 →
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.sentiment-card {
  padding: 8px 0;
}
.sentiment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.sentiment-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.sentiment-body {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.sentiment-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sentiment-time {
  font-size: 12px;
  color: #909399;
}
.sentiment-placeholder {
  padding: 20px;
}
.sp-line {
  height: 14px;
  background: linear-gradient(90deg, #f0f2f5 25%, #e8eaed 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 10px;
}
.sp-line--short {
  width: 60%;
}
.sentiment-empty {
  padding: 20px 0;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
