/**
 * Nexus AI 产品展示页
 * 参考 Nexus AI 主界面设计稿实现的一比一静态页面
 * 支持深浅主题切换
 */
import { useState, ElementType } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mic, Send, User, Presentation, Palette, BarChart3, LayoutDashboard, Sun, Moon } from 'lucide-react'
import NexusLogo from '@/components/ui/NexusLogo'
import LiquidGlassWrapper from '@/components/ui/LiquidGlassWrapper'
import { useTheme } from '@/hooks/useTheme'

type QuickAction = {
  label: string
  icon: ElementType
  route: string
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: '制作幻灯片',
    icon: Presentation,
    route: '/ppt'
  },
  {
    label: '创建网站',
    icon: LayoutDashboard,
    route: '/workspace'
  },
  {
    label: '数据分析',
    icon: BarChart3,
    route: '/workspace'
  },
  {
    label: '设计',
    icon: Palette,
    route: '/design'
  }
]

const ProductPage = () => {
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')
  const { theme, toggleTheme } = useTheme()

  const goWorkspace = () => {
    navigate('/workspace')
  }

  const handleSubmit = () => {
    if (!question.trim()) {
      goWorkspace()
      return
    }

    navigate('/workspace', {
      state: { prompt: question.trim() }
    })
    setQuestion('')
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* 顶部导航 */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <NexusLogo size={52} />
            <span className="text-2xl font-semibold tracking-tight text-foreground">Nexus AI</span>
          </div>
          <nav className="hidden md:flex items-center gap-10 text-sm font-medium text-muted-foreground">
            {['功能', '价格', '关于', '博客'].map((item) => (
              <button key={item} className="hover:text-foreground transition-colors">{item}</button>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            {/* 主题切换按钮 */}
            <button 
              onClick={toggleTheme}
              className="p-2 rounded-full bg-card border border-border hover:bg-muted transition-colors"
              title={theme === 'dark' ? '切换到浅色主题' : '切换到深色主题'}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-9 h-9 rounded-full bg-card shadow-sm flex items-center justify-center border border-border">
                <User size={18} />
              </div>
              <span>用户名</span>
            </button>
          </div>
        </header>

        {/* 主体内容 */}
        <main className="mt-16 flex flex-col items-center text-center space-y-8">
          <p className="text-sm tracking-[0.4em] uppercase text-primary">Nexus AI</p>
          <h1 className="text-4xl md:text-5xl font-bold text-foreground">我能为你做什么？</h1>
          <p className="text-muted-foreground text-base max-w-2xl">分配一个任务或提问任何问题</p>

          {/* 输入框 */}
          <div className="w-full max-w-3xl">
            <LiquidGlassWrapper
              padding="18px 26px"
              cornerRadius={999}
              className="flex items-center gap-4 text-left text-foreground w-full"
            >
              <input
                type="text"
                placeholder="分配一个任务或提问任何问题"
                className="flex-1 bg-transparent text-lg text-foreground placeholder:text-muted-foreground focus:outline-none min-w-0"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0" onClick={goWorkspace}>
                <Mic size={22} />
              </button>
              <button className="w-11 h-11 rounded-full bg-card/60 shadow-inner flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors flex-shrink-0 border border-border" onClick={handleSubmit}>
                <Send size={20} />
              </button>
            </LiquidGlassWrapper>
          </div>

          {/* 快捷操作 */}
          <div className="mt-6 flex flex-wrap justify-center gap-4">
            {QUICK_ACTIONS.map(({ label, icon: Icon, route }) => (
              <button
                key={label}
                className="nexus-quick-action"
                onClick={() => navigate(route)}
              >
                <span>
                  <Icon size={18} />
                  {label}
                </span>
              </button>
            ))}
          </div>

          {/* CTA 按钮 - Uiverse 风格 */}
          <div className="mt-10">
            <button className="nexus-cta-btn" onClick={goWorkspace}>
              <span className="btn-txt">体验更智能的 Nexus AI</span>
            </button>
          </div>
        </main>
      </div>
    </div>
  )
}

export default ProductPage

