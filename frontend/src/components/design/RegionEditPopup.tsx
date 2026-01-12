import React, { useState, useRef, useEffect } from 'react'
import { Wand2, X, Loader2, Send, Undo2 } from 'lucide-react'
import type { RegionSelection } from './CanvasArea'

interface RegionEditPopupProps {
  selection: RegionSelection
  onClose: () => void
  onSubmit: (prompt: string, keepStyle: boolean) => void
  isProcessing: boolean
}

export function RegionEditPopup({
  selection,
  onClose,
  onSubmit,
  isProcessing
}: RegionEditPopupProps) {
  const [prompt, setPrompt] = useState('')
  const [keepStyle, setKeepStyle] = useState(true)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const popupRef = useRef<HTMLDivElement>(null)

  // 自动聚焦输入框
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  // 快捷提示
  const quickPrompts = [
    { label: '移除', prompt: '移除这个区域的内容，用背景填充' },
    { label: '模糊', prompt: '将这个区域模糊处理' },
    { label: '增强', prompt: '增强这个区域的细节和清晰度' },
    { label: '换色', prompt: '改变这个区域的颜色' },
  ]

  const handleSubmit = () => {
    if (prompt.trim() && !isProcessing) {
      onSubmit(prompt.trim(), keepStyle)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
    if (e.key === 'Escape') {
      onClose()
    }
  }

  // 计算弹窗位置
  const popupStyle: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(selection.screenPosition.x + 10, window.innerWidth - 340),
    top: Math.min(selection.screenPosition.y, window.innerHeight - 300),
    zIndex: 100,
  }

  return (
    <div
      ref={popupRef}
      className="w-80 nexus-card shadow-2xl overflow-hidden"
      style={popupStyle}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--nexus-sidebar-border)]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Wand2 size={16} className="text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">局部编辑</h3>
            <p className="text-[10px] text-muted-foreground">
              区域: {Math.round(selection.bbox[2])}×{Math.round(selection.bbox[3])}px
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* 选区预览 */}
      <div className="px-4 py-3 border-b border-[var(--nexus-sidebar-border)]">
        <div className="relative w-full h-24 bg-muted rounded-lg overflow-hidden">
          {/* 原图背景 */}
          <img
            src={selection.imageBase64}
            alt="原图"
            className="absolute inset-0 w-full h-full object-cover opacity-30"
          />
          {/* 选区高亮 */}
          <div
            className="absolute border-2 border-primary bg-primary/30"
            style={{
              left: `${selection.bboxNormalized[0] * 100}%`,
              top: `${selection.bboxNormalized[1] * 100}%`,
              width: `${selection.bboxNormalized[2] * 100}%`,
              height: `${selection.bboxNormalized[3] * 100}%`,
            }}
          />
        </div>
      </div>

      {/* 快捷操作 */}
      <div className="px-4 py-2 border-b border-[var(--nexus-sidebar-border)]">
        <div className="flex gap-1.5 flex-wrap">
          {quickPrompts.map((qp) => (
            <button
              key={qp.label}
              onClick={() => setPrompt(qp.prompt)}
              className="px-2.5 py-1 text-xs rounded-full bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
            >
              {qp.label}
            </button>
          ))}
        </div>
      </div>

      {/* 输入区域 */}
      <div className="p-4">
        <textarea
          ref={inputRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="描述你想要的修改..."
          className="w-full px-3 py-2 nexus-input resize-none text-sm min-h-[60px] max-h-[100px]"
          disabled={isProcessing}
        />

        {/* 保持风格选项 */}
        <div className="flex items-center gap-2 mt-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={keepStyle}
              onChange={(e) => setKeepStyle(e.target.checked)}
              className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
            />
            <span className="text-xs text-muted-foreground">保持原图风格</span>
          </label>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors flex items-center justify-center gap-1.5"
          >
            <Undo2 size={14} />
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isProcessing}
            className={`flex-1 px-3 py-2 rounded-lg text-sm flex items-center justify-center gap-1.5 transition-all ${
              prompt.trim() && !isProcessing
                ? 'bg-primary text-primary-foreground hover:shadow-[0_0_15px_rgba(var(--primary-rgb),0.4)]'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            }`}
          >
            {isProcessing ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                处理中...
              </>
            ) : (
              <>
                <Send size={14} />
                应用修改
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
