/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        ink: '#070b12',
        deep: '#0a1018',
        panel: '#0e1622',
        line: '#1e2a3a',
        calm: '#5eead4',
        warm: '#fbbf24',
        iris: '#a78bfa',
      },
      fontFamily: {
        sans: ['Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Mono', 'Consolas', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 18px 40px -24px rgba(0, 0, 0, 0.9)',
        glow: '0 0 0 1px rgba(94, 234, 212, 0.28), 0 12px 40px -16px rgba(94, 234, 212, 0.35)',
        soft: 'inset 0 1px 0 rgba(255, 255, 255, 0.06)',
      },
      keyframes: {
        floaty: {
          '0%, 100%': { transform: 'translate3d(0, 0, 0) scale(1)' },
          '33%': { transform: 'translate3d(3%, -4%, 0) scale(1.06)' },
          '66%': { transform: 'translate3d(-3%, 3%, 0) scale(0.97)' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.55' },
          '50%': { opacity: '1' },
        },
        nudge: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(4px)' },
        },
        nudgeUp: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        riseIn: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        floaty: 'floaty 22s ease-in-out infinite',
        'floaty-slow': 'floaty 34s ease-in-out infinite',
        breathe: 'breathe 4s ease-in-out infinite',
        nudge: 'nudge 1.8s ease-in-out infinite',
        'nudge-up': 'nudgeUp 1.8s ease-in-out infinite',
        riseIn: 'riseIn 0.45s cubic-bezier(0.22, 0.61, 0.36, 1) both',
      },
    },
  },
  plugins: [],
}
