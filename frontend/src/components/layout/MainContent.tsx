import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  ChevronDown, Bell, Plus, Mic, Send,
  Presentation, Globe, Code2, BarChart3,
  Paperclip, Sparkles, X, Loader2, ArrowLeft
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'
import { useChatStore } from '@/stores/chatStore'
import { useLegacyPPTStore } from '@/stores/pptStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import NexusLogo from '@/components/ui/NexusLogo'
import MessageItem from '@/components/chat/MessageItem'
import { ScrollArea } from '@/components/ui/scroll-area'
import { PPTCreationWizard, PPTPanel } from '@/components/ppt'
import { PPTEditorPage } from '@/pages/ppt'

// 快捷操作按钮配置 - 根据设计图更新
const quickActions = [
  { icon: Presentation, label: '制作幻灯片', color: 'bg-amber-100 text-amber-600' },
  { icon: Globe, label: '创建网站', color: 'bg-orange-100 text-orange-600' },
  { icon: Code2, label: '编写代码', color: 'bg-blue-100 text-blue-600' },
  { icon: BarChart3, label: '数据分析', color: 'bg-green-100 text-green-600' },
]

// 视图类型
type ViewType = 'chat' | 'ppt'

const MainContent = () => {
  const navigate = useNavigate()
  const { connectionStatus, agentIsThinking } = useAppStore()
  const { messages, streamingContent } = useChatStore()
  const { 
    isWizardOpen, 
    setIsWizardOpen, 
    currentPresentation,
    clearCurrentPresentation 
  } = useLegacyPPTStore()
  const { sendMessage } = useWebSocket()
  const [input, setInput] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [activeView, setActiveView] = useState<ViewType>('chat')
  const [isPPTEditorOpen, setIsPPTEditorOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 当有新的 PPT 时，自动切换到 PPT 视图
  useEffect(() => {
    if (currentPresentation) {
      setActiveView('ppt')
    }
  }, [currentPresentation])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('[handleFileSelect] Called, files:', e.target.files)
    const files = e.target.files
    if (files && files.length > 0) {
      console.log('[handleFileSelect] Adding files:', Array.from(files).map(f => f.name))
      setSelectedFiles(prev => {
        const newFiles = [...prev, ...Array.from(files)]
        console.log('[handleFileSelect] New selectedFiles:', newFiles.map(f => f.name))
        return newFiles
      })
    }
    // 延迟清空 value，确保 React 状态更新完成
    setTimeout(() => {
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }, 100)
  }

  // Remove selected file
  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages, streamingContent])

  // 将文件转换为 base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = (error) => reject(error)
    })
  }

  const handleSend = async () => {
    const hasInput = input.trim().length > 0
    const hasFiles = selectedFiles.length > 0
    
    if ((!hasInput && !hasFiles) || agentIsThinking) return

    try {
      const content = input.trim()
      const attachments: Array<{
        id: string
        name: string
        type: 'image' | 'document' | 'other'
        mimeType: string
        size: number
        previewUrl?: string
        data?: string
      }> = []

      // 处理选中的文件，构建附件列表
      if (hasFiles) {
        for (const file of selectedFiles) {
          const attachment: typeof attachments[0] = {
            id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            name: file.name,
            type: file.type.startsWith('image/') ? 'image' : 
                  file.type.includes('pdf') || file.type.includes('document') || file.type.includes('text') ? 'document' : 'other',
            mimeType: file.type,
            size: file.size,
          }

          if (file.type.startsWith('image/')) {
            const base64 = await fileToBase64(file)
            attachment.previewUrl = base64
            attachment.data = base64
          } else {
            try {
              const text = await file.text()
              attachment.data = text
            } catch {
              attachment.data = `[无法读取文件内容: ${file.name}]`
            }
          }

          attachments.push(attachment)
        }
      }

      // 发送消息，附件数据单独传递，不混入消息内容
      sendMessage({ 
        role: 'user', 
        content: content || (attachments.length > 0 ? '请分析这些文件' : ''),
        attachments: attachments.map(a => ({
          id: a.id,
          name: a.name,
          type: a.type,
          mimeType: a.mimeType,
          size: a.size,
          previewUrl: a.previewUrl
        })),
        has_image: attachments.some(a => a.type === 'image'),
        file_data: attachments.map(a => ({
          name: a.name,
          type: a.type,
          mimeType: a.mimeType,
          data: a.data
        }))
      })
      
      setInput('')
      setSelectedFiles([])
    } catch (error) {
      console.error('发送消息失败:', error)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickAction = (label: string) => {
    if (label === '制作幻灯片') {
      // 导航到 PPT 创建器页面
      navigate('/ppt')
      return
    }
    
    setInput(`帮我${label}`)
    textareaRef.current?.focus()
  }

  // 返回聊天视图
  const handleBackToChat = () => {
    setActiveView('chat')
    clearCurrentPresentation()
  }

  // Only count non-system messages for determining if we should show chat view
  const hasUserOrAgentMessages = messages.some(m => m.role === 'user' || m.role === 'agent') || streamingContent

  // 如果当前是 PPT 视图，显示 PPTPanel
  if (activeView === 'ppt' && currentPresentation) {
    return (
      <main className="flex-1 flex flex-col bg-[var(--nexus-chat-bg)] overflow-hidden">
        {/* PPT 视图头部 */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-nexus-border bg-white">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBackToChat}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-nexus-text-muted hover:bg-nexus-sidebar rounded-lg transition-colors"
            >
              <ArrowLeft size={16} />
              返回
            </button>
            <div className="h-6 w-px bg-nexus-border" />
            <div className="flex items-center gap-2">
              <Presentation className="w-5 h-5 text-nexus-primary" />
              <span className="font-semibold text-nexus-text">
                {currentPresentation.title || 'PPT 预览'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              <span>{connectionStatus === 'connected' ? '已连接' : '连接中...'}</span>
            </div>
            
            <button className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-medium text-sm">
              U
            </button>
          </div>
        </header>

        {/* PPT 面板 */}
        <div className="flex-1 overflow-hidden">
          <PPTPanel />
        </div>
        
        {/* PPT 创建向导 */}
        <PPTCreationWizard 
          isOpen={isWizardOpen} 
          onClose={() => setIsWizardOpen(false)} 
        />
        
        {/* PPT 编辑器页面 */}
        {isPPTEditorOpen && (
          <PPTEditorPage
            onClose={() => setIsPPTEditorOpen(false)}
          />
        )}
      </main>
    )
  }

  return (
    <main className="flex-1 flex flex-col bg-[var(--nexus-chat-bg)] overflow-hidden">
      {/* Hidden file input (shared) - using sr-only instead of hidden to allow label trigger */}
      <input
        type="file"
        id="nexus-file-input"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        className="sr-only"
        accept="image/*,.pdf,.doc,.docx,.txt,.md,.json,.csv,.xlsx,.xls"
      />
      
      {/* Top Bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-transparent">
        <button className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted transition-colors">
          <span className="text-sm font-medium text-foreground">Nexus 1.0</span>
          <ChevronDown size={16} className="text-muted-foreground" />
        </button>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            <span>{connectionStatus === 'connected' ? '已连接' : '连接中...'}</span>
          </div>
          
          <button className="p-2 hover:bg-muted rounded-lg transition-colors">
            <Bell size={18} className="text-muted-foreground" />
          </button>
          
          <button className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-medium text-sm">
            U
          </button>
        </div>
      </header>

      {/* Content Area */}
      {!hasUserOrAgentMessages ? (
        /* Welcome Screen */
        <div className="flex-1 flex flex-col items-center justify-center px-6">
          {/* Main Title */}
          <h1 className="text-4xl font-semibold text-foreground mb-12">
            我能为你做什么？
          </h1>

          {/* Input Box */}
          <div className="w-full max-w-2xl">
            {/* Selected files display */}
            {selectedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {selectedFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-lg text-sm"
                  >
                    <Paperclip size={14} className="text-muted-foreground" />
                    <span className="text-foreground truncate max-w-[150px]">{file.name}</span>
                    <button
                      onClick={() => removeFile(index)}
                      className="p-0.5 hover:bg-background rounded"
                    >
                      <X size={14} className="text-muted-foreground" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="bg-card rounded-2xl border border-border shadow-lg overflow-hidden">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="分配一个任务或提问任何问题"
                rows={1}
                className="w-full px-5 pt-5 pb-2 bg-transparent text-foreground placeholder:text-muted-foreground resize-none focus:outline-none text-base"
                disabled={agentIsThinking}
              />
              
              <div className="px-4 pb-4 flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="nexus-icon-btn"
                    title="上传文件"
                  >
                    <Plus size={20} />
                  </button>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="nexus-icon-btn"
                    title="添加附件"
                  >
                    <Paperclip size={20} />
                  </button>
                  <button className="nexus-icon-btn" title="语音输入">
                    <Mic size={20} />
                  </button>
                  <button 
                    onClick={handleSend}
                    disabled={(!input.trim() && selectedFiles.length === 0) || agentIsThinking}
                    className="nexus-send-btn"
                  >
                    <Send size={18} />
                  </button>
                </div>
              </div>
            </div>

            {/* Tool Connection Hint */}
            <button className="flex items-center gap-3 w-full mt-4 px-5 py-4 rounded-2xl bg-card border border-border hover:shadow-md transition-all">
              <Sparkles size={20} className="text-primary" />
              <span className="text-sm font-medium text-foreground">将您的工具连接到 Nexus</span>
              <div className="flex items-center gap-1 ml-auto">
                <div className="flex -space-x-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="w-6 h-6 rounded bg-muted border-2 border-background" />
                  ))}
                </div>
                <X size={16} className="text-muted-foreground ml-3 hover:text-foreground cursor-pointer" />
              </div>
            </button>
          </div>

          {/* Quick Actions - 黄色边框药丸形状按钮 */}
          <div className="flex items-center justify-center gap-4 mt-10 flex-wrap">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() => handleQuickAction(action.label)}
                className="nexus-quick-action"
              >
                <div className={cn("icon", action.color)}>
                  <action.icon size={18} />
                </div>
                <span className="font-medium">{action.label}</span>
              </button>
            ))}
          </div>

          {/* Feature Card / Announcement */}
          <div className="w-full max-w-2xl mt-16">
            <div className="nexus-feature-card justify-center">
              <div className="nexus-announcement-icon">
                <NexusLogo size={24} className="text-[var(--nexus-gold)]" />
              </div>
              <div className="text-center">
                <h3 className="font-semibold text-foreground">构建您的全栈 Web 应用</h3>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Chat View */
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Messages */}
          <ScrollArea className="flex-1 px-6" viewportRef={scrollAreaRef}>
            <div className="max-w-3xl mx-auto py-6 space-y-4">
              {messages.map((message) => (
                <MessageItem key={message.id} message={message} />
              ))}
              {streamingContent && (
                <MessageItem
                  message={{
                    id: 'streaming',
                    role: 'agent',
                    content: streamingContent,
                    timestamp: new Date().toISOString(),
                    streaming: true,
                  }}
                />
              )}
              {agentIsThinking && !streamingContent && (
                <div className="flex items-center gap-3 p-4">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Loader2 size={16} className="text-primary animate-spin" />
                  </div>
                  <span className="text-sm text-muted-foreground">Nexus 正在思考...</span>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="px-6 py-4 border-t border-border">
            <div className="max-w-3xl mx-auto">
              {/* Selected files display */}
              {selectedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {selectedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-lg text-sm"
                    >
                      <Paperclip size={14} className="text-muted-foreground" />
                      <span className="text-foreground truncate max-w-[150px]">{file.name}</span>
                      <button
                        onClick={() => removeFile(index)}
                        className="p-0.5 hover:bg-background rounded"
                      >
                        <X size={14} className="text-muted-foreground" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="relative bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="继续对话..."
                  rows={1}
                  className="w-full px-5 py-4 pr-32 bg-transparent text-foreground placeholder:text-muted-foreground resize-none focus:outline-none text-base"
                  disabled={agentIsThinking}
                />
                
                <div className="absolute bottom-3 right-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2 hover:bg-muted rounded-lg transition-colors"
                    title="上传文件"
                  >
                    <Paperclip size={18} className="text-muted-foreground" />
                  </button>
                  <button className="p-2 hover:bg-muted rounded-lg transition-colors">
                    <Mic size={18} className="text-muted-foreground" />
                  </button>
                  <button 
                    onClick={handleSend}
                    disabled={(!input.trim() && selectedFiles.length === 0) || agentIsThinking}
                    className={cn(
                      "p-2 rounded-lg transition-all",
                      (input.trim() || selectedFiles.length > 0) && !agentIsThinking
                        ? "bg-foreground text-background hover:opacity-80"
                        : "bg-muted text-muted-foreground cursor-not-allowed"
                    )}
                  >
                    {agentIsThinking ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Send size={18} />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* PPT 创建向导 */}
      <PPTCreationWizard 
        isOpen={isWizardOpen} 
        onClose={() => setIsWizardOpen(false)} 
      />
      
      {/* PPT 编辑器页面 */}
      {isPPTEditorOpen && (
        <PPTEditorPage
          onClose={() => setIsPPTEditorOpen(false)}
        />
      )}
    </main>
  )
}

export default MainContent
