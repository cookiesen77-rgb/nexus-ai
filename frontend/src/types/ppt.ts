/**
 * PPT 相关类型定义
 */

// 幻灯片布局类型
export type SlideLayout = 
  | 'title'
  | 'title_content'
  | 'title_image'
  | 'two_column'
  | 'image_only'
  | 'section'
  | 'conclusion';

// 模板风格
export type TemplateStyle = 
  | 'modern'
  | 'minimal'
  | 'creative'
  | 'nature'
  | 'dark'
  | 'banana_template_y'
  | 'banana_template_vector_illustration'
  | 'banana_template_glass'
  | 'banana_template_b'
  | 'banana_template_s'
  | 'banana_template_academic';

// 单张幻灯片
export interface Slide {
  id: string;
  order: number;
  layout: SlideLayout;
  title: string;
  content: string;
  imageBase64: string;
  imagePrompt: string;
  notes: string;
}

// 演示文稿
export interface Presentation {
  id: string;
  title: string;
  topic: string;
  template: TemplateStyle;
  slides: Slide[];
  createdAt: string;
  updatedAt: string;
}

// PPT 模板
export interface PPTTemplate {
  id: string;
  name: string;
  nameZh: string;
  description: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  fonts: {
    title: string;
    body: string;
  };
}

// 创建 PPT 请求
export interface CreatePPTRequest {
  topic: string;
  pageCount: number;
  template: TemplateStyle;
  requirements?: string;
}

// PPT 进度信息
export interface PPTProgress {
  stage: 'starting' | 'generating_outline' | 'outline_complete' | 'generating_image' | 'images_complete' | 'complete';
  current: number;
  total: number;
  message: string;
}

// PPT WebSocket 消息类型
export type PPTMessageType = 
  | 'ppt_progress'
  | 'ppt_complete'
  | 'ppt_error'
  | 'ppt_templates'
  | 'ppt_slide_updated'
  | 'ppt_exported';

// PPT WebSocket 消息
export interface PPTMessage {
  type: PPTMessageType;
  presentation?: Presentation;
  slide?: Slide;
  slideIndex?: number;
  templates?: PPTTemplate[];
  progress?: PPTProgress;
  error?: string;
  path?: string;
  downloadUrl?: string;
}

// 模板预览配置（使用渐变色代替 emoji）
export const TEMPLATE_PREVIEWS: Record<TemplateStyle, { 
  gradient: string; 
  bgColor: string;
  primaryColor: string;
  textColor: string;
  description: string;
  previewImage?: string;
}> = {
  modern: {
    gradient: 'from-blue-600 to-indigo-700',
    bgColor: '#1E40AF',
    primaryColor: '#3B82F6',
    textColor: '#FFFFFF',
    description: '专业商务风格'
  },
  minimal: {
    gradient: 'from-slate-100 to-slate-200',
    bgColor: '#F8FAFC',
    primaryColor: '#475569',
    textColor: '#1E293B',
    description: '简洁学术风格'
  },
  creative: {
    gradient: 'from-violet-500 to-fuchsia-500',
    bgColor: '#7C3AED',
    primaryColor: '#EC4899',
    textColor: '#FFFFFF',
    description: '活力创意风格'
  },
  nature: {
    gradient: 'from-emerald-500 to-teal-600',
    bgColor: '#059669',
    primaryColor: '#10B981',
    textColor: '#FFFFFF',
    description: '清新自然风格'
  },
  dark: {
    gradient: 'from-slate-800 to-zinc-900',
    bgColor: '#18181B',
    primaryColor: '#06B6D4',
    textColor: '#F4F4F5',
    description: '深色科技风格'
  },
  banana_template_y: {
    gradient: 'from-amber-200 to-amber-300',
    bgColor: '#FDE68A',
    primaryColor: '#B45309',
    textColor: '#111827',
    description: '复古卷轴（Banana 模板）',
    previewImage: '/ppt-templates/banana/template_y.png',
  },
  banana_template_vector_illustration: {
    gradient: 'from-fuchsia-200 to-violet-200',
    bgColor: '#F5D0FE',
    primaryColor: '#7C3AED',
    textColor: '#111827',
    description: '矢量插画（Banana 模板）',
    previewImage: '/ppt-templates/banana/template_vector_illustration.png',
  },
  banana_template_glass: {
    gradient: 'from-slate-200 to-slate-300',
    bgColor: '#E2E8F0',
    primaryColor: '#0EA5E9',
    textColor: '#111827',
    description: '拟物玻璃（Banana 模板）',
    previewImage: '/ppt-templates/banana/template_glass.png',
  },
  banana_template_b: {
    gradient: 'from-blue-200 to-indigo-200',
    bgColor: '#BFDBFE',
    primaryColor: '#2563EB',
    textColor: '#111827',
    description: '科技蓝（Banana 模板）',
    previewImage: '/ppt-templates/banana/template_b.png',
  },
  banana_template_s: {
    gradient: 'from-slate-100 to-slate-200',
    bgColor: '#F1F5F9',
    primaryColor: '#334155',
    textColor: '#111827',
    description: '简约商务（Banana 模板）',
    previewImage: '/ppt-templates/banana/template_s.png',
  },
  banana_template_academic: {
    gradient: 'from-emerald-100 to-teal-100',
    bgColor: '#D1FAE5',
    primaryColor: '#047857',
    textColor: '#111827',
    description: '学术报告（Banana 模板）',
    previewImage: '/ppt-templates/banana/template_academic.jpg',
  },
};

// 模板中文名称
export const TEMPLATE_NAMES: Record<TemplateStyle, string> = {
  modern: '现代商务',
  minimal: '简约学术',
  creative: '创意营销',
  nature: '自然环保',
  dark: '深色科技',
  banana_template_y: '复古卷轴',
  banana_template_vector_illustration: '矢量插画',
  banana_template_glass: '拟物玻璃',
  banana_template_b: '科技蓝',
  banana_template_s: '简约商务',
  banana_template_academic: '学术报告',
};

// 布局中文名称
export const LAYOUT_NAMES: Record<SlideLayout, string> = {
  title: '标题页',
  title_content: '标题+正文',
  title_image: '标题+图片',
  two_column: '左右分栏',
  image_only: '纯图片',
  section: '章节页',
  conclusion: '总结页'
};

