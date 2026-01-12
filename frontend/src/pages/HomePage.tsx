/**
 * Nexus AI 主界面
 * 严格按照设计图一比一复刻 - 带侧边栏的聊天界面
 */
import { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { 
  FileText, Presentation, Sparkles, FolderOpen, Plus, Settings, 
  ChevronDown, ChevronRight, PanelLeftClose,
  Copy, RefreshCw, Circle, Check
} from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import { useChatStore } from '@/stores/chatStore'
import { useTaskStore } from '@/stores/taskStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import NexusLogo from '@/components/ui/NexusLogo'
import { useTheme } from '@/hooks/useTheme'

interface Project {
  id: string
  name: string
  selected: boolean
}

export const HomePage = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { agentIsThinking } = useAppStore()
  const { 
    getCurrentMessages, 
    setCurrentConversationId, 
    loadFromStorage: loadChatFromStorage,
  } = useChatStore()
  const { 
    tasks, 
    activeTaskId, 
    createTask, 
    setActiveTask, 
    updateTask,
    loadFromStorage: loadTaskFromStorage,
  } = useTaskStore()
  const { sendMessage, isConnected } = useWebSocket()
  const { theme, toggleTheme } = useTheme()
  
  const [input, setInput] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [projectsExpanded, setProjectsExpanded] = useState(true)
  const [tasksExpanded, setTasksExpanded] = useState(true)
  const [initialized, setInitialized] = useState(false)
  
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 示例项目数据
  const [projects] = useState<Project[]>([
    { id: '1', name: '新项目', selected: true },
  ])

  // 获取当前对话的消息
  const messages = getCurrentMessages()

  // 初始化：加载持久化数据
  useEffect(() => {
    if (!initialized) {
      // 加载任务和对话
      loadTaskFromStorage()
      loadChatFromStorage()
      setInitialized(true)
    }
  }, [initialized, loadTaskFromStorage, loadChatFromStorage])

  // 初始化后设置当前对话
  useEffect(() => {
    if (initialized) {
      const taskStore = useTaskStore.getState()
      
      // 如果没有任务，创建默认任务
      if (taskStore.tasks.length === 0) {
        const newTaskId = createTask('新对话')
        setCurrentConversationId(newTaskId)
      } else {
        // 设置当前对话为活动任务
        const currentActiveId = taskStore.activeTaskId || taskStore.tasks[0]?.id
        if (currentActiveId) {
          setActiveTask(currentActiveId)
          setCurrentConversationId(currentActiveId)
        }
      }
    }
  }, [initialized, createTask, setActiveTask, setCurrentConversationId])

  // 处理从 ProductPage 传递的初始消息
  useEffect(() => {
    if (location.state?.initialMessage && activeTaskId) {
      const initialMessage = location.state.initialMessage
      // 清除 state 避免重复发送
      navigate(location.pathname, { replace: true, state: {} })
      
      // 发送初始消息
      setTimeout(() => {
        sendMessage({
          role: 'user',
          content: initialMessage,
        })
        // 更新任务标题
        updateTask(activeTaskId, { title: initialMessage.slice(0, 20) + (initialMessage.length > 20 ? '...' : '') })
      }, 100)
    }
  }, [location.state, activeTaskId, sendMessage, navigate, updateTask])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 新建任务
  const handleNewTask = () => {
    const newTaskId = createTask(`新任务 ${tasks.length + 1}`)
    setCurrentConversationId(newTaskId)
    setTasksExpanded(true)
  }

  // 切换任务
  const handleTaskClick = (taskId: string) => {
    setActiveTask(taskId)
    setCurrentConversationId(taskId)
  }

  // 发送消息
  const handleSend = () => {
    if (!input.trim() || agentIsThinking) return
    
    const content = input.trim()
    
    // 如果是新任务的第一条消息，更新任务标题
    if (activeTaskId && messages.length === 0) {
      updateTask(activeTaskId, { 
        title: content.slice(0, 20) + (content.length > 20 ? '...' : '') 
      })
    }
    
    sendMessage({
      role: 'user',
      content: content,
    })
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 获取任务显示信息
  const getTaskDisplay = (task: { id: string; title: string; status?: string }) => {
    const isActive = activeTaskId === task.id
    const isCompleted = task.status === 'completed'
    return { isActive, isCompleted }
  }

  return (
    <div className="h-screen flex" style={{ backgroundColor: 'var(--background)', color: 'var(--foreground)' }}>
      {/* 左侧边栏 */}
      <aside
        className={`${sidebarCollapsed ? 'w-0' : 'w-[280px]'} border-r border-border flex flex-col transition-all duration-300 overflow-hidden bg-[var(--nexus-sidebar-bg)]`}
      >
        {/* 侧边栏头部 */}
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <NexusLogo size={42} />
            <span className="text-base font-medium text-foreground">nexus</span>
          </div>
          <button 
            onClick={() => setSidebarCollapsed(true)}
            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        {/* 新建任务按钮 */}
        <div className="px-3">
          <button 
            className="w-full flex items-center gap-2 px-3 py-2 text-muted-foreground hover:bg-muted hover:text-foreground rounded-lg transition-colors"
            onClick={handleNewTask}
          >
            <FileText size={18} />
            <span className="text-sm">新建任务</span>
          </button>
        </div>

        {/* 搜索 */}
        <div className="px-3 mt-1">
          <button
            className="w-full flex items-center gap-2 px-3 py-2 text-muted-foreground hover:bg-muted hover:text-foreground rounded-lg transition-colors"
            onClick={() => navigate('/ppt')}
          >
            <Presentation size={18} />
            <span className="text-sm">PPT制作</span>
          </button>
        </div>

        {/* 库 */}
        <div className="px-3 mt-1">
          <button
            className="w-full flex items-center gap-2 px-3 py-2 text-muted-foreground hover:bg-muted hover:text-foreground rounded-lg transition-colors"
            onClick={() => navigate('/design')}
          >
            <Sparkles size={18} />
            <span className="text-sm">设计</span>
          </button>
        </div>

        {/* 项目区域 */}
        <div className="px-3 mt-4">
          <div className="flex items-center justify-between px-2 py-1">
            <button 
              onClick={() => setProjectsExpanded(!projectsExpanded)}
              className="flex items-center gap-1 text-muted-foreground text-sm hover:text-foreground"
            >
              {projectsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>项目</span>
            </button>
            <button className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
              <Plus size={14} />
            </button>
          </div>
          
          {projectsExpanded && (
            <div className="mt-1 space-y-1">
              {projects.map((project) => (
                <button
                  key={project.id}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                    project.selected 
                      ? 'bg-accent text-accent-foreground' 
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`}
                >
                  <FolderOpen size={16} />
                  <span className="text-sm">{project.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 所有任务区域 */}
        <div className="px-3 mt-4 flex-1 overflow-y-auto">
          <div className="flex items-center justify-between px-2 py-1">
            <button 
              onClick={() => setTasksExpanded(!tasksExpanded)}
              className="flex items-center gap-1 text-muted-foreground text-sm hover:text-foreground"
            >
              {tasksExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>所有任务</span>
            </button>
            <button className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
              <Settings size={14} />
            </button>
          </div>
          
          {tasksExpanded && (
            <div className="mt-1 space-y-1">
              {tasks.map((task) => {
                const { isActive, isCompleted } = getTaskDisplay(task)
                return (
                  <button
                    key={task.id}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                      isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                    onClick={() => handleTaskClick(task.id)}
                  >
                    {isCompleted ? (
                      <Check size={16} className={isActive ? 'text-green-500 dark:text-green-400' : 'text-green-600'} />
                    ) : (
                      <Circle size={16} className="text-muted-foreground" />
                    )}
                    <span className="text-sm truncate max-w-[170px]" title={task.title}>
                      {task.title}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* 侧边栏底部 */}
        <div className="p-4 flex items-center justify-start border-t border-border">
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
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col bg-[var(--nexus-chat-bg)]">
        {/* 顶部导航栏 */}
        <header className="h-14 px-6 flex items-center justify-between border-b border-border bg-[var(--nexus-chat-bg)]/80 backdrop-blur-md sticky top-0 z-10">
          {/* 左侧 - 版本信息 */}
          <div className="flex items-center gap-2">
            {sidebarCollapsed && (
              <button 
                onClick={() => setSidebarCollapsed(false)}
                className="p-1.5 mr-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
              >
                <PanelLeftClose size={18} className="rotate-180" />
              </button>
            )}
            <span className="text-foreground font-medium">Nexus 1.0</span>
            <ChevronDown size={16} className="text-muted-foreground" />
          </div>
          
          {/* 右侧 - 用户操作 */}
          <div className="flex items-center gap-3">
            <label className="nexus-bell-toggle container" aria-label="通知">
              <input type="checkbox" defaultChecked />
              <svg className="bell-regular" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
                <path d="M224 0c-17.7 0-32 14.3-32 32V49.9C119.5 61.4 64 124.2 64 200v33.4c0 45.4-15.5 89.5-43.8 124.9L5.3 377c-5.8 7.2-6.9 17.1-2.9 25.4S14.8 416 24 416H424c9.2 0 17.6-5.3 21.6-13.6s2.9-18.2-2.9-25.4l-14.9-18.6C399.5 322.9 384 278.8 384 233.4V200c0-75.8-55.5-138.6-128-150.1V32c0-17.7-14.3-32-32-32zm0 96h8c57.4 0 104 46.6 104 104v33.4c0 47.9 13.9 94.6 39.7 134.6H72.3C98.1 328 112 281.3 112 233.4V200c0-57.4 46.6-104 104-104h8zm64 352H224 160c0 17 6.7 33.3 18.7 45.3s28.3 18.7 45.3 18.7s33.3-6.7 45.3-18.7s18.7-28.3 18.7-45.3z"></path>
              </svg>
              <svg className="bell-solid" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
                <path d="M224 0c-17.7 0-32 14.3-32 32V51.2C119 66 64 130.6 64 208v18.8c0 47-17.3 92.4-48.5 127.6l-7.4 8.3c-8.4 9.4-10.4 22.9-5.3 34.4S19.4 416 32 416H416c12.6 0 24-7.4 29.2-18.9s3.1-25-5.3-34.4l-7.4-8.3C401.3 319.2 384 273.9 384 226.8V208c0-77.4-55-142-128-156.8V32c0-17.7-14.3-32-32-32zm45.3 493.3c12-12 18.7-28.3 18.7-45.3H224 160c0 17 6.7 33.3 18.7 45.3s28.3 18.7 45.3 18.7s33.3-6.7 45.3-18.7z"></path>
              </svg>
            </label>
          </div>
        </header>

        {/* 聊天区域 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* 空状态提示 */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <NexusLogo size={64} />
              <h2 className="mt-4 text-xl font-medium text-foreground">开始新对话</h2>
              <p className="mt-2 text-muted-foreground">在下方输入框中输入您的问题或任务</p>
            </div>
          )}

          {/* 消息列表 */}
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((message, index) => (
              <div key={message.id || index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'user' ? (
                  // 用户消息
                  <div className="flex items-start gap-3">
                    <div className="bg-[var(--nexus-chat-bubble-user)] text-primary-foreground rounded-2xl px-4 py-3 max-w-md">
                      <p className="text-sm">{message.content}</p>
                    </div>
                  </div>
                ) : message.role === 'system' ? (
                  // 系统消息
                  <div className="w-full flex justify-center">
                    <span className="text-xs text-muted-foreground bg-muted/50 px-3 py-1 rounded-full">
                      {message.content}
                    </span>
                  </div>
                ) : (
                  // AI 消息
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0">
                      <NexusLogo size={42} />
                    </div>
                    <div className="bg-[var(--nexus-chat-bubble-agent)] text-foreground rounded-2xl px-4 py-3 max-w-md shadow-sm border border-border">
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      {/* 操作按钮 */}
                      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border">
                        <button 
                          className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => navigator.clipboard.writeText(message.content)}
                        >
                          <Copy size={14} />
                        </button>
                        <button className="p-1 text-muted-foreground hover:text-foreground transition-colors">
                          <RefreshCw size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {/* 加载指示器 */}
            {agentIsThinking && (
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <NexusLogo size={42} />
                </div>
                <div className="bg-[var(--nexus-chat-bubble-agent)] rounded-2xl px-4 py-3 shadow-sm border border-border">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 底部输入框 */}
        <div className="px-6 py-4 border-t border-border bg-[var(--nexus-chat-bg)]/80 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto">
            {/* Uiverse 样式改造，保持 Nexus 色系与交互 */}
            <div className="nexus-messageBox">
              <div className="fileUploadWrapper">
                <label htmlFor="file">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 337 337">
                    <circle strokeWidth="20" stroke="currentColor" fill="none" r="158.5" cy="168.5" cx="168.5" className="text-muted-foreground"></circle>
                    <path strokeLinecap="round" strokeWidth="25" stroke="currentColor" d="M167.759 79V259" className="text-muted-foreground"></path>
                    <path strokeLinecap="round" strokeWidth="25" stroke="currentColor" d="M79 167.138H259" className="text-muted-foreground"></path>
                  </svg>
                  <span className="tooltip">上传文件</span>
                </label>
                <input type="file" id="file" name="file" onChange={() => {}} />
              </div>
              <input
                required
                placeholder="输入您的问题..."
                type="text"
                id="messageInput"
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={agentIsThinking}
                className="text-foreground placeholder:text-muted-foreground"
              />
              <button
                id="sendButton"
                onClick={handleSend}
                disabled={!input.trim() || agentIsThinking}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 664 663">
                  <path
                    fill="none"
                    d="M646.293 331.888L17.7538 17.6187L155.245 331.888M646.293 331.888L17.753 646.157L155.245 331.888M646.293 331.888L318.735 330.228L155.245 331.888"
                  ></path>
                  <path
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    strokeWidth="33.67"
                    stroke="currentColor"
                    d="M646.293 331.888L17.7538 17.6187L155.245 331.888M646.293 331.888L17.753 646.157L155.245 331.888M646.293 331.888L318.735 330.228L155.245 331.888"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  ></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default HomePage
