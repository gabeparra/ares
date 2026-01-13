import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
  ],
  theme: {
    colors: {
      dark: {
        bg: '#0a0a0f',
        surface: '#1a1a1f',
        surface2: '#262a33',
        surface3: '#2d313c',
        border: 'rgba(255, 255, 255, 0.08)',
        border2: 'rgba(255, 255, 255, 0.12)',
        text: '#e2e8f0',
        text2: '#cbd5e0',
        text3: '#a8a8a8',
        text4: '#d0d0d0',
        text5: '#888',
        text6: '#666',
        text7: '#444',
      },
      red: {
        DEFAULT: '#ff0000',
        light: 'rgba(255, 0, 0, 0.12)',
        'light-2': 'rgba(255, 100, 100, 0.08)',
        accent: 'rgba(255, 200, 200, 0.9)',
        'accent-2': '#ff3333',
        'accent-3': '#ff5a5a',
        'border': 'rgba(255, 0, 0, 0.22)',
        'border-2': 'rgba(255, 0, 0, 0.3)',
        'border-3': 'rgba(255, 0, 0, 0.35)',
        'border-4': 'rgba(255, 0, 0, 0.5)',
        'bg-1': 'rgba(255, 0, 0, 0.04)',
        'bg-2': 'rgba(255, 0, 0, 0.08)',
        'bg-3': 'rgba(255, 0, 0, 0.1)',
        'bg-4': 'rgba(255, 0, 0, 0.15)',
        'bg-5': 'rgba(255, 0, 0, 0.2)',
        'bg-6': 'rgba(255, 0, 0, 0.25)',
        'shadow': 'rgba(255, 0, 0, 0.3)',
      },
      white: {
        'opacity-2': 'rgba(255, 255, 255, 0.02)',
        'opacity-3': 'rgba(255, 255, 255, 0.03)',
        'opacity-4': 'rgba(255, 255, 255, 0.04)',
        'opacity-6': 'rgba(255, 255, 255, 0.06)',
        'opacity-8': 'rgba(255, 255, 255, 0.08)',
        'opacity-10': 'rgba(255, 255, 255, 0.1)',
        'opacity-12': 'rgba(255, 255, 255, 0.12)',
        'opacity-65': 'rgba(255, 255, 255, 0.65)',
        'opacity-92': 'rgba(255, 255, 255, 0.92)',
        'opacity-95': 'rgba(255, 255, 255, 0.95)',
      },
      green: {
        'bg-1': 'rgba(34, 197, 94, 0.1)',
        'bg-2': 'rgba(34, 197, 94, 0.2)',
        'border-1': 'rgba(34, 197, 94, 0.3)',
        'border-2': 'rgba(34, 197, 94, 0.5)',
        'border-3': 'rgba(34, 197, 94, 0.6)',
        'shadow': 'rgba(34, 197, 94, 0.15)',
        DEFAULT: '#68d391',
      },
      yellow: {
        'bg-1': 'rgba(255, 200, 0, 0.1)',
        'bg-2': 'rgba(255, 150, 0, 0.08)',
        'border': 'rgba(255, 200, 0, 0.3)',
        'text': 'rgba(255, 220, 100, 0.9)',
        'shadow': 'rgba(255, 200, 0, 0.1)',
      },
      blue: {
        DEFAULT: '#63b3ed',
        'hover': '#4299e1',
      },
      error: {
        DEFAULT: '#c53030',
        'hover': '#e53e3e',
      },
      orange: {
        DEFAULT: '#fc8181',
      },
    },
    fontFamily: {
      sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
    },
    borderRadius: {
      'sm': '4px',
      'md': '8px',
      'lg': '10px',
      'xl': '12px',
      '2xl': '14px',
      '3xl': '15px',
      '4xl': '20px',
    },
    boxShadow: {
      'glass': '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
      'glass-hover': '0 12px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
      'card': '0 20px 60px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.08)',
      'auth': '0 30px 80px rgba(0, 0, 0, 0.6), 0 0 40px rgba(255, 0, 0, 0.15)',
      'button': '0 4px 16px rgba(0, 0, 0, 0.3)',
      'button-hover': '0 8px 24px rgba(0, 0, 0, 0.4), 0 0 20px rgba(255, 0, 0, 0.15)',
      'tab': '0 2px 8px rgba(0, 0, 0, 0.3)',
      'tab-active': '0 4px 16px rgba(255, 0, 0, 0.2), 0 -2px 12px rgba(255, 0, 0, 0.1)',
      'glow-red': '0 0 30px rgba(255, 0, 0, 0.3), 0 0 60px rgba(255, 0, 0, 0.15)',
      'glow-red-strong': '0 0 40px rgba(255, 0, 0, 0.5), 0 0 80px rgba(255, 0, 0, 0.2)',
    },
    breakpoints: {
      'sm': '480px',
      'md': '600px',
      'lg': '768px',
      'xl': '1024px',
      '2xl': '1200px',
      '3xl': '1920px',
    },
  },
  rules: [
    // Custom backdrop filter utilities
    ['backdrop-blur-12px', { 'backdrop-filter': 'blur(12px)' }],
    ['backdrop-blur-8px', { 'backdrop-filter': 'blur(8px)' }],
    // Animation utilities
    ['animate-fade-in', { 'animation': 'fadeIn 0.3s ease-out' }],
    ['animate-fade-in-scale', { 'animation': 'fadeInScale 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)' }],
    ['animate-slide-in-up', { 'animation': 'slideInUp 0.3s ease-out' }],
    ['animate-slide-in-down', { 'animation': 'slideInDown 0.3s ease-out' }],
    // Custom gradient backgrounds
    [/^bg-gradient-radial-ares$/, () => ({
      background: `radial-gradient(1400px 900px at 20% 10%, rgba(255, 0, 0, 0.12), transparent 60%),
        radial-gradient(1200px 800px at 80% 30%, rgba(255, 255, 255, 0.06), transparent 60%),
        radial-gradient(1000px 700px at 50% 70%, rgba(255, 100, 100, 0.08), transparent 60%),
        #0a0a0f`,
    })],
    // White opacity colors
    [/^bg-white-opacity-(\d+)$/, ([, num]) => ({ 'background-color': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    [/^text-white-opacity-(\d+)$/, ([, num]) => ({ 'color': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    [/^border-white-opacity-(\d+)$/, ([, num]) => ({ 'border-color': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    [/^hover:bg-white-opacity-(\d+)$/, ([, num]) => ({ 'background-color': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    [/^hover:border-white-opacity-(\d+)$/, ([, num]) => ({ 'border-color': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    [/^hover:text-white-opacity-(\d+)$/, ([, num]) => ({ 'color': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    // Red colors
    [/^bg-red-bg-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.04)', 'rgba(255, 0, 0, 0.08)', 'rgba(255, 0, 0, 0.1)', 'rgba(255, 0, 0, 0.15)', 'rgba(255, 0, 0, 0.2)', 'rgba(255, 0, 0, 0.25)'];
      return { 'background-color': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^border-red-bg-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.04)', 'rgba(255, 0, 0, 0.08)', 'rgba(255, 0, 0, 0.1)', 'rgba(255, 0, 0, 0.15)', 'rgba(255, 0, 0, 0.2)', 'rgba(255, 0, 0, 0.25)'];
      return { 'border-color': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^border-red-border-(\d+)?$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.22)', 'rgba(255, 0, 0, 0.3)', 'rgba(255, 0, 0, 0.35)', 'rgba(255, 0, 0, 0.5)'];
      if (!num) return { 'border-color': colors[0] };
      return { 'border-color': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^border-b-red-border-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.22)', 'rgba(255, 0, 0, 0.3)', 'rgba(255, 0, 0, 0.35)', 'rgba(255, 0, 0, 0.5)'];
      return { 'border-bottom-color': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^text-red-accent-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 200, 200, 0.9)', '#ff3333', '#ff5a5a'];
      return { 'color': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^to-red-accent$/, () => ({ '--un-gradient-to': 'rgba(255, 200, 200, 0.9)' })],
    [/^via-red-bg-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.04)', 'rgba(255, 0, 0, 0.08)'];
      return { '--un-gradient-via': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^to-red-bg-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.04)', 'rgba(255, 0, 0, 0.08)'];
      return { '--un-gradient-to': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^from-red-bg-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.04)', 'rgba(255, 0, 0, 0.08)', 'rgba(255, 0, 0, 0.1)', 'rgba(255, 0, 0, 0.15)'];
      return { '--un-gradient-from': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^via-red-border-(\d+)$/, ([, num]) => {
      const colors = ['rgba(255, 0, 0, 0.22)', 'rgba(255, 0, 0, 0.3)', 'rgba(255, 0, 0, 0.35)'];
      return { '--un-gradient-via': colors[parseInt(num) - 1] || colors[0] };
    }],
    [/^from-white-opacity-(\d+)$/, ([, num]) => ({ '--un-gradient-from': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
    [/^to-white-opacity-(\d+)$/, ([, num]) => ({ '--un-gradient-to': `rgba(255, 255, 255, 0.${num.padStart(2, '0')})` })],
  ],
  shortcuts: {
    // Glassmorphism effects
    'glass-panel': 'bg-white-opacity-2 backdrop-blur-12px border border-white-opacity-8 rounded-xl transition-all duration-300 hover:bg-white-opacity-3 hover:border-white-opacity-12 hover:shadow-glass-hover',
    'glass-header': 'bg-[rgba(26,26,31,0.95)] border border-white-opacity-12 rounded-2xl backdrop-blur-12px shadow-glass transition-all duration-300',
    'glass-tabs': 'bg-[rgba(26,26,31,0.98)] border border-white-opacity-12 backdrop-blur-12px shadow-glass',

    // Panel containers
    'panel-container': 'flex flex-col flex-1 min-h-0 h-full w-full overflow-hidden box-border',
    'panel': 'flex flex-col flex-1 min-h-0 h-full w-full overflow-hidden box-border bg-white-opacity-2 border border-white-opacity-8 rounded-xl p-5 transition-all duration-300 hover:bg-white-opacity-3 hover:border-white-opacity-12 hover:shadow-glass-hover',

    // Auth components
    'auth-card': 'w-full max-w-[520px] bg-[rgba(26,26,26,0.9)] border border-red-border rounded-3xl shadow-auth p-8 text-center backdrop-blur-8px animate-fade-in-scale',
    'auth-button': 'px-6 py-3 bg-gradient-to-br from-red-500 to-red-600 border border-red-border-3 rounded-xl cursor-pointer font-semibold transition-all duration-200 hover:from-red-400 hover:to-red-500 hover:-translate-y-0.5 hover:shadow-button-hover active:scale-95',

    // Buttons
    'button': 'px-7 py-3.5 text-base font-semibold rounded-xl border-none cursor-pointer transition-all duration-300 tracking-wide outline-none shadow-button hover:shadow-button-hover active:scale-95',
    'button-login': 'bg-gradient-to-br from-blue-500 to-blue-600 text-white hover:from-blue-400 hover:to-blue-500 hover:-translate-y-1',
    'button-logout': 'bg-gradient-to-br from-red-500 to-red-600 text-white hover:from-red-400 hover:to-red-500 hover:-translate-y-1',

    // Headers
    'panel-header': 'flex-shrink-0 text-white-opacity-92 border-b border-white-opacity-8 pb-2 mb-3 text-lg leading-tight font-semibold',
    'chat-header': 'flex justify-between items-center mb-4 pb-4 border-b border-white-opacity-10 bg-gradient-to-r from-transparent via-red-bg-1 to-transparent px-2 -mx-1 rounded-lg flex-shrink-0 flex-wrap gap-2',

    // Messages
    'message-bubble': 'mb-3 px-5 py-3.5 rounded-xl transition-all duration-200',
    'message-user': 'bg-gradient-to-br from-red-bg-5 to-red-bg-4 border border-red-border-2 text-white shadow-md hover:shadow-lg',
    'message-assistant': 'bg-white-opacity-6 border border-white-opacity-10 text-white-opacity-95 shadow-md hover:shadow-lg',

    // Empty states
    'empty-state': 'text-center text-white-opacity-40 py-20 px-12 italic text-lg bg-gradient-to-br from-white-opacity-2 to-red-bg-1 rounded-2xl border border-dashed border-white-opacity-10 m-6 transition-all duration-300 hover:border-white-opacity-15',
  },
  animation: {
    keyframes: {
      'fade-in': '{from{opacity:0}to{opacity:1}}',
      'fade-in-scale': '{from{opacity:0;transform:scale(0.95)}to{opacity:1;transform:scale(1)}}',
      'slide-in-down': '{from{opacity:0;transform:translateY(-70px)}to{opacity:1;transform:translateY(0)}}',
      'slide-in-up': '{from{opacity:0;transform:translateY(50px)}to{opacity:1;transform:translateY(0)}}',
      'slide-in': '{from{opacity:0;transform:translateX(-20px)}to{opacity:1;transform:translateX(0)}}',
      'pulse': '{0%,100%{opacity:1}50%{opacity:0.6}}',
      'pulse-2': '{0%,100%{opacity:1}50%{opacity:0.5}}',
      'pulse-glow': '{0%,100%{box-shadow:0 0 20px rgba(255,0,0,0.3)}50%{box-shadow:0 0 40px rgba(255,0,0,0.6)}}',
      'scale-in': '{from{opacity:0;transform:scale(0.8)}to{opacity:1;transform:scale(1)}}',
      'tts-rotate': '{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}',
      'blink': '{0%,100%{opacity:1}50%{opacity:0.5}}',
      'typing': '{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-10px)}}',
      'transcribe-pulse': '{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.8;transform:scale(1.05)}}',
      'spin': '{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}',
      'connection-status-pulse': '{0%,100%{opacity:1}50%{opacity:0.5}}',
      'float': '{0%,100%{transform:translateY(0px)}50%{transform:translateY(-10px)}}',
      'shimmer': '{0%{background-position:200% center}100%{background-position:-200% center}}',
      'glow': '{0%,100%{filter:drop-shadow(0 0 10px rgba(255,0,0,0.3))}50%{filter:drop-shadow(0 0 20px rgba(255,0,0,0.6))}}',
      'gradient-shift': '{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}',
    },
    durations: {
      'fade-in': '0.3s',
      'fade-in-scale': '0.4s',
      'float': '3s',
      'shimmer': '3s',
      'glow': '2s',
      'gradient-shift': '8s',
    },
    timingFns: {
      'fade-in': 'ease-out',
      'fade-in-scale': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    },
  },
})


