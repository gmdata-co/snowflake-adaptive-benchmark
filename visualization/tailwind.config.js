/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gen1: '#29B5E8',
        adaptive: '#F59E0B',
        dark: {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
        }
      },
    },
  },
  plugins: [],
}
