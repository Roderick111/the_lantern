/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        parchment: {
          50: '#fefdfb',
          100: '#fdf9f0',
          200: '#f5eedd',
        },
      },
      fontFamily: {
        serif: ['IBM Plex Serif', 'Crimson Text', 'Georgia', 'serif'],
        sans: ['IBM Plex Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Courier New', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      keyframes: {
        // Milestone 6: Phase transition animations
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-out': {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'slide-in-left': {
          '0%': { opacity: '0', transform: 'translateX(-20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        // Milestone 6: Toast animations
        'toast-enter': {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'toast-progress': {
          '0%': { width: '100%' },
          '100%': { width: '0%' },
        },
        // Milestone 6: Contradiction animations
        'contradiction-pulse': {
          '0%, 100%': {
            borderColor: 'rgb(251 191 36)', // amber-400
            boxShadow: '0 0 0 0 rgba(251, 191, 36, 0.4)',
          },
          '50%': {
            borderColor: 'rgb(245 158 11)', // amber-500
            boxShadow: '0 0 0 4px rgba(251, 191, 36, 0)',
          },
        },
        'contradiction-highlight': {
          '0%': {
            backgroundColor: 'rgba(251, 191, 36, 0.3)',
          },
          '100%': {
            backgroundColor: 'rgba(251, 191, 36, 0)',
          },
        },
        'shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
        // Milestone 6: Metric card animations
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        // Milestone 6: IP counter dot animation
        'ip-dot-pulse': {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.3)', opacity: '0.7' },
        },
      },
      animation: {
        // Phase transitions
        'fade-in': 'fade-in 0.3s ease-out',
        'fade-out': 'fade-out 0.3s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-down': 'slide-down 0.3s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'slide-in-left': 'slide-in-left 0.3s ease-out',
        // Toast
        'toast-enter': 'toast-enter 0.3s ease-out',
        'toast-progress': 'toast-progress 5s linear',
        // Contradiction
        'contradiction-pulse': 'contradiction-pulse 2s ease-in-out infinite',
        'contradiction-highlight': 'contradiction-highlight 1s ease-out',
        'shake': 'shake 0.5s ease-in-out',
        // Metric card
        'scale-in': 'scale-in 0.3s ease-out',
        'pulse-subtle': 'pulse-subtle 2s ease-in-out infinite',
        // IP counter
        'ip-dot-pulse': 'ip-dot-pulse 0.6s ease-in-out',
      },
    },
  },
  future: {
    hoverOnlyWhenSupported: true,
  },
  plugins: [],
}
