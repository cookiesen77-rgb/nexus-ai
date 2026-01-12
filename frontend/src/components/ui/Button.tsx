import { forwardRef, ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'ghost' | 'icon'
  size?: 'sm' | 'md' | 'lg'
  children: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'default', size = 'md', className = '', children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center transition-colors disabled:opacity-50'
    
    const variants = {
      default: 'bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] text-[var(--text)]',
      primary: 'bg-[var(--accent)] hover:opacity-90 text-white',
      ghost: 'hover:bg-[var(--bg-hover)] text-[var(--text)]',
      icon: 'hover:bg-[var(--bg-hover)] text-[var(--text-muted)] hover:text-[var(--text)] p-1',
    }

    const sizes = {
      sm: 'h-6 px-2 text-xs',
      md: 'h-7 px-3 text-sm',
      lg: 'h-8 px-4 text-sm',
    }

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${variant !== 'icon' ? sizes[size] : ''} ${className}`}
        {...props}
      >
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

