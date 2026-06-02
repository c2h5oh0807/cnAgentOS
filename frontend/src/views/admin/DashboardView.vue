<script setup lang="ts">
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { onMounted, onUnmounted, ref, computed, nextTick, watch } from 'vue'

import { get } from '@/api/client'
import AdminPageHeader from '@/components/AdminPageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import HealthAlertBar from '@/components/HealthAlertBar.vue'
import SentimentSummaryCard from '@/components/SentimentSummaryCard.vue'
import type { DashboardStats, TrendData, KeywordItem } from '@/types'
import { errorMessage } from '@/utils/display'

const loading = ref(false)
const stats = ref<DashboardStats | null>(null)
const trends = ref<TrendData | null>(null)
const keywords = ref<KeywordItem[]>([])
const insightTab = ref<'sentiment' | 'wordcloud'>('sentiment')

// Model error rate for health bar
const modelErrorRate = computed<number | undefined>(() => {
  if (!stats.value?.model_calls?.total) return undefined
  const totalFailed = Object.values(stats.value.model_calls.by_purpose || {})
    .reduce((s, p) => s + (p.failed || 0), 0)
  return Number(((totalFailed / stats.value.model_calls.total) * 100).toFixed(1))
})

// Deltas for KPI cards
const kpiDeltas = computed(() => {
  if (!trends.value) return {}
  const t = trends.value
  const mid = Math.floor(t.knowledge_items.length / 2)
  if (mid < 2) return {}
  const calc = (arr: TrendData['knowledge_items']) => {
    const recent = arr.slice(mid).reduce((s, d) => s + d.count, 0)
    const prev = arr.slice(0, mid).reduce((s, d) => s + d.count, 0)
    return prev > 0 ? Math.round(((recent - prev) / prev) * 100) : 0
  }
  return {
    knowledge_items: calc(t.knowledge_items),
    qa_questions: calc(t.qa_questions),
    chat_messages: calc(t.chat_messages),
  }
})

// Chart refs
const contentTrendChartRef = ref<HTMLElement | null>(null)
const modelTrendChartRef = ref<HTMLElement | null>(null)
const wordcloudChartRef = ref<HTMLElement | null>(null)
const modelChartRef = ref<HTMLElement | null>(null)
const sourceChartRef = ref<HTMLElement | null>(null)

let contentTrendChart: echarts.ECharts | null = null
let modelTrendChart: echarts.ECharts | null = null
let wordcloudChart: echarts.ECharts | null = null
let modelChart: echarts.ECharts | null = null
let sourceChart: echarts.ECharts | null = null
let refreshTimer: ReturnType<typeof setInterval> | null = null

// ----- Deterministic color for wordcloud -----
function stringToHue(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  return ((hash % 360) + 360) % 360
}

// ----- Data loading -----
async function load(): Promise<void> {
  loading.value = true
  try {
    const [statsData, trendsData, kwData] = await Promise.all([
      get<DashboardStats>('/api/v1/admin/dashboard/stats'),
      get<TrendData>('/api/v1/admin/dashboard/trends?days=30'),
      get<KeywordItem[]>('/api/v1/admin/dashboard/keywords?limit=50'),
    ])
    stats.value = statsData
    trends.value = trendsData
    keywords.value = kwData
    await nextTick()
    renderCharts()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

function renderCharts(): void {
  renderContentTrendChart()
  renderModelTrendChart()
  renderWordcloud()
  renderModelUsageChart()
  renderSourceDistribution()
}

// ----- Chart renderers -----
function renderContentTrendChart(): void {
  if (!contentTrendChartRef.value || !trends.value) return
  if (!contentTrendChart) contentTrendChart = echarts.init(contentTrendChartRef.value)

  const dates = trends.value.knowledge_items.map(d => d.date)
  contentTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['知识项', '问数', '消息'], textStyle: { fontSize: 11 } },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '知识项', type: 'line', smooth: true,
        data: trends.value.knowledge_items.map(d => d.count),
        itemStyle: { color: '#409EFF' },
      },
      {
        name: '问数', type: 'line', smooth: true,
        data: trends.value.qa_questions.map(d => d.count),
        itemStyle: { color: '#67C23A' },
      },
      {
        name: '消息', type: 'line', smooth: true,
        data: trends.value.chat_messages.map(d => d.count),
        itemStyle: { color: '#E6A23C' },
      },
    ],
  })
}

function renderModelTrendChart(): void {
  if (!modelTrendChartRef.value || !trends.value) return
  if (!modelTrendChart) modelTrendChart = echarts.init(modelTrendChartRef.value)

  const dates = trends.value.knowledge_items.map(d => d.date)
  const series: echarts.EChartsOption['series'] = []

  if (trends.value.model_calls?.length) {
    series.push({
      name: '模型调用',
      type: 'line',
      smooth: true,
      data: trends.value.model_calls.map(d => d.count),
      itemStyle: { color: '#909399' },
    } as any)
  }
  if (trends.value.model_tokens?.length) {
    series.push({
      name: 'Token(k)',
      type: 'line',
      smooth: true,
      lineStyle: { type: 'dashed' },
      data: trends.value.model_tokens.map(d => Math.round(d.count / 1000)),
      itemStyle: { color: '#B37FEB' },
    } as any)
  }

  if (!series.length) return
  modelTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['模型调用', 'Token(k)'], textStyle: { fontSize: 11 } },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1 },
    series,
  })
}

function renderWordcloud(): void {
  if (!wordcloudChartRef.value || !keywords.value.length) return
  if (!wordcloudChart) wordcloudChart = echarts.init(wordcloudChartRef.value)

  const maxCount = Math.max(...keywords.value.map(k => k.count))
  wordcloudChart.setOption({
    tooltip: { show: true },
    series: [
      {
        type: 'wordCloud',
        gridSize: 10,
        sizeRange: [12, 48],
        rotationRange: [-30, 30],
        shape: 'circle',
        data: keywords.value.map(k => ({
          name: k.word,
          value: k.count,
          textStyle: {
            color: `hsl(${stringToHue(k.word)}, 65%, 50%)`,
            fontSize: 12 + (k.count / maxCount) * 36,
          },
        })),
      },
    ],
  })
}

function renderModelUsageChart(): void {
  if (!modelChartRef.value || !stats.value?.model_calls) return
  if (!modelChart) modelChart = echarts.init(modelChartRef.value)

  const byPurpose = stats.value.model_calls.by_purpose || {}
  const purposes = Object.keys(byPurpose)
  if (!purposes.length) {
    modelChart.setOption({ title: { text: '暂无数据', left: 'center', top: 'center' } })
    return
  }

  const purposeLabels: Record<string, string> = {
    qa_answer: '智能问数',
    sentiment_analysis: '舆情分析',
    connection_test: '连接测试',
  }

  const xData = purposes.map(p => purposeLabels[p] || p)
  const countData = purposes.map(p => byPurpose[p].count)
  const failedData = purposes.map(p => byPurpose[p].failed)

  modelChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['调用次数', '失败次数'], textStyle: { fontSize: 11 } },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: xData },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '调用次数',
        type: 'bar',
        data: countData,
        itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '失败次数',
        type: 'bar',
        data: failedData,
        itemStyle: { color: '#F56C6C', borderRadius: [4, 4, 0, 0] },
      },
    ],
  })
}

function renderSourceDistribution(): void {
  if (!sourceChartRef.value || !stats.value?.source_distribution?.length) return
  if (!sourceChart) sourceChart = echarts.init(sourceChartRef.value)

  const sources = stats.value.source_distribution!
    .sort((a, b) => b.item_count - a.item_count)
    .slice(0, 15)

  sourceChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 120, right: 30, top: 10, bottom: 30 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: {
      type: 'category',
      data: sources.map(s => s.source_name),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: sources.map(s => ({
          value: s.item_count,
          itemStyle: {
            color: s.status === 'active' ? '#67C23A' : s.status === 'disabled' ? '#909399' : '#E6A23C',
          },
        })),
        barMaxWidth: 20,
      },
    ],
  })
}

// ----- Watch for tab switching (wordcloud re-render) -----
watch(insightTab, async (newVal) => {
  if (newVal === 'wordcloud') {
    // Dispose so we re-init since DOM was recreated by v-if
    if (wordcloudChart) { wordcloudChart.dispose(); wordcloudChart = null }
    await nextTick()
    renderWordcloud()
  }
})

// ----- Lifecycle -----
onMounted(() => {
  load()
  refreshTimer = setInterval(load, 60000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  ;[contentTrendChart, modelTrendChart, wordcloudChart, modelChart, sourceChart]
    .forEach(chart => chart?.dispose())
})
</script>

<template>
  <AdminPageHeader title="数智大屏" description="系统核心指标与数据可视化" />

  <!-- System Health Alert Bar -->
  <HealthAlertBar
    :risk-level="stats?.sentiment_summary?.risk_level"
    :collection-health="stats?.collection_health?.success_rate"
    :model-error-rate="modelErrorRate"
    :loading="loading && !stats"
  />

  <!-- Row 1: KPI Cards -->
  <el-row :gutter="16" style="margin-bottom: 16px">
    <el-col :xs="12" :sm="8" :md="4" style="margin-bottom: 12px">
      <KpiCard
        title="知识项"
        :value="stats?.knowledge_items?.total ?? '-'"
        :delta="kpiDeltas.knowledge_items"
        delta-label="较半月前"
        :subtitle="`可用 ${stats?.knowledge_items?.available ?? 0}`"
        color="#409EFF"
        :loading="loading && !stats"
      />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4" style="margin-bottom: 12px">
      <KpiCard
        title="采集成功率"
        :value="(stats?.collection_health?.success_rate ?? '-') + '%'"
        subtitle="近7天失败 {{ stats?.collection_health?.recent_failures_7d ?? 0 }} 次"
        color="#67C23A"
        :loading="loading && !stats"
      />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4" style="margin-bottom: 12px">
      <KpiCard
        title="模型调用"
        :value="stats?.model_calls?.total_today ?? '-'"
        delta-label="今日"
        :subtitle="`平均 ${stats?.model_calls?.avg_latency_ms ?? '-'}ms`"
        color="#B37FEB"
        :loading="loading && !stats"
      />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4" style="margin-bottom: 12px">
      <KpiCard
        title="问数会话"
        :value="stats?.qa_sessions?.total ?? '-'"
        :delta="kpiDeltas.qa_questions"
        delta-label="较半月前"
        color="#E6A23C"
        :loading="loading && !stats"
      />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4" style="margin-bottom: 12px">
      <KpiCard
        title="活跃用户"
        :value="(stats?.users?.active_today ?? '-') + '/' + (stats?.users?.total ?? '-')"
        subtitle="今日 / 总数"
        color="#F56C6C"
        :loading="loading && !stats"
      />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4" style="margin-bottom: 12px">
      <KpiCard
        title="数据源"
        :value="stats?.watch_sources?.total ?? '-'"
        :subtitle="`活跃 ${stats?.watch_sources?.active ?? 0}`"
        color="#19C9A8"
        :loading="loading && !stats"
      />
    </el-col>
  </el-row>

  <!-- Row 2: Two trend charts side by side -->
  <el-row :gutter="16" style="margin-bottom: 16px">
    <el-col :xs="24" :md="12" style="margin-bottom: 12px">
      <el-card>
        <template #header><span>采集趋势 (30日)</span></template>
        <div ref="contentTrendChartRef" style="width: 100%; height: 300px"></div>
      </el-card>
    </el-col>
    <el-col :xs="24" :md="12" style="margin-bottom: 12px">
      <el-card>
        <template #header><span>模型趋势 (30日)</span></template>
        <div ref="modelTrendChartRef" style="width: 100%; height: 300px"></div>
      </el-card>
    </el-col>
  </el-row>

  <!-- Row 3: Model Usage + Sentiment / Wordcloud -->
  <el-row :gutter="16" style="margin-bottom: 16px">
    <el-col :xs="24" :md="14" style="margin-bottom: 12px">
      <el-card>
        <template #header><span>模型调用统计</span></template>
        <div ref="modelChartRef" style="width: 100%; height: 300px"></div>
      </el-card>
    </el-col>
    <el-col :xs="24" :md="10" style="margin-bottom: 12px">
      <el-card>
        <template #header>
          <div style="display: flex; align-items: center; justify-content: space-between">
            <el-radio-group v-model="insightTab" size="small">
              <el-radio-button value="sentiment">舆情快照</el-radio-button>
              <el-radio-button value="wordcloud">词云</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <SentimentSummaryCard
          v-if="insightTab === 'sentiment'"
          :task-name="stats?.sentiment_summary?.latest_task_name"
          :risk-level="stats?.sentiment_summary?.risk_level"
          :summary-snippet="stats?.sentiment_summary?.summary_snippet"
          :completed-at="stats?.sentiment_summary?.completed_at"
          :loading="loading && !stats"
        />
        <div
          v-if="insightTab === 'wordcloud'"
          ref="wordcloudChartRef"
          style="width: 100%; height: 300px"
        />
        <div
          v-if="insightTab === 'wordcloud' && !keywords.length && !loading"
          style="text-align:center;padding:40px;color:#999"
        >暂无关键词数据</div>
      </el-card>
    </el-col>
  </el-row>

  <!-- Row 4: Source Distribution (full width) -->
  <el-row :gutter="16" style="margin-bottom: 16px">
    <el-col :span="24">
      <el-card>
        <template #header><span>数据源分布</span></template>
        <div ref="sourceChartRef" style="width: 100%; height: 300px"></div>
      </el-card>
    </el-col>
  </el-row>

  <!-- Loading overlay -->
  <div v-if="loading" v-loading="loading" style="min-height: 50px"></div>
</template>

<style scoped>
.el-card {
  border-radius: 8px;
}
</style>
