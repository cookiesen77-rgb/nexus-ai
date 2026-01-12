import React from 'react'
import {
  Download,
  Trash2,
  ArrowRight,
  Palette,
  Crop,
  Sparkles,
  Copy,
  Expand,
  Eraser,
  Layers2,
  Type,
  MoreHorizontal,
  Maximize2
} from 'lucide-react'
import type { CanvasElement } from './types'

interface ContextToolbarProps {
  element: CanvasElement
  onUpdate: (id: string, updates: Partial<CanvasElement>) => void
  onDelete: (id: string) => void
  onConnectFlow?: (element: CanvasElement) => void
  onRegionEdit?: (element: CanvasElement) => void
  // 第 4 张图那排（Lovart）：放大/移除背景/Mockup/擦除/编辑元素/编辑文字
  onUpscale?: (element: CanvasElement) => void
  onRemoveBackground?: (element: CanvasElement) => void
  onMockup?: (element: CanvasElement) => void
  onEditElements?: (element: CanvasElement) => void
  onEditText?: (element: CanvasElement) => void
}

export function ContextToolbar({
  element,
  onUpdate,
  onDelete,
  onConnectFlow,
  onRegionEdit,
  onUpscale,
  onRemoveBackground,
  onMockup,
  onEditElements,
  onEditText
}: ContextToolbarProps) {
  if (!element) return null

  const handleColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdate(element.id, { color: e.target.value })
  }

  const handleDownload = () => {
    if (element.type === 'image' && element.content) {
      const link = document.createElement('a')
      link.href = element.content
      link.download = `nexus-image-${element.id.slice(0, 8)}.png`
      link.click()
    }
  }

  const handleCopy = async () => {
    if (element.type === 'image' && element.content) {
      try {
        const response = await fetch(element.content)
        const blob = await response.blob()
        await navigator.clipboard.write([
          new ClipboardItem({ [blob.type]: blob })
        ])
      } catch (err) {
        console.error('Failed to copy image:', err)
      }
    }
  }

  // Lovart 风格的工具栏基础类（胶囊条）
  const toolbarBase =
    "lovart-glass rounded-2xl px-3 py-2 flex items-center gap-1 shadow-xl"
  const btn =
    "lovart-context-btn"
  const btnPrimary =
    "lovart-context-btn primary"
  const btnGhost =
    "lovart-context-btn"
  const btnDisabled =
    "lovart-context-btn opacity-50 cursor-not-allowed"
  const divider = "w-px h-5 bg-border mx-1"
  const labelText = "text-[10px] text-muted-foreground"
  const inputStyle = "w-12 px-1.5 py-1 bg-muted border border-border rounded-md text-xs text-center text-foreground focus:outline-none focus:border-primary/50"

  // 针对图片和视频元素显示增强的工具栏
  if (element.type === 'image' || element.type === 'video') {
    const canConnectFlow = element.type === 'image' && !!onConnectFlow
    const canRegionEdit = element.type === 'image' && !!onRegionEdit

    const canUpscale = element.type === 'image' && !!onUpscale
    const canRemoveBackground = element.type === 'image' && !!onRemoveBackground
    const canMockup = element.type === 'image' && !!onMockup
    const canEditElements = element.type === 'image' && !!onEditElements
    const canEditText = element.type === 'image' && !!onEditText

    // fallback（不提供回调时，至少做尺寸放大）
    const handleFallbackScaleUp = () => {
      const w = element.width || 300
      const h = element.height || 300
      onUpdate(element.id, { width: Math.round(w * 1.15), height: Math.round(h * 1.15) })
    }

    return (
      <div
        className={toolbarBase}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* 尺寸 */}
        <div className="flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground select-none">
          <span>{Math.round(element.width || 100)}</span>
          <span className="opacity-60">×</span>
          <span>{Math.round(element.height || 100)}</span>
        </div>

        <div className={divider} />

        {/* 继续生成（保留原功能） */}
        {canConnectFlow && (
          <button onClick={() => onConnectFlow(element)} className={btnPrimary} title="继续生成">
            <Sparkles size={14} />
            <span>继续生成</span>
          </button>
        )}

        {/* 第 4 张图那排：放大、移除背景、Mockup、擦除、编辑元素、编辑文字 */}
        <button
          onClick={() => (canUpscale ? onUpscale?.(element) : handleFallbackScaleUp())}
          className={btnGhost}
          title="放大（HD）"
        >
          <Maximize2 size={14} />
          <span>放大</span>
        </button>

        <button
          onClick={() => onRemoveBackground?.(element)}
          className={canRemoveBackground ? btnGhost : btnDisabled}
          title="移除背景"
          disabled={!canRemoveBackground}
        >
          <Eraser size={14} />
          <span>移除背景</span>
        </button>

        <button
          onClick={() => onMockup?.(element)}
          className={canMockup ? btnGhost : btnDisabled}
          title="Mockup"
          disabled={!canMockup}
        >
          <MoreHorizontal size={14} />
          <span>Mockup</span>
        </button>

        <button
          onClick={() => onRegionEdit?.(element)}
          className={canRegionEdit ? btnGhost : btnDisabled}
          title="擦除"
          disabled={!canRegionEdit}
        >
          <Crop size={14} />
          <span>擦除</span>
        </button>

        <button
          onClick={() => onEditElements?.(element)}
          className={canEditElements ? btnGhost : btnDisabled}
          title="编辑元素"
          disabled={!canEditElements}
        >
          <Layers2 size={14} />
          <span>编辑元素</span>
        </button>

        <button
          onClick={() => onEditText?.(element)}
          className={canEditText ? btnGhost : btnDisabled}
          title="编辑文字"
          disabled={!canEditText}
        >
          <Type size={14} />
          <span>编辑文字</span>
        </button>

        <button className={btnDisabled} title="扩展（待接入）" disabled>
          <Expand size={14} />
          <span>扩展</span>
        </button>

        <div className={divider} />

        {/* 复制/下载/删除 */}
        {element.type === 'image' && (
          <button
            onClick={handleCopy}
            className={btnGhost}
            title="复制到剪贴板"
          >
            <Copy size={14} />
            <span>复制</span>
          </button>
        )}

        {element.type === 'image' && (
          <button
            onClick={handleDownload}
            className={btnGhost}
            title="下载"
          >
            <Download size={14} />
            <span>下载</span>
          </button>
        )}

        <button
          onClick={() => onDelete(element.id)}
          className={btnGhost}
          title="删除"
        >
          <Trash2 size={14} />
          <span>删除</span>
        </button>
      </div>
    )
  }

  // 针对形状元素
  if (element.type === 'shape') {
    return (
      <div
        className={toolbarBase}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* 颜色选择器 */}
        <div className="relative flex items-center gap-1.5 px-1.5">
          <label className="relative cursor-pointer">
            <div 
              className="w-6 h-6 rounded-lg border-2 border-border hover:border-muted-foreground transition-colors overflow-hidden"
              style={{ backgroundColor: element.color || '#9ca3af' }}
            />
            <input
              type="color"
              value={element.color || '#9ca3af'}
              onChange={handleColorChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />
          </label>
        </div>

        <div className={divider} />

        {/* 尺寸输入 */}
        <div className="flex items-center gap-1.5 px-1">
          <span className={labelText}>W</span>
          <input
            type="number"
            value={Math.round(element.width || 100)}
            onChange={(e) => onUpdate(element.id, { width: parseInt(e.target.value) || 100 })}
            className={inputStyle}
          />
          <span className={labelText}>H</span>
          <input
            type="number"
            value={Math.round(element.height || 100)}
            onChange={(e) => onUpdate(element.id, { height: parseInt(e.target.value) || 100 })}
            className={inputStyle}
          />
        </div>

        <div className={divider} />

        {/* 流程连接 */}
        {onConnectFlow && (
          <button
            onClick={() => onConnectFlow(element)}
            className={btnGhost}
            title="连接流程"
          >
            <ArrowRight size={14} />
            <span>连接</span>
          </button>
        )}

        {/* 删除 */}
        <button
          onClick={() => onDelete(element.id)}
          className={btnGhost}
          title="删除"
        >
          <Trash2 size={14} />
          <span>删除</span>
        </button>
      </div>
    )
  }

  // 针对文本元素
  if (element.type === 'text') {
    return (
      <div
        className={toolbarBase}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* 颜色选择器 */}
        <div className="relative flex items-center gap-1.5 px-1.5">
          <label className="relative cursor-pointer">
            <div 
              className="w-6 h-6 rounded-lg border-2 border-border hover:border-muted-foreground transition-colors overflow-hidden flex items-center justify-center"
              style={{ backgroundColor: element.color || 'var(--foreground)' }}
            >
              <Palette size={10} className="opacity-50" style={{ mixBlendMode: 'difference' }} />
            </div>
            <input
              type="color"
              value={element.color || '#1A1A1A'}
              onChange={handleColorChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />
          </label>
        </div>

        <div className={divider} />

        {/* 字号 */}
        <div className="flex items-center gap-1 px-1">
          <span className={labelText}>Size</span>
          <input
            type="number"
            value={element.fontSize || 24}
            onChange={(e) => onUpdate(element.id, { fontSize: parseInt(e.target.value) || 24 })}
            className={inputStyle}
          />
        </div>

        <div className={divider} />

        {/* 删除 */}
        <button
          onClick={() => onDelete(element.id)}
          className={btnGhost}
          title="删除"
        >
          <Trash2 size={14} />
          <span>删除</span>
        </button>
      </div>
    )
  }

  // 默认工具栏 (路径等)
  return (
    <div
      className={toolbarBase}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {/* 颜色选择器 */}
      <div className="relative flex items-center px-1.5">
        <label className="relative cursor-pointer">
          <div 
            className="w-6 h-6 rounded-lg border-2 border-border hover:border-muted-foreground transition-colors"
            style={{ backgroundColor: element.color || 'var(--foreground)' }}
          />
          <input
            type="color"
            value={element.color || '#1A1A1A'}
            onChange={handleColorChange}
            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
          />
        </label>
      </div>

      {element.type === 'path' && (
        <>
          <div className={divider} />
          {/* 线宽 */}
          <div className="flex items-center gap-1 px-1">
            <span className={labelText}>Width</span>
            <input
              type="number"
              value={element.strokeWidth || 2}
              onChange={(e) => onUpdate(element.id, { strokeWidth: parseInt(e.target.value) || 2 })}
              className="w-10 px-1.5 py-1 bg-muted border border-border rounded-md text-xs text-center text-foreground focus:outline-none focus:border-primary/50"
              min={1}
              max={20}
            />
          </div>
        </>
      )}

      <div className={divider} />

      {/* 删除 */}
      <button
        onClick={() => onDelete(element.id)}
        className={btnGhost}
        title="删除"
      >
        <Trash2 size={14} />
        <span>删除</span>
      </button>
    </div>
  )
}
