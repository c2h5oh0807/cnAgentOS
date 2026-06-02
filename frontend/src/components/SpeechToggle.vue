<template>
  <div class="speech-toggle" v-if="supported">
    <button
      class="speech-btn"
      :class="{ active: enabled }"
      :title="enabled ? '关闭语音播报' : '开启语音播报'"
      @click="toggle"
    >
      <svg v-if="enabled" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
        <line x1="1" y1="1" x2="23" y2="23"/>
      </svg>
    </button>
    <span v-if="speaking" class="speech-indicator">
      <span class="speech-dot" />
      播报中
    </span>
  </div>
</template>

<script setup lang="ts">
import { useSpeech } from '@/composables/useSpeech'

const { toggle, speaking, enabled, supported } = useSpeech()
</script>

<style scoped>
.speech-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
}

.speech-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted, #999);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.speech-btn:hover {
  background: var(--wx-green-light, #EDF9F0);
  color: var(--wx-green, #07C160);
}

.speech-btn.active {
  color: var(--wx-green, #07C160);
}

.speech-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--wx-green, #07C160);
}

.speech-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--wx-green, #07C160);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
