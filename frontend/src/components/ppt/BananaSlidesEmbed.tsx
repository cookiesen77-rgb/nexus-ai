/**
 * Banana Slides 嵌入式 PPT 创建器
 * 将 banana-slides 集成到 Nexus 界面中
 */

import React, { useState } from 'react';
import { X, Loader2, ExternalLink, Maximize2, Minimize2 } from 'lucide-react';

interface BananaSlidesEmbedProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BananaSlidesEmbed: React.FC<BananaSlidesEmbedProps> = ({ isOpen, onClose }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  if (!isOpen) return null;

  const BANANA_SLIDES_URL = 'http://127.0.0.1:3002/';

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* 背景遮罩 */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* 主容器 */}
      <div 
        className={`
          relative bg-white rounded-2xl shadow-2xl overflow-hidden
          animate-in zoom-in-95 duration-200
          transition-all duration-300
          ${isFullscreen 
            ? 'w-[98vw] h-[96vh]' 
            : 'w-[95vw] max-w-7xl h-[90vh]'
          }
        `}
      >
        {/* 顶部工具栏 */}
        <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-gray-900/90 to-transparent z-10 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <span className="text-white/90 text-sm font-medium">
              🍌 Banana Slides - AI 智能 PPT 创建
            </span>
            {isLoading && (
              <span className="flex items-center gap-2 text-white/60 text-xs">
                <Loader2 className="w-3 h-3 animate-spin" />
                加载中...
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {/* 新窗口打开 */}
            <button
              onClick={() => window.open(BANANA_SLIDES_URL, '_blank')}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/70 hover:text-white"
              title="在新窗口打开"
            >
              <ExternalLink className="w-4 h-4" />
            </button>
            
            {/* 全屏切换 */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/70 hover:text-white"
              title={isFullscreen ? "退出全屏" : "全屏"}
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>
            
            {/* 关闭 */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/70 hover:text-white"
              title="关闭"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        {/* iframe 容器 */}
        <div className="w-full h-full pt-0">
          {/* 加载指示器 */}
          {isLoading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 z-5">
              <div className="relative mb-6">
                <div className="w-20 h-20 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-2xl flex items-center justify-center shadow-xl">
                  <span className="text-4xl">🍌</span>
                </div>
                <div className="absolute -inset-2 bg-yellow-400/20 rounded-3xl animate-ping" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-2">正在加载 Banana Slides</h3>
              <p className="text-gray-500 text-sm">AI 驱动的专业 PPT 创建工具</p>
              <div className="mt-4 flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-orange-500" />
                <span className="text-orange-600 font-medium">连接中...</span>
              </div>
            </div>
          )}
          
          <iframe
            src={BANANA_SLIDES_URL}
            className="w-full h-full border-0"
            onLoad={() => setIsLoading(false)}
            allow="clipboard-write; clipboard-read"
            title="Banana Slides PPT Creator"
          />
        </div>
      </div>
    </div>
  );
};

export default BananaSlidesEmbed;

