/**
 * 画布内图像生成器面板
 * 跟随选中的 image-generator 元素定位
 * 仿照 OpenLovart 的交互模式
 */
import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, ChevronDown, Zap, Image as ImageIcon, Upload, X, Loader2 } from 'lucide-react'
import type { CanvasElement, Resolution, AspectRatio } from './types'

interface CanvasImageGeneratorPanelProps {
  elementId: string
  position: { left: number; top: number }
  onGenerate: (prompt: string, resolution: Resolution, aspectRatio: AspectRatio, referenceImageBase64?: string) => Promise<void>
  isGenerating: boolean
  canvasElements: CanvasElement[]
  referenceImageId?: string
  onClose?: () => void
}

export function CanvasImageGeneratorPanel({
  elementId,
  position,
  onGenerate,
  isGenerating,
  canvasElements,
  referenceImageId,
  onClose
}: CanvasImageGeneratorPanelProps) {
  const [prompt, setPrompt] = useState('')
  const [resolution, setResolution] = useState<Resolution>('1K')
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('1:1')
  const [selectedReferenceId, setSelectedReferenceId] = useState<string | null>(referenceImageId || null)
  const [uploadedReference, setUploadedReference] = useState<string | null>(null)
  
  const [showResolutionMenu, setShowResolutionMenu] = useState(false)
  const [showAspectRatioMenu, setShowAspectRatioMenu] = useState(false)
  const [showReferenceMenu, setShowReferenceMenu] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const resolutions: Resolution[] = ['1K', '2K', '4K']
  const aspectRatios: AspectRatio[] = ['1:1', '4:3', '16:9']

  // 获取画布中的图像元素
  const imageElements = canvasElements.filter(
    el => el.type === 'image' && el.content && el.id !== elementId
  )

  // 自动设置参考图像（如果有关联）
  useEffect(() => {
    if (referenceImageId && !selectedReferenceId) {
      setSelectedReferenceId(referenceImageId)
    }
  }, [referenceImageId])

  // 获取当前参考图像
  const getReferenceImageBase64 = (): string | undefined => {
    if (uploadedReference) {
      return uploadedReference
    }
    if (selectedReferenceId) {
      const refElement = canvasElements.find(el => el.id === selectedReferenceId)
      if (refElement?.content) {
        // 提取 base64 数据
        if (refElement.content.includes('base64,')) {
          return refElement.content.split('base64,')[1]
        }
        return refElement.content
      }
    }
    return undefined
  }

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (prompt.trim() && !isGenerating) {
        await handleGenerate()
      }
    }
  }

  const handleGenerate = async () => {
    if (!prompt.trim() || isGenerating) return
    const refBase64 = getReferenceImageBase64()
    await onGenerate(prompt, resolution, aspectRatio, refBase64)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = () => {
        const result = reader.result as string
        if (result.includes('base64,')) {
          setUploadedReference(result.split('base64,')[1])
        } else {
          setUploadedReference(result)
        }
        setSelectedReferenceId(null)
      }
      reader.readAsDataURL(file)
    }
    setShowReferenceMenu(false)
  }

  const handleCanvasImageSelect = (imageId: string) => {
    setSelectedReferenceId(imageId)
    setUploadedReference(null)
    setShowReferenceMenu(false)
  }

  const clearReference = () => {
    setSelectedReferenceId(null)
    setUploadedReference(null)
  }

  const hasReference = selectedReferenceId || uploadedReference

  return (
    <div
      ref={panelRef}
      className="fixed z-[100] bg-white rounded-2xl shadow-2xl border border-gray-200 w-[420px] overflow-hidden"
      style={{
        left: `${position.left}px`,
        top: `${position.top}px`,
      }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {/* 隐藏文件输入 */}
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept="image/*"
        onChange={handleFileSelect}
      />

      {/* 输入区域 */}
      <div className="p-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="描述你想要生成的图像..."
          className="w-full h-24 resize-none outline-none text-gray-700 placeholder-gray-400 text-base bg-transparent"
          disabled={isGenerating}
          autoFocus
        />
      </div>

      {/* 参考图像预览 */}
      {hasReference && (
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2 p-2 bg-blue-50 rounded-lg">
            <ImageIcon size={14} className="text-blue-500 flex-shrink-0" />
            <span className="text-xs text-blue-700 flex-1 truncate">
              {uploadedReference ? '已上传图片' : '画布图片作为参考'}
            </span>
            <button
              onClick={clearReference}
              className="text-blue-500 hover:text-blue-700 p-0.5"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* 底部控制栏 */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* 模型标识 */}
          <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-gray-600">
            <div className="w-4 h-4 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <Sparkles size={10} className="text-white" />
            </div>
            <span>Gemini</span>
          </div>

          {/* 参考图像按钮 */}
          <div className="relative">
            <button
              onClick={() => setShowReferenceMenu(!showReferenceMenu)}
              className={`p-1.5 rounded-lg transition-colors ${
                hasReference ? 'text-blue-500 bg-blue-50' : 'text-gray-500 hover:bg-gray-100'
              }`}
              title="参考图像"
            >
              <Upload size={16} />
            </button>
            {showReferenceMenu && (
              <div className="absolute bottom-full mb-1 left-0 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-10 min-w-[160px]">
                <button
                  onClick={() => {
                    fileInputRef.current?.click()
                  }}
                  className="w-full px-3 py-2 text-sm text-left hover:bg-gray-50 text-gray-700 flex items-center gap-2"
                >
                  <Upload size={14} />
                  上传图片
                </button>
                {imageElements.length > 0 && (
                  <>
                    <div className="border-t border-gray-100 my-1" />
                    <div className="px-3 py-1 text-xs text-gray-400">画布图片</div>
                    <div className="max-h-[200px] overflow-y-auto">
                      {imageElements.map((el, idx) => (
                        <button
                          key={el.id}
                          onClick={() => handleCanvasImageSelect(el.id)}
                          className={`w-full px-3 py-2 text-sm text-left hover:bg-gray-50 flex items-center gap-2 ${
                            selectedReferenceId === el.id ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                          }`}
                        >
                          <div className="w-8 h-8 rounded bg-gray-100 overflow-hidden flex-shrink-0">
                            <img
                              src={el.content}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          </div>
                          <span>图片 {idx + 1}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* 分辨率选择 */}
          <div className="relative">
            <button
              onClick={() => setShowResolutionMenu(!showResolutionMenu)}
              className="flex items-center gap-1 text-xs text-gray-600 font-medium hover:bg-gray-100 px-2 py-1 rounded-lg transition-colors"
            >
              <span>{resolution}</span>
              <ChevronDown size={12} />
            </button>
            {showResolutionMenu && (
              <div className="absolute bottom-full mb-1 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-10 min-w-[70px]">
                {resolutions.map((res) => (
                  <button
                    key={res}
                    onClick={() => {
                      setResolution(res)
                      setShowResolutionMenu(false)
                    }}
                    className={`w-full px-3 py-1.5 text-xs text-left hover:bg-gray-50 ${
                      resolution === res ? 'text-blue-500 font-medium' : 'text-gray-700'
                    }`}
                  >
                    {res}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 宽高比选择 */}
          <div className="relative">
            <button
              onClick={() => setShowAspectRatioMenu(!showAspectRatioMenu)}
              className="flex items-center gap-1 text-xs text-gray-600 font-medium hover:bg-gray-100 px-2 py-1 rounded-lg transition-colors"
            >
              <span>{aspectRatio}</span>
              <ChevronDown size={12} />
            </button>
            {showAspectRatioMenu && (
              <div className="absolute bottom-full mb-1 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-10 min-w-[70px]">
                {aspectRatios.map((ratio) => (
                  <button
                    key={ratio}
                    onClick={() => {
                      setAspectRatio(ratio)
                      setShowAspectRatioMenu(false)
                    }}
                    className={`w-full px-3 py-1.5 text-xs text-left hover:bg-gray-50 ${
                      aspectRatio === ratio ? 'text-blue-500 font-medium' : 'text-gray-700'
                    }`}
                  >
                    {ratio}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 生成按钮 */}
        <button
          onClick={handleGenerate}
          disabled={!prompt.trim() || isGenerating}
          className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-medium text-sm transition-all ${
            prompt.trim() && !isGenerating
              ? 'bg-gray-900 text-white shadow-md hover:bg-gray-800'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isGenerating ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              <span>生成中...</span>
            </>
          ) : (
            <>
              <Zap size={16} className="fill-current" />
              <span>生成</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}
