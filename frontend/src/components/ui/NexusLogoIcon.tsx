/**
 * Nexus AI Icon 组件
 * 使用透明背景的矢量图，暗色模式自动反色
 */
import React from 'react'

interface NexusLogoIconProps {
  size?: number
  className?: string
}

const NexusLogoIcon = ({ size = 32, className = '' }: NexusLogoIconProps) => {
  return (
    <img 
      src="/nexus-logo.svg" 
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

export default NexusLogoIcon
