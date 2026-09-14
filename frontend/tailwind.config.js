/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: '#F5F4F1',
        card: '#FFFFFF',
        ink: '#181818',
        muted: '#6B6B6B',
        accent: '#FF5528',
        highlight: '#FFE500',
        border: '#E5E5E3',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'card': '14px',
      },
    },
  },
  plugins: [],
}
