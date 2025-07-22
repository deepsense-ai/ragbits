import { heroui } from "@heroui/react";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "selector",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "../../node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      backgroundColor: {
        dark: "#1A1A1A",
        light: "#FFFFFF",
      },
      keyframes: {
        "pop-in": {
          "0%": { transform: "scale(0.8)", opacity: 0 },
          "100%": { transform: "scale(1)", opacity: 1 },
        },
      },
      animation: {
        "pop-in": "pop-in 0.2s ease-out forwards",
      },
      screens: {
        xs: "440px",
      },
    },
  },
  plugins: [
    heroui({
      themes: {
        light: {
          colors: {
            background: "#FFFFFF",
            foreground: "#1A1A1A",
            primary: {
              DEFAULT: "#1C54FF",
              foreground: "#FFFFFF",
            },
          },
        },
      },
    }),
    require("@tailwindcss/typography"),
  ],
};
