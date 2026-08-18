import React, { forwardRef } from 'react';
import { useTheme } from '../../context/useTheme';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost' | 'terminal' | 'terminal-primary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  type?: 'button' | 'submit' | 'reset';
  /** Tooltip text shown on hover (native browser tooltip) */
  title?: string;
}

const sizeStyles = {
  sm: 'px-3 py-2.5 text-sm md:py-1.5 md:text-xs',
  md: 'px-6 py-3 text-sm md:py-2.5',
  lg: 'px-8 py-4 text-base',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      children,
      onClick,
      disabled = false,
      variant = 'primary',
      size = 'md',
      className = '',
      type = 'button',
      title,
    },
    ref
  ) {
    const { isDark, theme } = useTheme();

    // Theme-aware variant styles
    const variantStyles = {
      primary: 'bg-amber-600 hover:bg-amber-700 text-white border-amber-700 rounded-lg border-2',
      secondary: 'bg-amber-100 hover:bg-amber-200 text-amber-900 border-amber-300 rounded-lg border-2',
      ghost: 'bg-transparent hover:bg-amber-50 text-amber-700 border-transparent rounded-lg border-2',
      terminal: isDark
        ? `bg-gray-900 text-gray-100 border-gray-600 hover:!bg-gray-800 hover:!text-gray-100 hover:!border-gray-200 ${theme.fonts.ui} uppercase tracking-widest rounded-sm border transition-colors duration-200`
        : `bg-gray-50 text-gray-900 border-gray-300 hover:!bg-gray-100 hover:!text-gray-900 hover:!border-gray-400 ${theme.fonts.ui} uppercase tracking-widest rounded-sm border transition-colors duration-200`,
      'terminal-primary': isDark
        ? `bg-amber-900/60 text-white border-amber-600/70 hover:bg-amber-800 hover:border-amber-400 ${theme.fonts.ui} uppercase tracking-widest rounded-sm border shadow-[0_0_10px_rgba(217,119,6,0.1)] hover:shadow-[0_0_15px_rgba(217,119,6,0.2)]`
        : `bg-indigo-600 text-white border-indigo-700 hover:bg-indigo-700 hover:border-indigo-800 ${theme.fonts.ui} uppercase tracking-widest rounded-sm border shadow-md hover:shadow-lg`,
    };

    return (
      <button
        ref={ref}
        type={type}
        onClick={onClick}
        disabled={disabled}
        title={title}
        className={`
          transition-colors duration-100 min-h-[44px] md:min-h-0
          active:scale-[0.97] active:transition-transform
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${className}
        `}
      >
        {children}
      </button>
    );
  }
);
