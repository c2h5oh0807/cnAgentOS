<template>
  <div class="gesture-overlay" :class="{ expanded: showCamera }">
    <!-- Toggle button -->
    <button
      class="gesture-toggle"
      :class="{ active: enabled }"
      :title="enabled ? '关闭手势' : '开启手势'"
      @click="$emit('toggle')"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 11v-1a4 4 0 0 0-8 0v1" />
        <path d="M20 11H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2Z" />
      </svg>
    </button>

    <!-- Camera preview & status -->
    <div v-if="enabled" class="gesture-panel">
      <div class="gesture-camera" @click="showCamera = !showCamera">
        <video
          ref="videoRef"
          autoplay
          playsinline
          muted
          class="gesture-video"
          :class="{ hidden: !showCamera }"
        />
        <div class="gesture-status">
          <template v-if="error">
            <span class="gesture-error-icon">⚠</span>
            <span class="gesture-error-text">{{ error }}</span>
          </template>
          <template v-else-if="!cameraReady">
            <span class="gesture-loading" />
            <span>启动摄像头...</span>
          </template>
          <template v-else-if="currentGesture">
            <span class="gesture-icon">{{ currentGesture }}</span>
            <span class="gesture-label">
              {{ currentGesture === '←' ? '左滑' : currentGesture === '→' ? '右滑' : '已就绪' }}
            </span>
          </template>
          <template v-else>
            <span class="gesture-icon">✋</span>
            <span>挥手切换</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

defineProps<{
  enabled: boolean
  cameraReady: boolean
  currentGesture: string
  error: string
}>()

const emit = defineEmits<{
  toggle: []
  videoReady: [videoEl: HTMLVideoElement]
}>()

const showCamera = ref(true)
const videoRef = ref<HTMLVideoElement | null>(null)

watch(
  videoRef,
  (videoEl) => {
    if (videoEl) {
      emit('videoReady', videoEl)
    }
  },
  { flush: 'post' },
)
</script>

<style scoped>
.gesture-overlay {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  pointer-events: none;
}

.gesture-toggle,
.gesture-panel {
  pointer-events: auto;
}

.gesture-toggle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: var(--bg-card, #fff);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #666);
  transition: all 0.2s;
  z-index: 1;
}

.gesture-toggle:hover {
  transform: scale(1.05);
}

.gesture-toggle.active {
  background: var(--wx-green, #07C160);
  color: #fff;
  box-shadow: 0 2px 12px rgba(7, 193, 96, 0.4);
}

.gesture-panel {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  width: 180px;
  transition: all 0.3s;
}

.gesture-camera {
  cursor: pointer;
  position: relative;
}

.gesture-video {
  display: block;
  width: 100%;
  height: 135px;
  object-fit: cover;
  background: #1a1a1a;
  transform: scaleX(-1);
}

.gesture-video.hidden {
  display: none;
}

.gesture-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-secondary, #666);
  background: var(--bg-page, #f7f7f7);
  min-height: 32px;
}

.gesture-icon {
  font-size: 16px;
  font-weight: bold;
  color: var(--wx-green, #07C160);
}

.gesture-loading {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--wx-green, #07C160);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.gesture-error-icon {
  color: var(--wx-red, #FA5151);
  font-size: 14px;
}

.gesture-error-text {
  color: var(--wx-red, #FA5151);
  font-size: 11px;
}

.gesture-label {
  font-weight: 500;
}
</style>
