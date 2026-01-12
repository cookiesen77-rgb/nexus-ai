/**
 * Nexus AI Design Page
 * 设计模块主页面 - Nexus 统一风格
 */

import { useEffect, useCallback, useRef, useState } from 'react'
import { useDesignStore } from '../stores/designStore'
import { CanvasArea, FloatingToolbar, ElementSplitPanel, AiDesignerPanel, RegionEditPopup, GeneratorDock, LayersDrawer } from '../components/design'
import type { CanvasElement, Resolution, AspectRatio, RegionSelection } from '../components/design'
import { generateImage, saveProject, regenerateElement, generateVideo } from '../services/designApi'
import type { CanvasElement as StoreCanvasElement } from '../stores/designStore'
import { v4 as uuidv4 } from 'uuid'
import {
  ZoomIn,
  ZoomOut,
  ChevronDown,
  Layers,
  Wand2,
  Save,
  Undo2,
  Redo2
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'
import NexusLogo from '../components/ui/NexusLogo'

// 可用模型配置
const IMAGE_MODELS = [
  { id: 'gemini-flash', name: 'Gemini Flash', icon: '⚡', speed: 'fast', quality: 'good' },
  { id: 'gemini-pro', name: 'Gemini Pro', icon: '🎯', speed: 'medium', quality: 'excellent' },
  { id: 'flux-pro', name: 'Flux Pro', icon: '🎨', speed: 'medium', quality: 'excellent', coming: true },
  { id: 'dall-e-3', name: 'DALL-E 3', icon: '🖼️', speed: 'medium', quality: 'excellent', coming: true },
]

export default function DesignPage() {
  const {
    elements,
    selectedIds,
    scale,
    pan,
    activeTool,
    projectName,
    isDirty,
    isImageGeneratorOpen,
    imageGeneratorElementId,
    isGeneratingImage,
    isGeneratingVideo,
    isAiDesignerOpen,
    addElement,
    updateElement,
    deleteElement,
    setSelectedIds,
    setScale,
    setPan,
    setActiveTool,
    setProjectName,
    openImageGenerator,
    closeImageGenerator,
    toggleAiDesigner,
    setIsGeneratingImage,
    setIsGeneratingVideo,
    addImageElement,
    addVideoElement,
    addTextElement,
    addShapeElement,
    addImageGeneratorElement,
    addVideoGeneratorElement,
    createFlowConnection,
    toggleElementHidden,
    toggleElementLocked,

    // 元素拆分（Lovart 工作流）
    analyzedElements,
    selectedAnalyzedElementId,
    selectAnalyzedElement,
    clearAnalysis
  } = useDesignStore()

  const { theme, toggleTheme } = useTheme()
  const canvasRef = useRef<HTMLDivElement>(null)
  const [selectedModel, setSelectedModel] = useState('gemini-flash')
  const [isElementSplitOpen, setIsElementSplitOpen] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isLayersOpen, setIsLayersOpen] = useState(false)

  // 拆分面板：从图片工具条触发“编辑文字”时，自动选中首个 text 元素
  const [splitAutoSelectMode, setSplitAutoSelectMode] = useState<null | 'text'>(null)

  // 生成器 Dock：为不同按钮预置 prompt / 参数
  const [dockPresets, setDockPresets] = useState<Record<string, {
    prompt: string
    resolution?: Resolution
    aspectRatio?: AspectRatio
  }>>({})
  
  // 要上传到 AI 聊天的图像（点击画布图像时设置）
  const [pendingImageForAi, setPendingImageForAi] = useState<{
    imageBase64: string
    elementId: string
  } | null>(null)
  
  // 框选编辑状态
  const [regionSelection, setRegionSelection] = useState<RegionSelection | null>(null)
  const [isRegionProcessing, setIsRegionProcessing] = useState(false)
  
  // 选中的生成器元素（用于底部 Dock）
  const selectedElement = selectedIds.length === 1 ? elements.find(el => el.id === selectedIds[0]) : null
  const selectedGenerator =
    selectedElement && (selectedElement.type === 'image-generator' || selectedElement.type === 'video-generator')
      ? selectedElement
      : null

  // 元素拆分：当前目标图片（必须是画布中选中的 image）
  const splitTargetImage =
    isElementSplitOpen && selectedIds.length === 1
      ? elements.find((el) => el.id === selectedIds[0] && el.type === 'image' && !!el.content)
      : null

  // “编辑文字”自动选中首个文本元素（等分析结果回来再选）
  useEffect(() => {
    if (!isElementSplitOpen) return
    if (splitAutoSelectMode !== 'text') return
    const firstText = analyzedElements.find((e) => e.type === 'text')
    if (firstText) {
      selectAnalyzedElement(firstText.id)
      setSplitAutoSelectMode(null)
      return
    }
    // 分析完成但没有 text：避免模式残留导致后续“串图自动选中”
    if (analyzedElements.length > 0 && !analyzedElements.some((e) => e.type === 'text')) {
      setSplitAutoSelectMode(null)
    }
  }, [isElementSplitOpen, splitAutoSelectMode, analyzedElements, selectAnalyzedElement])
  
  // 互斥控制：打开一个面板时关闭另一个
  const handleToggleAiDesigner = useCallback(() => {
    if (!isAiDesignerOpen) {
      setIsElementSplitOpen(false) // 打开 AI 面板时关闭元素分析面板
      setSplitAutoSelectMode(null)
    }
    toggleAiDesigner()
  }, [isAiDesignerOpen, toggleAiDesigner, setSplitAutoSelectMode])
  
  const handleToggleElementSplit = useCallback(() => {
    if (!isElementSplitOpen && isAiDesignerOpen) {
      // 打开元素分析面板时关闭 AI 面板
      toggleAiDesigner()
    }

    // 关闭时清理高亮，避免画布残留框
    if (isElementSplitOpen) {
      selectAnalyzedElement(null)
      clearAnalysis()
      setSplitAutoSelectMode(null)
    }
    setIsElementSplitOpen(!isElementSplitOpen)
  }, [isElementSplitOpen, isAiDesignerOpen, toggleAiDesigner, selectAnalyzedElement, clearAnalysis])
  
  // 处理画布图像点击 - 上传到 AI 聊天
  const handleCanvasImageClick = useCallback((element: CanvasElement) => {
    if (element.type === 'image' && element.content) {
      // 设置待上传图像
      setPendingImageForAi({
        imageBase64: element.content,
        elementId: element.id
      })
      // 自动打开 AI 助手面板
      if (!isAiDesignerOpen) {
        setIsElementSplitOpen(false)
        toggleAiDesigner()
      }
    }
  }, [isAiDesignerOpen, toggleAiDesigner])
  
  // 处理框选编辑
  const handleRegionSelected = useCallback((selection: RegionSelection) => {
    setRegionSelection(selection)
  }, [])
  
  // 流程连接 - 从图像继续生成
  const handleConnectFlow = useCallback((element: CanvasElement) => {
    if (element.type === 'image' && element.content) {
      createFlowConnection(element as StoreCanvasElement)
    }
  }, [createFlowConnection])
  
  // 局部编辑 - 激活框选工具
  const handleRegionEdit = useCallback((element: CanvasElement) => {
    setActiveTool('region-edit')
    setSelectedIds([element.id])
  }, [setActiveTool, setSelectedIds])
  
  // 第 4 张图那排：放大/移除背景/Mockup/编辑元素/编辑文字
  const guessAspectRatio = (w: number, h: number): AspectRatio => {
    if (!w || !h) return '1:1'
    const r = w / h
    const near = (a: number, b: number) => Math.abs(a - b) < 0.12
    if (near(r, 1)) return '1:1'
    if (r > 1) {
      if (near(r, 16 / 9)) return '16:9'
      return '4:3'
    }
    if (near(r, 9 / 16)) return '9:16'
    return '3:4'
  }

  const handleUpscale = useCallback((element: CanvasElement) => {
    if (element.type !== 'image' || !element.content) return
    setSplitAutoSelectMode(null)
    setIsElementSplitOpen(false)

    const generatorId = createFlowConnection(element as StoreCanvasElement, { generatorName: 'HD Upscale' })
    if (!generatorId) return

    const aspectRatio = guessAspectRatio(element.width || 1024, element.height || 1024)
    setDockPresets((prev) => ({
      ...prev,
      [generatorId]: {
        prompt:
          'Upscale the reference image to higher resolution, preserve composition and style, no changes, sharper details, clean edges, high quality',
        resolution: '2K',
        aspectRatio
      }
    }))
  }, [createFlowConnection])

  const handleMockup = useCallback((element: CanvasElement) => {
    if (element.type !== 'image' || !element.content) return
    setSplitAutoSelectMode(null)
    setIsElementSplitOpen(false)

    const generatorId = createFlowConnection(element as StoreCanvasElement, { generatorName: 'Mockup' })
    if (!generatorId) return

    setDockPresets((prev) => ({
      ...prev,
      [generatorId]: {
        prompt:
          'Create a clean realistic mockup showcasing the reference image as a poster on a minimalist wall, soft natural shadows, premium paper texture, studio lighting, high quality',
        resolution: '1K',
        aspectRatio: '4:3'
      }
    }))
  }, [createFlowConnection])

  const handleRemoveBackground = useCallback(async (element: CanvasElement) => {
    if (element.type !== 'image' || !element.content) return
    setSplitAutoSelectMode(null)
    setIsElementSplitOpen(false)

    const ensureDataUrl = (src: string) => {
      if (!src) return src
      if (src.startsWith('data:')) return src
      if (src.includes('base64,')) return src
      return `data:image/png;base64,${src}`
    }

    const removeBg = async (src: string): Promise<string | null> => {
      const dataUrl = ensureDataUrl(src)
      return await new Promise((resolve) => {
        const img = new Image()
        img.onload = () => {
          const canvas = document.createElement('canvas')
          canvas.width = img.width
          canvas.height = img.height
          const ctx = canvas.getContext('2d')
          if (!ctx) return resolve(null)

          ctx.drawImage(img, 0, 0)
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
          const { data } = imageData

          // 采样边缘作为背景色估计（适用于纯色/弱纹理背景）
          const step = Math.max(1, Math.floor(Math.min(canvas.width, canvas.height) / 40))
          let sr = 0, sg = 0, sb = 0, count = 0
          const sample = (x: number, y: number) => {
            const idx = (y * canvas.width + x) * 4
            sr += data[idx]
            sg += data[idx + 1]
            sb += data[idx + 2]
            count++
          }
          for (let x = 0; x < canvas.width; x += step) {
            sample(x, 0)
            sample(x, canvas.height - 1)
          }
          for (let y = 0; y < canvas.height; y += step) {
            sample(0, y)
            sample(canvas.width - 1, y)
          }
          const br = sr / Math.max(1, count)
          const bg = sg / Math.max(1, count)
          const bb = sb / Math.max(1, count)

          const t1 = 24
          const t2 = 80
          for (let i = 0; i < data.length; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2]
            const dr = r - br
            const dg = g - bg
            const db = b - bb
            const dist = Math.sqrt(dr * dr + dg * dg + db * db)
            if (dist < t1) {
              data[i + 3] = 0
            } else if (dist < t2) {
              const a = Math.round(((dist - t1) / (t2 - t1)) * 255)
              data[i + 3] = Math.min(data[i + 3], a)
            }
          }

          ctx.putImageData(imageData, 0, 0)
          resolve(canvas.toDataURL('image/png'))
        }
        img.onerror = () => resolve(null)
        img.src = ensureDataUrl(src)
      })
    }

    const result = await removeBg(element.content)
    if (!result) return

    const w = element.width || 300
    const h = element.height || 300
    const newEl: CanvasElement = {
      id: uuidv4(),
      type: 'image',
      x: element.x + w + 40,
      y: element.y,
      width: w,
      height: h,
      content: result
    }
    addElement(newEl)
    setSelectedIds([newEl.id])
  }, [addElement, setSelectedIds])

  const openSplitPanelForImage = useCallback((imageEl: CanvasElement) => {
    if (imageEl.type !== 'image') return
    // 互斥：打开拆分时关闭 AI / 图层
    if (isAiDesignerOpen) toggleAiDesigner()
    setIsLayersOpen(false)
    setSelectedIds([imageEl.id])
    setIsElementSplitOpen(true)
  }, [isAiDesignerOpen, toggleAiDesigner, setSelectedIds])

  const handleEditElements = useCallback((element: CanvasElement) => {
    setSplitAutoSelectMode(null)
    openSplitPanelForImage(element)
  }, [openSplitPanelForImage])

  const handleEditText = useCallback((element: CanvasElement) => {
    setSplitAutoSelectMode('text')
    openSplitPanelForImage(element)
  }, [openSplitPanelForImage])
  
  // 生成器 Dock：生成图片（保留 Generator，生成多张不覆盖）
  const handleDockGenerateImage = useCallback(
    async (params: {
      prompt: string
      resolution: Resolution
      aspectRatio: AspectRatio
      referenceImageBase64?: string
      generatorElementId: string
    }) => {
      const generator = elements.find(el => el.id === params.generatorElementId)
      if (!generator || generator.type !== 'image-generator') return

      setIsGeneratingImage(true)
      try {
        const result = await generateImage({
          prompt: params.prompt,
          resolution: params.resolution,
          aspect_ratio: params.aspectRatio,
          reference_image: params.referenceImageBase64,
          model: selectedModel
        })

        if (result.success && result.data) {
          const groupId = generator.groupId || generator.id
          const existing = elements.filter(el => el.type === 'image' && el.groupId === groupId)
          const index = existing.length
          const columns = 4
          const gap = 16

          const baseW = 220
          const aspect = result.data.width ? result.data.height / result.data.width : 1
          const thumbW = baseW
          const thumbH = Math.max(80, Math.round(baseW * aspect))

          const col = index % columns
          const row = Math.floor(index / columns)

          const x = generator.x + col * (thumbW + gap)
          const y = generator.y - (row + 1) * (thumbH + gap)

          addElement({
            id: uuidv4(),
            type: 'image',
            x,
            y,
            width: thumbW,
            height: thumbH,
            groupId,
            name: `Generated ${index + 1}`,
            content: `data:image/png;base64,${result.data.image_base64}`
          })

          // 保持 generator 选中，方便继续生成
          setSelectedIds([generator.id])
        } else {
          console.error('Dock generate failed:', result.error)
          alert(`图像生成失败: ${result.error || '未知错误'}`)
        }
      } catch (error) {
        console.error('Dock generate error:', error)
        alert('图像生成失败，请重试')
      } finally {
        setIsGeneratingImage(false)
      }
    },
    [elements, selectedModel, addElement, setSelectedIds, setIsGeneratingImage]
  )

  const handleDockGenerateVideo = useCallback(
    async (params: { prompt: string; durationSeconds: number; generatorElementId: string }) => {
      setIsGeneratingVideo(true)
      try {
        const result = await generateVideo({
          prompt: params.prompt,
          duration: params.durationSeconds,
          model: 'kling',
        })
        if (!result.success) {
          alert(result.error || '视频生成功能即将上线')
        }
      } catch (e) {
        alert('视频生成功能即将上线')
      } finally {
        setIsGeneratingVideo(false)
      }
    },
    [setIsGeneratingVideo]
  )

  // 处理框选编辑提交
  const handleRegionEditSubmit = useCallback(async (prompt: string, keepStyle: boolean) => {
    if (!regionSelection) return
    
    setIsRegionProcessing(true)
    try {
      const result = await regenerateElement({
        original_image_base64: regionSelection.imageBase64,
        element_id: regionSelection.elementId,
        element_bbox: regionSelection.bbox,
        modification_prompt: prompt,
        keep_style: keepStyle
      })
      
      if (result.success && result.data) {
        // 更新画布上的图像
        updateElement(regionSelection.elementId, {
          content: `data:image/png;base64,${result.data.result_base64}`,
          width: result.data.width,
          height: result.data.height
        })
        
        // 关闭弹窗
        setRegionSelection(null)
        // 切换回选择工具
        setActiveTool('select')
      } else {
        console.error('局部编辑失败:', result.error)
        alert(`局部编辑失败: ${result.error || '未知错误'}`)
      }
    } catch (error) {
      console.error('局部编辑请求失败:', error)
      alert('局部编辑请求失败，请重试')
    } finally {
      setIsRegionProcessing(false)
    }
  }, [regionSelection, updateElement, setActiveTool])

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedIds.length > 0) {
        selectedIds.forEach(id => deleteElement(id))
      }

      if (e.key === 'v' || e.key === 'V') setActiveTool('select')
      if (e.key === 'h' || e.key === 'H') setActiveTool('hand')
      if (e.key === 'Escape') {
        setSelectedIds([])
        closeImageGenerator()
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }

      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault()
        handleResetZoom()
      }

      if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
        e.preventDefault()
        handleZoomIn()
      }

      if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault()
        handleZoomOut()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedIds, deleteElement, setActiveTool, setSelectedIds, closeImageGenerator])

  // 鼠标滚轮缩放
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        e.stopPropagation()
        
        const rect = canvas.getBoundingClientRect()
        const mouseX = e.clientX - rect.left
        const mouseY = e.clientY - rect.top
        
        const delta = e.deltaY > 0 ? 0.9 : 1.1
        const newScale = Math.max(0.1, Math.min(5, scale * delta))
        
        const scaleRatio = newScale / scale
        const newPanX = mouseX - (mouseX - pan.x) * scaleRatio
        const newPanY = mouseY - (mouseY - pan.y) * scaleRatio
        
        setScale(newScale)
        setPan({ x: newPanX, y: newPanY })
      }
    }

    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', handleWheel)
  }, [scale, pan, setScale, setPan])

  const handleZoomIn = () => setScale(Math.min(5, scale * 1.2))
  const handleZoomOut = () => setScale(Math.max(0.1, scale * 0.8))
  const handleResetZoom = () => {
    setScale(1)
    setPan({ x: 0, y: 0 })
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const result = await saveProject({
        name: projectName,
        elements: elements
      })
      if (result.success) {
        console.log('Project saved successfully')
      }
    } catch (error) {
      console.error('Save error:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleImageGenerate = useCallback(
    async (prompt: string, resolution: Resolution, aspectRatio: AspectRatio, referenceImage?: string) => {
      setIsGeneratingImage(true)

      try {
        const result = await generateImage({
          prompt,
          resolution,
          aspect_ratio: aspectRatio,
          reference_image: referenceImage,
          model: selectedModel
        })

        if (result.success && result.data) {
          if (imageGeneratorElementId) {
            const targetElement = elements.find(el => el.id === imageGeneratorElementId)
            if (targetElement) {
              updateElement(imageGeneratorElementId, {
                type: 'image',
                content: `data:image/png;base64,${result.data.image_base64}`,
                width: result.data.width,
                height: result.data.height
              })
            }
          } else {
            const newElement: CanvasElement = {
              id: uuidv4(),
              type: 'image',
              x: 100,
              y: 100,
              width: result.data.width,
              height: result.data.height,
              content: `data:image/png;base64,${result.data.image_base64}`
            }
            addElement(newElement)
            setSelectedIds([newElement.id])
          }

          closeImageGenerator()
        } else {
          console.error('Image generation failed:', result.error)
        }
      } catch (error) {
        console.error('Image generation error:', error)
      } finally {
        setIsGeneratingImage(false)
      }
    },
    [imageGeneratorElementId, elements, updateElement, addElement, setSelectedIds, closeImageGenerator, setIsGeneratingImage, selectedModel]
  )

  // AI 助手触发的图像生成
  const handleAiGenerateImage = useCallback(
    async (prompt: string, resolution: string, aspectRatio: string) => {
      setIsGeneratingImage(true)

      try {
        const result = await generateImage({
          prompt,
          resolution: resolution as Resolution,
          aspect_ratio: aspectRatio as AspectRatio,
          model: selectedModel
        })

        if (result.success && result.data) {
          // 计算居中位置
          const canvasRect = canvasRef.current?.getBoundingClientRect()
          const centerX = canvasRect ? (canvasRect.width / 2 - pan.x) / scale : 300
          const centerY = canvasRect ? (canvasRect.height / 2 - pan.y) / scale : 300

          const imageBase64 = `data:image/png;base64,${result.data.image_base64}`
          
          const newElement: CanvasElement = {
            id: uuidv4(),
            type: 'image',
            x: centerX - result.data.width / 2,
            y: centerY - result.data.height / 2,
            width: result.data.width,
            height: result.data.height,
            content: imageBase64
          }
          addElement(newElement)
          setSelectedIds([newElement.id])
          
          // 生成图像后自动设置为待分析图像，触发 AI 助手中的分析
          // 用户可以双击图像进行分析
          setTimeout(() => {
            setPendingImageForAi({
              imageBase64: imageBase64,
              elementId: newElement.id
            })
          }, 1000) // 延迟1秒让用户先看到图像
        } else {
          console.error('AI image generation failed:', result.error)
        }
      } catch (error) {
        console.error('AI image generation error:', error)
      } finally {
        setIsGeneratingImage(false)
      }
    },
    [addElement, setSelectedIds, setIsGeneratingImage, selectedModel, pan, scale]
  )
  
  // 直接添加图像到画布（用于 LLM 直接返回图片 URL 的情况）
  const handleAddImageToCanvas = useCallback((imageBase64: string) => {
    const canvasRect = canvasRef.current?.getBoundingClientRect()
    const centerX = canvasRect ? (canvasRect.width / 2 - pan.x) / scale : 300
    const centerY = canvasRect ? (canvasRect.height / 2 - pan.y) / scale : 300
    
    // 创建一个临时 Image 对象来获取图像尺寸
    const img = new Image()
    img.onload = () => {
      const newElement: CanvasElement = {
        id: uuidv4(),
        type: 'image',
        x: centerX - img.width / 2,
        y: centerY - img.height / 2,
        width: img.width,
        height: img.height,
        content: imageBase64
      }
      addElement(newElement)
      setSelectedIds([newElement.id])
    }
    img.onerror = () => {
      // 如果无法获取尺寸，使用默认尺寸
      const newElement: CanvasElement = {
        id: uuidv4(),
        type: 'image',
        x: centerX - 256,
        y: centerY - 256,
        width: 512,
        height: 512,
        content: imageBase64
      }
      addElement(newElement)
      setSelectedIds([newElement.id])
    }
    img.src = imageBase64
  }, [addElement, setSelectedIds, pan, scale])

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* 顶部导航栏 - Nexus 风格 */}
      <header className="h-14 bg-card border-b border-border flex items-center justify-between px-4 shrink-0 z-50">
        {/* 左侧: Logo + 项目名 */}
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2 group" title="返回首页">
            <NexusLogo size={36} />
            <ChevronDown size={14} className="text-muted-foreground group-hover:text-foreground transition-colors" />
          </Link>
          
          <div className="h-6 w-px bg-border" />
          
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="bg-transparent text-foreground text-sm outline-none border-none focus:ring-0 max-w-[200px] font-medium placeholder:text-muted-foreground"
            placeholder="未命名项目"
          />
          
          {isDirty && (
            <span className="text-xs text-[var(--nexus-warning)] px-2 py-0.5 rounded-full bg-[var(--nexus-warning)]/10">
              未保存
            </span>
          )}
        </div>

        {/* 中央: 工具按钮 */}
        <div className="flex items-center gap-1">
          <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-all" title="撤销">
            <Undo2 size={18} />
          </button>
          <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-all" title="重做">
            <Redo2 size={18} />
          </button>
        </div>

        {/* 右侧: 功能按钮 */}
        <div className="flex items-center gap-2">
          {/* 主题切换 */}
          <label className="nexus-theme-switch switch" aria-label="切换主题">
            <input 
              type="checkbox" 
              checked={theme === 'light'}
              onChange={toggleTheme}
            />
            <span className="slider">
              <div className="star star_1"></div>
              <div className="star star_2"></div>
              <div className="star star_3"></div>
              <svg viewBox="0 0 16 16" className="cloud_1 cloud">
                <path
                  transform="matrix(.77976 0 0 .78395-299.99-418.63)"
                  fill="#fff"
                  d="m391.84 540.91c-.421-.329-.949-.524-1.523-.524-1.351 0-2.451 1.084-2.485 2.435-1.395.526-2.388 1.88-2.388 3.466 0 1.874 1.385 3.423 3.182 3.667v.034h12.73v-.006c1.775-.104 3.182-1.584 3.182-3.395 0-1.747-1.309-3.186-2.994-3.379.007-.106.011-.214.011-.322 0-2.707-2.271-4.901-5.072-4.901-2.073 0-3.856 1.202-4.643 2.925"
                ></path>
              </svg>
            </span>
          </label>

          <div className="h-6 w-px bg-border" />

          {/* 元素拆分 */}
          <button
            onClick={handleToggleElementSplit}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all ${
              isElementSplitOpen
                ? 'bg-primary/10 text-primary border border-primary/30'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
            title="元素拆分"
          >
            <Layers size={16} />
            <span className="hidden md:inline">拆分</span>
          </button>

          {/* AI 助手 */}
          <button
            onClick={handleToggleAiDesigner}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all ${
              isAiDesignerOpen
                ? 'bg-primary/10 text-primary border border-primary/30'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
            title="AI 设计助手"
          >
            <Wand2 size={16} />
            <span className="hidden md:inline">AI 助手</span>
          </button>

          {/* 保存按钮 */}
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="nexus-btn-primary flex items-center gap-2 text-sm"
          >
            <Save size={16} />
            <span>{isSaving ? '保存中...' : '保存'}</span>
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <main ref={canvasRef} className="flex-1 relative overflow-hidden bg-background">
        {/* 浮动工具栏 - 左侧 */}
        <FloatingToolbar
          activeTool={activeTool}
          onToolChange={setActiveTool}
          onAddImage={addImageElement}
          onAddVideo={addVideoElement}
          onAddText={addTextElement}
          onAddShape={addShapeElement}
          onOpenImageGenerator={() => {
            // 在画布中央创建 image-generator 占位元素（OpenLovart 风格）
            const canvasRect = canvasRef.current?.getBoundingClientRect()
            const centerX = canvasRect ? (canvasRect.width / 2 - pan.x) / scale : 400
            const centerY = canvasRect ? (canvasRect.height / 2 - pan.y) / scale : 300
            addImageGeneratorElement(centerX, centerY)
          }}
          onOpenVideoGenerator={() => {
            const canvasRect = canvasRef.current?.getBoundingClientRect()
            const centerX = canvasRect ? (canvasRect.width / 2 - pan.x) / scale : 400
            const centerY = canvasRect ? (canvasRect.height / 2 - pan.y) / scale : 300
            addVideoGeneratorElement(centerX, centerY)
          }}
        />

        {/* 画布区域 */}
        <CanvasArea
          scale={scale}
          pan={pan}
          onPanChange={setPan}
          elements={elements}
          selectedIds={selectedIds}
          onSelect={setSelectedIds}
          onElementChange={updateElement}
          onDelete={deleteElement}
          onAddElement={addElement}
          activeTool={activeTool}
          onImageDoubleClick={handleCanvasImageClick}
          onRegionSelected={handleRegionSelected}
          onConnectFlow={handleConnectFlow}
          onRegionEdit={handleRegionEdit}
          onUpscale={handleUpscale}
          onRemoveBackground={handleRemoveBackground}
          onMockup={handleMockup}
          onEditElements={handleEditElements}
          onEditText={handleEditText}
          // Lovart 拆分：画布高亮框
          showAnalyzedOverlays={isElementSplitOpen}
          analysisTargetElementId={splitTargetImage?.id || null}
          analyzedElements={analyzedElements}
          selectedAnalyzedElementId={selectedAnalyzedElementId}
          onSelectAnalyzedElement={selectAnalyzedElement}
        />

        {/* 左下角：图层 + 缩放控制 */}
        <div className="absolute left-4 bottom-4 z-50 flex flex-col gap-2">
          <button
            onClick={() => {
              // 打开图层面板时，关闭元素拆分面板，避免 UI 互相遮挡；同时清理“编辑文字”自动选中模式
              setIsElementSplitOpen(false)
              setSplitAutoSelectMode(null)
              setIsLayersOpen(true)
            }}
            className="nexus-card px-3 py-2 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
            title="图层"
          >
            <Layers size={16} />
            <span>图层</span>
          </button>

          <div className="nexus-card px-2 py-1.5 flex items-center gap-1">
            <button
              onClick={handleZoomOut}
              className="p-1.5 hover:bg-muted rounded-lg text-muted-foreground hover:text-foreground transition-all"
              title="缩小 (Ctrl+-)"
            >
              <ZoomOut size={16} />
            </button>
            <button
              onClick={handleResetZoom}
              className="px-2 py-1 hover:bg-muted rounded-lg text-muted-foreground text-xs font-medium min-w-[48px] text-center transition-all"
              title="重置 (Ctrl+0)"
            >
              {Math.round(scale * 100)}%
            </button>
            <button
              onClick={handleZoomIn}
              className="p-1.5 hover:bg-muted rounded-lg text-muted-foreground hover:text-foreground transition-all"
              title="放大 (Ctrl++)"
            >
              <ZoomIn size={16} />
            </button>
          </div>
        </div>

        {/* Lovart 风格底部 Dock：选中 Generator 时出现 */}
        {selectedGenerator && (
          <GeneratorDock
            mode={selectedGenerator.type === 'video-generator' ? 'video' : 'image'}
            isGenerating={selectedGenerator.type === 'video-generator' ? isGeneratingVideo : isGeneratingImage}
            canvasElements={elements}
            generatorElement={selectedGenerator}
            initialPrompt={dockPresets[selectedGenerator.id]?.prompt}
            initialResolution={dockPresets[selectedGenerator.id]?.resolution}
            initialAspectRatio={dockPresets[selectedGenerator.id]?.aspectRatio}
            onSetReferenceImageId={(imageId: string | null) => {
              updateElement(selectedGenerator.id, { referenceImageId: imageId || undefined })
            }}
            selectedImageModel={selectedModel}
            onChangeImageModel={setSelectedModel}
            imageModels={IMAGE_MODELS.map(m => ({ id: m.id, name: m.name, icon: m.icon, coming: m.coming }))}
            onClose={() => setSelectedIds([])}
            onGenerateImage={handleDockGenerateImage}
            onGenerateVideo={handleDockGenerateVideo}
          />
        )}

        {/* AI 设计师侧边栏 */}
        {isAiDesignerOpen && (
          <div className="absolute right-0 top-0 bottom-0 w-[380px] max-w-[90vw] bg-[var(--nexus-sidebar-bg)] border-l border-[var(--nexus-sidebar-border)] shadow-2xl z-50">
            <AiDesignerPanel
              onClose={handleToggleAiDesigner}
              onGenerateImage={handleAiGenerateImage}
              onAddImageToCanvas={handleAddImageToCanvas}
              pendingImage={pendingImageForAi}
              onClearPendingImage={() => setPendingImageForAi(null)}
              canvasElements={elements}
            />
          </div>
        )}

        {/* 元素拆分侧边栏 */}
        {isElementSplitOpen && (
          <div className="absolute right-0 top-0 bottom-0 w-80 max-w-[90vw] bg-card border-l border-border shadow-2xl z-50">
            <ElementSplitPanel
              onClose={() => {
                setIsElementSplitOpen(false)
                selectAnalyzedElement(null)
                clearAnalysis()
                setSplitAutoSelectMode(null)
              }}
            />
          </div>
        )}
        
        {/* 框选编辑弹窗 */}
        {regionSelection && (
          <RegionEditPopup
            selection={regionSelection}
            onClose={() => {
              setRegionSelection(null)
              setActiveTool('select')
            }}
            onSubmit={handleRegionEditSubmit}
            isProcessing={isRegionProcessing}
          />
        )}

        {/* 图层面板（Lovart 风格） */}
        <LayersDrawer
          isOpen={isLayersOpen}
          elements={elements}
          selectedIds={selectedIds}
          onSelect={(ids: string[]) => setSelectedIds(ids)}
          onToggleHidden={toggleElementHidden}
          onToggleLocked={toggleElementLocked}
          onClose={() => setIsLayersOpen(false)}
        />
      </main>
    </div>
  )
}
