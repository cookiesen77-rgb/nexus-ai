/**
 * Lovart 风格图层面板（图层 + 历史记录占位）
 */
import React, { useMemo, useState } from 'react'
import { ChevronDown, Eye, EyeOff, Lock, Unlock, Layers, X } from 'lucide-react'
import type { CanvasElement } from '../../stores/designStore'

interface LayersDrawerProps {
  isOpen: boolean
  elements: CanvasElement[]
  selectedIds: string[]
  onSelect: (ids: string[]) => void
  onToggleHidden: (id: string) => void
  onToggleLocked: (id: string) => void
  onClose: () => void
}

function getElementLabel(el: CanvasElement): string {
  if (el.name) return el.name
  switch (el.type) {
    case 'image-generator':
      return 'Image Generator'
    case 'video-generator':
      return 'Video Generator'
    case 'image':
      return 'Image'
    case 'video':
      return 'Video'
    case 'text':
      return 'Text'
    case 'shape':
      return 'Shape'
    case 'path':
      return 'Path'
    case 'connector':
      return 'Connector'
    default:
      return 'Layer'
  }
}

export function LayersDrawer({
  isOpen,
  elements,
  selectedIds,
  onSelect,
  onToggleHidden,
  onToggleLocked,
  onClose
}: LayersDrawerProps) {
  const [historyCollapsed, setHistoryCollapsed] = useState(false)

  const layers = useMemo(() => {
    // Lovart：最近生成的在上方
    const sorted = [...elements].filter(el => el.type !== 'connector').reverse()
    return sorted
  }, [elements])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[120]">
      {/* backdrop */}
      <div className="absolute inset-0 bg-black/10" onMouseDown={onClose} />

      {/* panel */}
      <div
        className="absolute left-4 bottom-4 w-[360px] max-w-[calc(100vw-2rem)] h-[72vh] lovart-glass rounded-3xl shadow-2xl overflow-hidden"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-2xl bg-[var(--muted)] flex items-center justify-center">
              <Layers size={16} className="text-[var(--muted-foreground)]" />
            </div>
            <div className="font-semibold text-[var(--foreground)]">图层</div>
          </div>
          <button
            type="button"
            className="p-2 rounded-xl hover:bg-[var(--muted)] text-[var(--muted-foreground)]"
            onClick={onClose}
            title="关闭"
          >
            <X size={16} />
          </button>
        </div>

        {/* History */}
        <div className="border-b border-[var(--border)]">
          <button
            type="button"
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-[var(--muted)]/40 transition"
            onClick={() => setHistoryCollapsed(v => !v)}
          >
            <span className="text-sm font-medium text-[var(--foreground)]">历史记录</span>
            <ChevronDown
              size={16}
              className={`text-[var(--muted-foreground)] transition-transform ${historyCollapsed ? '-rotate-90' : ''}`}
            />
          </button>
          {!historyCollapsed && (
            <div className="px-4 pb-4">
              <div className="h-[110px] rounded-2xl bg-[var(--muted)]/60 border border-[var(--border)] flex items-center justify-center">
                <div className="text-center">
                  <div className="text-[var(--muted-foreground)] text-sm">暂无历史记录</div>
                  <div className="text-[var(--muted-foreground)] text-xs mt-1">后续接入操作历史</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Layers list */}
        <div className="px-2 py-2 overflow-y-auto h-[calc(72vh-56px-56px-140px)]">
          <div className="px-2 py-2 text-xs font-medium text-[var(--muted-foreground)]">图层</div>
          <div className="space-y-1 px-1 pb-3">
            {layers.map((el) => {
              const isSelected = selectedIds.includes(el.id)
              return (
                <div
                  key={el.id}
                  className={`flex items-center gap-3 px-2 py-2 rounded-2xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--muted)] border-[var(--border)]'
                      : 'bg-transparent border-transparent hover:bg-[var(--muted)]/40'
                  }`}
                  onClick={() => onSelect([el.id])}
                >
                  {/* thumb */}
                  <div className="w-12 h-12 rounded-2xl bg-[var(--muted)] border border-[var(--border)] overflow-hidden flex items-center justify-center shrink-0">
                    {el.type === 'image' && el.content ? (
                      <img src={el.content} alt="" className="w-full h-full object-cover" />
                    ) : el.type === 'video' ? (
                      <div className="text-[var(--muted-foreground)] text-xs">VIDEO</div>
                    ) : el.type === 'image-generator' ? (
                      <div className="text-[var(--muted-foreground)] text-xs">IMG</div>
                    ) : el.type === 'video-generator' ? (
                      <div className="text-[var(--muted-foreground)] text-xs">VID</div>
                    ) : (
                      <div className="text-[var(--muted-foreground)] text-xs">{el.type}</div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[var(--foreground)] truncate">
                      {getElementLabel(el)}
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)] truncate">
                      {el.type}
                      {el.width && el.height ? ` · ${Math.round(el.width)}×${Math.round(el.height)}` : ''}
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      className={`w-9 h-9 rounded-2xl flex items-center justify-center transition ${
                        el.locked ? 'bg-[var(--muted)]' : 'hover:bg-[var(--muted)]'
                      }`}
                      title={el.locked ? '解锁' : '锁定'}
                      onClick={(e) => {
                        e.stopPropagation()
                        onToggleLocked(el.id)
                      }}
                    >
                      {el.locked ? (
                        <Lock size={16} className="text-[var(--muted-foreground)]" />
                      ) : (
                        <Unlock size={16} className="text-[var(--muted-foreground)]" />
                      )}
                    </button>
                    <button
                      type="button"
                      className={`w-9 h-9 rounded-2xl flex items-center justify-center transition ${
                        el.hidden ? 'bg-[var(--muted)]' : 'hover:bg-[var(--muted)]'
                      }`}
                      title={el.hidden ? '显示' : '隐藏'}
                      onClick={(e) => {
                        e.stopPropagation()
                        onToggleHidden(el.id)
                      }}
                    >
                      {el.hidden ? (
                        <EyeOff size={16} className="text-[var(--muted-foreground)]" />
                      ) : (
                        <Eye size={16} className="text-[var(--muted-foreground)]" />
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

