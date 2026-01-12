import React, { useState, useRef, useEffect } from 'react'
import { ContextToolbar } from './ContextToolbar'
import type { CanvasElement } from './types'
import { v4 as uuidv4 } from 'uuid'

// 框选区域信息
export interface RegionSelection {
  elementId: string
  imageBase64: string
  bbox: [number, number, number, number] // [x, y, width, height] 相对于图像
  bboxNormalized: [number, number, number, number] // 归一化坐标 [0-1]
  screenPosition: { x: number; y: number } // 弹窗显示位置
}

interface CanvasAreaProps {
  scale: number
  pan: { x: number; y: number }
  onPanChange: (pan: { x: number; y: number }) => void
  elements: CanvasElement[]
  selectedIds: string[]
  onSelect: (ids: string[]) => void
  onElementChange: (id: string, newAttrs: Partial<CanvasElement>) => void
  onDelete: (id: string) => void
  onAddElement: (element: CanvasElement) => void
  activeTool: string
  onDragStart?: () => void
  onDragEnd?: () => void
  onConnectFlow?: (element: CanvasElement) => void
  // 双击图像上传到 AI 聊天
  onImageDoubleClick?: (element: CanvasElement) => void
  // 框选编辑完成回调
  onRegionSelected?: (selection: RegionSelection) => void
  // 图像元素工具栏回调
  onRegionEdit?: (element: CanvasElement) => void

  // 第 4 张图那排（Lovart）：放大/移除背景/Mockup/编辑元素/编辑文字
  onUpscale?: (element: CanvasElement) => void
  onRemoveBackground?: (element: CanvasElement) => void
  onMockup?: (element: CanvasElement) => void
  onEditElements?: (element: CanvasElement) => void
  onEditText?: (element: CanvasElement) => void

  // Lovart 拆分：元素分析高亮（可选）
  analyzedElements?: Array<{
    id: string
    type: string
    label: string
    bbox: [number, number, number, number] // 0-1: [x, y, w, h]
    confidence: number
    content?: string
    description?: string
  }>
  selectedAnalyzedElementId?: string | null
  onSelectAnalyzedElement?: (id: string | null) => void
  analysisTargetElementId?: string | null
  showAnalyzedOverlays?: boolean
}

export function CanvasArea({
  scale,
  pan,
  onPanChange,
  elements,
  selectedIds,
  onSelect,
  onElementChange,
  onDelete,
  onAddElement,
  activeTool,
  onDragStart,
  onDragEnd,
  onConnectFlow,
  onImageDoubleClick,
  onRegionSelected,
  onRegionEdit,
  onUpscale,
  onRemoveBackground,
  onMockup,
  onEditElements,
  onEditText,
  analyzedElements,
  selectedAnalyzedElementId,
  onSelectAnalyzedElement,
  analysisTargetElementId,
  showAnalyzedOverlays
}: CanvasAreaProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const toolbarRef = useRef<HTMLDivElement>(null)
  const [toolbarSize, setToolbarSize] = useState<{ w: number; h: number }>({ w: 420, h: 44 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })
  const [isDrawing, setIsDrawing] = useState(false)
  const [currentPath, setCurrentPath] = useState<{ x: number; y: number }[]>([])

  // 量测工具条尺寸，修复靠近画布上边缘时的可点击性/遮挡问题
  useEffect(() => {
    const el = toolbarRef.current
    if (!el) return

    const update = () => {
      const r = el.getBoundingClientRect()
      if (!r.width || !r.height) return
      setToolbarSize((prev) => {
        const w = Math.round(r.width)
        const h = Math.round(r.height)
        if (prev.w === w && prev.h === h) return prev
        return { w, h }
      })
    }

    update()

    // 用 ResizeObserver 更稳：按钮/文字变化也能更新
    const ro = new ResizeObserver(() => update())
    ro.observe(el)

    return () => ro.disconnect()
  }, [selectedIds, elements, scale, pan.x, pan.y])
  const [resizeHandle, setResizeHandle] = useState<string | null>(null)
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0, elementX: 0, elementY: 0 })
  
  // 框选编辑状态
  const [isRegionSelecting, setIsRegionSelecting] = useState(false)
  const [regionSelectStart, setRegionSelectStart] = useState({ x: 0, y: 0 })
  const [regionSelectEnd, setRegionSelectEnd] = useState({ x: 0, y: 0 })
  const [regionSelectTarget, setRegionSelectTarget] = useState<CanvasElement | null>(null)

  // Handle canvas click for deselection
  const handleCanvasClick = (e: React.MouseEvent) => {
    if (e.target === canvasRef.current || (e.target as HTMLElement).classList.contains('canvas-background')) {
      onSelect([])
    }
  }

  // Handle mouse down for panning or drawing
  const handleMouseDown = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement
    
    // If clicking on a resize handle, don't pan
    if (target.classList.contains('resize-handle')) {
      return
    }

    // Hand tool or middle mouse button for panning
    if (activeTool === 'hand' || e.button === 1) {
      e.preventDefault()
      setIsPanning(true)
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
      return
    }

    // Draw tool
    if (activeTool === 'draw') {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (rect) {
        const x = (e.clientX - rect.left - pan.x) / scale
        const y = (e.clientY - rect.top - pan.y) / scale
        setIsDrawing(true)
        setCurrentPath([{ x, y }])
      }
      return
    }
  }
  
  // 开始框选 - 在图像上
  const handleRegionSelectStart = (e: React.MouseEvent, element: CanvasElement) => {
    if (activeTool !== 'region-edit') return
    e.stopPropagation()
    e.preventDefault()
    
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    
    const canvasX = (e.clientX - rect.left - pan.x) / scale
    const canvasY = (e.clientY - rect.top - pan.y) / scale
    
    // 计算相对于图像的坐标
    const relX = canvasX - element.x
    const relY = canvasY - element.y
    
    setIsRegionSelecting(true)
    setRegionSelectTarget(element)
    setRegionSelectStart({ x: relX, y: relY })
    setRegionSelectEnd({ x: relX, y: relY })
  }

  // Handle mouse move for panning or drawing
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      e.preventDefault()
      onPanChange({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      })
      return
    }

    if (isDrawing && activeTool === 'draw') {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (rect) {
        const x = (e.clientX - rect.left - pan.x) / scale
        const y = (e.clientY - rect.top - pan.y) / scale
        setCurrentPath(prev => [...prev, { x, y }])
      }
      return
    }
    
    // 框选拖动
    if (isRegionSelecting && regionSelectTarget) {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (rect) {
        const canvasX = (e.clientX - rect.left - pan.x) / scale
        const canvasY = (e.clientY - rect.top - pan.y) / scale
        
        // 计算相对于图像的坐标，并限制在图像范围内
        const imgWidth = regionSelectTarget.width || 100
        const imgHeight = regionSelectTarget.height || 100
        
        const relX = Math.max(0, Math.min(imgWidth, canvasX - regionSelectTarget.x))
        const relY = Math.max(0, Math.min(imgHeight, canvasY - regionSelectTarget.y))
        
        setRegionSelectEnd({ x: relX, y: relY })
      }
      return
    }
  }

  // Handle mouse up
  const handleMouseUp = () => {
    if (isPanning) {
      setIsPanning(false)
      return
    }

    if (isDrawing && currentPath.length > 1) {
      const newElement: CanvasElement = {
        id: uuidv4(),
        type: 'path',
        x: Math.min(...currentPath.map(p => p.x)),
        y: Math.min(...currentPath.map(p => p.y)),
        points: currentPath,
        color: 'var(--foreground)',
        strokeWidth: 2
      }
      onAddElement(newElement)
      setIsDrawing(false)
      setCurrentPath([])
    }
    
    // 框选完成
    if (isRegionSelecting && regionSelectTarget) {
      const minX = Math.min(regionSelectStart.x, regionSelectEnd.x)
      const minY = Math.min(regionSelectStart.y, regionSelectEnd.y)
      const maxX = Math.max(regionSelectStart.x, regionSelectEnd.x)
      const maxY = Math.max(regionSelectStart.y, regionSelectEnd.y)
      
      const width = maxX - minX
      const height = maxY - minY
      
      // 只有框选区域足够大时才触发
      if (width > 10 && height > 10) {
        const imgWidth = regionSelectTarget.width || 100
        const imgHeight = regionSelectTarget.height || 100
        
        // 计算屏幕位置（弹窗显示位置）
        const rect = canvasRef.current?.getBoundingClientRect()
        const screenX = rect ? rect.left + pan.x + (regionSelectTarget.x + maxX) * scale : 0
        const screenY = rect ? rect.top + pan.y + (regionSelectTarget.y + minY) * scale : 0
        
        const selection: RegionSelection = {
          elementId: regionSelectTarget.id,
          imageBase64: regionSelectTarget.content || '',
          bbox: [minX, minY, width, height],
          bboxNormalized: [
            minX / imgWidth,
            minY / imgHeight,
            width / imgWidth,
            height / imgHeight
          ],
          screenPosition: { x: screenX, y: screenY }
        }
        
        onRegionSelected?.(selection)
      }
      
      setIsRegionSelecting(false)
      setRegionSelectTarget(null)
      setRegionSelectStart({ x: 0, y: 0 })
      setRegionSelectEnd({ x: 0, y: 0 })
    }
  }

  // Element drag handlers
  const handleElementMouseDown = (e: React.MouseEvent, element: CanvasElement) => {
    e.stopPropagation()
    
    if (activeTool === 'hand') return

    // Select element
    if (e.shiftKey) {
      if (selectedIds.includes(element.id)) {
        onSelect(selectedIds.filter(id => id !== element.id))
      } else {
        onSelect([...selectedIds, element.id])
      }
    } else if (!selectedIds.includes(element.id)) {
      onSelect([element.id])
    }

    // Locked elements can be selected but not moved
    if (element.locked) return

    // Start dragging
    setIsDragging(true)
    const rect = canvasRef.current?.getBoundingClientRect()
    if (rect) {
      setDragStart({
        x: (e.clientX - rect.left - pan.x) / scale - element.x,
        y: (e.clientY - rect.top - pan.y) / scale - element.y
      })
    }
    onDragStart?.()
  }

  // Global mouse move for dragging elements
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      if (isDragging && selectedIds.length > 0) {
        const rect = canvasRef.current?.getBoundingClientRect()
        if (rect) {
          const newX = (e.clientX - rect.left - pan.x) / scale - dragStart.x
          const newY = (e.clientY - rect.top - pan.y) / scale - dragStart.y
          
          selectedIds.forEach(id => {
            const element = elements.find(el => el.id === id)
            if (element && !element.locked) {
              const deltaX = newX - element.x
              const deltaY = newY - element.y
              // Only update the first selected element based on drag
              if (id === selectedIds[0]) {
                onElementChange(id, { x: newX, y: newY })
              } else {
                // Move other selected elements by the same delta
                onElementChange(id, { 
                  x: element.x + deltaX, 
                  y: element.y + deltaY 
                })
              }
            }
          })
        }
      }

      // Resize handling
      if (resizeHandle && selectedIds.length === 1) {
        const element = elements.find(el => el.id === selectedIds[0])
        if (element && !element.locked && canvasRef.current) {
          const rect = canvasRef.current.getBoundingClientRect()
          const mouseX = (e.clientX - rect.left - pan.x) / scale
          const mouseY = (e.clientY - rect.top - pan.y) / scale

          let newWidth = resizeStart.width
          let newHeight = resizeStart.height
          let newX = resizeStart.elementX
          let newY = resizeStart.elementY

          // Calculate based on resize handle
          if (resizeHandle.includes('e')) {
            newWidth = Math.max(20, mouseX - resizeStart.elementX)
          }
          if (resizeHandle.includes('w')) {
            const deltaX = mouseX - resizeStart.x
            newWidth = Math.max(20, resizeStart.width - deltaX)
            newX = resizeStart.elementX + resizeStart.width - newWidth
          }
          if (resizeHandle.includes('s')) {
            newHeight = Math.max(20, mouseY - resizeStart.elementY)
          }
          if (resizeHandle.includes('n')) {
            const deltaY = mouseY - resizeStart.y
            newHeight = Math.max(20, resizeStart.height - deltaY)
            newY = resizeStart.elementY + resizeStart.height - newHeight
          }

          onElementChange(selectedIds[0], { 
            width: newWidth, 
            height: newHeight,
            x: newX,
            y: newY
          })
        }
      }
    }

    const handleGlobalMouseUp = () => {
      if (isDragging) {
        setIsDragging(false)
        onDragEnd?.()
      }
      if (resizeHandle) {
        setResizeHandle(null)
      }
    }

    window.addEventListener('mousemove', handleGlobalMouseMove)
    window.addEventListener('mouseup', handleGlobalMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove)
      window.removeEventListener('mouseup', handleGlobalMouseUp)
    }
  }, [isDragging, resizeHandle, selectedIds, elements, dragStart, resizeStart, pan, scale])

  // Start resize
  const handleResizeStart = (e: React.MouseEvent, handle: string, element: CanvasElement) => {
    e.stopPropagation()
    e.preventDefault()
    const rect = canvasRef.current?.getBoundingClientRect()
    if (rect) {
      setResizeHandle(handle)
      setResizeStart({
        x: (e.clientX - rect.left - pan.x) / scale,
        y: (e.clientY - rect.top - pan.y) / scale,
        width: element.width || 100,
        height: element.height || 100,
        elementX: element.x,
        elementY: element.y
      })
    }
  }

  // Render element
  const renderElement = (element: CanvasElement) => {
    const isSelected = selectedIds.includes(element.id)
    const width = element.width || 100
    const height = element.height || 100

    const commonStyle: React.CSSProperties = {
      position: 'absolute',
      left: element.x,
      top: element.y,
      width,
      height,
      cursor: activeTool === 'hand' ? 'grab' : 'move',
      userSelect: 'none'
    }

    const selectionOverlay = isSelected && (
      <>
        {/* Selection border - 使用 primary 颜色 */}
        <div 
          className="absolute inset-0 border-2 border-primary pointer-events-none rounded"
          style={{ margin: -2 }}
        />
        {/* Resize handles */}
        {['nw', 'n', 'ne', 'w', 'e', 'sw', 's', 'se'].map(handle => {
          const positions: Record<string, React.CSSProperties> = {
            nw: { top: -4, left: -4, cursor: 'nwse-resize' },
            n: { top: -4, left: '50%', transform: 'translateX(-50%)', cursor: 'ns-resize' },
            ne: { top: -4, right: -4, cursor: 'nesw-resize' },
            w: { top: '50%', left: -4, transform: 'translateY(-50%)', cursor: 'ew-resize' },
            e: { top: '50%', right: -4, transform: 'translateY(-50%)', cursor: 'ew-resize' },
            sw: { bottom: -4, left: -4, cursor: 'nesw-resize' },
            s: { bottom: -4, left: '50%', transform: 'translateX(-50%)', cursor: 'ns-resize' },
            se: { bottom: -4, right: -4, cursor: 'nwse-resize' }
          }
          return (
            <div
              key={handle}
              className="resize-handle absolute w-2 h-2 bg-card border-2 border-primary rounded-sm z-10"
              style={positions[handle]}
              onMouseDown={(e) => handleResizeStart(e, handle, element)}
            />
          )
        })}
      </>
    )

    switch (element.type) {
      case 'image':
        const isRegionEditing = activeTool === 'region-edit'
        const isThisImageBeingSelected = isRegionSelecting && regionSelectTarget?.id === element.id
        const showElementOverlay =
          !!showAnalyzedOverlays &&
          !isRegionEditing &&
          analysisTargetElementId === element.id &&
          !!analyzedElements &&
          analyzedElements.length > 0
        
        return (
          <div
            key={element.id}
            style={{
              ...commonStyle,
              cursor: isRegionEditing ? 'crosshair' : commonStyle.cursor
            }}
            onMouseDown={(e) => {
              if (isRegionEditing) {
                handleRegionSelectStart(e, element)
              } else {
                handleElementMouseDown(e, element)
              }
            }}
            onDoubleClick={(e) => {
              if (!isRegionEditing) {
                e.stopPropagation()
                onImageDoubleClick?.(element)
              }
            }}
            className="relative group"
            title={isRegionEditing ? "在图像上框选区域进行局部编辑" : "双击上传到 AI 助手进行分析"}
          >
            <img
              src={element.content}
              alt=""
              className="w-full h-full object-cover rounded-lg"
              draggable={false}
            />

            {/* Lovart：元素拆分高亮层（只在拆分面板打开时显示） */}
            {showElementOverlay && (
              <>
                {analyzedElements!.map((ae) => {
                  const isAeSelected = ae.id === selectedAnalyzedElementId
                  const [x, y, w, h] = ae.bbox

                  return (
                    <button
                      key={ae.id}
                      type="button"
                      title={`${ae.label}（${Math.round(ae.confidence * 100)}%）`}
                      className={`absolute rounded-md transition-all ${
                        isAeSelected
                          ? 'border-2 border-primary bg-primary/10'
                          : 'border border-muted-foreground/60 bg-transparent hover:bg-primary/5 hover:border-primary/60'
                      }`}
                      style={{
                        left: `${x * 100}%`,
                        top: `${y * 100}%`,
                        width: `${w * 100}%`,
                        height: `${h * 100}%`
                      }}
                      onMouseDown={(e) => {
                        // 不触发拖拽
                        e.stopPropagation()
                      }}
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectAnalyzedElement?.(isAeSelected ? null : ae.id)
                      }}
                    >
                      <span className="sr-only">{ae.label}</span>
                    </button>
                  )
                })}
              </>
            )}
            
            {/* 框选模式提示 */}
            {isRegionEditing && !isThisImageBeingSelected && (
              <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary/50 rounded-lg flex items-center justify-center">
                <span className="text-primary text-sm font-medium bg-card/90 px-3 py-1.5 rounded-full shadow-lg">
                  拖动框选编辑区域
                </span>
              </div>
            )}
            
            {/* 框选矩形 */}
            {isThisImageBeingSelected && (
              <div
                className="absolute border-2 border-primary bg-primary/20 pointer-events-none"
                style={{
                  left: Math.min(regionSelectStart.x, regionSelectEnd.x),
                  top: Math.min(regionSelectStart.y, regionSelectEnd.y),
                  width: Math.abs(regionSelectEnd.x - regionSelectStart.x),
                  height: Math.abs(regionSelectEnd.y - regionSelectStart.y),
                }}
              />
            )}
            
            {/* 双击提示 - 悬停时显示 (非框选模式) */}
            {!isRegionEditing && (
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all duration-200 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100">
                <span className="text-white text-sm font-medium bg-black/50 px-3 py-1.5 rounded-full">
                  双击分析图像
                </span>
              </div>
            )}
            {selectionOverlay}
          </div>
        )

      case 'video':
        return (
          <div
            key={element.id}
            style={commonStyle}
            onMouseDown={(e) => handleElementMouseDown(e, element)}
            className="relative group"
          >
            <video
              src={element.content}
              className="w-full h-full object-cover rounded-lg"
              controls={isSelected}
            />
            {selectionOverlay}
          </div>
        )

      case 'text':
        return (
          <div
            key={element.id}
            style={{
              ...commonStyle,
              width: element.width || 'auto',
              height: 'auto',
              minWidth: 50
            }}
            onMouseDown={(e) => handleElementMouseDown(e, element)}
            className="relative group"
          >
            <div
              contentEditable={isSelected}
              suppressContentEditableWarning
              onBlur={(e) => onElementChange(element.id, { content: e.currentTarget.textContent || '' })}
              style={{
                fontSize: element.fontSize || 24,
                fontFamily: element.fontFamily || 'Inter',
                color: element.color || 'var(--foreground)',
                outline: 'none',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}
              className="px-1"
            >
              {element.content || '双击编辑'}
            </div>
            {selectionOverlay}
          </div>
        )

      case 'shape':
        const renderShape = () => {
          const shapeStyle: React.CSSProperties = {
            width: '100%',
            height: '100%',
            backgroundColor: element.color || 'var(--muted-foreground)'
          }

          switch (element.shapeType) {
            case 'circle':
              return <div style={{ ...shapeStyle, borderRadius: '50%' }} />
            case 'triangle':
              return (
                <div 
                  style={{
                    width: 0,
                    height: 0,
                    borderLeft: `${width / 2}px solid transparent`,
                    borderRight: `${width / 2}px solid transparent`,
                    borderBottom: `${height}px solid ${element.color || 'var(--muted-foreground)'}`,
                    backgroundColor: 'transparent'
                  }}
                />
              )
            case 'square':
            default:
              return <div style={{ ...shapeStyle, borderRadius: 8 }} />
          }
        }

        return (
          <div
            key={element.id}
            style={commonStyle}
            onMouseDown={(e) => handleElementMouseDown(e, element)}
            className="relative group"
          >
            {renderShape()}
            {selectionOverlay}
          </div>
        )

      case 'path':
        if (!element.points || element.points.length < 2) return null
        const minX = Math.min(...element.points.map(p => p.x))
        const minY = Math.min(...element.points.map(p => p.y))
        const maxX = Math.max(...element.points.map(p => p.x))
        const maxY = Math.max(...element.points.map(p => p.y))
        const pathWidth = maxX - minX + (element.strokeWidth || 2) * 2
        const pathHeight = maxY - minY + (element.strokeWidth || 2) * 2

        const pathD = element.points
          .map((p, i) => {
            const x = p.x - minX + (element.strokeWidth || 2)
            const y = p.y - minY + (element.strokeWidth || 2)
            return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
          })
          .join(' ')

        return (
          <svg
            key={element.id}
            style={{
              position: 'absolute',
              left: minX - (element.strokeWidth || 2),
              top: minY - (element.strokeWidth || 2),
              width: pathWidth,
              height: pathHeight,
              overflow: 'visible',
              cursor: activeTool === 'hand' ? 'grab' : 'move'
            }}
            onMouseDown={(e) => handleElementMouseDown(e, element)}
            className="relative group"
          >
            <path
              d={pathD}
              fill="none"
              stroke={element.color || 'var(--foreground)'}
              strokeWidth={element.strokeWidth || 2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {isSelected && (
              <rect
                x={0}
                y={0}
                width={pathWidth}
                height={pathHeight}
                fill="none"
                className="stroke-primary"
                strokeWidth={2}
                strokeDasharray="4,4"
              />
            )}
          </svg>
        )

      case 'image-generator':
        return (
          <div
            key={element.id}
            style={commonStyle}
            onMouseDown={(e) => handleElementMouseDown(e, element)}
            className="relative group"
          >
            <div className="w-full h-full bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30 border-2 border-dashed border-blue-400 dark:border-blue-500 rounded-xl flex flex-col items-center justify-center gap-3">
              {/* 图标 */}
              <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-8 h-8 text-blue-500" fill="currentColor">
                  <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
                </svg>
              </div>
              {/* 标题 */}
              <div className="text-center">
                <div className="text-blue-600 dark:text-blue-400 text-sm font-medium">AI 图像生成器</div>
                <div className="text-blue-400 dark:text-blue-500 text-xs mt-1">
                  {Math.round(width)} × {Math.round(height)}
                </div>
              </div>
              {/* 提示 */}
              {isSelected && (
                <div className="text-blue-500 dark:text-blue-400 text-xs bg-blue-100 dark:bg-blue-900/50 px-3 py-1 rounded-full">
                  在下方输入提示词生成
                </div>
              )}
            </div>
            {selectionOverlay}
          </div>
        )

      case 'video-generator':
        return (
          <div
            key={element.id}
            style={commonStyle}
            onMouseDown={(e) => handleElementMouseDown(e, element)}
            className="relative group"
          >
            <div className="w-full h-full bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950/30 dark:to-pink-950/30 border-2 border-dashed border-purple-400 dark:border-purple-500 rounded-xl flex flex-col items-center justify-center gap-3">
              <div className="w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-8 h-8 text-purple-500" fill="currentColor">
                  <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
                </svg>
              </div>
              <div className="text-center">
                <div className="text-purple-600 dark:text-purple-400 text-sm font-medium">AI 视频生成器</div>
                <div className="text-purple-400 dark:text-purple-500 text-xs mt-1">
                  {Math.round(width)} × {Math.round(height)}
                </div>
              </div>
            </div>
            {selectionOverlay}
          </div>
        )

      case 'connector':
        // 连接线在 SVG 层单独渲染，这里返回 null
        return null

      default:
        return null
    }
  }

  // Create dot pattern for canvas background - 使用 CSS 变量适应主题
  const dotPattern = `radial-gradient(circle, var(--border) 1px, transparent 1px)`

  return (
    <div
      ref={canvasRef}
      className="w-full h-full relative overflow-hidden bg-background"
      style={{
        cursor: activeTool === 'hand' ? (isPanning ? 'grabbing' : 'grab') : 
                activeTool === 'draw' ? 'crosshair' : 
                activeTool === 'region-edit' ? 'crosshair' : 'default'
      }}
      onClick={handleCanvasClick}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Canvas Background with dot pattern */}
      <div 
        className="canvas-background absolute inset-0"
        style={{
          backgroundImage: dotPattern,
          backgroundSize: `${20 * scale}px ${20 * scale}px`,
          backgroundPosition: `${pan.x}px ${pan.y}px`,
          pointerEvents: 'none'
        }}
      />

      {/* Canvas Transform Layer */}
      <div
        className="absolute origin-top-left"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
          transformOrigin: '0 0'
        }}
      >
        {/* Render Connectors (behind elements) */}
        <svg
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: '10000px',
            height: '10000px',
            overflow: 'visible',
            pointerEvents: 'none'
          }}
        >
          {/* Arrow marker definition */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" className="fill-muted-foreground" />
            </marker>
            <marker
              id="arrowhead-selected"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" className="fill-primary" />
            </marker>
          </defs>
          
          {elements
            .filter(el => el.type === 'connector' && !el.hidden)
            .map(connector => {
              const fromEl = elements.find(e => e.id === connector.connectorFrom)
              const toEl = elements.find(e => e.id === connector.connectorTo)
              
              if (!fromEl || !toEl) return null
              
              const fromX = fromEl.x + (fromEl.width || 100) / 2
              const fromY = fromEl.y + (fromEl.height || 100) / 2
              const toX = toEl.x + (toEl.width || 100) / 2
              const toY = toEl.y + (toEl.height || 100) / 2
              
              const isConnectorSelected = selectedIds.includes(connector.id)
              
              return (
                <line
                  key={connector.id}
                  x1={fromX}
                  y1={fromY}
                  x2={toX}
                  y2={toY}
                  className={isConnectorSelected ? 'stroke-primary' : 'stroke-muted-foreground'}
                  strokeWidth={connector.strokeWidth || 2}
                  strokeDasharray={connector.connectorStyle === 'dashed' ? '8 4' : '0'}
                  markerEnd={isConnectorSelected ? 'url(#arrowhead-selected)' : 'url(#arrowhead)'}
                />
              )
            })}
        </svg>

        {/* Render Elements */}
        {elements.filter(el => el.type !== 'connector' && !el.hidden).map(renderElement)}

        {/* Current Drawing Path */}
        {isDrawing && currentPath.length > 1 && (
          <svg
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: '100%',
              height: '100%',
              overflow: 'visible',
              pointerEvents: 'none'
            }}
          >
            <path
              d={currentPath.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')}
              fill="none"
              stroke="var(--foreground)"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>

      {/* Context Toolbar for Selected Element (Lovart-style: anchored above element) */}
      {(() => {
        if (selectedIds.length !== 1) return null
        const element = elements.find(el => el.id === selectedIds[0])
        if (!element || element.hidden) return null

        const rect = canvasRef.current?.getBoundingClientRect()
        const w = element.width || 100

        const rawLeft = (element.x + w / 2) * scale + pan.x
        const rawTop = element.y * scale + pan.y - 12

        const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v))
        const margin = 12
        // translate(-50%, -100%)：left 需要考虑宽度/2，top 需要考虑高度
        const leftMin = rect ? margin + toolbarSize.w / 2 : margin
        const leftMax = rect ? rect.width - margin - toolbarSize.w / 2 : 999999
        const topMin = rect ? margin + toolbarSize.h : margin
        const topMax = rect ? rect.height - margin : 999999

        const left = rect ? clamp(rawLeft, leftMin, leftMax) : rawLeft
        const top = rect ? clamp(rawTop, topMin, topMax) : rawTop

        return (
          <div
            ref={toolbarRef}
            className="absolute z-50 pointer-events-auto"
            style={{ left, top, transform: 'translate(-50%, -100%)' }}
          >
            <ContextToolbar
              key={element.id}
              element={element}
              onUpdate={onElementChange}
              onDelete={onDelete}
              onConnectFlow={onConnectFlow}
              onRegionEdit={onRegionEdit}
              onUpscale={onUpscale}
              onRemoveBackground={onRemoveBackground}
              onMockup={onMockup}
              onEditElements={onEditElements}
              onEditText={onEditText}
            />
          </div>
        )
      })()}
    </div>
  )
}
