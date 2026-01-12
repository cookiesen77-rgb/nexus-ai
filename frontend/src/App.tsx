import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useThemeStore } from '@/stores/themeStore'
import HomePage from '@/pages/HomePage'
import ProductPage from '@/pages/ProductPage'
import MainLayout from '@/components/layout/MainLayout'
import { PPTCreator, PPTOutlineEditor, PPTDetailEditor, PPTSlidePreview } from '@/pages'
import DesignPage from '@/pages/DesignPage'

function App() {
  const { theme } = useThemeStore()
  
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  return (
    <BrowserRouter>
      <Routes>
        {/* 产品页 - 设计稿复刻 */}
        <Route path="/" element={<ProductPage />} />
        <Route path="/workspace" element={<HomePage />} />
        
        {/* PPT 创建器路由 */}
        <Route path="/ppt" element={<PPTCreator />} />
        <Route path="/ppt/project/:projectId/outline" element={<PPTOutlineEditor />} />
        <Route path="/ppt/project/:projectId/detail" element={<PPTDetailEditor />} />
        <Route path="/ppt/project/:projectId/preview" element={<PPTSlidePreview />} />
        
        {/* AI 设计模块路由 */}
        <Route path="/design" element={<DesignPage />} />
        
        {/* 聊天应用 - 保留侧边栏版本 */}
        <Route path="/chat/*" element={<MainLayout />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
