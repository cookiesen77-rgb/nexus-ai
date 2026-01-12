/**
 * AI 设计助手面板 - Lovart 风格
 * AI Designer Panel - Lovart Style
 */

import React, { useState, useRef, useEffect } from 'react'
import {
  Plus,
  SlidersHorizontal,
  Share2,
  Paperclip,
  AtSign,
  Globe,
  X,
  Send,
  Trash2,
  ChevronRight,
  Layers,
  Eye,
  Scissors,
  XCircle
} from 'lucide-react'
import { useDesignStore, ChatMessage } from '../../stores/designStore'
import { designChat, analyzeImage } from '../../services/designApi'
import type { CanvasElement } from './types'
import NexusLogo from '../ui/NexusLogo'

interface AiDesignerPanelProps {
  onClose: () => void
  onGenerateImage: (prompt: string, resolution: string, aspectRatio: string) => void
  onAddImageToCanvas?: (imageBase64: string) => void
  pendingImage?: {
    imageBase64: string
    elementId: string
  } | null
  onClearPendingImage?: () => void
  canvasElements?: CanvasElement[]
}

// 快捷建议
const QUICK_SUGGESTIONS = [
  { title: '产品海报', description: '帮我设计一张产品宣传海报', icon: '🎨' },
  { title: '社交媒体图', description: '创建一张适合 Instagram 的图片', icon: '📱' },
  { title: '品牌 Logo', description: '设计一个现代简约的 Logo', icon: '✨' },
  { title: '活动封面', description: '制作一张活动宣传封面图', icon: '🎉' }
]

const LLM_MODELS = [
  { id: 'grok-4.1', name: 'Grok 4.1' },
  { id: 'grok-4.1-mini', name: 'Grok 4.1 Mini' }
]

export function AiDesignerPanel({ 
  onClose, 
  onGenerateImage,
  onAddImageToCanvas,
  pendingImage, 
  onClearPendingImage,
  canvasElements = []
}: AiDesignerPanelProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // LLM 配置（Lovart：@ 切换模型，🌐 联网搜索）
  const [llmModel, setLlmModel] = useState('grok-4.1')
  const [enableWebSearch, setEnableWebSearch] = useState(false)
  const [showModelMenu, setShowModelMenu] = useState(false)
  const [showChatHistory, setShowChatHistory] = useState(false)
  
  // 图像分析状态
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analyzedElements, setAnalyzedElements] = useState<Array<{
    id: string
    type: string
    label: string
    bbox: number[]
    confidence: number
    content?: string
    description?: string
  }>>([])
  const [currentAnalysisImage, setCurrentAnalysisImage] = useState<string | null>(null)
  const [showAnalysisPanel, setShowAnalysisPanel] = useState(false)

  const {
    conversationHistory,
    isAiThinking,
    addMessage,
    clearConversation,
    setIsAiThinking,
    chatSessions,
    startNewChat,
    loadChatSession,
    deleteChatSession
  } = useDesignStore()
  
  // 当收到 pendingImage 时，自动触发分析
  useEffect(() => {
    if (pendingImage?.imageBase64) {
      setCurrentAnalysisImage(pendingImage.imageBase64)
      handleImageAnalysis(pendingImage.imageBase64)
      onClearPendingImage?.()
    }
  }, [pendingImage])
  
  // 分析图像
  const handleImageAnalysis = async (imageBase64: string) => {
    setIsAnalyzing(true)
    setShowAnalysisPanel(true)
    
    addMessage('user', '请分析这张图像，识别其中的可编辑元素。', undefined, undefined, imageBase64)
    
    try {
      const result = await analyzeImage({
        image_base64: imageBase64,
        analysis_type: 'full'
      })
      
      if (result.success && result.data) {
        setAnalyzedElements(result.data.elements || [])
        
        const elementsCount = result.data.elements?.length || 0
        let reply = `图像分析完成\n\n${result.data.overall_description}\n\n`
        reply += `识别到 ${elementsCount} 个可编辑元素`
        
        addMessage('assistant', reply, {
          type: 'analyze_complete',
          data: { elements_count: elementsCount }
        })
      } else {
        addMessage('assistant', result.error || '图像分析失败，请稍后重试。')
      }
    } catch (error) {
      console.error('Image analysis error:', error)
      addMessage('assistant', '图像分析过程中出现错误，请稍后重试。')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversationHistory])

  // 从文本中提取图片 URL
  const extractImageUrls = (text: string): string[] => {
    const markdownPattern = /!\[.*?\]\((https?:\/\/[^\s)]+)\)/g
    const directUrlPattern = /https?:\/\/[^\s)]+\.(jpg|jpeg|png|gif|webp)/gi
    
    const urls: string[] = []
    let match
    
    while ((match = markdownPattern.exec(text)) !== null) {
      urls.push(match[1])
    }
    
    while ((match = directUrlPattern.exec(text)) !== null) {
      if (!urls.includes(match[0])) {
        urls.push(match[0])
      }
    }
    
    return urls
  }
  
  // 下载图片并转为 base64
  const downloadImageAsBase64 = async (url: string): Promise<string | null> => {
    try {
      const response = await fetch(url)
      const blob = await response.blob()
      return new Promise((resolve) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result as string)
        reader.onerror = () => resolve(null)
        reader.readAsDataURL(blob)
      })
    } catch (error) {
      console.error('Failed to download image:', error)
      return null
    }
  }
  
  // 清理 AI 回复中的内部处理文本
  const cleanAiResponse = (text: string): string => {
    const patternsToRemove = [
      /正在为您生成\d+张图片[\s\S]*?(?=\n\n|$)/gi,
      /I generated images with the prompt:[\s\S]*?(?=\n\n|$)/gi,
      /正在为你生成图像\.{3}/gi,
      /正在生成[\s\S]*?(?=\n|$)/gi,
      /Generating[\s\S]*?(?=\n|$)/gi,
      /Processing[\s\S]*?(?=\n|$)/gi,
      /!\[image\]\([^)]+\)/g,
      /https?:\/\/[^\s)]+\.(jpg|jpeg|png|gif|webp)[^\s]*/gi,
    ]
    
    let cleaned = text
    patternsToRemove.forEach(pattern => {
      cleaned = cleaned.replace(pattern, '')
    })
    
    cleaned = cleaned
      .replace(/\n{3,}/g, '\n\n')
      .replace(/^\s+|\s+$/g, '')
    
    return cleaned || '已完成'
  }

  const handleAttachClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    // reset value so selecting the same file twice still triggers change
    e.target.value = ''
    if (!file) return

    // Image: analyze directly (Lovart: 上传参考图)
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = () => {
        const base64 = reader.result as string
        setCurrentAnalysisImage(base64)
        handleImageAnalysis(base64)
      }
      reader.readAsDataURL(file)
      return
    }

    // Text-like docs: append into input for LLM to read
    try {
      const text = await file.text()
      const clipped = text.length > 8000 ? `${text.slice(0, 8000)}\n\n（已截断，完整内容请拆分上传）` : text
      setInput((prev) => {
        const prefix = prev.trim().length ? `${prev.trim()}\n\n` : ''
        return `${prefix}【文档：${file.name}】\n${clipped}`
      })
      inputRef.current?.focus()
    } catch {
      addMessage('assistant', '暂不支持解析该文件格式，请上传图片或文本文件。')
    }
  }

  const handleShare = async () => {
    try {
      const content = conversationHistory
        .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
        .join('\n\n')
      await navigator.clipboard.writeText(content)
      addMessage('assistant', '已复制当前对话内容')
    } catch {
      addMessage('assistant', '复制失败，请手动选择文本复制。')
    }
  }

  // 发送消息
  const handleSend = async () => {
    if (!input.trim() || isAiThinking) return

    const userMessage = input.trim()
    setInput('')

    addMessage('user', userMessage)
    setIsAiThinking(true)

    try {
      const historyForApi = conversationHistory.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const result = await designChat({
        message: userMessage,
        conversation_history: historyForApi,
        model: llmModel,
        enable_web_search: enableWebSearch
      })

      if (result.success && result.data) {
        const { reply, action, optimized_prompt } = result.data

        const imageUrls = extractImageUrls(reply)
        
        if (imageUrls.length > 0) {
          const cleanReply = cleanAiResponse(reply)
          
          if (cleanReply && cleanReply !== '已完成') {
            addMessage('assistant', cleanReply)
          }
          
          const downloadedImages: string[] = []
          for (const url of imageUrls) {
            const base64 = await downloadImageAsBase64(url)
            if (base64) {
              downloadedImages.push(base64)
              if (onAddImageToCanvas) {
                onAddImageToCanvas(base64)
              }
            }
          }
          
          if (downloadedImages.length > 0) {
            addMessage('assistant', `为你生成了 ${downloadedImages.length} 张图像`, {
              type: 'images_generated',
              data: { count: downloadedImages.length }
            }, undefined, downloadedImages[0])
          }
        } else {
          const cleanedReply = cleanAiResponse(reply)
          if (cleanedReply) {
            addMessage('assistant', cleanedReply, action ? {
              type: action.type,
              data: action.data as Record<string, unknown>
            } : undefined, optimized_prompt)
          }

          if (action?.type === 'generate_image' && optimized_prompt) {
            const resolution = (action.data?.resolution as string) || '1K'
            const aspectRatio = (action.data?.aspect_ratio as string) || '1:1'
            
            setTimeout(() => {
              onGenerateImage(optimized_prompt, resolution, aspectRatio)
            }, 500)
          }
        }
      } else {
        addMessage('assistant', result.error || '抱歉，我遇到了一些问题，请稍后再试。')
      }
    } catch (error) {
      console.error('Chat error:', error)
      addMessage('assistant', '抱歉，网络连接出现问题，请检查后再试。')
    } finally {
      setIsAiThinking(false)
    }
  }

  const handleSuggestionClick = (description: string) => {
    setInput(description)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 渲染消息
  const renderMessage = (message: ChatMessage, index: number) => {
    const isUser = message.role === 'user'

    return (
      <div
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 lovart-fade-in`}
        style={{ animationDelay: `${index * 0.05}s` }}
      >
        <div
          className={`max-w-[85%] px-4 py-3 ${
            isUser
              ? 'lovart-message-user'
              : 'lovart-message-ai'
          }`}
        >
          {/* 图像缩略图 */}
          {message.imageBase64 && (
            <div className="mb-3 lovart-image-preview">
              <img 
                src={message.imageBase64} 
                alt="图像" 
                className="w-full h-auto"
              />
            </div>
          )}
          
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
          
          {/* 图像生成指示 */}
          {message.action?.type === 'generate_image' && (
            <div className="mt-3 pt-3 border-t border-white/20">
              <div className="lovart-progress">
                <div className="lovart-progress-bar" />
              </div>
            </div>
          )}
          
          {/* 分析完成 */}
          {message.action?.type === 'analyze_complete' && (
            <button
              onClick={() => setShowAnalysisPanel(true)}
              className="mt-3 pt-3 border-t border-current/20 flex items-center gap-2 text-xs opacity-80 hover:opacity-100 transition-opacity"
            >
              <Layers size={14} />
              <span>查看元素详情</span>
              <ChevronRight size={12} />
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex flex-col h-full lovart-ai-panel lovart-slide-in">
      {/* 头部 */}
      <div className="p-4 border-b border-[var(--border)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[var(--muted)] flex items-center justify-center">
            <NexusLogo size={28} />
          </div>
          <div>
            <h2 className="font-semibold text-[var(--foreground)]">AI 设计助手</h2>
            <p className="text-[10px] text-[var(--muted-foreground)]">{llmModel}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              startNewChat()
              setShowChatHistory(false)
              setCurrentAnalysisImage(null)
              setAnalyzedElements([])
              setShowAnalysisPanel(false)
              onClearPendingImage?.()
            }}
            className="lovart-toolbar-btn"
            title="新建对话（更换画布，保留历史）"
          >
            <Plus size={16} />
          </button>
          <button
            onClick={() => setShowChatHistory(true)}
            className="lovart-toolbar-btn"
            title="历史对话"
          >
            <SlidersHorizontal size={16} />
          </button>
          <button
            onClick={handleShare}
            className="lovart-toolbar-btn"
            title="分享 / 复制内容"
          >
            <Share2 size={16} />
          </button>
          {conversationHistory.length > 0 && (
            <button
              onClick={clearConversation}
              className="lovart-toolbar-btn"
              title="清空对话"
            >
              <Trash2 size={16} />
            </button>
          )}
          <button onClick={onClose} className="lovart-toolbar-btn">
            <X size={16} />
          </button>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {conversationHistory.length === 0 ? (
          <div className="h-full flex flex-col">
            {/* 欢迎信息 */}
            <div className="mb-8 text-center">
              <div className="w-20 h-20 mx-auto rounded-3xl bg-[var(--muted)] flex items-center justify-center mb-4">
                <NexusLogo size={52} />
              </div>
              <h2 className="text-xl font-bold text-[var(--foreground)] mb-2">
                AI 设计助手
              </h2>
              <p className="text-sm text-[var(--muted-foreground)] max-w-[280px] mx-auto">
                告诉我你的设计想法，我会帮你优化创意并生成专业图像
              </p>
            </div>

            {/* 快捷建议 */}
            <div className="grid grid-cols-2 gap-3">
              {QUICK_SUGGESTIONS.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion.description)}
                  className="lovart-suggestion text-left"
                >
                  <span className="text-2xl mb-2 block">{suggestion.icon}</span>
                  <p className="text-sm font-medium text-[var(--foreground)]">{suggestion.title}</p>
                  <p className="text-xs text-[var(--muted-foreground)] mt-1 line-clamp-2">{suggestion.description}</p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div>
            {conversationHistory.map((msg, idx) => renderMessage(msg, idx))}
            
            {/* 思考中 */}
            {isAiThinking && (
              <div className="flex justify-start mb-4 lovart-fade-in">
                <div className="lovart-typing">
                  <div className="lovart-typing-dot" />
                  <div className="lovart-typing-dot" />
                  <div className="lovart-typing-dot" />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="p-4 shrink-0">
        {/* 附件上传（📎） */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*,.txt,.md,.json,.pdf"
          onChange={handleFileChange}
        />

        {/* 分析图像预览 */}
        {currentAnalysisImage && (
          <div className="mb-3 p-3 bg-[var(--muted)] rounded-xl flex items-center gap-3">
            <img 
              src={currentAnalysisImage} 
              alt="分析中" 
              className="w-12 h-12 object-cover rounded-lg"
            />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--foreground)]">
                {isAnalyzing ? '正在分析...' : '分析完成'}
              </p>
              <p className="text-[10px] text-[var(--muted-foreground)]">
                {analyzedElements.length > 0 ? `${analyzedElements.length} 个元素` : '点击图像分析'}
              </p>
            </div>
            <button
              onClick={() => {
                setCurrentAnalysisImage(null)
                setAnalyzedElements([])
                setShowAnalysisPanel(false)
              }}
              className="p-1.5 hover:bg-[var(--background)] rounded-lg text-[var(--muted-foreground)]"
            >
              <XCircle size={16} />
            </button>
          </div>
        )}
        
        <div className="lovart-input-container">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="请输入你的设计需求"
            className="w-full bg-transparent outline-none resize-none text-sm py-2 min-h-[44px] max-h-[140px]"
            disabled={isAiThinking || isAnalyzing}
            rows={2}
          />

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleAttachClick}
                className="w-9 h-9 rounded-2xl hover:bg-[var(--muted)] transition flex items-center justify-center text-[var(--muted-foreground)]"
                title="上传参考图 / 阅读文档"
                disabled={isAiThinking || isAnalyzing}
              >
                <Paperclip size={18} />
              </button>

              {/* @ 模型切换 */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowModelMenu((v) => !v)}
                  className="w-9 h-9 rounded-2xl hover:bg-[var(--muted)] transition flex items-center justify-center text-[var(--muted-foreground)]"
                  title="切换模型"
                >
                  <AtSign size={18} />
                </button>
                {showModelMenu && (
                  <div className="absolute bottom-full mb-2 left-0 w-[240px] rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-xl overflow-hidden z-10">
                    {LLM_MODELS.map((m) => (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          setLlmModel(m.id)
                          setShowModelMenu(false)
                        }}
                        className={`w-full px-4 py-3 text-left text-sm hover:bg-[var(--muted)] transition ${
                          m.id === llmModel ? 'font-medium' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--foreground)]">{m.name}</span>
                          {m.id === llmModel && <span className="text-xs text-[var(--muted-foreground)]">已选</span>}
                        </div>
                        <div className="text-[10px] text-[var(--muted-foreground)] mt-0.5">{m.id}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* 🌐 联网搜索 */}
              <button
                type="button"
                onClick={() => setEnableWebSearch((v) => !v)}
                className={`w-9 h-9 rounded-2xl transition flex items-center justify-center ${
                  enableWebSearch ? 'bg-primary/10 text-primary' : 'hover:bg-[var(--muted)] text-[var(--muted-foreground)]'
                }`}
                title="联网搜索"
              >
                <Globe size={18} />
              </button>
            </div>

            <button
              onClick={handleSend}
              disabled={!input.trim() || isAiThinking || isAnalyzing}
              className="lovart-send-btn shrink-0"
              title="发送"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
        <p className="mt-2 text-[10px] text-[var(--muted-foreground)] text-center">
          Enter 发送 · 双击画布图像分析
        </p>
      </div>
      
      {/* 历史对话面板（调节按钮） */}
      {showChatHistory && (
        <div className="absolute inset-0 z-20 bg-[var(--card)] flex flex-col lovart-slide-in">
          <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-2xl bg-[var(--muted)] flex items-center justify-center">
                <SlidersHorizontal size={16} className="text-[var(--muted-foreground)]" />
              </div>
              <div>
                <div className="font-semibold text-[var(--foreground)]">历史对话</div>
                <div className="text-[10px] text-[var(--muted-foreground)]">
                  新建对话会更换画布，但历史会保留在这里
                </div>
              </div>
            </div>
            <button onClick={() => setShowChatHistory(false)} className="lovart-toolbar-btn" title="关闭">
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {chatSessions.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-[var(--muted-foreground)]">
                暂无历史对话
              </div>
            ) : (
              chatSessions.map((s) => (
                <div
                  key={s.id}
                  className="p-3 rounded-2xl border border-[var(--border)] hover:bg-[var(--muted)]/40 transition"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-[var(--foreground)] truncate">{s.title}</div>
                      <div className="text-[10px] text-[var(--muted-foreground)] mt-1">
                        {new Date(s.createdAt).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className="px-3 py-2 rounded-xl bg-[var(--muted)] hover:bg-[var(--muted)]/80 text-xs text-[var(--foreground)] transition"
                        onClick={() => {
                          loadChatSession(s.id)
                          setShowChatHistory(false)
                        }}
                      >
                        打开
                      </button>
                      <button
                        className="px-3 py-2 rounded-xl bg-destructive/10 hover:bg-destructive/15 text-xs text-destructive transition"
                        onClick={() => deleteChatSession(s.id)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* 元素分析面板 */}
      {showAnalysisPanel && analyzedElements.length > 0 && (
        <div className="absolute inset-0 bg-[var(--card)] z-10 flex flex-col lovart-slide-in">
          <div className="p-4 border-b border-[var(--border)] flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                <Layers size={18} className="text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-[var(--foreground)]">元素分析</h3>
                <p className="text-[10px] text-[var(--muted-foreground)]">
                  {analyzedElements.length} 个可编辑元素
                </p>
              </div>
            </div>
            <button onClick={() => setShowAnalysisPanel(false)} className="lovart-toolbar-btn">
              <X size={16} />
            </button>
          </div>
          
          {/* 图像预览 */}
          {currentAnalysisImage && (
            <div className="p-4 border-b border-[var(--border)]">
              <div className="relative rounded-xl overflow-hidden bg-[var(--muted)]">
                <img 
                  src={currentAnalysisImage} 
                  alt="分析图像" 
                  className="w-full h-auto"
                />
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  {analyzedElements.map((el, index) => {
                    const colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ef4444']
                    const color = colors[index % colors.length]
                    return (
                      <rect
                        key={el.id}
                        x={`${el.bbox[0] * 100}%`}
                        y={`${el.bbox[1] * 100}%`}
                        width={`${el.bbox[2] * 100}%`}
                        height={`${el.bbox[3] * 100}%`}
                        fill="none"
                        stroke={color}
                        strokeWidth="2"
                        strokeDasharray="4,2"
                        opacity="0.8"
                      />
                    )
                  })}
                </svg>
              </div>
            </div>
          )}
          
          {/* 元素列表 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {analyzedElements.map((el, index) => {
              const colors = ['bg-amber-500', 'bg-emerald-500', 'bg-blue-500', 'bg-violet-500', 'bg-red-500']
              const colorClass = colors[index % colors.length]
              
              return (
                <div
                  key={el.id}
                  className="p-3 rounded-xl bg-[var(--muted)] hover:bg-[var(--muted)]/80 border border-transparent hover:border-[var(--border)] transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${colorClass}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[var(--foreground)]">{el.label}</p>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        {el.type} · {Math.round(el.confidence * 100)}%
                      </p>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="lovart-toolbar-btn !w-8 !h-8" title="查看">
                        <Eye size={14} />
                      </button>
                      <button className="lovart-toolbar-btn !w-8 !h-8" title="编辑">
                        <Scissors size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          
          {/* 底部 */}
          <div className="p-4 border-t border-[var(--border)] shrink-0">
            <button
              onClick={() => setShowAnalysisPanel(false)}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--primary)] to-[var(--primary-hover)] text-white text-sm font-medium shadow-lg hover:shadow-xl transition-all"
            >
              返回对话
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
