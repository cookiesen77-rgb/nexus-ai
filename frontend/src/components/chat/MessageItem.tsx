import { Message, FileAttachment } from '@/types'
import { Loader2, User, Copy, Check, RefreshCw, FileText, File } from 'lucide-react'
import { useState } from 'react'
import NexusLogo from '@/components/ui/NexusLogo'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useTheme } from '@/hooks/useTheme'

// 附件预览组件
const AttachmentPreview = ({ attachment }: { attachment: FileAttachment }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  
  if (attachment.type === 'image' && attachment.previewUrl) {
    return (
      <div className="relative group">
        <img 
          src={attachment.previewUrl} 
          alt={attachment.name}
          className={`rounded-lg cursor-pointer transition-all ${
            isExpanded ? 'max-w-full max-h-96' : 'max-w-[200px] max-h-[150px]'
          } object-cover border border-white/20`}
          onClick={() => setIsExpanded(!isExpanded)}
        />
        <div className="absolute bottom-1 left-1 right-1 bg-black/60 text-white text-xs px-2 py-1 rounded truncate opacity-0 group-hover:opacity-100 transition-opacity">
          {attachment.name}
        </div>
      </div>
    )
  }
  
  // 非图片文件显示图标和文件名
  const getFileIcon = () => {
    if (attachment.type === 'document') return <FileText size={20} />
    return <File size={20} />
  }
  
  return (
    <div className="flex items-center gap-2 bg-white/10 px-3 py-2 rounded-lg">
      <div className="text-white/70">{getFileIcon()}</div>
      <div className="flex flex-col">
        <span className="text-sm text-white truncate max-w-[150px]">{attachment.name}</span>
        <span className="text-xs text-white/50">
          {(attachment.size / 1024).toFixed(1)} KB
        </span>
      </div>
    </div>
  )
}

interface MessageItemProps {
  message: Message
}

const MessageItem = ({ message }: MessageItemProps) => {
  const { theme } = useTheme()
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  const isAgent = message.role === 'agent'
  const isStreaming = message.streaming

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '')
      const codeString = String(children).replace(/\n$/, '')
      
      if (!inline && match) {
        return (
          <div className="relative group my-4">
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => navigator.clipboard.writeText(codeString)}
                className="p-1.5 rounded-md bg-muted hover:bg-accent transition-colors"
              >
                <Copy size={14} className="text-muted-foreground" />
              </button>
            </div>
            <SyntaxHighlighter
              style={theme === 'dark' ? oneDark : oneLight}
              language={match[1]}
              PreTag="div"
              className="rounded-xl !bg-muted !p-4 text-sm"
              {...props}
            >
              {codeString}
            </SyntaxHighlighter>
          </div>
        )
      }
      
      return (
        <code className="px-1.5 py-0.5 rounded-md bg-muted text-sm font-mono" {...props}>
          {children}
        </code>
      )
    },
    p: ({ children }: any) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
    ul: ({ children }: any) => <ul className="list-disc pl-5 mb-3 last:mb-0 space-y-1">{children}</ul>,
    ol: ({ children }: any) => <ol className="list-decimal pl-5 mb-3 last:mb-0 space-y-1">{children}</ol>,
    li: ({ children }: any) => <li className="leading-relaxed">{children}</li>,
    a: ({ href, children }: any) => (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="text-primary hover:underline"
      >
        {children}
      </a>
    ),
    h1: ({ children }: any) => <h1 className="text-xl font-semibold mb-3 mt-4 first:mt-0">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-lg font-semibold mb-2 mt-4 first:mt-0">{children}</h2>,
    h3: ({ children }: any) => <h3 className="text-base font-semibold mb-2 mt-3 first:mt-0">{children}</h3>,
    blockquote: ({ children }: any) => (
      <blockquote className="border-l-4 border-primary/30 pl-4 my-3 text-muted-foreground italic">
        {children}
      </blockquote>
    ),
  }

  if (isUser) {
    const hasAttachments = message.attachments && message.attachments.length > 0
    
    return (
      <div className="flex justify-end">
        <div className="flex items-start gap-3 max-w-[80%]">
          <div className="flex flex-col gap-2 items-end">
            {/* 附件预览（图片/文件） */}
            {hasAttachments && (
              <div className="flex flex-wrap gap-2 justify-end">
                {message.attachments!.map((attachment) => (
                  <AttachmentPreview key={attachment.id} attachment={attachment} />
                ))}
              </div>
            )}
            {/* 文字内容 */}
            {message.content && (
              <div className="bg-foreground text-background px-4 py-3 rounded-2xl rounded-br-md">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
              </div>
            )}
          </div>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0">
            <User size={16} className="text-white" />
          </div>
        </div>
      </div>
    )
  }

  if (isAgent) {
    return (
      <div className="flex justify-start">
        <div className="flex items-start gap-3 max-w-[80%]">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            {isStreaming ? (
              <Loader2 size={16} className="text-primary animate-spin" />
            ) : (
              <NexusLogo size={20} className="text-primary" />
            )}
          </div>
          <div className="flex-1">
            <div className="bg-card border border-border px-4 py-3 rounded-2xl rounded-bl-md shadow-sm">
              <div className="text-sm text-foreground prose prose-sm dark:prose-invert max-w-none">
                <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {message.content}
                </Markdown>
                {isStreaming && (
                  <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
                )}
              </div>
            </div>
            
            {/* Action buttons */}
            {!isStreaming && (
              <div className="flex items-center gap-2 mt-2 ml-1">
                <button 
                  onClick={handleCopy}
                  className="p-1.5 hover:bg-muted rounded-md transition-colors"
                >
                  {copied ? (
                    <Check size={14} className="text-green-500" />
                  ) : (
                    <Copy size={14} className="text-muted-foreground" />
                  )}
                </button>
                <button className="p-1.5 hover:bg-muted rounded-md transition-colors">
                  <RefreshCw size={14} className="text-muted-foreground" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // System message
  return (
    <div className="flex justify-center">
      <div className="px-4 py-2 rounded-full bg-muted text-sm text-muted-foreground">
        {message.content}
      </div>
    </div>
  )
}

export default MessageItem
