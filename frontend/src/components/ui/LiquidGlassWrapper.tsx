import type { PropsWithChildren, CSSProperties } from 'react'

type WrapperProps = PropsWithChildren<{
  className?: string
  padding?: string
  cornerRadius?: number
  onClick?: () => void
  style?: CSSProperties
}>

/**
 * CSS-based glass effect wrapper - more reliable than WebGL
 * 支持深浅主题
 */
const LiquidGlassWrapper = ({
  children,
  className = '',
  cornerRadius = 42,
  padding = '18px 24px',
  onClick,
  style,
}: WrapperProps) => {
  return (
    <div 
      onClick={onClick} 
      className={`backdrop-blur-md bg-card/60 border border-border shadow-lg hover:shadow-xl transition-all duration-300 ${className}`}
      style={{ 
        cursor: onClick ? 'pointer' : 'default',
        borderRadius: cornerRadius,
        padding,
        ...style 
      }}
    >
      {children}
    </div>
  )
}

export default LiquidGlassWrapper

