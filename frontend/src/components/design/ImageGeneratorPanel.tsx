import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, ChevronDown, Upload, X, Loader2, Check } from 'lucide-react'
import type { Resolution, AspectRatio } from './types'

interface ImageModel {
  id: string
  name: string
  icon: string
  speed: string
  quality: string
  coming?: boolean
}

interface ImageGeneratorPanelProps {
  elementId: string
  onGenerate: (prompt: string, resolution: Resolution, aspectRatio: AspectRatio, referenceImage?: string) => Promise<void>
  isGenerating: boolean
  style?: React.CSSProperties
  canvasElements?: Array<{ id: string; type: string; content?: string; referenceImageId?: string }>
  onClose?: () => void
  selectedModel?: string
  onModelChange?: (model: string) => void
  models?: ImageModel[]
}

export function ImageGeneratorPanel({ 
  elementId, 
  onGenerate, 
  isGenerating, 
  style, 
  canvasElements,
  onClose,
  selectedModel = 'gemini-flash',
  onModelChange,
  models = []
}: ImageGeneratorPanelProps) {
  const [prompt, setPrompt] = useState('')
  const [resolution, setResolution] = useState<Resolution>('1K')
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('1:1')
  const [showResolutionDropdown, setShowResolutionDropdown] = useState(false)
  const [showAspectDropdown, setShowAspectDropdown] = useState(false)
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [referenceImage, setReferenceImage] = useState<string | null>(null)
  const [referenceImagePreview, setReferenceImagePreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowResolutionDropdown(false)
        setShowAspectDropdown(false)
        setShowModelDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (elementId && canvasElements) {
      const element = canvasElements.find(el => el.id === elementId)
      if (element?.referenceImageId) {
        const refElement = canvasElements.find(el => el.id === element.referenceImageId)
        if (refElement?.type === 'image' && refElement.content) {
          setReferenceImagePreview(refElement.content)
          setReferenceImage(refElement.content)
        }
      }
    }
  }, [elementId, canvasElements])

  const handleGenerate = () => {
    if (prompt.trim() && !isGenerating) {
      onGenerate(prompt, resolution, aspectRatio, referenceImage || undefined)
    }
  }

  const handleReferenceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = reader.result as string
        setReferenceImage(base64)
        setReferenceImagePreview(base64)
      }
      reader.readAsDataURL(file)
    }
  }

  const clearReferenceImage = () => {
    setReferenceImage(null)
    setReferenceImagePreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const currentModel = models.find(m => m.id === selectedModel) || models[0]
  const resolutions: Resolution[] = ['1K', '2K', '4K']
  const aspectRatios: AspectRatio[] = ['1:1', '4:3', '16:9']

  return (
    <div 
      ref={panelRef}
      className="fixed nexus-card p-5 z-50 w-[380px]"
      style={style}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-primary rounded-xl flex items-center justify-center shadow-lg">
            <Sparkles size={18} className="text-primary-foreground" />
          </div>
          <div>
            <span className="font-semibold text-foreground text-base">AI 图像生成</span>
            <p className="text-xs text-muted-foreground">使用 AI 创建精美图像</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-muted rounded-lg text-muted-foreground hover:text-foreground transition-colors"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Model Selector */}
      {models.length > 0 && (
        <div className="mb-4">
          <label className="text-xs text-muted-foreground mb-2 block font-medium">模型</label>
          <div className="relative">
            <button
              onClick={() => {
                setShowModelDropdown(!showModelDropdown)
                setShowResolutionDropdown(false)
                setShowAspectDropdown(false)
              }}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-muted rounded-xl text-sm text-foreground border border-border hover:border-muted-foreground transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-base">{currentModel?.icon}</span>
                <span>{currentModel?.name}</span>
                {currentModel?.coming && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-[var(--nexus-warning)]/10 text-[var(--nexus-warning)] rounded-full">即将上线</span>
                )}
              </div>
              <ChevronDown size={14} className={`text-muted-foreground transition-transform ${showModelDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {showModelDropdown && (
              <div className="absolute top-full left-0 mt-1 w-full nexus-card p-1.5 z-10">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      if (!model.coming) {
                        onModelChange?.(model.id)
                        setShowModelDropdown(false)
                      }
                    }}
                    disabled={model.coming}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors flex items-center justify-between ${
                      model.coming
                        ? 'text-muted-foreground/50 cursor-not-allowed'
                        : selectedModel === model.id 
                          ? 'bg-primary/10 text-primary' 
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-base">{model.icon}</span>
                      <div>
                        <span className="block">{model.name}</span>
                        <span className="text-[10px] text-muted-foreground/70">{model.speed} • {model.quality}</span>
                      </div>
                    </div>
                    {selectedModel === model.id && !model.coming && (
                      <Check size={14} className="text-primary" />
                    )}
                    {model.coming && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-[var(--nexus-warning)]/10 text-[var(--nexus-warning)] rounded-full">即将</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Prompt Input */}
      <div className="relative mb-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="描述你想要生成的图像..."
          className="nexus-input w-full resize-none h-24"
        />
      </div>

      {/* Reference Image Section */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground font-medium">参考图（可选）</span>
          {referenceImagePreview && (
            <button
              onClick={clearReferenceImage}
              className="text-xs text-destructive hover:text-destructive/80 transition-colors"
            >
              移除
            </button>
          )}
        </div>
        
        {referenceImagePreview ? (
          <div className="relative w-16 h-16 rounded-lg overflow-hidden border border-border">
            <img 
              src={referenceImagePreview} 
              alt="Reference" 
              className="w-full h-full object-cover"
            />
          </div>
        ) : (
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex items-center justify-center gap-2 py-3 border border-dashed border-border rounded-xl text-muted-foreground hover:border-primary/30 hover:text-primary/70 hover:bg-primary/5 transition-all text-sm"
          >
            <Upload size={16} />
            <span>上传参考图</span>
          </button>
        )}
        
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleReferenceUpload}
          accept="image/*"
          className="hidden"
        />
      </div>

      {/* Options Row */}
      <div className="flex gap-2 mb-5">
        {/* Resolution */}
        <div className="relative flex-1">
          <label className="text-[10px] text-muted-foreground/70 mb-1 block">分辨率</label>
          <button
            onClick={() => {
              setShowResolutionDropdown(!showResolutionDropdown)
              setShowAspectDropdown(false)
              setShowModelDropdown(false)
            }}
            className="w-full flex items-center justify-between px-3 py-2 bg-muted rounded-lg text-sm text-muted-foreground border border-border hover:border-muted-foreground transition-colors"
          >
            <span>{resolution}</span>
            <ChevronDown size={12} className={`text-muted-foreground/70 transition-transform ${showResolutionDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showResolutionDropdown && (
            <div className="absolute top-full left-0 mt-1 w-full nexus-card p-1 z-10">
              {resolutions.map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    setResolution(r)
                    setShowResolutionDropdown(false)
                  }}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    resolution === r 
                      ? 'bg-primary/10 text-primary' 
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Aspect Ratio */}
        <div className="relative flex-1">
          <label className="text-[10px] text-muted-foreground/70 mb-1 block">宽高比</label>
          <button
            onClick={() => {
              setShowAspectDropdown(!showAspectDropdown)
              setShowResolutionDropdown(false)
              setShowModelDropdown(false)
            }}
            className="w-full flex items-center justify-between px-3 py-2 bg-muted rounded-lg text-sm text-muted-foreground border border-border hover:border-muted-foreground transition-colors"
          >
            <span>{aspectRatio}</span>
            <ChevronDown size={12} className={`text-muted-foreground/70 transition-transform ${showAspectDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showAspectDropdown && (
            <div className="absolute top-full left-0 mt-1 w-full nexus-card p-1 z-10">
              {aspectRatios.map((ar) => (
                <button
                  key={ar}
                  onClick={() => {
                    setAspectRatio(ar)
                    setShowAspectDropdown(false)
                  }}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    aspectRatio === ar 
                      ? 'bg-primary/10 text-primary' 
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {ar}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={!prompt.trim() || isGenerating}
        className={`w-full py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all ${
          prompt.trim() && !isGenerating
            ? 'nexus-btn-primary'
            : 'bg-muted text-muted-foreground cursor-not-allowed border border-border'
        }`}
      >
        {isGenerating ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            <span>生成中...</span>
          </>
        ) : (
          <>
            <Sparkles size={16} />
            <span>生成图像</span>
          </>
        )}
      </button>
    </div>
  )
}
