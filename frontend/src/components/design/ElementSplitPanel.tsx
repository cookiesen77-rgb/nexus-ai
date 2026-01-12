/**
 * 元素拆分面板
 * Element Split Panel
 * 
 * 使用 AI 视觉分析图像，识别可编辑元素
 * 支持元素选择、高亮、重新生成
 */

import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import {
  Layers,
  Upload,
  X,
  Loader2,
  Type,
  Image as ImageIcon,
  Square,
  User,
  Shapes,
  RotateCcw,
  RefreshCw,
  Sparkles,
  Target,
  ChevronRight,
  AlertCircle,
  Plus
} from 'lucide-react'
import { useDesignStore, AnalyzedElement } from '../../stores/designStore'
import { analyzeImage, regenerateElement } from '../../services/designApi'
import { v4 as uuidv4 } from 'uuid'

interface ElementSplitPanelProps {
  onClose?: () => void
}

export function ElementSplitPanel({
  onClose
}: ElementSplitPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  // 并发控制：只采纳最新一次分析结果，避免快速切换图片时“串图”
  const analyzeSeqRef = useRef(0)
  const [regeneratePrompt, setRegeneratePrompt] = useState('')
  const [isRegenerating, setIsRegenerating] = useState(false)

  const {
    elements: canvasElements,
    selectedIds,
    addElement,
    updateElement,
    setSelectedIds,

    analyzedElements,
    selectedAnalyzedElementId,
    isAnalyzing,
    analyzedImageBase64,
    setAnalyzedElements,
    selectAnalyzedElement,
    setIsAnalyzing,
    setAnalyzedImageBase64,
    clearAnalysis
  } = useDesignStore()

  // 画布中当前选中的图片（Lovart：拆分基于画布图片，而不是重新上传）
  const selectedCanvasImage = useMemo(() => {
    if (selectedIds.length !== 1) return null
    const el = canvasElements.find(e => e.id === selectedIds[0])
    if (!el || el.type !== 'image' || !el.content) return null
    return el
  }, [canvasElements, selectedIds])

  const selectedElement = useMemo(() => {
    if (!selectedAnalyzedElementId) return null
    return analyzedElements.find(e => e.id === selectedAnalyzedElementId) || null
  }, [analyzedElements, selectedAnalyzedElementId])

  // AI 分析图像
  const handleAnalyze = useCallback(async (imageBase64: string) => {
    const seq = ++analyzeSeqRef.current
    setIsAnalyzing(true)
    setAnalyzedElements([])
    
    try {
      const result = await analyzeImage({
        image_base64: imageBase64,
        analysis_type: 'full'
      })

      // 旧请求直接丢弃，避免覆盖当前选中图片的结果
      if (seq !== analyzeSeqRef.current) return

      if (result.success && result.data) {
        setAnalyzedElements(result.data.elements as AnalyzedElement[])
      } else {
        console.error('Analysis failed:', result.error)
        // 设置模拟数据
        setAnalyzedElements([
          {
            id: 'element-001',
            type: 'background',
            label: '背景',
            bbox: [0, 0, 1, 1],
            confidence: 0.9,
            description: '图像背景'
          }
        ])
      }
    } catch (error) {
      if (seq !== analyzeSeqRef.current) return
      console.error('Analysis error:', error)
    } finally {
      if (seq === analyzeSeqRef.current) {
        setIsAnalyzing(false)
      }
    }
  }, [setIsAnalyzing, setAnalyzedElements])

  // 处理图片上传（兜底：当画布没有选中图片时使用）
  const handleUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = reader.result as string
        setAnalyzedImageBase64(base64)
        selectAnalyzedElement(null)
        handleAnalyze(base64)
      }
      reader.readAsDataURL(file)
    }
  }, [setAnalyzedImageBase64, selectAnalyzedElement, handleAnalyze])

  // 当画布选中图片变化时，自动触发分析（Lovart 工作流）
  useEffect(() => {
    if (!selectedCanvasImage?.content) return

    // 同一张图不重复分析
    if (analyzedImageBase64 === selectedCanvasImage.content) return

    setAnalyzedImageBase64(selectedCanvasImage.content)
    selectAnalyzedElement(null)
    handleAnalyze(selectedCanvasImage.content)
  }, [
    selectedCanvasImage?.id,
    selectedCanvasImage?.content,
    analyzedImageBase64,
    setAnalyzedImageBase64,
    selectAnalyzedElement,
    handleAnalyze
  ])

  // 重新分析
  const handleReanalyze = useCallback(() => {
    if (analyzedImageBase64) {
      handleAnalyze(analyzedImageBase64)
    }
  }, [analyzedImageBase64, handleAnalyze])

  // 重置
  const handleReset = useCallback(() => {
    clearAnalysis()
    setRegeneratePrompt('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [clearAnalysis])

  const getAnchorPosition = useCallback(() => {
    // 默认放在画布左上，若当前有选中图像则放在其右侧
    if (selectedCanvasImage) {
      const ax = selectedCanvasImage.x + (selectedCanvasImage.width || 400) + 40
      const ay = selectedCanvasImage.y
      return { x: ax, y: ay }
    }
    return { x: 100, y: 100 }
  }, [selectedCanvasImage])

  const ensureDataUrl = (src: string) => {
    if (!src) return src
    return src.startsWith('data:') ? src : `data:image/png;base64,${src}`
  }

  const cropImageFromBbox = useCallback(async (
    imageSrc: string,
    bbox: [number, number, number, number]
  ): Promise<{ dataUrl: string; width: number; height: number } | null> => {
    const src = ensureDataUrl(imageSrc)
    return await new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        const [x, y, w, h] = bbox
        const sx = Math.max(0, Math.round(img.width * x))
        const sy = Math.max(0, Math.round(img.height * y))
        const sw = Math.max(1, Math.round(img.width * w))
        const sh = Math.max(1, Math.round(img.height * h))

        const canvas = document.createElement('canvas')
        canvas.width = sw
        canvas.height = sh
        const ctx = canvas.getContext('2d')
        if (!ctx) return resolve(null)

        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)
        const dataUrl = canvas.toDataURL('image/png')
        resolve({ dataUrl, width: sw, height: sh })
      }
      img.onerror = () => resolve(null)
      img.src = src
    })
  }, [])

  // 将选中的分析元素导出为画布图层（Lovart：文本图像分离 + 图层化）
  const handleExportSelectedLayer = useCallback(async () => {
    if (!selectedElement || !analyzedImageBase64) return

    const anchor = getAnchorPosition()

    if (selectedElement.type === 'text') {
      const text = selectedElement.content || selectedElement.label
      // 尽量对齐原图 bbox（类似 Figma 图层的直觉）
      let x = anchor.x
      let y = anchor.y
      let fontSize = 36

      if (selectedCanvasImage?.width && selectedCanvasImage?.height) {
        const [bx, by, , bh] = selectedElement.bbox
        x = selectedCanvasImage.x + selectedCanvasImage.width * bx
        y = selectedCanvasImage.y + selectedCanvasImage.height * by
        const est = Math.round(selectedCanvasImage.height * bh * 0.9)
        const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v))
        fontSize = clamp(est, 12, 180)
      }

      addElement({
        id: uuidv4(),
        type: 'text',
        x,
        y,
        content: text,
        fontSize,
        color: 'var(--foreground)'
      })
      return
    }

    const cropped = await cropImageFromBbox(analyzedImageBase64, selectedElement.bbox)
    if (!cropped) return

    addElement({
      id: uuidv4(),
      type: 'image',
      x: anchor.x,
      y: anchor.y,
      width: cropped.width,
      height: cropped.height,
      content: cropped.dataUrl
    })
  }, [selectedElement, analyzedImageBase64, getAnchorPosition, cropImageFromBbox, addElement, selectedCanvasImage])

  // 重新生成选中的元素
  const handleRegenerate = useCallback(async () => {
    if (!selectedAnalyzedElementId || !analyzedImageBase64 || !regeneratePrompt.trim()) return

    const element = analyzedElements.find(e => e.id === selectedAnalyzedElementId)
    if (!element) return

    setIsRegenerating(true)
    try {
      const result = await regenerateElement({
        original_image_base64: analyzedImageBase64,
        element_id: element.id,
        element_bbox: element.bbox,
        modification_prompt: regeneratePrompt,
        keep_style: true
      })

      if (result.success && result.data) {
        const newDataUrl = `data:image/png;base64,${result.data.result_base64}`

        // 1) 更新拆分面板预览
        setAnalyzedImageBase64(newDataUrl)

        // 2) 若当前是画布选中图片的拆分：同步回写到画布（局部重绘）
        if (selectedCanvasImage) {
          updateElement(selectedCanvasImage.id, {
            content: newDataUrl,
            width: result.data.width,
            height: result.data.height
          })
          // 保持选中，方便继续拆分/编辑
          setSelectedIds([selectedCanvasImage.id])
        }

        // 3) 重新分析（基于新图）
        selectAnalyzedElement(null)
        handleAnalyze(newDataUrl)
        setRegeneratePrompt('')
      }
    } catch (error) {
      console.error('Regenerate error:', error)
    } finally {
      setIsRegenerating(false)
    }
  }, [
    selectedAnalyzedElementId,
    analyzedImageBase64,
    regeneratePrompt,
    analyzedElements,
    setAnalyzedImageBase64,
    handleAnalyze,
    selectedCanvasImage,
    updateElement,
    setSelectedIds,
    selectAnalyzedElement
  ])

  // 获取元素图标
  const getElementIcon = (type: string) => {
    switch (type) {
      case 'text': return <Type size={14} />
      case 'object': return <ImageIcon size={14} />
      case 'background': return <Square size={14} />
      case 'person': return <User size={14} />
      case 'shape': return <Shapes size={14} />
      default: return <Layers size={14} />
    }
  }

  // 获取元素类型颜色
  const getElementColor = (type: string) => {
    switch (type) {
      case 'text': return 'bg-[var(--nexus-warning-light)] text-[var(--nexus-warning)]'
      case 'object': return 'bg-[var(--nexus-success-light)] text-[var(--nexus-success)]'
      case 'background': return 'bg-[var(--nexus-info-light)] text-[var(--nexus-info)]'
      case 'person': return 'bg-[var(--primary-light)] text-[var(--primary)]'
      case 'shape': return 'bg-[var(--muted)] text-[var(--muted-foreground)]'
      default: return 'bg-[var(--muted)] text-[var(--muted-foreground)]'
    }
  }

  // selectedElement 已由 useMemo 计算

  return (
    <div className="flex flex-col h-full">
      {/* 头部 */}
      <div className="p-4 border-b border-[var(--nexus-sidebar-border)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]">
            <Layers size={16} className="text-[var(--primary-foreground)]" />
          </div>
          <div>
            <span className="font-medium text-[var(--foreground)]">元素分析</span>
            <p className="text-[10px] text-[var(--muted-foreground)]">AI 智能识别</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {analyzedImageBase64 && (
            <>
              <button
                onClick={handleReanalyze}
                className="nexus-icon-btn text-[var(--muted-foreground)] hover:text-[var(--primary)]"
                title="重新分析"
                disabled={isAnalyzing}
              >
                <RefreshCw size={16} className={isAnalyzing ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={handleReset}
                className="nexus-icon-btn text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                title="重置"
              >
                <RotateCcw size={16} />
              </button>
            </>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="nexus-icon-btn text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {!analyzedImageBase64 ? (
          // 空状态：优先提示从画布选择图片（Lovart 工作流）
          <div className="flex-1 p-4 flex items-center justify-center">
            <div className="text-center">
              {selectedCanvasImage ? (
                <>
                  <div className="w-24 h-24 mx-auto mb-4 rounded-2xl bg-[var(--muted)] border border-[var(--border)] flex items-center justify-center">
                    <Layers size={32} className="text-[var(--muted-foreground)]" />
                  </div>
                  <p className="text-sm text-[var(--foreground)] mb-1">已选中画布图片</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    正在准备分析并拆分元素…
                  </p>
                </>
              ) : (
                <>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-24 h-24 mx-auto mb-4 rounded-2xl bg-[var(--muted)] border-2 border-dashed border-[var(--border)] flex items-center justify-center cursor-pointer hover:border-[var(--primary)] hover:bg-[var(--primary-light)] transition-all group"
                  >
                    <Upload size={32} className="text-[var(--muted-foreground)] group-hover:text-[var(--primary)] transition-colors" />
                  </button>
                  <p className="text-sm text-[var(--foreground)] mb-1">请先在画布选中一张图片</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    然后点击“拆分”，系统会自动识别可编辑元素（文本分离 / 图层 / 局部重绘）
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)] mt-2">
                    或者：上传图片进行分析
                  </p>
                </>
              )}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleUpload}
                accept="image/*"
                className="hidden"
              />
            </div>
          </div>
        ) : (
          <>
            {/* 预览图 + 元素高亮 */}
            <div className="p-4 border-b border-[var(--nexus-sidebar-border)] shrink-0">
              <div className="relative aspect-video bg-[var(--muted)] rounded-xl overflow-hidden">
                {isAnalyzing && (
                  <div className="absolute inset-0 bg-[var(--background)]/70 flex items-center justify-center z-20">
                    <div className="text-center">
                      <Loader2 size={32} className="text-[var(--primary)] animate-spin mx-auto mb-2" />
                      <p className="text-sm text-[var(--foreground)]">AI 分析中...</p>
                      <p className="text-xs text-[var(--muted-foreground)]">正在识别图像元素</p>
                    </div>
                  </div>
                )}
                
                <img
                  src={analyzedImageBase64}
                  alt="Analyzed"
                  className="w-full h-full object-contain"
                />

                {/* 元素边界框叠加 */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  {analyzedElements.map((element) => {
                    const [x, y, w, h] = element.bbox
                    const isSelected = element.id === selectedAnalyzedElementId
                    
                    return (
                      <g key={element.id}>
                        <rect
                          x={`${x * 100}%`}
                          y={`${y * 100}%`}
                          width={`${w * 100}%`}
                          height={`${h * 100}%`}
                          fill="none"
                          stroke={isSelected ? 'var(--primary)' : 'var(--muted-foreground)'}
                          strokeWidth={isSelected ? 2 : 1}
                          strokeDasharray={isSelected ? 'none' : '4,4'}
                          opacity={isSelected ? 1 : 0.5}
                          className="transition-all"
                        />
                        {isSelected && (
                          <rect
                            x={`${x * 100}%`}
                            y={`${y * 100}%`}
                            width={`${w * 100}%`}
                            height={`${h * 100}%`}
                            fill="var(--primary)"
                            opacity={0.1}
                          />
                        )}
                      </g>
                    )
                  })}
                </svg>
              </div>
            </div>

            {/* 元素列表 */}
            <div className="flex-1 overflow-y-auto p-2">
              {analyzedElements.length === 0 && !isAnalyzing ? (
                <div className="text-center py-8">
                  <AlertCircle size={32} className="mx-auto mb-2 text-[var(--muted-foreground)]" />
                  <p className="text-sm text-[var(--muted-foreground)]">未检测到可编辑元素</p>
                  <button
                    onClick={handleReanalyze}
                    className="mt-3 text-xs text-[var(--primary)] hover:underline"
                  >
                    重新分析
                  </button>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-xs text-[var(--muted-foreground)] font-medium px-2 py-1">
                    检测到 {analyzedElements.length} 个元素
                  </p>
                  
                  {analyzedElements.map((element) => {
                    const isSelected = element.id === selectedAnalyzedElementId
                    
                    return (
                      <button
                        key={element.id}
                        onClick={() => selectAnalyzedElement(isSelected ? null : element.id)}
                        className={`w-full flex items-center gap-2 p-2.5 rounded-lg transition-all text-left ${
                          isSelected
                            ? 'bg-[var(--primary-light)] border border-[var(--primary)]'
                            : 'hover:bg-[var(--muted)] border border-transparent'
                        }`}
                      >
                        {/* 元素图标 */}
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${getElementColor(element.type)}`}>
                          {getElementIcon(element.type)}
                        </div>

                        {/* 元素信息 */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-[var(--foreground)] truncate font-medium">
                            {element.label}
                          </p>
                          <p className="text-[10px] text-[var(--muted-foreground)] truncate">
                            {element.description || element.type}
                            {element.content && ` · "${element.content}"`}
                          </p>
                        </div>

                        {/* 置信度 */}
                        <div className="text-[10px] text-[var(--muted-foreground)] shrink-0">
                          {Math.round(element.confidence * 100)}%
                        </div>

                        <ChevronRight size={14} className={`text-[var(--muted-foreground)] shrink-0 transition-transform ${isSelected ? 'rotate-90' : ''}`} />
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* 选中元素的操作区 */}
            {selectedElement && (
              <div className="p-4 border-t border-[var(--nexus-sidebar-border)] shrink-0 space-y-3">
                <div className="flex items-center gap-2">
                  <Target size={14} className="text-[var(--primary)]" />
                  <span className="text-sm font-medium text-[var(--foreground)]">
                    {selectedElement.label}
                  </span>
                </div>
                
                <p className="text-xs text-[var(--muted-foreground)]">
                  {selectedElement.description || '无描述'}
                </p>

                {/* Lovart：导出为图层（文本图像分离 / 图层化） */}
                <button
                  onClick={handleExportSelectedLayer}
                  className="w-full py-2 nexus-btn-secondary flex items-center justify-center gap-2 text-sm"
                >
                  <Plus size={14} />
                  <span>{selectedElement.type === 'text' ? '添加为文本层' : '导出为图层'}</span>
                </button>

                {/* 重新生成输入 */}
                <div className="space-y-2">
                  <label className="text-xs text-[var(--muted-foreground)]">修改描述</label>
                  <textarea
                    value={regeneratePrompt}
                    onChange={(e) => setRegeneratePrompt(e.target.value)}
                    placeholder="描述你想要的修改..."
                    className="w-full px-3 py-2 nexus-input text-sm resize-none h-16"
                  />
                </div>

                <button
                  onClick={handleRegenerate}
                  disabled={!regeneratePrompt.trim() || isRegenerating}
                  className={`w-full py-2.5 nexus-btn-primary flex items-center justify-center gap-2 text-sm ${
                    (!regeneratePrompt.trim() || isRegenerating) ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  {isRegenerating ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>局部重绘中...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} />
                      <span>局部重绘</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
