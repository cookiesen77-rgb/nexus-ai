import { useEffect } from 'react'
import { RefreshCw, X } from 'lucide-react'
import { Button } from '@/components/ui'
import { useFileStore } from '@/stores/fileStore'
import { api } from '@/services/api'
import { FileTree } from './FileTree'
import { FileEditor } from './FileEditor'

export function FileExplorer() {
  const { openFiles, activeFile, setRoot, closeFile, setActiveFile } = useFileStore()

  const loadFiles = async () => {
    try {
      const response = await api.listFiles('/')
      if (response.success && response.data) {
        setRoot(response.data)
      }
    } catch (error) {
      console.error('Failed to load files:', error)
    }
  }

  useEffect(() => {
    loadFiles()
  }, [])

  return (
    <div className="h-full flex">
      <div className="w-64 border-r border-[var(--border)] flex flex-col">
        <div className="h-8 flex items-center justify-between px-3 border-b border-[var(--border)]">
          <span className="text-xs text-[var(--text-muted)] uppercase">Explorer</span>
          <Button variant="icon" onClick={loadFiles}>
            <RefreshCw size={14} />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <FileTree />
        </div>
      </div>
      <div className="flex-1 flex flex-col">
        {openFiles.length > 0 ? (
          <>
            <div className="flex border-b border-[var(--border)] overflow-x-auto">
              {openFiles.map((file) => (
                <div
                  key={file.path}
                  className={`flex items-center gap-1 px-3 py-1.5 border-r border-[var(--border)] cursor-pointer text-sm ${
                    activeFile?.path === file.path
                      ? 'bg-[var(--bg-editor)]'
                      : 'bg-[var(--bg-sidebar)] hover:bg-[var(--bg-hover)]'
                  }`}
                  onClick={() => setActiveFile(file)}
                >
                  <span className="truncate max-w-[120px]">{file.name}</span>
                  <button
                    className="ml-1 hover:bg-[var(--bg-hover)] p-0.5"
                    onClick={(e) => {
                      e.stopPropagation()
                      closeFile(file.path)
                    }}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex-1">
              <FileEditor />
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-[var(--text-muted)]">
            Select a file from the explorer
          </div>
        )}
      </div>
    </div>
  )
}

