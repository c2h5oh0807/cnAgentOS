<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: true,
})

const rendered = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>

<template>
  <div class="md-renderer" v-html="rendered" />
</template>

<style scoped>
.md-renderer {
  line-height: 1.6;
  word-break: break-word;
  white-space: normal;
}

.md-renderer :deep(p) {
  margin: 0 0 8px;
}

.md-renderer :deep(p:last-child) {
  margin-bottom: 0;
}

.md-renderer :deep(ul),
.md-renderer :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
}

.md-renderer :deep(li) {
  margin-bottom: 2px;
}

.md-renderer :deep(code) {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: rgba(0, 0, 0, 0.06);
  color: var(--text-primary);
}

.md-renderer :deep(pre) {
  margin: 8px 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.04);
  overflow-x: auto;
}

.md-renderer :deep(pre code) {
  padding: 0;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
}

.md-renderer :deep(h1),
.md-renderer :deep(h2),
.md-renderer :deep(h3),
.md-renderer :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
  color: var(--text-primary);
}

.md-renderer :deep(h1) { font-size: 16px; }
.md-renderer :deep(h2) { font-size: 15px; }
.md-renderer :deep(h3) { font-size: 14px; }

.md-renderer :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 12px;
  border-left: 3px solid var(--wx-green, #42b883);
  background: rgba(66, 184, 131, 0.06);
  border-radius: 0 6px 6px 0;
  color: var(--text-secondary);
}

.md-renderer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}

.md-renderer :deep(th),
.md-renderer :deep(td) {
  padding: 6px 10px;
  border: 1px solid var(--border-light, #e8e8e8);
  text-align: left;
}

.md-renderer :deep(th) {
  font-weight: 600;
  background: rgba(0, 0, 0, 0.02);
}

.md-renderer :deep(a) {
  color: var(--wx-green, #42b883);
  text-decoration: underline;
}

.md-renderer :deep(hr) {
  margin: 12px 0;
  border: none;
  border-top: 1px solid var(--border-light, #e8e8e8);
}

.md-renderer :deep(img) {
  max-width: 100%;
  border-radius: 6px;
  margin: 8px 0;
}

.md-renderer :deep(strong) {
  font-weight: 600;
}
</style>
