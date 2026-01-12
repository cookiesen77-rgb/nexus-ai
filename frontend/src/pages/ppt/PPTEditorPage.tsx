/**
 * PPT 编辑器页面
 * 深度集成 Banana Slides 功能到 Nexus
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft,
  Download,
  FileText,
  Image,
  Loader2,
  Plus,
  Trash2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Wand2,
  Edit3,
  Save,
  X,
} from 'lucide-react';

// Types
interface PPTPage {
  id: string;
  order_index: number;
  outline_content: {
    title: string;
    points: string[];
  };
  description_content?: string;
  image_base64?: string;
  status: string;
  part?: string;
}

interface PPTProject {
  id: string;
  name: string;
  status: string;
  pages: PPTPage[];
  outline: any[];
  created_at: string;
  updated_at: string;
}

interface PPTEditorPageProps {
  onClose: () => void;
  initialIdea?: string;
}

const API_BASE = '/api/ppt';

export const PPTEditorPage: React.FC<PPTEditorPageProps> = ({ onClose, initialIdea }) => {
  // State
  const [view, setView] = useState<'create' | 'editor'>('create');
  const [project, setProject] = useState<PPTProject | null>(null);
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [createMode, setCreateMode] = useState<'idea' | 'outline' | 'description'>('idea');
  const [ideaInput, setIdeaInput] = useState(initialIdea || '');
  const [outlineInput, setOutlineInput] = useState('');
  const [descriptionInput, setDescriptionInput] = useState('');
  const [pageCount, setPageCount] = useState(8);
  const [styleInput, setStyleInput] = useState('');

  // Edit state
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState('');

  // API helpers
  const fetchAPI = async (endpoint: string, options?: RequestInit) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error?.message || '请求失败');
    }
    return data.data;
  };

  // Create project
  const handleCreate = async () => {
    setIsLoading(true);
    setError(null);

    try {
      let requestBody: any = {};

      if (createMode === 'idea') {
        if (!ideaInput.trim()) {
          throw new Error('请输入 PPT 主题');
        }
        requestBody = {
          creation_type: 'idea',
          idea_prompt: ideaInput.trim(),
          template_style: styleInput || undefined,
          name: ideaInput.trim().substring(0, 30),
        };
      } else if (createMode === 'outline') {
        if (!outlineInput.trim()) {
          throw new Error('请输入大纲');
        }
        requestBody = {
          creation_type: 'outline',
          outline_text: outlineInput.trim(),
          template_style: styleInput || undefined,
        };
      } else {
        if (!descriptionInput.trim()) {
          throw new Error('请输入描述');
        }
        requestBody = {
          creation_type: 'description',
          description_text: descriptionInput.trim(),
          template_style: styleInput || undefined,
        };
      }

      // Create project
      setLoadingMessage('创建项目...');
      const createResult = await fetchAPI('/projects', {
        method: 'POST',
        body: JSON.stringify(requestBody),
      });

      const projectId = createResult.project_id;

      // Generate outline
      setLoadingMessage('生成大纲...');
      await fetchAPI(`/projects/${projectId}/generate/outline?language=zh`, {
        method: 'POST',
      });

      // Generate descriptions
      setLoadingMessage('生成页面内容...');
      const descTask = await fetchAPI(`/projects/${projectId}/generate/descriptions?language=zh`, {
        method: 'POST',
      });

      // Poll for description completion
      await pollTask(projectId, descTask.task_id, '生成页面内容');

      // Generate images
      setLoadingMessage('生成页面图片...');
      const imageTask = await fetchAPI(`/projects/${projectId}/generate/images`, {
        method: 'POST',
        body: JSON.stringify({ language: 'zh' }),
      });

      // Poll for image completion
      await pollTask(projectId, imageTask.task_id, '生成页面图片');

      // Get final project
      setLoadingMessage('加载项目...');
      const finalProject = await fetchAPI(`/projects/${projectId}`);

      setProject(finalProject);
      setView('editor');
      setSelectedPageIndex(0);

    } catch (err: any) {
      setError(err.message || '创建失败');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  // Poll task status
  const pollTask = async (projectId: string, taskId: string, taskName: string) => {
    const maxAttempts = 60; // 5 minutes max
    let attempts = 0;

    while (attempts < maxAttempts) {
      const task = await fetchAPI(`/projects/${projectId}/tasks/${taskId}`);

      if (task.status === 'COMPLETED') {
        return task;
      } else if (task.status === 'FAILED') {
        throw new Error(`${taskName}失败: ${task.error_message}`);
      }

      // Update loading message with progress
      if (task.progress?.completed !== undefined) {
        setLoadingMessage(`${taskName}... (${task.progress.completed}/${task.progress.total})`);
      }

      await new Promise(resolve => setTimeout(resolve, 5000));
      attempts++;
    }

    throw new Error(`${taskName}超时`);
  };

  // Export handlers
  const handleExportPPTX = async () => {
    if (!project) return;

    try {
      setIsLoading(true);
      setLoadingMessage('导出 PPTX...');

      const result = await fetchAPI(`/projects/${project.id}/export/pptx`);

      // Download file
      const link = document.createElement('a');
      link.href = result.download_url;
      link.download = `${project.name}.pptx`;
      link.click();

    } catch (err: any) {
      setError(err.message || '导出失败');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const handleExportPDF = async () => {
    if (!project) return;

    try {
      setIsLoading(true);
      setLoadingMessage('导出 PDF...');

      const result = await fetchAPI(`/projects/${project.id}/export/pdf`);

      const link = document.createElement('a');
      link.href = result.download_url;
      link.download = `${project.name}.pdf`;
      link.click();

    } catch (err: any) {
      setError(err.message || '导出失败');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  // Regenerate image
  const handleRegenerateImage = async (pageId: string) => {
    if (!project) return;

    try {
      setIsLoading(true);
      setLoadingMessage('重新生成图片...');

      const task = await fetchAPI(`/projects/${project.id}/pages/${pageId}/generate/image?language=zh&force_regenerate=true`, {
        method: 'POST',
      });

      await pollTask(project.id, task.task_id, '重新生成图片');

      // Refresh project
      const updatedProject = await fetchAPI(`/projects/${project.id}`);
      setProject(updatedProject);

    } catch (err: any) {
      setError(err.message || '重新生成失败');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  // Selected page
  const selectedPage = project?.pages[selectedPageIndex];

  // Render create view - 按照设计图样式
  const renderCreateView = () => (
    <div className="h-full flex flex-col bg-[#F5F5F7]">
      {/* Header - 简洁白色 */}
      <header className="flex items-center px-6 py-4 bg-white border-b border-gray-200">
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-800 transition-colors"
        >
          <ArrowLeft size={22} />
        </button>
        <h1 className="flex-1 text-center text-lg font-semibold text-gray-800">创建演示文稿</h1>
        <div className="w-6" />
      </header>

      {/* Content - 居中布局 */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-md space-y-8">
          {/* Cute Logo */}
          <div className="flex flex-col items-center">
            <div className="w-28 h-28 mb-4">
              {/* 可爱的 Nexus Logo - 笑脸样式 */}
              <svg viewBox="0 0 120 120" className="w-full h-full">
                {/* 眼睛 - 小圆点 */}
                <circle cx="42" cy="35" r="4" fill="#333" />
                <circle cx="78" cy="35" r="4" fill="#333" />
                {/* N 字母主体 - 圆润风格 */}
                <path
                  d="M25 85 L25 50 C25 40 35 35 45 45 L75 75 L75 50 C75 40 85 35 95 40 L95 85"
                  fill="none"
                  stroke="#333"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800">创建演示文稿</h2>
          </div>

          {/* Mode selector - 圆角药丸形状 */}
          <div className="flex bg-gray-100 rounded-full p-1">
            {[
              { id: 'idea', label: '一句话生成' },
              { id: 'outline', label: '大纲生成' },
              { id: 'description', label: '文档生成' },
            ].map(mode => (
              <button
                key={mode.id}
                onClick={() => setCreateMode(mode.id as any)}
                className={`flex-1 py-2.5 px-4 rounded-full text-sm font-medium transition-all ${
                  createMode === mode.id
                    ? 'bg-white text-gray-800 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>

          {/* Input area */}
          <div className="space-y-4">
            {createMode === 'idea' && (
              <input
                type="text"
                value={ideaInput}
                onChange={e => setIdeaInput(e.target.value)}
                placeholder="输入主题"
                className="w-full px-5 py-4 rounded-2xl border border-gray-200 bg-white text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 text-base"
              />
            )}

            {createMode === 'outline' && (
              <textarea
                value={outlineInput}
                onChange={e => setOutlineInput(e.target.value)}
                placeholder="输入大纲内容&#10;1. 引言&#10;2. 主要内容&#10;3. 总结"
                rows={6}
                className="w-full px-5 py-4 rounded-2xl border border-gray-200 bg-white text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 text-base resize-none"
              />
            )}

            {createMode === 'description' && (
              <textarea
                value={descriptionInput}
                onChange={e => setDescriptionInput(e.target.value)}
                placeholder="输入详细描述..."
                rows={6}
                className="w-full px-5 py-4 rounded-2xl border border-gray-200 bg-white text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 text-base resize-none"
              />
            )}

            {/* Style selector */}
            <select
              value={styleInput}
              onChange={e => setStyleInput(e.target.value)}
              className="w-full px-5 py-4 rounded-2xl border border-gray-200 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 text-base appearance-none cursor-pointer"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%239CA3AF' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 16px center',
                backgroundSize: '20px',
              }}
            >
              <option value="">选择风格</option>
              <option value="modern">现代简约</option>
              <option value="tech">科技风格</option>
              <option value="business">商务专业</option>
              <option value="creative">创意设计</option>
              <option value="nature">自然清新</option>
            </select>
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm">
              {error}
            </div>
          )}

          {/* Create button - 蓝色圆角按钮 */}
          <button
            onClick={handleCreate}
            disabled={isLoading}
            className="w-full py-4 rounded-full bg-[#7B9EBE] text-white font-medium hover:bg-[#6A8DAD] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-2 text-base"
          >
            {isLoading ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                <span>{loadingMessage || '创建中...'}</span>
              </>
            ) : (
              <span>开始生成</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  // Render editor view
  const renderEditorView = () => {
    if (!project) return null;

    return (
      <div className="h-full flex flex-col bg-[var(--nexus-chat-bg)]">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 className="text-lg font-semibold text-foreground">{project.name}</h1>
            <span className="text-sm text-muted-foreground">
              {project.pages.length} 页
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportPPTX}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Download size={16} />
              <span>导出 PPTX</span>
            </button>
            <button
              onClick={handleExportPDF}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
            >
              <FileText size={16} />
              <span>导出 PDF</span>
            </button>
          </div>
        </header>

        {/* Main content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Slide list */}
          <div className="w-48 border-r border-border bg-card overflow-auto p-2">
            {project.pages.map((page, index) => (
              <button
                key={page.id}
                onClick={() => setSelectedPageIndex(index)}
                className={`w-full aspect-video mb-2 rounded-lg overflow-hidden border-2 transition-all ${
                  selectedPageIndex === index
                    ? 'border-primary ring-2 ring-primary/30'
                    : 'border-transparent hover:border-border'
                }`}
              >
                {page.image_base64 ? (
                  <img
                    src={`data:image/png;base64,${page.image_base64}`}
                    alt={page.outline_content.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-muted flex items-center justify-center">
                    <span className="text-xs text-muted-foreground">{index + 1}</span>
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Preview area */}
          <div className="flex-1 flex flex-col p-6">
            {/* Preview */}
            <div className="flex-1 flex items-center justify-center bg-black/20 rounded-xl overflow-hidden">
              {selectedPage?.image_base64 ? (
                <img
                  src={`data:image/png;base64,${selectedPage.image_base64}`}
                  alt={selectedPage.outline_content.title}
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <div className="text-center text-muted-foreground">
                  <Image size={48} className="mx-auto mb-2 opacity-50" />
                  <p>暂无图片</p>
                </div>
              )}
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-center gap-4 mt-4">
              <button
                onClick={() => setSelectedPageIndex(Math.max(0, selectedPageIndex - 1))}
                disabled={selectedPageIndex === 0}
                className="p-2 rounded-lg hover:bg-muted disabled:opacity-30 transition-colors"
              >
                <ChevronLeft size={24} />
              </button>
              <span className="text-sm text-muted-foreground">
                {selectedPageIndex + 1} / {project.pages.length}
              </span>
              <button
                onClick={() => setSelectedPageIndex(Math.min(project.pages.length - 1, selectedPageIndex + 1))}
                disabled={selectedPageIndex === project.pages.length - 1}
                className="p-2 rounded-lg hover:bg-muted disabled:opacity-30 transition-colors"
              >
                <ChevronRight size={24} />
              </button>
            </div>
          </div>

          {/* Edit panel */}
          <div className="w-80 border-l border-border bg-card overflow-auto p-4">
            {selectedPage && (
              <div className="space-y-4">
                <h3 className="font-semibold text-foreground">页面信息</h3>

                {/* Title */}
                <div>
                  <label className="block text-sm text-muted-foreground mb-1">标题</label>
                  <p className="text-foreground">{selectedPage.outline_content.title}</p>
                </div>

                {/* Points */}
                {selectedPage.outline_content.points.length > 0 && (
                  <div>
                    <label className="block text-sm text-muted-foreground mb-1">要点</label>
                    <ul className="space-y-1">
                      {selectedPage.outline_content.points.map((point, i) => (
                        <li key={i} className="text-sm text-foreground">• {point}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Description */}
                {selectedPage.description_content && (
                  <div>
                    <label className="block text-sm text-muted-foreground mb-1">描述</label>
                    <p className="text-sm text-foreground whitespace-pre-wrap">
                      {selectedPage.description_content.substring(0, 200)}...
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="pt-4 border-t border-border space-y-2">
                  <button
                    onClick={() => handleRegenerateImage(selectedPage.id)}
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg border border-border hover:bg-muted disabled:opacity-50 transition-colors"
                  >
                    <RefreshCw size={16} />
                    <span>重新生成图片</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card p-6 rounded-xl flex items-center gap-3">
              <Loader2 size={24} className="animate-spin text-primary" />
              <span className="text-foreground">{loadingMessage || '处理中...'}</span>
            </div>
          </div>
        )}

        {/* Error toast */}
        {error && (
          <div className="absolute bottom-4 right-4 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 flex items-center gap-2">
            <span>{error}</span>
            <button onClick={() => setError(null)}>
              <X size={16} />
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-background">
      {view === 'create' ? renderCreateView() : renderEditorView()}
    </div>
  );
};

export default PPTEditorPage;

