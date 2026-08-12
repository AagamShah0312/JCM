import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#dae6ff',
          200: '#bcd2ff',
          300: '#8fb4ff',
          400: '#5b8bfe',
          500: '#3563fb',
          600: '#1f43f0',
          700: '#1732dd',
          800: '#192bb3',
          900: '#1a2a8d',
        },
      },
    },
  },
  plugins: [],
};
export default config;
