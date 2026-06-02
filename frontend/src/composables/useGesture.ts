/**
 * useGesture — 基于 MediaPipe HandLandmarker 的手势识别 composable
 *
 * 使用 @mediapipe/tasks-vision（新版 API），WASM 和模型文件本地加载。
 * - WASM: /mediapipe/wasm/ （通过 FilesetResolver 加载）
 * - 模型: /mediapipe/hand_landmarker.task
 *
 * 降级策略：无摄像头/授权拒绝时 error 有值，页面操作不受影响。
 */

import { ref, type Ref, onUnmounted } from 'vue'
import { HandLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'

export interface UseGestureOptions {
  onSwipeLeft?: () => void
  onSwipeRight?: () => void
  enabled: Ref<boolean>
}

// 手部连接点索引（MediaPipe HandLandmarker 使用 21 个关键点）
const INDEX_TIP = 8   // 食指指尖

export function useGesture(options: UseGestureOptions) {
  const cameraReady = ref(false)
  const currentGesture = ref('')  // '←' | '→' | '✋' | ''
  const error = ref('')

  const SWIPE_THRESHOLD = 0.12
  const HISTORY_SIZE = 8

  let handLandmarker: HandLandmarker | null = null
  let mediaStream: MediaStream | null = null
  let animFrameId: number | null = null
  let xHistory: number[] = []
  let isRunning = false
  let activeVideoEl: HTMLVideoElement | null = null
  let startGeneration = 0

  /** 处理检测结果 → 识别滑动 */
  function detectGesture(landmarks: Array<{x: number; y: number; z: number}>): void {
    if (!landmarks?.length) {
      currentGesture.value = ''
      return
    }

    const indexTip = landmarks[INDEX_TIP]
    const x = indexTip.x

    xHistory.push(x)
    if (xHistory.length > HISTORY_SIZE) xHistory.shift()

    if (xHistory.length === HISTORY_SIZE) {
      const diff = xHistory[HISTORY_SIZE - 1] - xHistory[0]

      if (diff > SWIPE_THRESHOLD) {
        currentGesture.value = '→'
        xHistory = []
        options.onSwipeRight?.()
      } else if (diff < -SWIPE_THRESHOLD) {
        currentGesture.value = '←'
        xHistory = []
        options.onSwipeLeft?.()
      } else if (Math.abs(diff) < 0.02) {
        currentGesture.value = '✋'
      }
    }
  }

  /** 帧循环：持续检测手部 */
  function detectLoop(videoEl: HTMLVideoElement): void {
    if (!isRunning) return

    if (!handLandmarker || videoEl.readyState < 2) {
      animFrameId = requestAnimationFrame(() => detectLoop(videoEl))
      return
    }

    try {
      const results = handLandmarker.detectForVideo(videoEl, performance.now())
      if (results.landmarks?.length) {
        detectGesture(results.landmarks[0])
      } else {
        currentGesture.value = ''
        xHistory = []
      }
    } catch {
      // 单帧失败不影响后续
    }

    animFrameId = requestAnimationFrame(() => detectLoop(videoEl))
  }

  /** 启动手势识别 */
  async function start(videoEl: HTMLVideoElement): Promise<void> {
    const generation = ++startGeneration
    releaseResources()
    isRunning = true
    error.value = '正在加载手势模型...'

    let nextHandLandmarker: HandLandmarker | null = null
    let nextMediaStream: MediaStream | null = null

    try {
      // 1. 加载 WASM（从本地路径 /mediapipe/wasm/）
      const vision = await FilesetResolver.forVisionTasks('/mediapipe/wasm/')
      if (!isStartCurrent(generation)) return

      error.value = '正在初始化检测器...'

      // 2. 创建 HandLandmarker
      nextHandLandmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: '/mediapipe/hand_landmarker.task',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        numHands: 1,
        minHandDetectionConfidence: 0.5,
        minHandPresenceConfidence: 0.5,
        minTrackingConfidence: 0.5,
      })
      if (!isStartCurrent(generation)) return

      error.value = '正在请求摄像头...'

      // 3. 获取摄像头
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('当前浏览器不支持摄像头访问，请使用 localhost 或 HTTPS 打开页面')
      }
      nextMediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: 'user' },
      })
      if (!isStartCurrent(generation)) return

      videoEl.srcObject = nextMediaStream
      await videoEl.play()
      if (!isStartCurrent(generation)) return

      // 4. 启动检测循环
      handLandmarker = nextHandLandmarker
      nextHandLandmarker = null
      mediaStream = nextMediaStream
      nextMediaStream = null
      activeVideoEl = videoEl
      cameraReady.value = true
      error.value = ''
      detectLoop(videoEl)
    } catch (e: unknown) {
      if (generation === startGeneration) {
        isRunning = false
        releaseResources()
        error.value = describeStartError(e)
      }
    } finally {
      try { nextHandLandmarker?.close() } catch { /* ignore */ }
      nextMediaStream?.getTracks().forEach(track => track.stop())
      if (videoEl.srcObject === nextMediaStream) {
        videoEl.srcObject = null
      }
    }
  }

  /** 停止并释放资源 */
  function stop(): void {
    startGeneration += 1
    isRunning = false
    releaseResources()
    error.value = ''
  }

  function isStartCurrent(generation: number): boolean {
    return generation === startGeneration && isRunning && options.enabled.value
  }

  function releaseResources(): void {
    if (animFrameId !== null) {
      cancelAnimationFrame(animFrameId)
      animFrameId = null
    }
    if (handLandmarker) {
      try { handLandmarker.close() } catch { /* ignore */ }
      handLandmarker = null
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop())
      mediaStream = null
    }
    if (activeVideoEl) {
      activeVideoEl.srcObject = null
      activeVideoEl = null
    }
    xHistory = []
    cameraReady.value = false
    currentGesture.value = ''
  }

  function describeStartError(error: unknown): string {
    const name = readErrorProperty(error, 'name')
    const message = readErrorProperty(error, 'message')

    if (name === 'NotAllowedError' || message.includes('Permission')) {
      return '摄像头权限被拒绝，请在浏览器地址栏中允许访问'
    }
    if (name === 'NotFoundError') {
      return '未检测到摄像头'
    }
    if (name === 'NotReadableError') {
      return '摄像头正被其他程序占用'
    }
    return message || '启动失败'
  }

  function readErrorProperty(error: unknown, key: 'name' | 'message'): string {
    if (typeof error !== 'object' || error === null) return ''

    const value = (error as Record<string, unknown>)[key]
    return typeof value === 'string' ? value : ''
  }

  onUnmounted(() => stop())

  return { cameraReady, currentGesture, error, start, stop }
}
