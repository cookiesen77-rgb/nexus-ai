/**
 * 幻灯片编辑器组件
 */

import React, { useState } from 'react';
import { Slide, SlideLayout, LAYOUT_NAMES } from '@/types/ppt';
import { RefreshCw, Save } from 'lucide-react';

interface SlideEditorProps {
  slide: Slide;
  slideIndex: number;
}

const layouts: SlideLayout[] = [
  'title', 'title_content', 'title_image', 
  'two_column', 'image_only', 'section', 'conclusion'
];

export const SlideEditor: React.FC<SlideEditorProps> = ({ slide, slideIndex }) => {
  // Placeholder functions - 实际实现需要调用后端 API
  const updateSlide = (index: number, data: Partial<Slide>) => {
    console.log('Update slide', index, data);
  };
  const regenerateImage = (index: number, prompt?: string) => {
    console.log('Regenerate image for slide', index, prompt);
  };
  
  const [editedSlide, setEditedSlide] = useState<Slide>(slide);
  const [customPrompt, setCustomPrompt] = useState('');
  const [isRegenerating, setIsRegenerating] = useState(false);
  
  // 同步外部更新
  React.useEffect(() => {
    setEditedSlide(slide);
  }, [slide]);
  
  const handleSave = () => {
    updateSlide(slideIndex, {
      title: editedSlide.title,
      content: editedSlide.content,
      layout: editedSlide.layout,
      notes: editedSlide.notes
    });
  };
  
  const handleRegenerate = () => {
    setIsRegenerating(true);
    regenerateImage(slideIndex, customPrompt || undefined);
    // 实际完成状态应该由 WebSocket 消息更新
    setTimeout(() => setIsRegenerating(false), 2000);
  };
  
  return (
    <div className="flex flex-col h-full p-4 space-y-4 overflow-y-auto">
      <h3 className="text-lg font-semibold text-nexus-text">编辑幻灯片 {slideIndex + 1}</h3>
      
      {/* 布局选择 */}
      <div>
        <label className="block text-sm font-medium text-nexus-text-muted mb-2">
          布局
        </label>
        <select
          value={editedSlide.layout}
          onChange={(e) => setEditedSlide({ ...editedSlide, layout: e.target.value as SlideLayout })}
          className="w-full px-3 py-2 rounded-lg bg-nexus-input border border-nexus-border text-nexus-text focus:outline-none focus:ring-2 focus:ring-nexus-primary"
        >
          {layouts.map((layout) => (
            <option key={layout} value={layout}>
              {LAYOUT_NAMES[layout]}
            </option>
          ))}
        </select>
      </div>
      
      {/* 标题 */}
      <div>
        <label className="block text-sm font-medium text-nexus-text-muted mb-2">
          标题
        </label>
        <input
          type="text"
          value={editedSlide.title}
          onChange={(e) => setEditedSlide({ ...editedSlide, title: e.target.value })}
          className="w-full px-3 py-2 rounded-lg bg-nexus-input border border-nexus-border text-nexus-text focus:outline-none focus:ring-2 focus:ring-nexus-primary"
          placeholder="输入标题"
        />
      </div>
      
      {/* 内容 */}
      <div>
        <label className="block text-sm font-medium text-nexus-text-muted mb-2">
          内容
        </label>
        <textarea
          value={editedSlide.content}
          onChange={(e) => setEditedSlide({ ...editedSlide, content: e.target.value })}
          rows={6}
          className="w-full px-3 py-2 rounded-lg bg-nexus-input border border-nexus-border text-nexus-text focus:outline-none focus:ring-2 focus:ring-nexus-primary resize-none"
          placeholder="输入内容（每行一个要点）"
        />
      </div>
      
      {/* 演讲备注 */}
      <div>
        <label className="block text-sm font-medium text-nexus-text-muted mb-2">
          演讲备注
        </label>
        <textarea
          value={editedSlide.notes}
          onChange={(e) => setEditedSlide({ ...editedSlide, notes: e.target.value })}
          rows={3}
          className="w-full px-3 py-2 rounded-lg bg-nexus-input border border-nexus-border text-nexus-text focus:outline-none focus:ring-2 focus:ring-nexus-primary resize-none"
          placeholder="输入演讲备注（可选）"
        />
      </div>
      
      {/* 保存按钮 */}
      <button
        onClick={handleSave}
        className="flex items-center justify-center gap-2 px-4 py-2 bg-nexus-primary text-white rounded-lg hover:bg-nexus-primary/90 transition-colors"
      >
        <Save className="w-4 h-4" />
        保存更改
      </button>
      
      {/* 分隔线 */}
      <div className="border-t border-nexus-border pt-4">
        <h4 className="text-sm font-medium text-nexus-text-muted mb-2">
          重新生成配图
        </h4>
        
        <textarea
          value={customPrompt}
          onChange={(e) => setCustomPrompt(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded-lg bg-nexus-input border border-nexus-border text-nexus-text focus:outline-none focus:ring-2 focus:ring-nexus-primary resize-none mb-2"
          placeholder="输入自定义提示词（可选，留空则根据内容自动生成）"
        />
        
        <button
          onClick={handleRegenerate}
          disabled={isRegenerating}
          className={`
            flex items-center justify-center gap-2 w-full px-4 py-2 rounded-lg transition-colors
            ${isRegenerating 
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-nexus-accent text-white hover:bg-nexus-accent/90'
            }
          `}
        >
          <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`} />
          {isRegenerating ? '生成中...' : '重新生成配图'}
        </button>
      </div>
    </div>
  );
};

export default SlideEditor;

