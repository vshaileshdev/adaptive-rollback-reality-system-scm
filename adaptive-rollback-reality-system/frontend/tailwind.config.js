/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        normal: "#10b981", // green-500
        warning: "#f59e0b", // amber-500
        critical: "#ef4444", // red-500
      }
    },
  },
  plugins: [],
}
