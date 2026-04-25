import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16202a",
        mist: "#f4f1e8",
        card: "#fffdf7",
        accent: "#0f766e",
        amber: "#b45309",
        rose: "#be123c"
      },
      fontFamily: {
        sans: ["Space Grotesk", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      boxShadow: {
        panel: "0 18px 48px rgba(22, 32, 42, 0.08)"
      }
    }
  },
  plugins: []
} satisfies Config;

