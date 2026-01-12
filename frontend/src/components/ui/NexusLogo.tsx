/**
 * Nexus AI Logo 组件
 * 使用透明背景的矢量图，暗色模式自动反色
 */
import React from 'react'

interface NexusLogoProps {
  size?: number
  className?: string
}

const NexusLogo = ({ size = 32, className = '' }: NexusLogoProps) => {
  return (
    <img 
      src="/nexus-logo.png" 
      alt="Nexus AI"
      width={size}
      height={size}
      className={`dark:invert ${className}`}
      style={{ 
        objectFit: 'contain',
      }}
    />
  )
}

export default NexusLogo
