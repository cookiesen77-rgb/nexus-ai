import { useState } from 'react'
import {
  Plus, Search, Library, ChevronDown, ChevronRight, Folder, 
  Settings, PanelLeftClose, PanelLeft, Smartphone, Grid3X3,
  FileText, CheckCircle2, Loader2, Circle
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/hooks/useTheme'
import { useAppStore } from '@/stores/appStore'
import { useTaskStore } from '@/stores/taskStore'
import { useChatStore } from '@/stores/chatStore'
import NexusLogo from '@/components/ui/NexusLogo'
import type { Task } from '@/types'

const Sidebar = () => {
  const { toggleTheme } = useTheme()
  const { setActiveView } = useAppStore()
  const { tasks, activeTask, setActiveTask, createTask } = useTaskStore()
  const { clearMessages } = useChatStore()
  const [collapsed, setCollapsed] = useState(false)
  const [projectsExpanded, setProjectsExpanded] = useState(true)
  const [tasksExpanded, setTasksExpanded] = useState(true)

  const handleNewTask = () => {
    createTask('新任务', '')
    setActiveView('chat')
    clearMessages()
  }

  const getTaskStatusIcon = (status: Task['status']) => {
    switch (status) {
      case 'pending': return <Circle size={14} className="text-muted-foreground" />
      case 'running': return <Loader2 size={14} className="text-primary animate-spin" />
      case 'completed': return <CheckCircle2 size={14} className="text-green-500" />
      case 'failed': return <Circle size={14} className="text-red-500" />
      default: return <Circle size={14} className="text-muted-foreground" />
    }
  }

  if (collapsed) {
    return (
      <aside className="flex flex-col h-full w-16 bg-[var(--nexus-sidebar-bg)] border-r border-[var(--nexus-sidebar-border)]">
        <div className="flex items-center justify-center p-4">
          <button onClick={() => setCollapsed(false)} className="p-2 hover:bg-muted rounded-lg">
            <PanelLeft size={20} className="text-muted-foreground" />
          </button>
        </div>
        <nav className="flex-1 flex flex-col items-center gap-2 p-2">
          <button onClick={handleNewTask} className="p-3 hover:bg-muted rounded-lg">
            <FileText size={20} className="text-muted-foreground" />
          </button>
          <button className="p-3 hover:bg-muted rounded-lg">
            <Search size={20} className="text-muted-foreground" />
          </button>
          <button className="p-3 hover:bg-muted rounded-lg">
            <Library size={20} className="text-muted-foreground" />
          </button>
        </nav>
        <div className="p-2 flex flex-col items-center gap-2">
          <button onClick={toggleTheme} className="p-3 hover:bg-muted rounded-lg">
            <Settings size={20} className="text-muted-foreground" />
          </button>
        </div>
      </aside>
    )
  }

  return (
    <aside className="flex flex-col h-full w-[280px] bg-[var(--nexus-sidebar-bg)] border-r border-[var(--nexus-sidebar-border)]">
      {/* Header - Logo */}
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2 cursor-pointer group">
          <NexusLogo size={28} className="text-foreground" />
          <span className="text-lg font-semibold text-foreground tracking-tight">nexus</span>
        </div>
        <button 
          onClick={() => setCollapsed(true)}
          className="p-2 hover:bg-muted rounded-lg transition-colors"
        >
          <PanelLeftClose size={18} className="text-muted-foreground" />
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="px-3 space-y-1">
        <button
          onClick={handleNewTask}
          className="nexus-sidebar-item w-full"
        >
          <FileText size={18} />
          <span>新建任务</span>
        </button>
        
        <button className="nexus-sidebar-item w-full">
          <Search size={18} />
          <span>搜索</span>
        </button>
        
        <button className="nexus-sidebar-item w-full">
          <Library size={18} />
          <span>库</span>
        </button>
      </nav>

      {/* Projects & Tasks */}
      <div className="flex-1 overflow-hidden flex flex-col mt-4 px-3">
        {/* Projects Section */}
        <div className="mb-2">
          <button
            onClick={() => setProjectsExpanded(!projectsExpanded)}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            <div className="flex items-center gap-1">
              <span>项目</span>
              {projectsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
            <button 
              onClick={(e) => { e.stopPropagation() }}
              className="p-1 hover:bg-muted rounded"
            >
              <Plus size={14} />
            </button>
          </button>
          
          {projectsExpanded && (
            <div className="ml-2 space-y-1">
              <button className="nexus-sidebar-item w-full">
                <Folder size={16} className="text-amber-500" />
                <span>新项目</span>
              </button>
            </div>
          )}
        </div>

        {/* Tasks Section */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <button
            onClick={() => setTasksExpanded(!tasksExpanded)}
            className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            <div className="flex items-center gap-1">
              <span>所有任务</span>
              {tasksExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
            <button 
              onClick={(e) => { e.stopPropagation() }}
              className="p-1 hover:bg-muted rounded"
            >
              <Settings size={14} />
            </button>
          </button>
          
          {tasksExpanded && (
            <div className="flex-1 overflow-y-auto ml-2 space-y-1">
              {tasks.length === 0 ? (
                <p className="px-3 py-2 text-sm text-muted-foreground">暂无任务</p>
              ) : (
                tasks.map((task) => (
                  <button
                    key={task.id}
                    onClick={() => { setActiveTask(task.id); setActiveView('chat') }}
                    className={cn(
                      "nexus-sidebar-item w-full",
                      activeTask?.id === task.id && "active"
                    )}
                  >
                    {getTaskStatusIcon(task.status)}
                    <span className="truncate flex-1 text-left">{task.title}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-[var(--nexus-sidebar-border)]">
        <div className="flex items-center justify-between">
          <button onClick={toggleTheme} className="p-2 hover:bg-muted rounded-lg transition-colors">
            <Settings size={18} className="text-muted-foreground" />
          </button>
          <button className="p-2 hover:bg-muted rounded-lg transition-colors">
            <Grid3X3 size={18} className="text-muted-foreground" />
          </button>
          <button className="p-2 hover:bg-muted rounded-lg transition-colors">
            <Smartphone size={18} className="text-muted-foreground" />
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
