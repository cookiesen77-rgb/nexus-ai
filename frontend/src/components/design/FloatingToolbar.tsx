import React, { useState, useRef } from 'react'
import { 
  MousePointer2, PlusSquare, Square, Type, Pencil, 
  Image as ImageIcon, Video, Circle, Triangle, 
  Hand, Sparkles, Crop, Wand2
} from 'lucide-react'

interface FloatingToolbarProps {
  activeTool: string
  onToolChange: (tool: string) => void
  onAddImage: (file: File) => void
  onAddVideo: (file: File) => void
  onAddText: () => void
  onAddShape: (type: 'square' | 'circle' | 'triangle' | 'star' | 'message' | 'arrow-left' | 'arrow-right') => void
  onOpenImageGenerator: () => void
  onOpenVideoGenerator?: () => void
}

export function FloatingToolbar({ 
  activeTool, 
  onToolChange, 
  onAddImage, 
  onAddVideo, 
  onAddText, 
  onAddShape, 
  onOpenImageGenerator, 
  onOpenVideoGenerator 
}: FloatingToolbarProps) {
  const [showUploadMenu, setShowUploadMenu] = useState(false)
  const [showShapeMenu, setShowShapeMenu] = useState(false)
  const [showSelectMenu, setShowSelectMenu] = useState(false)
  const [showTextMenu, setShowTextMenu] = useState(false)
  const [showDrawMenu, setShowDrawMenu] = useState(false)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const videoInputRef = useRef<HTMLInputElement>(null)

  const handleImageUploadClick = () => {
    imageInputRef.current?.click()
    setShowUploadMenu(false)
  }

  const handleVideoUploadClick = () => {
    videoInputRef.current?.click()
    setShowUploadMenu(false)
  }

  const handleImageFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      onAddImage(file)
    }
  }

  const handleVideoFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      onAddVideo(file)
    }
  }

  const handleShapeClick = (type: 'square' | 'circle' | 'triangle' | 'star' | 'message' | 'arrow-left' | 'arrow-right') => {
    onAddShape(type)
    setShowShapeMenu(false)
    onToolChange('select')
  }

  // Nexus 风格的工具按钮类
  const toolButtonClass = (isActive: boolean) => 
    `p-2.5 rounded-xl transition-all flex items-center justify-center ${
      isActive 
        ? 'bg-primary text-primary-foreground' 
        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
    }`

  return (
    <div className="absolute left-4 top-1/2 -translate-y-1/2 flex flex-col gap-4 z-50">
      {/* 主工具栏 - Nexus 卡片风格 */}
      <div className="nexus-card p-2 flex flex-col gap-1 w-12 items-center">
        {/* Select / Hand Tool */}
        <div
          className="relative"
          onMouseEnter={() => setShowSelectMenu(true)}
          onMouseLeave={() => setShowSelectMenu(false)}
        >
          <button
            className={toolButtonClass(['select', 'hand'].includes(activeTool))}
            title="选择 / 平移"
          >
            {activeTool === 'hand' ? <Hand size={18} /> : <MousePointer2 size={18} />}
          </button>

          {showSelectMenu && (
            <div className="absolute left-full top-0 pl-2 z-50">
              <div className="nexus-card p-1.5 min-w-[140px] flex flex-col gap-0.5">
                <button
                  onClick={() => { onToolChange('select'); setShowSelectMenu(false) }}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg hover:bg-muted text-sm transition-colors text-left ${
                    activeTool === 'select' ? 'bg-muted text-foreground font-medium' : 'text-muted-foreground'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <MousePointer2 size={15} />
                    <span>选择</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">V</span>
                </button>
                <button
                  onClick={() => { onToolChange('hand'); setShowSelectMenu(false) }}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg hover:bg-muted text-sm transition-colors text-left ${
                    activeTool === 'hand' ? 'bg-muted text-foreground font-medium' : 'text-muted-foreground'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Hand size={15} />
                    <span>平移</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">H</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Add/Upload Tool */}
        <div
          className="relative"
          onMouseEnter={() => setShowUploadMenu(true)}
          onMouseLeave={() => setShowUploadMenu(false)}
        >
          <button
            className={toolButtonClass(showUploadMenu)}
            title="添加 / 上传"
          >
            <PlusSquare size={18} />
          </button>

          {showUploadMenu && (
            <div className="absolute left-full top-0 pl-2 z-50">
              <div className="nexus-card p-1.5 min-w-[150px] flex flex-col gap-0.5">
                <button
                  onClick={handleImageUploadClick}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-muted text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                >
                  <ImageIcon size={15} />
                  <span>上传图片</span>
                </button>
                <button
                  onClick={handleVideoUploadClick}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-muted text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                >
                  <Video size={15} />
                  <span>上传视频</span>
                </button>
                <div className="h-px bg-border my-1" />
                <button
                  onClick={() => {
                    onOpenImageGenerator()
                    setShowUploadMenu(false)
                  }}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-primary/10 text-sm text-primary transition-colors text-left"
                >
                  <Sparkles size={15} />
                  <span>AI 生成图像</span>
                </button>
                {onOpenVideoGenerator && (
                  <button
                    onClick={() => {
                      onOpenVideoGenerator()
                      setShowUploadMenu(false)
                    }}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-primary/10 text-sm text-primary transition-colors text-left"
                  >
                    <Video size={15} />
                    <span>AI 生成视频</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Shape Tool */}
        <div
          className="relative"
          onMouseEnter={() => setShowShapeMenu(true)}
          onMouseLeave={() => setShowShapeMenu(false)}
        >
          <button
            className={toolButtonClass(activeTool === 'shape' || showShapeMenu)}
            title="形状"
          >
            <Square size={18} />
          </button>

          {showShapeMenu && (
            <div className="absolute left-full top-0 pl-2 z-50">
              <div className="nexus-card p-3 min-w-[140px]">
                <div className="mb-2 text-[11px] text-muted-foreground font-medium uppercase tracking-wider">形状</div>
                <div className="flex gap-1.5">
                  <button 
                    onClick={() => handleShapeClick('square')} 
                    className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Square size={18} />
                  </button>
                  <button 
                    onClick={() => handleShapeClick('circle')} 
                    className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Circle size={18} />
                  </button>
                  <button 
                    onClick={() => handleShapeClick('triangle')} 
                    className="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Triangle size={18} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Region Edit Tool - 框选编辑 */}
        <button
          onClick={() => onToolChange('region-edit')}
          className={toolButtonClass(activeTool === 'region-edit')}
          title="框选编辑 (在图像上框选区域进行 AI 局部编辑)"
        >
          <Crop size={18} />
        </button>

        {/* Text Tool */}
        <div
          className="relative"
          onMouseEnter={() => setShowTextMenu(true)}
          onMouseLeave={() => setShowTextMenu(false)}
        >
          <button
            className={toolButtonClass(activeTool === 'text' || showTextMenu)}
            title="文本"
          >
            <Type size={18} />
          </button>

          {showTextMenu && (
            <div className="absolute left-full top-0 pl-2 z-50">
              <div className="nexus-card p-1.5 min-w-[130px] flex flex-col gap-0.5">
                <button
                  onClick={() => {
                    onToolChange('text')
                    onAddText()
                    setShowTextMenu(false)
                  }}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-muted text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                >
                  <Type size={15} />
                  <span>添加文本</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Draw Tool */}
        <div
          className="relative"
          onMouseEnter={() => setShowDrawMenu(true)}
          onMouseLeave={() => setShowDrawMenu(false)}
        >
          <button
            className={toolButtonClass(activeTool === 'draw' || showDrawMenu)}
            title="绘制"
          >
            <Pencil size={18} />
          </button>

          {showDrawMenu && (
            <div className="absolute left-full top-0 pl-2 z-50">
              <div className="nexus-card p-1.5 min-w-[120px] flex flex-col gap-0.5">
                <button
                  onClick={() => {
                    onToolChange('draw')
                    setShowDrawMenu(false)
                  }}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-muted text-sm transition-colors text-left ${
                    activeTool === 'draw' ? 'bg-muted text-foreground font-medium' : 'text-muted-foreground'
                  }`}
                >
                  <Pencil size={15} />
                  <span>画笔</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="w-full h-px bg-border my-1" />

        {/* Image Generator Tool (Lovart style) */}
        <button
          onClick={() => {
            onOpenImageGenerator()
            onToolChange('select')
          }}
          className={toolButtonClass(false)}
          title="图像生成器 (A)"
        >
          <Sparkles size={18} />
        </button>

        {/* Video Generator Tool (Lovart style) */}
        <button
          onClick={() => {
            onOpenVideoGenerator?.()
            onToolChange('select')
          }}
          className={toolButtonClass(false)}
          title="视频生成器"
          disabled={!onOpenVideoGenerator}
        >
          <Video size={18} />
        </button>

        {/* Hidden File Inputs */}
        <input
          type="file"
          ref={imageInputRef}
          className="hidden"
          onChange={handleImageFileChange}
          accept="image/*"
        />
        <input
          type="file"
          ref={videoInputRef}
          className="hidden"
          onChange={handleVideoFileChange}
          accept="video/*"
        />
      </div>
    </div>
  )
}
