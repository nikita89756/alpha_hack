/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'dark-primary': '#0f0f10',
        'dark-secondary': '#151515',
        'dark-accent': '#161616',
        'dark-text': '#E0E0E0',
        'dark-border': '#2a2a2a',
        'dark-hover': '#1e1f20',
        'custom-blue': '#bbfd4f',
        'custom-gray': '#3a3a3f',
        'custom-light-gray': '#4a4a50',
        'custom-border': '#2f3034',
      },
      boxShadow: {
        'custom': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'custom-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
      },
    },
  },
  plugins: [],
};
