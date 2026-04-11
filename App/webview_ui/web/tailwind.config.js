module.exports = {
  content: [
    './index.html',
    './js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        black: {
          100: 'rgb(var(--color-black-100-rgb) / <alpha-value>)',
          200: 'rgb(var(--color-black-200-rgb) / <alpha-value>)',
          300: 'rgb(var(--color-black-300-rgb) / <alpha-value>)',
          400: 'rgb(var(--color-black-400-rgb) / <alpha-value>)',
          500: 'rgb(var(--color-black-500-rgb) / <alpha-value>)',
          600: 'rgb(var(--color-black-600-rgb) / <alpha-value>)',
          700: 'rgb(var(--color-black-700-rgb) / <alpha-value>)',
          800: 'rgb(var(--color-black-800-rgb) / <alpha-value>)',
          900: 'rgb(var(--color-black-900-rgb) / <alpha-value>)',
          950: 'rgb(var(--color-black-950-rgb) / <alpha-value>)',
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
