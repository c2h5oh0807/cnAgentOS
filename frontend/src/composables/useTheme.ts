import { computed, ref, watch } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'cnagentos-theme'

/** Detect system preference on first visit when no stored preference exists. */
function detectSystemTheme(): Theme {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function loadTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return detectSystemTheme()
}

function apply(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)
}

const current = ref<Theme>(loadTheme())
apply(current.value)

/** Persist changes to localStorage and update <html data-theme>. */
watch(current, (t) => {
  localStorage.setItem(STORAGE_KEY, t)
  apply(t)
})

export function useTheme() {
  const isDark = computed(() => current.value === 'dark')

  function toggle(): void {
    current.value = current.value === 'light' ? 'dark' : 'light'
  }

  return { theme: current, isDark, toggle }
}
