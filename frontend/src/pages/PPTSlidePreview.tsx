/**
 * Nexus PPT 幻灯片预览
 * 基于 banana-slides SlidePreview.tsx 深度集成
 */
import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { 
  ArrowLeft, 
  Loader2, 
  Image as ImageIcon,
  Download,
  FileDown,
  Sparkles,
  Play,
  Edit,
  RefreshCw,
} from 'lucide-react'
import { usePPTStore, PPTPage } from '@/stores/pptStore'

// 文件 URL 辅助函数
const getFileUrl = (path: string | undefined) => {
  if (!path) return ''
  // 如果已经是完整 URL，直接返回
  if (path.startsWith('http')) return path
  // 否则构建 banana-slides 文件 URL
  return `/api/banana/files/${path.replace(/^\//, '')}`
}

export const PPTSlidePreview: React.FC = () => {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const { 
    currentProject, 
    loadProject, 
    generateImages,
    generatePageImage,
    editPageImage,
    exportPPTX,
    exportPDF,
    exportEditablePPTX,
    isLoading, 
    error,
    clearError,
    pageGeneratingTasks,
    taskProgress,
  } = usePPTStore()

  const [selectedPageId, setSelectedPageId] = useState<string | null>(null)
  const [editPrompt, setEditPrompt] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  useEffect(() => {
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      loadProject(projectId)
    }
  }, [projectId, currentProject, loadProject])

  // 自动选择第一个页面
  useEffect(() => {
    if (currentProject?.pages.length && !selectedPageId) {
      setSelectedPageId(currentProject.pages[0].id)
    }
  }, [currentProject, selectedPageId])

  const handleGenerateImages = async () => {
    clearError()
    try {
      await generateImages()
    } catch (error) {
      console.error('生成图片失败:', error)
    }
  }

  const handleGeneratePageImage = async (pageId: string) => {
    clearError()
    try {
      await generatePageImage(pageId)
    } catch (error) {
      console.error('生成页面图片失败:', error)
    }
  }

  const handleEditImage = async (pageId: string) => {
    if (!editPrompt.trim()) return
    
    setIsEditing(true)
    clearError()
    
    try {
      await editPageImage(pageId, editPrompt)
      setEditPrompt('')
    } catch (error) {
      console.error('编辑图片失败:', error)
    } finally {
      setIsEditing(false)
    }
  }

  const handleExportPPTX = async () => {
    setIsExporting(true)
    try {
      await exportPPTX()
    } catch (error) {
      console.error('导出 PPTX 失败:', error)
    } finally {
      setIsExporting(false)
    }
  }

  const handleExportPDF = async () => {
    setIsExporting(true)
    try {
      await exportPDF()
    } catch (error) {
      console.error('导出 PDF 失败:', error)
    } finally {
      setIsExporting(false)
    }
  }

  const pages = currentProject?.pages || []
  const selectedPage = pages.find(p => p.id === selectedPageId)
  const hasImages = pages.some(p => p.generated_image_path)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex flex-col">
      {/* 导航栏 */}
      <nav className="h-16 bg-slate-800/40 backdrop-blur-xl border-b border-slate-700/50 flex items-center px-6 justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => projectId && navigate(`/ppt/project/${projectId}/detail`)}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">幻灯片预览</h1>
            <p className="text-sm text-slate-400">预览和编辑生成的幻灯片</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* 批量生成按钮 */}
          <button
            onClick={handleGenerateImages}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50 transition-all"
          >
            {isLoading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Sparkles size={18} />
            )}
            <span>{hasImages ? '重新生成全部' : '生成全部图片'}</span>
          </button>
          
          {/* 导出菜单 */}
          <div className="relative group">
            <button
              disabled={!hasImages || isExporting}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isExporting ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Download size={18} />
              )}
              <span>导出</span>
            </button>
            
            {/* 下拉菜单 */}
            <div className="absolute right-0 top-full mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                onClick={handleExportPPTX}
                disabled={isExporting}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-slate-300 hover:bg-slate-700/50 hover:text-white transition-colors first:rounded-t-lg"
              >
                <FileDown size={16} />
                <span>导出 PPTX</span>
              </button>
              <button
                onClick={handleExportPDF}
                disabled={isExporting}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-slate-300 hover:bg-slate-700/50 hover:text-white transition-colors"
              >
                <FileDown size={16} />
                <span>导出 PDF</span>
              </button>
              <button
                onClick={() => exportEditablePPTX()}
                disabled={isExporting}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-slate-300 hover:bg-slate-700/50 hover:text-white transition-colors last:rounded-b-lg"
              >
                <Edit size={16} />
                <span>导出可编辑 PPTX</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 错误提示 */}
      {error && (
        <div className="mx-6 mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 flex-shrink-0">
          {error}
        </div>
      )}

      {/* 任务进度 */}
      {taskProgress && (
        <div className="mx-6 mt-4 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-purple-300 text-sm">
              {taskProgress.current_step || '处理中...'}
            </span>
            <span className="text-purple-300 text-sm">
              {taskProgress.completed}/{taskProgress.total}
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all"
              style={{ width: `${(taskProgress.completed / taskProgress.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 主内容 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 缩略图侧边栏 */}
        <div className="w-64 bg-slate-800/30 border-r border-slate-700/50 overflow-y-auto p-4 flex-shrink-0">
          <h2 className="text-sm font-medium text-slate-400 mb-3">页面列表</h2>
          <div className="space-y-2">
            {pages.map((page, index) => {
              const isGenerating = pageGeneratingTasks[page.id]
              const isSelected = selectedPageId === page.id
              
              return (
                <button
                  key={page.id}
                  onClick={() => setSelectedPageId(page.id)}
                  className={`w-full text-left rounded-lg overflow-hidden transition-all ${
                    isSelected 
                      ? 'ring-2 ring-purple-500' 
                      : 'hover:ring-1 hover:ring-slate-600'
                  }`}
                >
                  <div className="aspect-video bg-slate-700/50 relative">
                    {page.generated_image_path ? (
                      <img
                        src={getFileUrl(page.generated_image_path)}
                        alt={page.outline_content?.title || `页面 ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-500">
                        <ImageIcon size={24} />
                      </div>
                    )}
                    
                    {isGenerating && (
                      <div className="absolute inset-0 bg-slate-900/70 flex items-center justify-center">
                        <Loader2 size={20} className="animate-spin text-purple-400" />
                      </div>
                    )}
                    
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-slate-900/90 to-transparent p-2">
                      <span className="text-xs text-white font-medium">{index + 1}</span>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* 主预览区 */}
        <div className="flex-1 p-6 overflow-y-auto">
          {selectedPage ? (
            <div className="max-w-4xl mx-auto">
              {/* 页面标题 */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">
                  {selectedPage.outline_content?.title || '未命名页面'}
                </h2>
                
                <button
                  onClick={() => handleGeneratePageImage(selectedPage.id)}
                  disabled={!!pageGeneratingTasks[selectedPage.id]}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded-lg transition-all disabled:opacity-50"
                >
                  {pageGeneratingTasks[selectedPage.id] ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>生成中</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw size={14} />
                      <span>{selectedPage.generated_image_path ? '重新生成' : '生成图片'}</span>
                    </>
                  )}
                </button>
              </div>
              
              {/* 图片预览 */}
              <div className="aspect-video bg-slate-800/50 border border-slate-700/50 rounded-lg overflow-hidden mb-4">
                {selectedPage.generated_image_path ? (
                  <img
                    src={getFileUrl(selectedPage.generated_image_path)}
                    alt={selectedPage.outline_content?.title || '幻灯片'}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-slate-500">
                    <ImageIcon size={48} className="mb-3" />
                    <p className="text-sm">尚未生成图片</p>
                    <button
                      onClick={() => handleGeneratePageImage(selectedPage.id)}
                      disabled={!!pageGeneratingTasks[selectedPage.id]}
                      className="mt-3 flex items-center gap-2 px-4 py-2 bg-purple-500/20 text-purple-300 rounded-lg hover:bg-purple-500/30 transition-all disabled:opacity-50"
                    >
                      {pageGeneratingTasks[selectedPage.id] ? (
                        <>
                          <Loader2 size={16} className="animate-spin" />
                          <span>生成中...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles size={16} />
                          <span>生成图片</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
              
              {/* 图片编辑 */}
              {selectedPage.generated_image_path && (
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="输入编辑指令，例如：把背景改成蓝色..."
                    value={editPrompt}
                    onChange={(e) => setEditPrompt(e.target.value)}
                    className="flex-1 px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
                  />
                  <button
                    onClick={() => handleEditImage(selectedPage.id)}
                    disabled={isEditing || !editPrompt.trim()}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50 transition-all"
                  >
                    {isEditing ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Edit size={18} />
                    )}
                    <span>编辑</span>
                  </button>
                </div>
              )}
              
              {/* 页面描述 */}
              {selectedPage.description_content?.text && (
                <div className="mt-6 p-4 bg-slate-800/30 border border-slate-700/50 rounded-lg">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">页面描述</h3>
                  <p className="text-sm text-slate-300 whitespace-pre-wrap">
                    {selectedPage.description_content.text}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              选择一个页面查看预览
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PPTSlidePreview

