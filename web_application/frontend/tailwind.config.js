/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:  ['var(--font-sans)',  'DM Sans',          'system-ui', 'sans-serif'],
        serif: ['var(--font-serif)', 'Instrument Serif', 'Georgia',   'serif'],
        mono:  ['var(--font-mono)',  'DM Mono',          'Menlo',     'monospace'],
      },
      colors: {
        border:      'hsl(var(--border))',
        input:       'hsl(var(--input))',
        ring:        'hsl(var(--ring))',
        background:  'hsl(var(--background))',
        foreground:  'hsl(var(--foreground))',
        surface:     'hsl(var(--surface))',
        primary: {
          DEFAULT:    'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT:    'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT:    'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT:    'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT:    'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        card: {
          DEFAULT:    'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        success:  'hsl(var(--success))',
        warning:  'hsl(var(--warning))',
      },
      borderRadius: {
        sm:   'calc(var(--radius) - 4px)',
        md:   'calc(var(--radius) - 2px)',
        lg:   'var(--radius)',
        xl:   'calc(var(--radius) + 4px)',
        '2xl':'calc(var(--radius) + 8px)',
        '3xl':'calc(var(--radius) + 14px)',
      },
      backgroundImage: {
        'gradient-radial':   'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':    'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'shimmer':           'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.04) 50%, transparent 100%)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'slide-in-right': {
          from: { opacity: '0', transform: 'translateX(-14px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
        'scale-in': {
          '0%':   { opacity: '0', transform: 'scale(0.5)' },
          '70%':  { transform: 'scale(1.08)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(99,102,241,0)' },
          '50%':      { boxShadow: '0 0 0 8px rgba(99,102,241,0.18)' },
        },
        'shimmer': {
          from: { backgroundPosition: '-200% 0' },
          to:   { backgroundPosition:  '200% 0' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-14px)' },
        },
        'orb-breathe': {
          '0%, 100%': { opacity: '0.35', transform: 'scale(1)' },
          '50%':      { opacity: '0.65', transform: 'scale(1.12)' },
        },
        'ping-slow': {
          '0%':       { transform: 'scale(1)',   opacity: '0.6' },
          '70%, 100%':{ transform: 'scale(1.9)', opacity: '0' },
        },
        'track-grow': {
          from: { height: '0%' },
          to:   { height: 'var(--track-pct)' },
        },
        'counter-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-up':         'fade-up 0.5s cubic-bezier(0.22,1,0.36,1)',
        'fade-up-delay':   'fade-up 0.5s cubic-bezier(0.22,1,0.36,1) 0.15s both',
        'fade-up-delay2':  'fade-up 0.5s cubic-bezier(0.22,1,0.36,1) 0.3s both',
        'fade-in':         'fade-in 0.3s ease-out',
        'slide-in-right':  'slide-in-right 0.4s cubic-bezier(0.22,1,0.36,1)',
        'scale-in':        'scale-in 0.35s cubic-bezier(0.34,1.56,0.64,1)',
        'glow-pulse':      'glow-pulse 2.5s ease-in-out infinite',
        'shimmer':         'shimmer 2.2s linear infinite',
        'float':           'float 6s ease-in-out infinite',
        'orb-breathe':     'orb-breathe 5s ease-in-out infinite',
        'ping-slow':       'ping-slow 2s cubic-bezier(0,0,0.2,1) infinite',
        'counter-up':      'counter-up 0.5s cubic-bezier(0.22,1,0.36,1)',
      },
      boxShadow: {
        'glow-indigo':     '0 0 32px rgba(99,102,241,0.28)',
        'glow-indigo-sm':  '0 0 14px rgba(99,102,241,0.22)',
        'glow-emerald':    '0 0 20px rgba(16,185,129,0.22)',
        'glow-amber':      '0 0 20px rgba(245,158,11,0.22)',
        'glow-red':        '0 0 20px rgba(248,113,113,0.22)',
        'card':            '0 1px 3px rgba(0,0,0,0.5)',
        'card-hover':      '0 6px 24px rgba(0,0,0,0.55), 0 0 0 1px rgba(99,102,241,0.18)',
        'elevation-1':     '0 2px 8px rgba(0,0,0,0.45)',
        'elevation-2':     '0 8px 32px rgba(0,0,0,0.55)',
        'input-focus':     '0 0 0 3px rgba(99,102,241,0.2)',
      },
    },
  },
  plugins: [],
}
