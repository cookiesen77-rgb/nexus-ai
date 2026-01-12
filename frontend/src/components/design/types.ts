/**
 * 设计模块类型定义
 */

export type CanvasElementType = 'image' | 'text' | 'shape' | 'path' | 'image-generator' | 'video-generator' | 'video' | 'connector'

export interface CanvasElement {
  id: string
  type: CanvasElementType
  x: number
  y: number
  name?: string
  content?: string
  width?: number
  height?: number
  hidden?: boolean
  locked?: boolean
  color?: string
  shapeType?: 'square' | 'circle' | 'triangle' | 'star' | 'message' | 'arrow-left' | 'arrow-right'
  fontSize?: number
  fontFamily?: string
  points?: { x: number; y: number }[]
  strokeWidth?: number
  referenceImageId?: string
  groupId?: string
  linkedElements?: string[]
  connectorFrom?: string
  connectorTo?: string
  connectorStyle?: 'solid' | 'dashed'
}

export type Resolution = '1K' | '2K' | '4K'
export type AspectRatio = '1:1' | '4:3' | '16:9' | '9:16' | '3:4'

export interface DesignProject {
  id: string
  title: string
  description?: string
  thumbnail?: string
  userId?: string
  createdAt: string
  updatedAt: string
}
