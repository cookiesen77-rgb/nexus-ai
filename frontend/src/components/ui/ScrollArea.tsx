import { ReactNode, useRef, useEffect } from 'react'

interface ScrollAreaProps {
  children: ReactNode
  className?: string
  autoScroll?: boolean
}

export function ScrollArea({ children, className = '', autoScroll = false }: ScrollAreaProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoScroll && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [children, autoScroll])

  return (
    <div
      ref={ref}
      className={`overflow-auto ${className}`}
    >
      {children}
    </div>
  )
}

