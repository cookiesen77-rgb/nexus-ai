/**
 * 模板选择器组件 - 专业版
 */

import React from 'react';
import { 
  Building2, 
  Minimize2, 
  Palette, 
  Leaf, 
  Moon,
  Image as ImageIcon,
  CheckCircle2 
} from 'lucide-react';
import { TemplateStyle, TEMPLATE_NAMES, TEMPLATE_PREVIEWS } from '@/types/ppt';

interface TemplateSelectorProps {
  selectedTemplate: TemplateStyle;
  onSelect: (template: TemplateStyle) => void;
}

// 模板图标映射
const TEMPLATE_ICONS: Record<TemplateStyle, React.ReactNode> = {
  modern: <Building2 className="w-6 h-6" />,
  minimal: <Minimize2 className="w-6 h-6" />,
  creative: <Palette className="w-6 h-6" />,
  nature: <Leaf className="w-6 h-6" />,
  dark: <Moon className="w-6 h-6" />,
  banana_template_y: <ImageIcon className="w-6 h-6" />,
  banana_template_vector_illustration: <ImageIcon className="w-6 h-6" />,
  banana_template_glass: <ImageIcon className="w-6 h-6" />,
  banana_template_b: <ImageIcon className="w-6 h-6" />,
  banana_template_s: <ImageIcon className="w-6 h-6" />,
  banana_template_academic: <ImageIcon className="w-6 h-6" />,
};

const templates: TemplateStyle[] = [
  'modern',
  'minimal',
  'creative',
  'nature',
  'dark',
  'banana_template_y',
  'banana_template_vector_illustration',
  'banana_template_glass',
  'banana_template_b',
  'banana_template_s',
  'banana_template_academic',
];

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  selectedTemplate,
  onSelect
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {templates.map((template) => {
        const preview = TEMPLATE_PREVIEWS[template];
        const isSelected = selectedTemplate === template;
        
        return (
          <button
            key={template}
            onClick={() => onSelect(template)}
            className={`
              group relative p-4 rounded-2xl border-2 transition-all duration-300
              hover:scale-[1.02] hover:shadow-xl bg-white
              ${isSelected 
                ? 'border-nexus-primary shadow-lg ring-2 ring-nexus-primary/20' 
                : 'border-gray-200 hover:border-nexus-primary/50'
              }
            `}
          >
            {/* 预览区域 - 模拟 PPT 预览 */}
            <div 
              className={`
                relative w-full aspect-[16/10] rounded-xl overflow-hidden mb-3
                bg-gradient-to-br ${preview.gradient}
              `}
            >
              {preview.previewImage ? (
                <img
                  src={preview.previewImage}
                  alt={TEMPLATE_NAMES[template]}
                  className="absolute inset-0 w-full h-full object-cover"
                />
              ) : (
                <>
                  {/* 模拟 PPT 内容 */}
                  <div className="absolute inset-0 p-2.5 flex flex-col">
                    <div 
                      className="w-2/3 h-1.5 rounded-full mb-1.5"
                      style={{ backgroundColor: `${preview.textColor}40` }}
                    />
                    <div 
                      className="w-1/2 h-1 rounded-full mb-3"
                      style={{ backgroundColor: `${preview.textColor}30` }}
                    />
                    <div className="flex-1 flex gap-1.5">
                      <div 
                        className="w-1/2 rounded-md"
                        style={{ backgroundColor: `${preview.textColor}15` }}
                      />
                      <div className="w-1/2 flex flex-col gap-0.5">
                        <div 
                          className="h-0.5 rounded-full w-full"
                          style={{ backgroundColor: `${preview.textColor}25` }}
                        />
                        <div 
                          className="h-0.5 rounded-full w-3/4"
                          style={{ backgroundColor: `${preview.textColor}25` }}
                        />
                        <div 
                          className="h-0.5 rounded-full w-4/5"
                          style={{ backgroundColor: `${preview.textColor}25` }}
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}
              
              {/* 模板图标 */}
              <div 
                className="absolute top-1.5 right-1.5 p-1 rounded-md"
                style={{ backgroundColor: `${preview.textColor}20`, color: preview.textColor }}
              >
                {TEMPLATE_ICONS[template]}
              </div>
            </div>
            
            {/* 模板信息 */}
            <div className="text-left">
              <div className="font-semibold text-gray-800 text-sm group-hover:text-nexus-primary transition-colors">
                {TEMPLATE_NAMES[template]}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {preview.description}
              </div>
            </div>
            
            {/* 选中标记 */}
            {isSelected && (
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-nexus-primary rounded-full flex items-center justify-center shadow-lg">
                <CheckCircle2 className="w-4 h-4 text-white" />
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default TemplateSelector;
