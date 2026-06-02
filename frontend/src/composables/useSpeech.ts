/**
 * useSpeech — 基于 Web Speech API 的语音播报 composable
 *
 * 全局单例模式，所有组件共享一个 SpeechSynthesis 实例。
 * 偏好存储到 localStorage：voice_enabled
 *
 * 使用方式：
 *   const { speak, stop, enabled, supported } = useSpeech()
 *   speak('检测到高风险舆情')
 */

import { ref } from 'vue'

const STORAGE_KEY = 'voice_enabled'

// 全局单例状态
const _supported = ref(typeof window !== 'undefined' && 'speechSynthesis' in window)
const _speaking = ref(false)
const _enabled = ref(readPreference())

function readPreference(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== 'false'
  } catch {
    return true
  }
}

function savePreference(val: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, val ? 'true' : 'false')
  } catch { /* ignore */ }
}

let _utterance: SpeechSynthesisUtterance | null = null
let _onEnd: (() => void) | null = null

/** 内部：停止当前播报 */
function cancelSpeech(): void {
  if (typeof window === 'undefined') return
  window.speechSynthesis.cancel()
  _speaking.value = false
}

export function useSpeech() {
  /** 播报一段文字 */
  function speak(text: string, onEnd?: () => void): void {
    if (!_supported.value || !_enabled.value || !text.trim()) return

    // 停止当前播报
    cancelSpeech()

    _onEnd = onEnd || null
    _utterance = new SpeechSynthesisUtterance(text.trim())

    // 中文语音配置
    _utterance.lang = 'zh-CN'
    _utterance.rate = 1.0
    _utterance.pitch = 1.0
    _utterance.volume = 1.0

    _utterance.onstart = () => {
      _speaking.value = true
    }

    _utterance.onend = () => {
      _speaking.value = false
      _onEnd?.()
      _onEnd = null
    }

    _utterance.onerror = () => {
      _speaking.value = false
      _onEnd = null
    }

    window.speechSynthesis.speak(_utterance)
  }

  /** 停止播报 */
  function stop(): void {
    cancelSpeech()
  }

  /** 切换语音开关 */
  function toggle(): void {
    _enabled.value = !_enabled.value
    savePreference(_enabled.value)
    if (!_enabled.value) {
      cancelSpeech()
    }
  }

  /** 设置语音开关 */
  function setEnabled(val: boolean): void {
    _enabled.value = val
    savePreference(val)
    if (!val) cancelSpeech()
  }

  return {
    speak,
    stop,
    toggle,
    setEnabled,
    speaking: _speaking,
    enabled: _enabled,
    supported: _supported,
  }
}
