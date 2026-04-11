module.exports = {
  content: [
    './index.html',
    './js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        black: {
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
          950: '#0a0a0a',
        },
      },
      fontFamily: {
        sans: ['Lato', 'system-ui', 'sans-serif'],
      },
      fontWeight: {
        bold: '900',
      },
      fontSize: {
        base: ['var(--fs-base)', { lineHeight: '1.5' }],
        xl: ['var(--fs-xl)', { lineHeight: '1.2' }],
        xs: 'var(--fs-s)',
        sm: 'var(--fs-s)',
        lg: 'var(--fs-l)',
        '2xl': 'var(--fs-xl)',
      },
    },
  },
};
