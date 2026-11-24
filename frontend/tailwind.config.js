/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cricket: {
          dark: "#0b1329",
          card: "#131f3f",
          border: "#1f2e59",
          accent: "#22c55e",
        }
      }
    },
  },
  plugins: [],
};