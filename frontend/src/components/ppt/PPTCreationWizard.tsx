/**
 * PPT 创建向导组件 - 专业版
 */

import React, { useState, useEffect } from 'react';
import { 
  X, 
  Wand2, 
  ChevronRight, 
  ChevronLeft,
  Presentation,
  Building2,
  Minimize2,
  Palette,
  Leaf,
  Moon,
  Sparkles,
  FileText,
  CheckCircle2
} from 'lucide-react';
import { useLegacyPPTStore } from '@/stores/pptStore';
import { TemplateStyle, TEMPLATE_NAMES, TEMPLATE_PREVIEWS } from '@/types/ppt';

interface PPTCreationWizardProps {
  isOpen: boolean;
  onClose: () => void;
}

// 模板图标映射
const TEMPLATE_ICONS: Record<TemplateStyle, React.ReactNode> = {
  modern: <Building2 className="w-8 h-8" />,
  minimal: <Minimize2 className="w-8 h-8" />,
  creative: <Palette className="w-8 h-8" />,
  nature: <Leaf className="w-8 h-8" />,
  dark: <Moon className="w-8 h-8" />,
  banana_template_y: <FileText className="w-8 h-8" />,
  banana_template_vector_illustration: <Palette className="w-8 h-8" />,
  banana_template_glass: <Sparkles className="w-8 h-8" />,
  banana_template_b: <Building2 className="w-8 h-8" />,
  banana_template_s: <Minimize2 className="w-8 h-8" />,
  banana_template_academic: <FileText className="w-8 h-8" />,
};

// 步骤指示器组件
const StepIndicator: React.FC<{ currentStep: number; totalSteps: number }> = ({ 
  currentStep, 
  totalSteps 
}) => (
  <div className="flex items-center justify-center gap-2 mb-6">
    {Array.from({ length: totalSteps }, (_, i) => (
      <div key={i} className="flex items-center">
        <div 
          className={`
            w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
            transition-all duration-300
            ${i + 1 <= currentStep 
              ? 'bg-nexus-primary text-white' 
              : 'bg-gray-200 text-gray-500'
            }
          `}
        >
          {i + 1 <= currentStep ? (
            i + 1 < currentStep ? <CheckCircle2 className="w-5 h-5" /> : i + 1
          ) : i + 1}
        </div>
        {i < totalSteps - 1 && (
          <div 
            className={`
              w-12 h-1 mx-1 rounded-full transition-all duration-300
              ${i + 1 < currentStep ? 'bg-nexus-primary' : 'bg-gray-200'}
            `}
          />
        )}
      </div>
    ))}
  </div>
);

// 模板卡片组件
const TemplateCard: React.FC<{
  template: TemplateStyle;
  isSelected: boolean;
  onSelect: () => void;
}> = ({ template, isSelected, onSelect }) => {
  const preview = TEMPLATE_PREVIEWS[template];
  
  return (
    <button
      onClick={onSelect}
      className={`
        group relative p-4 rounded-2xl border-2 transition-all duration-300
        hover:scale-[1.02] hover:shadow-xl
        ${isSelected 
          ? 'border-nexus-primary shadow-lg ring-2 ring-nexus-primary/20' 
          : 'border-gray-200 hover:border-nexus-primary/50'
        }
        bg-white
      `}
    >
      {/* 预览区域 - 模拟 PPT 预览 */}
      <div 
        className={`
          relative w-full aspect-[16/10] rounded-xl overflow-hidden mb-3
          bg-gradient-to-br ${preview.gradient}
        `}
      >
        {/* 模拟 PPT 内容 */}
        <div className="absolute inset-0 p-3 flex flex-col">
          <div 
            className="w-2/3 h-2 rounded-full mb-2"
            style={{ backgroundColor: `${preview.textColor}40` }}
          />
          <div 
            className="w-1/2 h-1.5 rounded-full mb-4"
            style={{ backgroundColor: `${preview.textColor}30` }}
          />
          <div className="flex-1 flex gap-2">
            <div 
              className="w-1/2 rounded-lg"
              style={{ backgroundColor: `${preview.textColor}15` }}
            />
            <div className="w-1/2 flex flex-col gap-1">
              <div 
                className="h-1 rounded-full w-full"
                style={{ backgroundColor: `${preview.textColor}25` }}
              />
              <div 
                className="h-1 rounded-full w-3/4"
                style={{ backgroundColor: `${preview.textColor}25` }}
              />
              <div 
                className="h-1 rounded-full w-4/5"
                style={{ backgroundColor: `${preview.textColor}25` }}
              />
            </div>
          </div>
        </div>
        
        {/* 模板图标 */}
        <div 
          className="absolute top-2 right-2 p-1.5 rounded-lg"
          style={{ backgroundColor: `${preview.textColor}20`, color: preview.textColor }}
        >
          {TEMPLATE_ICONS[template]}
        </div>
      </div>
      
      {/* 模板信息 */}
      <div className="text-left">
        <div className="font-semibold text-gray-800 group-hover:text-nexus-primary transition-colors">
          {TEMPLATE_NAMES[template]}
        </div>
        <div className="text-xs text-gray-500 mt-0.5">
          {preview.description}
        </div>
      </div>
      
      {/* 选中标记 */}
      {isSelected && (
        <div className="absolute -top-2 -right-2 w-7 h-7 bg-nexus-primary rounded-full flex items-center justify-center shadow-lg">
          <CheckCircle2 className="w-5 h-5 text-white" />
        </div>
      )}
    </button>
  );
};

export const PPTCreationWizard: React.FC<PPTCreationWizardProps> = ({ isOpen, onClose }) => {
  const { isGenerating, generationProgress, generationMessage, setGenerationProgress } = useLegacyPPTStore();
  
  // createPPT placeholder - 实际实现需要调用后端 API
  const createPPT = async (params: { topic: string; pageCount: number; template: TemplateStyle; requirements: string }) => {
    setGenerationProgress(10, '正在生成大纲...');
    // TODO: 实际调用后端 API
    console.log('Creating PPT with params:', params);
  };
  
  const [step, setStep] = useState(1);
  const [topic, setTopic] = useState('');
  const [pageCount, setPageCount] = useState(8);
  const [template, setTemplate] = useState<TemplateStyle>('modern');
  const [requirements, setRequirements] = useState('');
  
  // 重置状态
  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setTopic('');
      setPageCount(8);
      setTemplate('modern');
      setRequirements('');
    }
  }, [isOpen]);
  
  if (!isOpen) return null;
  
  const handleCreate = () => {
    if (!topic.trim()) return;
    
    createPPT({
      topic: topic.trim(),
      pageCount,
      template,
      requirements: requirements.trim()
    });
    
    setStep(3);
  };
  
  const handleClose = () => {
    if (!isGenerating) {
      onClose();
    }
  };

  // generationProgress 在旧版 store 中已经是 0-100 的百分比
  const progressPercent = generationProgress || 0;
  
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* 背景遮罩 - 加深且带模糊 */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />
      
      {/* 模态框 */}
      <div className="relative bg-white rounded-3xl shadow-2xl w-full max-w-3xl mx-4 overflow-hidden animate-in zoom-in-95 duration-200">
        {/* 顶部装饰渐变 */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-nexus-primary via-orange-400 to-amber-500" />
        
        {/* 头部 */}
        <div className="flex items-center justify-between px-8 py-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-nexus-primary/10 rounded-xl">
              <Presentation className="w-6 h-6 text-nexus-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">
                {step === 1 && '创建演示文稿'}
                {step === 2 && '选择模板风格'}
                {step === 3 && '正在生成'}
              </h2>
              <p className="text-sm text-gray-500">
                {step === 1 && '输入主题，AI 将为您创建专业 PPT'}
                {step === 2 && '选择最适合您内容的视觉风格'}
                {step === 3 && '请稍候，AI 正在创作中...'}
              </p>
            </div>
          </div>
          {!isGenerating && (
            <button
              onClick={handleClose}
              className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          )}
        </div>
        
        {/* 步骤指示器 */}
        {step !== 3 && (
          <div className="px-8 pt-6">
            <StepIndicator currentStep={step} totalSteps={2} />
          </div>
        )}
        
        {/* 内容区域 */}
        <div className="px-8 py-6 max-h-[60vh] overflow-y-auto">
          {/* 步骤 1: 输入主题 */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
                  <FileText className="w-4 h-4" />
                  演示文稿主题
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full px-5 py-4 rounded-2xl bg-gray-50 border-2 border-gray-200 text-gray-800 
                           focus:outline-none focus:border-nexus-primary focus:bg-white
                           transition-all duration-200 text-lg placeholder:text-gray-400"
                  placeholder="例如：2024年度工作总结、产品发布会、AI技术趋势分析..."
                  autoFocus
                />
              </div>
              
              <div>
                <label className="flex items-center justify-between text-sm font-semibold text-gray-700 mb-3">
                  <span>幻灯片数量</span>
                  <span className="text-nexus-primary font-bold text-lg">{pageCount} 页</span>
                </label>
                <div className="relative">
                  <input
                    type="range"
                    min={4}
                    max={20}
                    value={pageCount}
                    onChange={(e) => setPageCount(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer
                             [&::-webkit-slider-thumb]:appearance-none
                             [&::-webkit-slider-thumb]:w-6
                             [&::-webkit-slider-thumb]:h-6
                             [&::-webkit-slider-thumb]:bg-nexus-primary
                             [&::-webkit-slider-thumb]:rounded-full
                             [&::-webkit-slider-thumb]:cursor-pointer
                             [&::-webkit-slider-thumb]:shadow-lg
                             [&::-webkit-slider-thumb]:transition-transform
                             [&::-webkit-slider-thumb]:hover:scale-110"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-2">
                    <span>4 页</span>
                    <span>20 页</span>
                  </div>
                </div>
              </div>
              
              <div>
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
                  <Sparkles className="w-4 h-4" />
                  额外要求
                  <span className="text-gray-400 font-normal">（可选）</span>
                </label>
                <textarea
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  rows={3}
                  className="w-full px-5 py-4 rounded-2xl bg-gray-50 border-2 border-gray-200 text-gray-800 
                           focus:outline-none focus:border-nexus-primary focus:bg-white
                           transition-all duration-200 resize-none placeholder:text-gray-400"
                  placeholder="例如：需要包含数据图表、重点介绍技术细节、风格偏科技感..."
                />
              </div>
            </div>
          )}
          
          {/* 步骤 2: 选择模板 */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {(['modern', 'minimal', 'creative', 'nature', 'dark'] as TemplateStyle[]).map((t) => (
                  <TemplateCard
                    key={t}
                    template={t}
                    isSelected={template === t}
                    onSelect={() => setTemplate(t)}
                  />
                ))}
              </div>
              
              {/* 已选信息卡片 */}
              <div className="bg-gradient-to-r from-nexus-primary/5 to-orange-50 rounded-2xl p-5 border border-nexus-primary/10">
                <div className="flex items-center gap-4">
                  <div 
                    className={`
                      w-16 h-10 rounded-lg bg-gradient-to-br ${TEMPLATE_PREVIEWS[template].gradient}
                      flex items-center justify-center
                    `}
                  >
                    <div className="text-white">
                      {TEMPLATE_ICONS[template]}
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800">
                      {TEMPLATE_NAMES[template]}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {topic} · {pageCount} 页
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* 步骤 3: 生成进度 */}
          {step === 3 && (
            <div className="py-8">
              <div className="flex flex-col items-center">
                {/* 动画 Logo */}
                <div className="relative mb-8">
                  <div className="w-24 h-24 bg-gradient-to-br from-nexus-primary to-orange-400 rounded-3xl flex items-center justify-center shadow-2xl shadow-nexus-primary/30">
                    <Wand2 className="w-12 h-12 text-white animate-pulse" />
                  </div>
                  <div className="absolute -inset-2 bg-gradient-to-br from-nexus-primary/20 to-orange-400/20 rounded-[2rem] -z-10 animate-ping" />
                </div>
                
                {/* 状态文字 */}
                <h3 className="text-2xl font-bold text-gray-800 mb-2">
                  {generationMessage || 'AI 正在思考...'}
                </h3>
                
                {generationProgress > 0 && (
                  <>
                    <p className="text-gray-500 mb-6">
                      进度 {generationProgress}%
                    </p>
                    
                    {/* 进度条 */}
                    <div className="w-full max-w-md">
                      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-nexus-primary to-orange-400 rounded-full transition-all duration-500 ease-out"
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                      <p className="text-center text-sm text-gray-400 mt-2">
                        {Math.round(progressPercent)}% 完成
                      </p>
                    </div>
                  </>
                )}
                
                {/* 提示信息 */}
                <div className="mt-8 bg-gray-50 rounded-2xl p-5 text-center max-w-md">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">正在进行的工作：</span>
                    <br />
                    📝 生成大纲结构 → 🎨 创作配图 → 📊 排版设计
                  </p>
                  <p className="text-xs text-gray-400 mt-3">
                    预计需要 1-2 分钟，请耐心等待
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* 底部按钮 */}
        {step !== 3 && (
          <div className="flex items-center justify-between px-8 py-5 border-t border-gray-100 bg-gray-50/50">
            {step === 2 ? (
              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                上一步
              </button>
            ) : (
              <div />
            )}
            
            {step === 1 ? (
              <button
                onClick={() => setStep(2)}
                disabled={!topic.trim()}
                className={`
                  flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all duration-200
                  ${topic.trim()
                    ? 'bg-nexus-primary text-white hover:bg-nexus-primary/90 shadow-lg shadow-nexus-primary/30 hover:shadow-xl'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }
                `}
              >
                下一步
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleCreate}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-nexus-primary to-orange-500 text-white font-semibold 
                         hover:shadow-xl hover:shadow-nexus-primary/30 transition-all duration-200 hover:scale-[1.02]"
              >
                <Wand2 className="w-5 h-5" />
                开始生成
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PPTCreationWizard;
