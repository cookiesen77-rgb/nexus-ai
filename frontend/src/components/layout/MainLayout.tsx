import Sidebar from './Sidebar'
import MainContent from './MainContent'
import { useWebSocket } from '@/hooks/useWebSocket'

const MainLayout = () => {
  // Initialize WebSocket connection
  useWebSocket()

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <MainContent />
    </div>
  )
}

export default MainLayout
