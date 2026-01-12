import { create } from 'zustand'
import type { FileNode } from '@/types'

interface FileState {
  root: FileNode | null
  openFiles: FileNode[]
  activeFile: FileNode | null
  expandedPaths: Set<string>
  
  setRoot: (root: FileNode) => void
  openFile: (file: FileNode) => void
  closeFile: (path: string) => void
  setActiveFile: (file: FileNode | null) => void
  updateFileContent: (path: string, content: string) => void
  toggleExpanded: (path: string) => void
  refreshTree: () => void
}

export const useFileStore = create<FileState>((set) => ({
  root: null,
  openFiles: [],
  activeFile: null,
  expandedPaths: new Set(),

  setRoot: (root) => {
    set({ root })
  },

  openFile: (file) => {
    set((state) => {
      const exists = state.openFiles.some((f) => f.path === file.path)
      if (exists) {
        return { activeFile: file }
      }
      return {
        openFiles: [...state.openFiles, file],
        activeFile: file,
      }
    })
  },

  closeFile: (path) => {
    set((state) => {
      const newOpenFiles = state.openFiles.filter((f) => f.path !== path)
      const newActiveFile =
        state.activeFile?.path === path
          ? newOpenFiles[newOpenFiles.length - 1] || null
          : state.activeFile
      return {
        openFiles: newOpenFiles,
        activeFile: newActiveFile,
      }
    })
  },

  setActiveFile: (file) => {
    set({ activeFile: file })
  },

  updateFileContent: (path, content) => {
    set((state) => ({
      openFiles: state.openFiles.map((f) =>
        f.path === path ? { ...f, content } : f
      ),
      activeFile:
        state.activeFile?.path === path
          ? { ...state.activeFile, content }
          : state.activeFile,
    }))
  },

  toggleExpanded: (path) => {
    set((state) => {
      const newExpanded = new Set(state.expandedPaths)
      if (newExpanded.has(path)) {
        newExpanded.delete(path)
      } else {
        newExpanded.add(path)
      }
      return { expandedPaths: newExpanded }
    })
  },

  refreshTree: () => {
    // Will be implemented with API call
  },
}))

