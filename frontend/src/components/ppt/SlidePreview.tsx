/**
 * 幻灯片预览组件
 */

import React from 'react';
import { Slide, LAYOUT_NAMES, TemplateStyle } from '@/types/ppt';

interface SlidePreviewProps {
  slide: Slide;
  template: TemplateStyle;
  className?: string;
}

// 模板颜色配置
const templateColors: Record<TemplateStyle, { bg: string; text: string; textMuted: string }> = {
  modern: { bg: 'bg-white', text: 'text-gray-800', textMuted: 'text-gray-600' },
  minimal: { bg: 'bg-gray-50', text: 'text-gray-900', textMuted: 'text-gray-500' },
  creative: { bg: 'bg-gradient-to-br from-purple-50 to-pink-50', text: 'text-purple-900', textMuted: 'text-purple-700' },
  nature: { bg: 'bg-green-50', text: 'text-green-900', textMuted: 'text-green-700' },
  dark: { bg: 'bg-slate-900', text: 'text-white', textMuted: 'text-slate-300' },
  banana_template_y: { bg: 'bg-amber-100', text: 'text-amber-900', textMuted: 'text-amber-700' },
  banana_template_vector_illustration: { bg: 'bg-fuchsia-50', text: 'text-fuchsia-900', textMuted: 'text-fuchsia-700' },
  banana_template_glass: { bg: 'bg-slate-100', text: 'text-slate-900', textMuted: 'text-slate-600' },
  banana_template_b: { bg: 'bg-blue-50', text: 'text-blue-900', textMuted: 'text-blue-700' },
  banana_template_s: { bg: 'bg-gray-50', text: 'text-gray-800', textMuted: 'text-gray-600' },
  banana_template_academic: { bg: 'bg-emerald-50', text: 'text-emerald-900', textMuted: 'text-emerald-700' },
};

export const SlidePreview: React.FC<SlidePreviewProps> = ({ slide, template, className = '' }) => {
  const colors = templateColors[template];
  const hasImage = !!slide.imageBase64;
  
  return (
    <div className={`relative aspect-video rounded-xl overflow-hidden shadow-2xl ${className}`}>
      {/* 背景图片或纯色背景 */}
      {hasImage ? (
        <img 
          src={`data:image/png;base64,${slide.imageBase64}`}
          alt={slide.title}
          className="absolute inset-0 w-full h-full object-cover"
        />
      ) : (
        <div className={`absolute inset-0 ${colors.bg}`} />
      )}
      
      {/* 内容覆盖层 */}
      <div className={`
        absolute inset-0 flex flex-col p-8
        ${hasImage ? 'bg-black/20' : ''}
      `}>
        {/* 根据布局渲染内容 */}
        {slide.layout === 'title' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <h1 className={`text-4xl font-bold mb-4 ${hasImage ? 'text-white drop-shadow-lg' : colors.text}`}>
              {slide.title}
            </h1>
            <p className={`text-xl ${hasImage ? 'text-white/80' : colors.textMuted}`}>
              {slide.content}
            </p>
          </div>
        )}
        
        {(slide.layout === 'title_content' || slide.layout === 'section') && (
          <div className="flex-1 flex flex-col">
            <h2 className={`text-3xl font-bold mb-6 ${hasImage ? 'text-white drop-shadow-lg' : colors.text}`}>
              {slide.title}
            </h2>
            <div className={`flex-1 ${hasImage ? 'text-white/90' : colors.textMuted}`}>
              {slide.content.split('\n').map((line, i) => (
                <p key={i} className="mb-2 text-lg">
                  {line.startsWith('•') || line.startsWith('-') ? line : `• ${line}`}
                </p>
              ))}
            </div>
          </div>
        )}
        
        {slide.layout === 'title_image' && (
          <div className="flex-1 flex flex-col">
            <h2 className={`text-3xl font-bold mb-4 ${hasImage ? 'text-white drop-shadow-lg' : colors.text}`}>
              {slide.title}
            </h2>
            <p className={`${hasImage ? 'text-white/80' : colors.textMuted}`}>
              {slide.content}
            </p>
          </div>
        )}
        
        {slide.layout === 'conclusion' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <h2 className={`text-3xl font-bold mb-6 ${hasImage ? 'text-white drop-shadow-lg' : colors.text}`}>
              {slide.title}
            </h2>
            <div className={`${hasImage ? 'text-white/90' : colors.textMuted}`}>
              {slide.content.split('\n').map((line, i) => (
                <p key={i} className="mb-2 text-lg">
                  {line}
                </p>
              ))}
            </div>
          </div>
        )}
        
        {slide.layout === 'image_only' && (
          <div className="flex-1" />
        )}
        
        {slide.layout === 'two_column' && (
          <div className="flex-1 flex flex-col">
            <h2 className={`text-3xl font-bold mb-6 ${hasImage ? 'text-white drop-shadow-lg' : colors.text}`}>
              {slide.title}
            </h2>
            <div className="flex-1 grid grid-cols-2 gap-8">
              <div className={`${hasImage ? 'text-white/90' : colors.textMuted}`}>
                {slide.content.split('\n').slice(0, Math.ceil(slide.content.split('\n').length / 2)).map((line, i) => (
                  <p key={i} className="mb-2">{line}</p>
                ))}
              </div>
              <div className={`${hasImage ? 'text-white/90' : colors.textMuted}`}>
                {slide.content.split('\n').slice(Math.ceil(slide.content.split('\n').length / 2)).map((line, i) => (
                  <p key={i} className="mb-2">{line}</p>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* 布局标签 */}
      <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/50 rounded text-xs text-white">
        {LAYOUT_NAMES[slide.layout]}
      </div>
    </div>
  );
};

export default SlidePreview;

