import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import type { ViewType, BrowserState, TerminalSession, ConnectionStatus } from '@/types'

interface AppState {
  activeView: ViewType
  setActiveView: (view: ViewType) => void
  agentIsThinking: boolean
  setAgentIsThinking: (isThinking: boolean) => void
  browser: BrowserState
  setBrowserUrl: (url: string) => void
  setBrowserLoading: (isLoading: boolean) => void
  setBrowserHtmlContent: (html: string) => void
  setBrowserScreenshot: (screenshot: string | null) => void
  terminalSessions: TerminalSession[]
  addTerminalSession: () => void
  updateTerminalSession: (id: string, updates: Partial<TerminalSession>) => void
  removeTerminalSession: (id: string) => void
  connectionStatus: ConnectionStatus
  setConnectionStatus: (status: ConnectionStatus) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeView: 'chat',
  setActiveView: (view) => set({ activeView: view }),
  agentIsThinking: false,
  setAgentIsThinking: (isThinking) => set({ agentIsThinking: isThinking }),
  browser: {
    url: 'about:blank',
    isLoading: false,
    htmlContent: '',
    screenshot: null,
  },
  setBrowserUrl: (url) => set((state) => ({ browser: { ...state.browser, url } })),
  setBrowserLoading: (isLoading) => set((state) => ({ browser: { ...state.browser, isLoading } })),
  setBrowserHtmlContent: (html) => set((state) => ({ browser: { ...state.browser, htmlContent: html } })),
  setBrowserScreenshot: (screenshot) => set((state) => ({ browser: { ...state.browser, screenshot } })),
  terminalSessions: [],
  addTerminalSession: () => set((state) => ({
    terminalSessions: [...state.terminalSessions, {
      id: uuidv4(),
      output: 'Terminal session started.\n',
      input: '',
      isRunning: false,
    }],
    activeView: 'terminal',
  })),
  updateTerminalSession: (id, updates) => set((state) => ({
    terminalSessions: state.terminalSessions.map(session =>
      session.id === id ? { ...session, ...updates } : session
    ),
  })),
  removeTerminalSession: (id) => set((state) => ({
    terminalSessions: state.terminalSessions.filter(session => session.id !== id),
  })),
  connectionStatus: 'disconnected',
  setConnectionStatus: (status) => set({ connectionStatus: status }),
}))
