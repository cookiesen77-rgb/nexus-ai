import { useState } from 'react'
import { RefreshCw, ArrowLeft, ArrowRight, Globe } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'

export function BrowserPreview() {
  const { browser, setBrowserUrl, setBrowserLoading } = useAppStore()
  const [urlInput, setUrlInput] = useState(browser.url)

  const handleNavigate = async () => {
    if (!urlInput.trim()) return

    let url = urlInput.trim()
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url
    }

    setBrowserUrl(url)
    setBrowserLoading(true)
    
    // TODO: Implement browser navigation via API
    setTimeout(() => {
      setBrowserLoading(false)
    }, 1000)
  }

  const handleRefresh = () => {
    handleNavigate()
  }

  return (
    <div className="h-full flex flex-col bg-card">
      <div className="flex items-center gap-2 p-3 border-b border-border">
        <button className="p-2 hover:bg-muted rounded-lg transition-colors" disabled>
          <ArrowLeft size={16} className="text-muted-foreground" />
        </button>
        <button className="p-2 hover:bg-muted rounded-lg transition-colors" disabled>
          <ArrowRight size={16} className="text-muted-foreground" />
        </button>
        <button 
          className="p-2 hover:bg-muted rounded-lg transition-colors" 
          onClick={handleRefresh} 
          disabled={browser.isLoading}
        >
          <RefreshCw size={16} className={browser.isLoading ? 'animate-spin text-primary' : 'text-muted-foreground'} />
        </button>
        <div className="flex-1 flex items-center gap-2 px-3 h-9 bg-muted rounded-lg">
          <Globe size={14} className="text-muted-foreground" />
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
            placeholder="输入网址..."
            className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground"
          />
        </div>
      </div>
      <div className="flex-1 bg-background overflow-hidden">
        {browser.screenshot ? (
          <img
            src={`data:image/png;base64,${browser.screenshot}`}
            alt="Browser screenshot"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Globe size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">输入网址开始浏览</p>
              <p className="text-sm mt-1">或者让 Nexus AI 为你自动浏览</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BrowserPreview
