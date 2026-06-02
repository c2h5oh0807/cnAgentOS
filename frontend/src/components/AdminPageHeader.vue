<script setup lang="ts">
defineProps<{ title: string; description: string }>()
</script>

<template>
  <div class="wx-page-head">
    <div class="wx-page-head-info">
      <h1>{{ title }}</h1>
      <p class="wx-page-head-desc">{{ description }}</p>
    </div>
    <div class="wx-page-head-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.wx-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.wx-page-head-info h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.wx-page-head-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}

.wx-page-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .wx-page-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
