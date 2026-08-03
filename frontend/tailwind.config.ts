import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        // 设计规范辅助色
        growth: {
          50: "#ecfdf5", 100: "#d1fae5", 500: "#10b981", 600: "#059669",
          DEFAULT: "#10B981",
        },
        decline: {
          50: "#fef2f2", 100: "#fee2e2", 500: "#ef4444", 600: "#dc2626",
          DEFAULT: "#EF4444",
        },
        warning: {
          50: "#fffbeb", 100: "#fef3c7", 500: "#f59e0b", 600: "#d97706",
          DEFAULT: "#F59E0B",
        },
        // 左侧导航深色背景
        sidebar: { DEFAULT: "#1A1D29", hover: "#252938", active: "#2563EB" },
        // 大屏深色背景
        screen: { DEFAULT: "#0F172A", card: "#1E293B" },
      },
      borderRadius: {
        card: "12px",
        btn: "8px",
        datalabel: "4px",
      },
      fontSize: {
        kpi: ["28px", { lineHeight: "36px", fontWeight: "700" }],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        scan: "scan 3s linear infinite",
        blink: "blink 1s step-start infinite",
        marquee: "marquee 30s linear infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        blink: {
          "0%, 50%": { opacity: "1" },
          "50.01%, 100%": { opacity: "0" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
