/**
 * 幻灯片列表组件
 */

import React from 'react';
import { Slide } from '@/types/ppt';
import { Image, FileText } from 'lucide-react';

interface SlideListProps {
  slides: Slide[];
  currentSlideIndex?: number;
  onSlideSelect?: (index: number) => void;
}

export const SlideList: React.FC<SlideListProps> = ({ slides, currentSlideIndex = 0, onSlideSelect }) => {
  const setCurrentSlideIndex = onSlideSelect || ((index: number) => console.log('Select slide', index));
  
  return (
    <div className="flex flex-col gap-3 p-4 overflow-y-auto h-full">
      {slides.map((slide, index) => {
        const isSelected = index === currentSlideIndex;
        const hasImage = !!slide.imageBase64;
        
        return (
          <button
            key={slide.id}
            onClick={() => setCurrentSlideIndex(index)}
            className={`
              relative group rounded-lg overflow-hidden border-2 transition-all
              ${isSelected 
                ? 'border-nexus-primary shadow-lg' 
                : 'border-nexus-border hover:border-nexus-primary/50'
              }
            `}
          >
            {/* 缩略图 */}
            <div className="aspect-video bg-nexus-sidebar relative">
              {hasImage ? (
                <img 
                  src={`data:image/png;base64,${slide.imageBase64}`}
                  alt={slide.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
                  <FileText className="w-8 h-8 text-gray-400" />
                </div>
              )}
              
              {/* 标题覆盖层 */}
              <div className="absolute inset-0 bg-black/30 flex items-end p-2">
                <span className="text-white text-xs font-medium truncate">
                  {slide.title || `幻灯片 ${index + 1}`}
                </span>
              </div>
            </div>
            
            {/* 页码 */}
            <div className={`
              absolute top-1 left-1 px-2 py-0.5 rounded text-xs font-bold
              ${isSelected ? 'bg-nexus-primary text-white' : 'bg-black/50 text-white'}
            `}>
              {index + 1}
            </div>
            
            {/* 图片状态指示器 */}
            <div className={`
              absolute top-1 right-1 p-1 rounded
              ${hasImage ? 'bg-green-500' : 'bg-gray-400'}
            `}>
              <Image className="w-3 h-3 text-white" />
            </div>
          </button>
        );
      })}
    </div>
  );
};

export default SlideList;

