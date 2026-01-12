/**
 * Nexus PPT 大纲编辑器
 * 基于 banana-slides OutlineEditor.tsx 深度集成
 */
import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { 
  ArrowLeft, 
  ArrowRight, 
  Loader2, 
  FileText,
  Plus,
  Trash2,
  Sparkles,
  GripVertical,
  RefreshCw,
} from 'lucide-react'
import { usePPTStore, PPTPage } from '@/stores/pptStore'

export const PPTOutlineEditor: React.FC = () => {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const { 
    currentProject, 
    loadProject, 
    generateOutline,
    updateOutline,
    refineOutline,
    isLoading, 
    error,
    clearError,
  } = usePPTStore()

  const [refinePrompt, setRefinePrompt] = useState('')
  const [isRefining, setIsRefining] = useState(false)

  useEffect(() => {
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      loadProject(projectId)
    }
  }, [projectId, currentProject, loadProject])

  const handleGenerateOutline = async () => {
    clearError()
    try {
      await generateOutline()
    } catch (error) {
      console.error('生成大纲失败:', error)
    }
  }

  const handleRefine = async () => {
    if (!refinePrompt.trim()) return
    
    setIsRefining(true)
    clearError()
    
    try {
      await refineOutline(refinePrompt)
      setRefinePrompt('')
    } catch (error) {
      console.error('优化大纲失败:', error)
    } finally {
      setIsRefining(false)
    }
  }

  const handleNext = () => {
    if (projectId) {
      navigate(`/ppt/project/${projectId}/detail`)
    }
  }

  const pages = currentProject?.pages || []

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900">
      {/* 导航栏 */}
      <nav className="h-16 bg-slate-800/40 backdrop-blur-xl border-b border-slate-700/50 flex items-center px-6 justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/ppt')}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">大纲编辑</h1>
            <p className="text-sm text-slate-400">编辑和调整 PPT 大纲结构</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* 步骤指示器 */}
          <div className="hidden md:flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/20 text-purple-300 rounded-full text-sm">
              <FileText size={14} />
              <span>1. 大纲</span>
            </div>
            <ArrowRight size={16} className="text-slate-600" />
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 text-slate-400 rounded-full text-sm">
              <span>2. 描述</span>
            </div>
            <ArrowRight size={16} className="text-slate-600" />
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 text-slate-400 rounded-full text-sm">
              <span>3. 预览</span>
            </div>
          </div>
          
          <button
            onClick={handleNext}
            disabled={pages.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <span>下一步</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </nav>

      {/* 主内容 */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* 生成大纲按钮 */}
        {pages.length === 0 && (
          <div className="mb-8 text-center">
            <button
              onClick={handleGenerateOutline}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-medium rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 transition-all shadow-lg shadow-purple-500/30"
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  <span>生成大纲中...</span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>AI 生成大纲</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* AI 优化输入 */}
        {pages.length > 0 && (
          <div className="mb-6 flex gap-3">
            <input
              type="text"
              placeholder="输入优化建议，例如：增加关于机器学习的内容..."
              value={refinePrompt}
              onChange={(e) => setRefinePrompt(e.target.value)}
              className="flex-1 px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
            />
            <button
              onClick={handleRefine}
              disabled={isRefining || !refinePrompt.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50 transition-all"
            >
              {isRefining ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <RefreshCw size={18} />
              )}
              <span>AI 优化</span>
            </button>
          </div>
        )}

        {/* 大纲列表 */}
        <div className="space-y-3">
          {pages.map((page, index) => (
            <div
              key={page.id}
              className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 hover:border-purple-500/30 transition-all group"
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 flex items-center gap-2">
                  <GripVertical size={18} className="text-slate-600 cursor-grab" />
                  <span className="w-8 h-8 flex items-center justify-center bg-purple-500/20 text-purple-300 rounded-lg text-sm font-medium">
                    {index + 1}
                  </span>
                </div>
                
                <div className="flex-1 min-w-0">
                  <h3 className="text-white font-medium mb-2">
                    {page.outline_content?.title || `页面 ${index + 1}`}
                  </h3>
                  
                  {page.outline_content?.points && page.outline_content.points.length > 0 && (
                    <ul className="space-y-1">
                      {page.outline_content.points.map((point, i) => (
                        <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-2 flex-shrink-0" />
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                
                <button className="p-2 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* 添加页面按钮 */}
        {pages.length > 0 && (
          <button className="w-full mt-4 py-3 border-2 border-dashed border-slate-700 rounded-lg text-slate-500 hover:border-purple-500/50 hover:text-purple-400 transition-all flex items-center justify-center gap-2">
            <Plus size={20} />
            <span>添加页面</span>
          </button>
        )}
      </main>
    </div>
  )
}

export default PPTOutlineEditor

