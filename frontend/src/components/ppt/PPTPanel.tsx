/**
 * PPT 主面板组件
 */

import React from 'react';
import { useLegacyPPTStore } from '@/stores/pptStore';
import { SlideList } from './SlideList';
import { SlidePreview } from './SlidePreview';
import { SlideEditor } from './SlideEditor';
import { PPTCreationWizard } from './PPTCreationWizard';
import { Download, Plus, ChevronLeft, ChevronRight, Presentation } from 'lucide-react';

export const PPTPanel: React.FC = () => {
  const { 
    currentPresentation, 
    isWizardOpen,
    setIsWizardOpen,
    clearCurrentPresentation
  } = useLegacyPPTStore();
  
  const [currentSlideIndex, setCurrentSlideIndex] = React.useState(0);
  
  // Export PPTX placeholder (uses new store API)
  const exportPPTX = () => {
    console.log('Export PPTX - use new PPT store for actual export');
  };
  
  const currentSlide = currentPresentation?.slides[currentSlideIndex];
  
  // 上一张
  const goToPrevSlide = () => {
    if (currentSlideIndex > 0) {
      setCurrentSlideIndex(currentSlideIndex - 1);
    }
  };
  
  // 下一张
  const goToNextSlide = () => {
    if (currentPresentation && currentSlideIndex < currentPresentation.slides.length - 1) {
      setCurrentSlideIndex(currentSlideIndex + 1);
    }
  };
  
  return (
    <div className="flex flex-col h-full bg-nexus-editor">
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-nexus-border bg-nexus-sidebar">
        <div className="flex items-center gap-4">
          <Presentation className="w-5 h-5 text-nexus-primary" />
          <h2 className="font-semibold text-nexus-text">
            {currentPresentation?.title || 'PPT 制作'}
          </h2>
        </div>
        
        <div className="flex items-center gap-2">
          {currentPresentation && (
            <>
              <button
                onClick={exportPPTX}
                className="flex items-center gap-2 px-4 py-2 bg-nexus-primary text-white rounded-lg hover:bg-nexus-primary/90 transition-colors"
              >
                <Download className="w-4 h-4" />
                导出 PPTX
              </button>
              <button
                onClick={clearCurrentPresentation}
                className="px-4 py-2 text-nexus-text-muted hover:bg-nexus-input rounded-lg transition-colors"
              >
                关闭
              </button>
            </>
          )}
          <button
            onClick={() => setIsWizardOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-nexus-accent text-white rounded-lg hover:bg-nexus-accent/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建 PPT
          </button>
        </div>
      </div>
      
      {/* 主内容区 */}
      {currentPresentation ? (
        <div className="flex-1 flex overflow-hidden">
          {/* 左侧：幻灯片列表 */}
          <div className="w-48 border-r border-nexus-border bg-nexus-sidebar overflow-hidden">
            <SlideList 
              slides={currentPresentation.slides} 
              currentSlideIndex={currentSlideIndex}
              onSlideSelect={setCurrentSlideIndex}
            />
          </div>
          
          {/* 中间：预览区 */}
          <div className="flex-1 flex flex-col p-6 overflow-hidden">
            {/* 预览 */}
            <div className="flex-1 flex items-center justify-center">
              {currentSlide && (
                <SlidePreview 
                  slide={currentSlide} 
                  template={currentPresentation.template as import('@/types/ppt').TemplateStyle}
                  className="w-full max-w-4xl"
                />
              )}
            </div>
            
            {/* 导航控件 */}
            <div className="flex items-center justify-center gap-4 mt-4">
              <button
                onClick={goToPrevSlide}
                disabled={currentSlideIndex === 0}
                className={`
                  p-2 rounded-lg transition-colors
                  ${currentSlideIndex === 0 
                    ? 'text-gray-400 cursor-not-allowed' 
                    : 'text-nexus-text hover:bg-nexus-sidebar'
                  }
                `}
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
              
              <span className="text-nexus-text">
                {currentSlideIndex + 1} / {currentPresentation.slides.length}
              </span>
              
              <button
                onClick={goToNextSlide}
                disabled={currentSlideIndex === currentPresentation.slides.length - 1}
                className={`
                  p-2 rounded-lg transition-colors
                  ${currentSlideIndex === currentPresentation.slides.length - 1
                    ? 'text-gray-400 cursor-not-allowed' 
                    : 'text-nexus-text hover:bg-nexus-sidebar'
                  }
                `}
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            </div>
          </div>
          
          {/* 右侧：编辑区 */}
          <div className="w-80 border-l border-nexus-border bg-nexus-sidebar overflow-hidden">
            {currentSlide && (
              <SlideEditor slide={currentSlide} slideIndex={currentSlideIndex} />
            )}
          </div>
        </div>
      ) : (
        /* 空状态 */
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="w-32 h-32 bg-nexus-sidebar rounded-full flex items-center justify-center mb-6">
            <Presentation className="w-16 h-16 text-nexus-text-muted" />
          </div>
          <h3 className="text-2xl font-bold text-nexus-text mb-2">
            创建您的 PPT
          </h3>
          <p className="text-nexus-text-muted text-center mb-6 max-w-md">
            使用 AI 快速生成专业的演示文稿。只需输入主题，选择模板，
            AI 将自动生成大纲和精美配图。
          </p>
          <button
            onClick={() => setIsWizardOpen(true)}
            className="flex items-center gap-2 px-6 py-3 bg-nexus-primary text-white rounded-xl font-medium hover:bg-nexus-primary/90 transition-colors"
          >
            <Plus className="w-5 h-5" />
            开始创建
          </button>
        </div>
      )}
      
      {/* 创建向导 */}
      <PPTCreationWizard 
        isOpen={isWizardOpen} 
        onClose={() => setIsWizardOpen(false)} 
      />
    </div>
  );
};

export default PPTPanel;

