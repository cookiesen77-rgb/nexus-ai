/**
 * Nexus AI PPT 创建页面
 * 严格按照设计图一比一复刻
 */
import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { useLegacyPPTStore, usePPTStore } from '@/stores/pptStore'

type CreationType = 'idea' | 'outline' | 'description'

// 预设风格选项
const STYLE_OPTIONS = [
  { id: 'professional', name: '专业商务', description: '适合正式场合的商务演示' },
  { id: 'creative', name: '创意设计', description: '适合创意展示和设计提案' },
  { id: 'minimal', name: '简约清新', description: '干净简洁的现代风格' },
  { id: 'tech', name: '科技未来', description: '适合科技产品和技术演示' },
  { id: 'education', name: '教育培训', description: '适合教学课件和培训材料' },
]

// 选项卡配置
const tabConfig: Record<CreationType, { label: string; placeholder: string }> = {
  idea: { 
    label: '一句话生成', 
    placeholder: '输入主题，如：人工智能的发展趋势' 
  },
  outline: { 
    label: '大纲生成', 
    placeholder: '输入您的PPT大纲，每行一个要点' 
  },
  description: { 
    label: '文档生成', 
    placeholder: '粘贴您的文档内容，AI将自动生成PPT' 
  },
}

import NexusLogo from '@/components/ui/NexusLogo'
import NexusLogoIcon from '@/components/ui/NexusLogoIcon'

export const PPTCreator = () => {
  const navigate = useNavigate()
  const { createProject, isLoading: isGenerating } = usePPTStore()
  
  // 包装 createPPT 以适配旧的调用方式
  const createPPT = async (params: { type: string; content: string; style: string }) => {
    const creationType = params.type as 'idea' | 'outline' | 'description';
    await createProject(creationType, params.content, params.style);
  }
  
  const [activeTab, setActiveTab] = useState<CreationType>('idea')
  const [content, setContent] = useState('')
  const [selectedStyle, setSelectedStyle] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = async () => {
    if (!content.trim()) return
    
    setIsLoading(true)
    try {
      await createPPT({
        type: activeTab,
        content: content.trim(),
        style: selectedStyle || 'professional',
      })
    } catch (error) {
      console.error('PPT creation failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleBack = () => {
    navigate(-1)
  }

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex flex-col">
      {/* 顶部导航栏 - 白色背景 */}
      <header className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-center relative">
        {/* 返回按钮 */}
        <button
          onClick={handleBack}
          className="absolute left-6 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={22} strokeWidth={2} />
        </button>
        
        {/* 标题 */}
        <h1 className="text-lg font-medium text-gray-800">创建演示文稿</h1>
      </header>

      {/* 主内容区 - 居中布局 */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Logo - 只显示图标部分 */}
          <div className="flex flex-col items-center">
            <div className="mb-4">
              <NexusLogoIcon size={150} />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 tracking-tight">创建演示文稿</h2>
          </div>

          {/* 选项卡 - 浅黄/米色背景，圆角药丸 */}
          <div className="flex bg-[#F5F0E6] rounded-full p-1.5">
            {(Object.keys(tabConfig) as CreationType[]).map((type) => (
              <button
                key={type}
                onClick={() => setActiveTab(type)}
                className={`flex-1 py-2.5 px-4 rounded-full text-sm font-medium transition-all duration-200 focus:outline-none ${
                  activeTab === type
                    ? 'bg-white text-gray-800 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-white/50'
                }`}
              >
                {tabConfig[type].label}
              </button>
            ))}
          </div>

          {/* 输入区域 */}
          <div className="space-y-3">
            {/* 主题输入框 */}
            {activeTab === 'idea' ? (
              <input
                type="text"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="输入主题"
                className="w-full px-5 py-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 bg-white text-gray-700 placeholder:text-gray-400 text-base"
              />
            ) : (
              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={tabConfig[activeTab].placeholder}
                rows={5}
                className="w-full px-5 py-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 bg-white text-gray-700 placeholder:text-gray-400 resize-none text-base"
              />
            )}
            
            {/* 风格选择下拉框 */}
            <select
              value={selectedStyle}
              onChange={(e) => setSelectedStyle(e.target.value)}
              className="w-full px-5 py-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 bg-white text-gray-400 appearance-none cursor-pointer text-base"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239CA3AF'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 1rem center',
                backgroundSize: '1.25rem',
              }}
            >
              <option value="" disabled>选择风格</option>
              {STYLE_OPTIONS.map((style) => (
                <option key={style.id} value={style.id} className="text-gray-700">
                  {style.name}
                </option>
              ))}
            </select>
          </div>

          {/* 开始生成按钮 - 蓝紫色（偏蓝的淡紫色），按照设计图 */}
          <button
            onClick={handleSubmit}
            disabled={!content.trim() || isLoading}
            className="w-full py-4 rounded-full bg-[#8BA4D0] hover:bg-[#7A94C0] active:bg-[#6A84B0] text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#8BA4D0] focus:ring-offset-2 transition-all duration-200 flex items-center justify-center gap-2 text-base"
          >
            {isLoading ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                <span>创建中...</span>
              </>
            ) : (
              <span>开始生成</span>
            )}
          </button>
        </div>
      </main>
    </div>
  )
}

// 同时保留默认导出以兼容其他引用
export default PPTCreator
