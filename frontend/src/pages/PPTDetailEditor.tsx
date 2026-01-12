/**
 * Nexus PPT 详情编辑器
 * 基于 banana-slides DetailEditor.tsx 深度集成
 */
import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { 
  ArrowLeft, 
  ArrowRight, 
  Loader2, 
  FileEdit,
  Sparkles,
  RefreshCw,
} from 'lucide-react'
import { usePPTStore, PPTPage } from '@/stores/pptStore'

export const PPTDetailEditor: React.FC = () => {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const { 
    currentProject, 
    loadProject, 
    generateDescriptions,
    generatePageDescription,
    refineDescriptions,
    isLoading, 
    error,
    clearError,
    pageDescriptionGeneratingTasks,
    taskProgress,
  } = usePPTStore()

  const [refinePrompt, setRefinePrompt] = useState('')
  const [isRefining, setIsRefining] = useState(false)

  useEffect(() => {
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      loadProject(projectId)
    }
  }, [projectId, currentProject, loadProject])

  const handleGenerateDescriptions = async () => {
    clearError()
    try {
      await generateDescriptions()
    } catch (error) {
      console.error('生成描述失败:', error)
    }
  }

  const handleGeneratePageDescription = async (pageId: string) => {
    clearError()
    try {
      await generatePageDescription(pageId)
    } catch (error) {
      console.error('生成页面描述失败:', error)
    }
  }

  const handleRefine = async () => {
    if (!refinePrompt.trim()) return
    
    setIsRefining(true)
    clearError()
    
    try {
      await refineDescriptions(refinePrompt)
      setRefinePrompt('')
    } catch (error) {
      console.error('优化描述失败:', error)
    } finally {
      setIsRefining(false)
    }
  }

  const handleNext = () => {
    if (projectId) {
      navigate(`/ppt/project/${projectId}/preview`)
    }
  }

  const pages = currentProject?.pages || []
  const hasDescriptions = pages.some(p => p.description_content?.text)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900">
      {/* 导航栏 */}
      <nav className="h-16 bg-slate-800/40 backdrop-blur-xl border-b border-slate-700/50 flex items-center px-6 justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => projectId && navigate(`/ppt/project/${projectId}/outline`)}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-white">页面描述</h1>
            <p className="text-sm text-slate-400">编辑每页的详细内容</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* 步骤指示器 */}
          <div className="hidden md:flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 text-slate-400 rounded-full text-sm">
              <span>1. 大纲</span>
            </div>
            <ArrowRight size={16} className="text-slate-600" />
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/20 text-purple-300 rounded-full text-sm">
              <FileEdit size={14} />
              <span>2. 描述</span>
            </div>
            <ArrowRight size={16} className="text-slate-600" />
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 text-slate-400 rounded-full text-sm">
              <span>3. 预览</span>
            </div>
          </div>
          
          <button
            onClick={handleNext}
            disabled={!hasDescriptions}
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

        {/* 任务进度 */}
        {taskProgress && (
          <div className="mb-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
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

        {/* 批量生成按钮 */}
        {pages.length > 0 && !hasDescriptions && (
          <div className="mb-8 text-center">
            <button
              onClick={handleGenerateDescriptions}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-medium rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 transition-all shadow-lg shadow-purple-500/30"
            >
              {isLoading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  <span>生成描述中...</span>
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>AI 批量生成描述</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* AI 优化输入 */}
        {hasDescriptions && (
          <div className="mb-6 flex gap-3">
            <input
              type="text"
              placeholder="输入优化建议，例如：让内容更加简洁..."
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

        {/* 页面描述列表 */}
        <div className="space-y-4">
          {pages.map((page, index) => {
            const isGenerating = pageDescriptionGeneratingTasks[page.id]
            const hasDescription = !!page.description_content?.text
            
            return (
              <div
                key={page.id}
                className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-5 hover:border-purple-500/30 transition-all"
              >
                <div className="flex items-start gap-4">
                  <span className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-purple-500/20 text-purple-300 rounded-lg text-sm font-medium">
                    {index + 1}
                  </span>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-white font-medium">
                        {page.outline_content?.title || `页面 ${index + 1}`}
                      </h3>
                      
                      <button
                        onClick={() => handleGeneratePageDescription(page.id)}
                        disabled={isGenerating}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded-lg transition-all disabled:opacity-50"
                      >
                        {isGenerating ? (
                          <>
                            <Loader2 size={14} className="animate-spin" />
                            <span>生成中</span>
                          </>
                        ) : (
                          <>
                            <RefreshCw size={14} />
                            <span>{hasDescription ? '重新生成' : '生成描述'}</span>
                          </>
                        )}
                      </button>
                    </div>
                    
                    {hasDescription ? (
                      <div className="text-sm text-slate-300 whitespace-pre-wrap">
                        {page.description_content?.text}
                      </div>
                    ) : (
                      <div className="text-sm text-slate-500 italic">
                        {isGenerating ? '正在生成描述...' : '点击右侧按钮生成描述'}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </main>
    </div>
  )
}

export default PPTDetailEditor

