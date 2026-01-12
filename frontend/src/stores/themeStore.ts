import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Theme } from '@/types'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

// 辅助函数：应用主题到 DOM
const applyThemeToDOM = (theme: Theme) => {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// 检测用户系统主题偏好
const getSystemTheme = (): Theme => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'light' // 默认浅色
}

// 检查是否是首次访问（localStorage 中没有主题设置）
const isFirstVisit = (): boolean => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('nexus-theme') === null
  }
  return true
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      // 首次访问时使用系统主题偏好，否则使用默认浅色
      theme: isFirstVisit() ? getSystemTheme() : 'light',
      setTheme: (theme) => {
        applyThemeToDOM(theme)
        set({ theme })
      },
      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark'
        applyThemeToDOM(newTheme)
        set({ theme: newTheme })
      },
    }),
    {
      name: 'nexus-theme',
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyThemeToDOM(state.theme)
        }
      },
    }
  )
)

