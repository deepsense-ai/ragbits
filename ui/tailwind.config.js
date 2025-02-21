import { heroui } from "@heroui/react";

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      backgroundColor: {
        dark: "#1A1A1A",
        light: "#FFFFFF",
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
