import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import type { Task, TaskPhase } from '@/types'

const STORAGE_KEY = 'nexus_tasks'
const ACTIVE_TASK_KEY = 'nexus_active_task_id'

interface TaskState {
  tasks: Task[]
  activeTask: Task | null
  activeTaskId: string | null

  // 创建任务（返回新任务 ID）
  createTask: (title?: string, description?: string) => string

  // 添加任务
  addTask: (task: Task) => void

  // 更新任务
  updateTask: (id: string, updates: Partial<Task>) => void

  // 删除任务
  deleteTask: (id: string) => void

  // 设置当前活动任务
  setActiveTask: (id: string | null) => void

  // 任务操作
  startTask: (id: string) => void
  pauseTask: (id: string) => void
  stopTask: (id: string) => void
  completeTask: (id: string) => void

  // Phase 操作
  addPhaseToTask: (taskId: string, phase: Omit<TaskPhase, 'id'>) => void
  updatePhaseInTask: (taskId: string, phaseId: string, updates: Partial<TaskPhase>) => void

  // 持久化
  loadFromStorage: () => void
  saveToStorage: () => void
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  activeTask: null,
  activeTaskId: null,

  // 创建任务并返回 ID
  createTask: (title = '新任务', description = '') => {
    const newTask: Task = {
      id: uuidv4(),
      title,
      description,
      status: 'pending',
      progress: 0,
      phases: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }

    set((state) => ({
      tasks: [...state.tasks, newTask],
      activeTask: newTask,
      activeTaskId: newTask.id,
    }))

    get().saveToStorage()
    return newTask.id
  },

  addTask: (task) => {
    set((state) => ({
      tasks: [...state.tasks, task],
      activeTask: task,
      activeTaskId: task.id,
    }))
    get().saveToStorage()
  },

  updateTask: (id, updates) => {
    set((state) => {
      const updatedTasks = state.tasks.map((task) =>
        task.id === id ? { ...task, ...updates, updatedAt: new Date().toISOString() } : task
      )
      const updatedActiveTask = state.activeTask?.id === id
        ? { ...state.activeTask, ...updates, updatedAt: new Date().toISOString() }
        : state.activeTask

      return {
        tasks: updatedTasks,
        activeTask: updatedActiveTask,
      }
    })
    get().saveToStorage()
  },

  deleteTask: (id) => {
    set((state) => {
      const filteredTasks = state.tasks.filter((task) => task.id !== id)
      const newActiveTask = state.activeTaskId === id
        ? (filteredTasks[0] || null)
        : state.activeTask

      return {
        tasks: filteredTasks,
        activeTask: newActiveTask,
        activeTaskId: newActiveTask?.id || null,
      }
    })
    get().saveToStorage()
  },

  setActiveTask: (id) => {
    set((state) => {
      const task = id ? state.tasks.find((t) => t.id === id) || null : null
      return {
        activeTask: task,
        activeTaskId: id,
      }
    })
    // 保存活动任务 ID
    if (id) {
      localStorage.setItem(ACTIVE_TASK_KEY, id)
    } else {
      localStorage.removeItem(ACTIVE_TASK_KEY)
    }
  },

  startTask: (id) => {
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === id ? { ...task, status: 'running', updatedAt: new Date().toISOString() } : task
      ),
      activeTask: state.activeTask?.id === id
        ? { ...state.activeTask, status: 'running', updatedAt: new Date().toISOString() }
        : state.activeTask,
    }))
    get().saveToStorage()
  },

  pauseTask: (id) => {
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === id ? { ...task, status: 'paused', updatedAt: new Date().toISOString() } : task
      ),
      activeTask: state.activeTask?.id === id
        ? { ...state.activeTask, status: 'paused', updatedAt: new Date().toISOString() }
        : state.activeTask,
    }))
    get().saveToStorage()
  },

  stopTask: (id) => {
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === id ? { ...task, status: 'failed', updatedAt: new Date().toISOString() } : task
      ),
      activeTask: state.activeTask?.id === id
        ? { ...state.activeTask, status: 'failed', updatedAt: new Date().toISOString() }
        : state.activeTask,
    }))
    get().saveToStorage()
  },

  completeTask: (id) => {
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === id ? { ...task, status: 'completed', progress: 100, updatedAt: new Date().toISOString() } : task
      ),
      activeTask: state.activeTask?.id === id
        ? { ...state.activeTask, status: 'completed', progress: 100, updatedAt: new Date().toISOString() }
        : state.activeTask,
    }))
    get().saveToStorage()
  },

  addPhaseToTask: (taskId, phase) => {
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId
          ? {
              ...task,
              phases: [...(task.phases || []), { id: uuidv4(), ...phase }],
              updatedAt: new Date().toISOString(),
            }
          : task
      ),
      activeTask: state.activeTask?.id === taskId
        ? {
            ...state.activeTask,
            phases: [...(state.activeTask.phases || []), { id: uuidv4(), ...phase }],
            updatedAt: new Date().toISOString(),
          }
        : state.activeTask,
    }))
    get().saveToStorage()
  },

  updatePhaseInTask: (taskId, phaseId, updates) => {
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId
          ? {
              ...task,
              phases: (task.phases || []).map((phase) =>
                phase.id === phaseId ? { ...phase, ...updates } : phase
              ),
              updatedAt: new Date().toISOString(),
            }
          : task
      ),
      activeTask: state.activeTask?.id === taskId
        ? {
            ...state.activeTask,
            phases: (state.activeTask.phases || []).map((phase) =>
              phase.id === phaseId ? { ...phase, ...updates } : phase
            ),
            updatedAt: new Date().toISOString(),
          }
        : state.activeTask,
    }))
    get().saveToStorage()
  },

  // 从 localStorage 加载
  loadFromStorage: () => {
    try {
      const storedTasks = localStorage.getItem(STORAGE_KEY)
      const storedActiveId = localStorage.getItem(ACTIVE_TASK_KEY)

      if (storedTasks) {
        const tasks: Task[] = JSON.parse(storedTasks)
        const activeTask = storedActiveId
          ? tasks.find((t) => t.id === storedActiveId) || tasks[0] || null
          : tasks[0] || null

        set({
          tasks,
          activeTask,
          activeTaskId: activeTask?.id || null,
        })
        console.log('[TaskStore] Loaded tasks from storage:', tasks.length)
      }
    } catch (e) {
      console.error('[TaskStore] Failed to load from storage:', e)
    }
  },

  // 保存到 localStorage
  saveToStorage: () => {
    try {
      const { tasks } = get()
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
    } catch (e) {
      console.error('[TaskStore] Failed to save to storage:', e)
    }
  },
}))
