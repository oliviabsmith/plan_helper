import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f1f5fe",
          100: "#e2ebfd",
          200: "#c4d7fb",
          300: "#a6c3f9",
          400: "#699bf4",
          500: "#2c73ef",
          600: "#2859d1",
          700: "#1e409b",
          800: "#152865",
          900: "#0b1030"
        }
      }
    }
  },
  plugins: []
} satisfies Config;
