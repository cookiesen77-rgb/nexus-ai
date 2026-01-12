import React, { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  viewportRef?: React.RefObject<HTMLDivElement>
}

const ScrollArea = forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ className, children, viewportRef, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('relative overflow-hidden', className)} {...props}>
        <div 
          ref={viewportRef}
          className="h-full w-full overflow-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-border"
        >
          {children}
        </div>
      </div>
    )
  }
)

ScrollArea.displayName = 'ScrollArea'

export { ScrollArea }

