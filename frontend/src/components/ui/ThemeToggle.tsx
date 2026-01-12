import { Sun, Moon } from 'lucide-react'
import { useThemeStore } from '@/stores/themeStore'
import { Button } from './Button'
import { Tooltip } from './Tooltip'

export function ThemeToggle() {
  const { theme, toggleTheme } = useThemeStore()

  return (
    <Tooltip content={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
      <Button variant="icon" onClick={toggleTheme}>
        {theme === 'dark' ? (
          <Sun size={16} />
        ) : (
          <Moon size={16} />
        )}
      </Button>
    </Tooltip>
  )
}

