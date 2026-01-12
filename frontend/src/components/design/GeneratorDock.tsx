/**
 * Lovart 风格底部生成器 Dock
 * - 选择 image-generator/video-generator 元素时出现
 * - 保留 Generator 元素，多次生成产生多张图像/视频元素，不覆盖历史
 */
import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Plus,
  Paperclip,
  ChevronDown,
  Sparkles,
  Image as ImageIcon,
  Video,
  Zap,
  X,
  Loader2
} from 'lucide-react'
import type { CanvasElement } from '../../stores/designStore'
import type { Resolution, AspectRatio } from './types'

type DockMode = 'image' | 'video'

interface GeneratorDockProps {
  mode: DockMode
  isGenerating: boolean
  canvasElements: CanvasElement[]
  generatorElement: CanvasElement
  // 预置：来自工具条按钮（放大/Mockup 等）
  initialPrompt?: string
  initialResolution?: Resolution
  initialAspectRatio?: AspectRatio
  // 参考图：支持从画布图片点选
  onSetReferenceImageId?: (imageId: string | null) => void
  selectedImageModel: string
  onChangeImageModel: (modelId: string) => void
  imageModels: Array<{ id: string; name: string; icon?: string; coming?: boolean }>
  onClose: () => void
  onGenerateImage: (params: {
    prompt: string
    resolution: Resolution
    aspectRatio: AspectRatio
    referenceImageBase64?: string
    generatorElementId: string
  }) => Promise<void>
  onGenerateVideo?: (params: {
    prompt: string
    durationSeconds: number
    generatorElementId: string
  }) => Promise<void>
}

function stripDataUrlPrefix(maybe: string): string {
  if (!maybe) return maybe
  if (maybe.includes('base64,')) return maybe.split('base64,')[1]
  return maybe
}

export function GeneratorDock({
  mode,
  isGenerating,
  canvasElements,
  generatorElement,
  initialPrompt,
  initialResolution,
  initialAspectRatio,
  onSetReferenceImageId,
  selectedImageModel,
  onChangeImageModel,
  imageModels,
  onClose,
  onGenerateImage,
  onGenerateVideo
}: GeneratorDockProps) {
  const [prompt, setPrompt] = useState('')
  const [resolution, setResolution] = useState<Resolution>('1K')
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('1:1')
  const [durationSeconds, setDurationSeconds] = useState<number>(5)
  // 防止 preset 晚到时覆盖用户刚刚手动调整过的值
  const [touched, setTouched] = useState<{ prompt: boolean; resolution: boolean; aspectRatio: boolean }>({
    prompt: false,
    resolution: false,
    aspectRatio: false
  })

  const [showModelMenu, setShowModelMenu] = useState(false)
  const [showReferenceMenu, setShowReferenceMenu] = useState(false)
  const [showResolutionMenu, setShowResolutionMenu] = useState(false)
  const [showAspectRatioMenu, setShowAspectRatioMenu] = useState(false)
  const [showDurationMenu, setShowDurationMenu] = useState(false)

  const [uploadedReference, setUploadedReference] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const imageElements = useMemo(
    () => canvasElements.filter((el) => el.type === 'image' && el.content && !el.hidden),
    [canvasElements]
  )

  const referenceElement = useMemo(() => {
    if (!generatorElement.referenceImageId) return null
    return canvasElements.find((el) => el.id === generatorElement.referenceImageId) || null
  }, [generatorElement.referenceImageId, canvasElements])

  const referenceBase64 = useMemo(() => {
    if (uploadedReference) return uploadedReference
    if (referenceElement?.content) return stripDataUrlPrefix(referenceElement.content)
    return undefined
  }, [uploadedReference, referenceElement])

  // 当切换生成器时，重置输入（避免不同生成器串 prompt/参数）
  useEffect(() => {
    setPrompt(initialPrompt || '')
    setResolution(initialResolution || '1K')
    setAspectRatio(initialAspectRatio || '1:1')
    setDurationSeconds(5)
    setUploadedReference(null)
    setTouched({ prompt: false, resolution: false, aspectRatio: false })
    setShowModelMenu(false)
    setShowReferenceMenu(false)
    setShowResolutionMenu(false)
    setShowAspectRatioMenu(false)
    setShowDurationMenu(false)
  }, [generatorElement.id])

  // 兜底：若初始 preset 晚于首次渲染到达，则在用户未触碰对应字段时补上
  useEffect(() => {
    if (touched.prompt) return
    if (prompt.trim()) return
    if (initialPrompt) setPrompt(initialPrompt)
  }, [initialPrompt, touched.prompt, prompt])

  useEffect(() => {
    if (touched.resolution) return
    if (initialResolution) setResolution(initialResolution)
  }, [initialResolution, touched.resolution])

  useEffect(() => {
    if (touched.aspectRatio) return
    if (initialAspectRatio) setAspectRatio(initialAspectRatio)
  }, [initialAspectRatio, touched.aspectRatio])

  const openUploadPicker = () => fileInputRef.current?.click()

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      setUploadedReference(stripDataUrlPrefix(result))
      // 上传参考图时，优先使用上传图，清空画布引用
      onSetReferenceImageId?.(null)
      setShowReferenceMenu(false)
    }
    reader.readAsDataURL(file)
  }

  const handleClearReference = () => {
    setUploadedReference(null)
    onSetReferenceImageId?.(null)
  }

  const handleSubmit = async () => {
    const text = prompt.trim()
    if (!text || isGenerating) return
    if (mode === 'image') {
      await onGenerateImage({
        prompt: text,
        resolution,
        aspectRatio,
        referenceImageBase64: referenceBase64,
        generatorElementId: generatorElement.id
      })
      return
    }
    if (mode === 'video') {
      await onGenerateVideo?.({
        prompt: text,
        durationSeconds,
        generatorElementId: generatorElement.id
      })
    }
  }

  // z-index：不要遮挡右侧面板与左下角控件
  return (
    <div className="fixed left-1/2 bottom-6 -translate-x-1/2 z-40 w-[860px] max-w-[calc(100vw-2rem)]">
      {/* hidden upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileSelect}
      />

      <div className="lovart-glass rounded-3xl shadow-2xl overflow-hidden">
        {/* content */}
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-start gap-4">
            {/* left small preview of generator type */}
            <div className="w-12 h-12 rounded-2xl bg-[var(--muted)] flex items-center justify-center shrink-0">
              {mode === 'image' ? (
                <ImageIcon size={20} className="text-[var(--muted-foreground)]" />
              ) : (
                <Video size={20} className="text-[var(--muted-foreground)]" />
              )}
            </div>

            <div className="flex-1">
              <textarea
                value={prompt}
                onChange={(e) => {
                  setTouched((prev) => (prev.prompt ? prev : { ...prev, prompt: true }))
                  setPrompt(e.target.value)
                }}
                placeholder="今天我们要创作什么"
                className="w-full bg-transparent outline-none resize-none text-[15px] leading-relaxed text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] min-h-[64px]"
                disabled={isGenerating}
              />

              {/* video: start/end frames placeholders (UI only for now) */}
              {mode === 'video' && (
                <div className="mt-4 flex items-center gap-3">
                  <button
                    className="w-[92px] h-[92px] rounded-2xl border border-[var(--border)] bg-[var(--muted)] flex flex-col items-center justify-center gap-1 text-[var(--muted-foreground)] hover:bg-[var(--muted)]/80 transition"
                    type="button"
                    title="起始帧"
                  >
                    <Plus size={18} />
                    <span className="text-xs">起始帧</span>
                  </button>
                  <button
                    className="w-[92px] h-[92px] rounded-2xl border border-[var(--border)] bg-[var(--muted)] flex flex-col items-center justify-center gap-1 text-[var(--muted-foreground)] hover:bg-[var(--muted)]/80 transition"
                    type="button"
                    title="结束帧"
                  >
                    <Plus size={18} />
                    <span className="text-xs">结束帧</span>
                  </button>
                  <div className="text-xs text-[var(--muted-foreground)]">
                    选择图像作为起始/结束帧（视频生成功能即将上线）
                  </div>
                </div>
              )}

              {/* reference */}
              {mode === 'image' && (referenceBase64 || generatorElement.referenceImageId) && (
                <div className="mt-3 flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
                  <span className="inline-flex items-center gap-1">
                    <Paperclip size={14} /> 参考图已设置
                  </span>
                  <button
                    type="button"
                    className="px-2 py-1 rounded-lg bg-[var(--muted)] hover:bg-[var(--muted)]/80 transition text-[var(--foreground)]"
                    onClick={handleClearReference}
                  >
                    清除
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl text-[var(--muted-foreground)] hover:bg-[var(--muted)] transition"
              title="关闭"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* footer bar */}
        <div className="px-6 py-4 border-t border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* attach reference */}
            <div className="relative">
              <button
                type="button"
                className="w-10 h-10 rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)] transition flex items-center justify-center"
                onClick={() => setShowReferenceMenu((v) => !v)}
                title="参考图（可上传或从画布选择）"
                disabled={mode !== 'image'}
              >
                <Paperclip size={18} className="text-[var(--muted-foreground)]" />
              </button>
              {showReferenceMenu && mode === 'image' && (
                <div className="absolute bottom-full mb-2 left-0 w-[300px] rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl overflow-hidden">
                  <button
                    type="button"
                    onClick={() => {
                      openUploadPicker()
                    }}
                    className="w-full px-4 py-3 text-sm text-left hover:bg-[var(--muted)] transition flex items-center gap-2"
                  >
                    <Paperclip size={16} className="text-[var(--muted-foreground)]" />
                    <span className="text-[var(--foreground)]">上传图片</span>
                  </button>

                  <div className="border-t border-[var(--border)]" />

                  <div className="px-4 py-2 text-xs text-[var(--muted-foreground)]">
                    从画布选择
                  </div>
                  <div className="max-h-[220px] overflow-y-auto">
                    {imageElements.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-[var(--muted-foreground)]">
                        画布里还没有图片
                      </div>
                    ) : (
                      imageElements.map((imgEl, idx) => {
                        const active = generatorElement.referenceImageId === imgEl.id
                        return (
                          <button
                            key={imgEl.id}
                            type="button"
                            onClick={() => {
                              setUploadedReference(null)
                              onSetReferenceImageId?.(imgEl.id)
                              setShowReferenceMenu(false)
                            }}
                            className={`w-full px-4 py-2 text-sm text-left hover:bg-[var(--muted)] transition flex items-center gap-3 ${
                              active ? 'bg-[var(--muted)]' : ''
                            }`}
                          >
                            <div className="w-10 h-10 rounded-xl overflow-hidden bg-[var(--muted)] border border-[var(--border)] shrink-0">
                              <img src={imgEl.content} alt="" className="w-full h-full object-cover" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-[var(--foreground)] truncate">
                                图片 {idx + 1}
                              </div>
                              <div className="text-xs text-[var(--muted-foreground)] truncate">
                                {Math.round(imgEl.width || 0)}×{Math.round(imgEl.height || 0)}
                              </div>
                            </div>
                            {active && <span className="text-xs text-[var(--foreground)]">已选</span>}
                          </button>
                        )
                      })
                    )}
                  </div>

                  <div className="border-t border-[var(--border)]" />
                  <button
                    type="button"
                    onClick={() => {
                      handleClearReference()
                      setShowReferenceMenu(false)
                    }}
                    className="w-full px-4 py-3 text-sm text-left hover:bg-[var(--muted)] transition text-[var(--foreground)]"
                    disabled={!referenceBase64 && !generatorElement.referenceImageId}
                  >
                    清除参考图
                  </button>
                </div>
              )}
            </div>

            {/* model dropdown */}
            <div className="relative">
              <button
                type="button"
                className="h-10 px-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)] transition flex items-center gap-2 text-sm"
                onClick={() => setShowModelMenu((v) => !v)}
              >
                <Sparkles size={16} className="text-[var(--muted-foreground)]" />
                <span className="text-[var(--foreground)]">
                  {imageModels.find((m) => m.id === selectedImageModel)?.name || selectedImageModel}
                </span>
                <ChevronDown size={14} className="text-[var(--muted-foreground)]" />
              </button>
              {showModelMenu && (
                <div className="absolute bottom-full mb-2 left-0 w-[240px] rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl overflow-hidden">
                  {imageModels.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => {
                        if (m.coming) return
                        onChangeImageModel(m.id)
                        setShowModelMenu(false)
                      }}
                      className={`w-full text-left px-4 py-3 text-sm hover:bg-[var(--muted)] transition flex items-center justify-between ${
                        m.id === selectedImageModel ? 'text-[var(--foreground)] font-medium' : 'text-[var(--foreground)]'
                      } ${m.coming ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <span className="flex items-center gap-2">
                        <span className="text-base">{m.icon || '✨'}</span>
                        <span>{m.name}</span>
                      </span>
                      {m.coming && <span className="text-xs text-[var(--muted-foreground)]">即将上线</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* image controls */}
            {mode === 'image' && (
              <>
                <div className="relative">
                  <button
                    type="button"
                    className="h-10 px-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)] transition flex items-center gap-2 text-sm"
                    onClick={() => setShowResolutionMenu((v) => !v)}
                  >
                    <span className="text-[var(--foreground)]">{resolution}</span>
                    <ChevronDown size={14} className="text-[var(--muted-foreground)]" />
                  </button>
                  {showResolutionMenu && (
                    <div className="absolute bottom-full mb-2 left-0 rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl overflow-hidden min-w-[120px]">
                      {(['1K', '2K', '4K'] as Resolution[]).map((r) => (
                        <button
                          key={r}
                          type="button"
                          onClick={() => {
                            setTouched((prev) => (prev.resolution ? prev : { ...prev, resolution: true }))
                            setResolution(r)
                            setShowResolutionMenu(false)
                          }}
                          className={`w-full text-left px-4 py-2 text-sm hover:bg-[var(--muted)] transition ${
                            r === resolution ? 'font-medium' : ''
                          }`}
                        >
                          {r}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="relative">
                  <button
                    type="button"
                    className="h-10 px-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)] transition flex items-center gap-2 text-sm"
                    onClick={() => setShowAspectRatioMenu((v) => !v)}
                  >
                    <span className="text-[var(--foreground)]">{aspectRatio}</span>
                    <ChevronDown size={14} className="text-[var(--muted-foreground)]" />
                  </button>
                  {showAspectRatioMenu && (
                    <div className="absolute bottom-full mb-2 left-0 rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl overflow-hidden min-w-[120px]">
                      {(['1:1', '4:3', '16:9', '9:16', '3:4'] as AspectRatio[]).map((ar) => (
                        <button
                          key={ar}
                          type="button"
                          onClick={() => {
                            setTouched((prev) => (prev.aspectRatio ? prev : { ...prev, aspectRatio: true }))
                            setAspectRatio(ar)
                            setShowAspectRatioMenu(false)
                          }}
                          className={`w-full text-left px-4 py-2 text-sm hover:bg-[var(--muted)] transition ${
                            ar === aspectRatio ? 'font-medium' : ''
                          }`}
                        >
                          {ar}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* video controls */}
            {mode === 'video' && (
              <div className="relative">
                <button
                  type="button"
                  className="h-10 px-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)] transition flex items-center gap-2 text-sm"
                  onClick={() => setShowDurationMenu((v) => !v)}
                >
                  <span className="text-[var(--foreground)]">{durationSeconds}s</span>
                  <ChevronDown size={14} className="text-[var(--muted-foreground)]" />
                </button>
                {showDurationMenu && (
                  <div className="absolute bottom-full mb-2 left-0 rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl overflow-hidden min-w-[120px]">
                    {[3, 5, 8, 10].map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => {
                          setDurationSeconds(s)
                          setShowDurationMenu(false)
                        }}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-[var(--muted)] transition ${
                          s === durationSeconds ? 'font-medium' : ''
                        }`}
                      >
                        {s}s
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!prompt.trim() || isGenerating || (mode === 'video' && !onGenerateVideo)}
              className={`h-11 px-6 rounded-2xl flex items-center gap-2 font-medium transition-all ${
                prompt.trim() && !isGenerating
                  ? 'bg-[var(--foreground)] text-[var(--background)] hover:opacity-90'
                  : 'bg-[var(--muted)] text-[var(--muted-foreground)] cursor-not-allowed'
              }`}
              title={mode === 'video' ? '视频生成功能即将上线' : '生成'}
            >
              {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} className="fill-current" />}
              <span>{isGenerating ? '生成中...' : '生成'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

