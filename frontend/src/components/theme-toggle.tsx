import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/theme-context';
import clsx from 'clsx';

interface ThemeToggleProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ThemeToggle = ({ className, size = 'md' }: ThemeToggleProps) => {
  const { theme, toggleTheme } = useTheme();

  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
  };

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  return (
    <button
      onClick={toggleTheme}
      className={clsx(
        'inline-flex items-center justify-center rounded-xl border transition-all',
        'bg-white dark:bg-slate-800',
        'border-slate-200 dark:border-slate-700',
        'text-slate-700 dark:text-slate-300',
        'hover:bg-slate-50 dark:hover:bg-slate-700',
        'hover:border-slate-300 dark:hover:border-slate-600',
        'focus:outline-none focus:ring-2 focus:ring-slate-400 dark:focus:ring-slate-500 focus:ring-offset-2',
        sizeClasses[size],
        className,
      )}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <Moon className={iconSizes[size]} />
      ) : (
        <Sun className={iconSizes[size]} />
      )}
    </button>
  );
};


