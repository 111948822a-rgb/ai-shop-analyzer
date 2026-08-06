"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { translations, type Locale, type Dict } from "./dict";

type I18nContextValue = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (path: string, vars?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "app-locale";

/** 按点号路径取嵌套对象值，如 t("dashboard.title") */
function getByPath(obj: unknown, path: string): string | undefined {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur && typeof cur === "object" && p in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[p];
    } else {
      return undefined;
    }
  }
  return typeof cur === "string" ? cur : undefined;
}

/** 简单插值：把 {key} 替换为 vars[key] */
function interpolate(str: string, vars?: Record<string, string | number>): string {
  if (!vars) return str;
  return str.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  // 默认英文（满足 TikTok 审核要求）
  const [locale, setLocaleState] = useState<Locale>("en");

  // 初始化时从 localStorage 读取用户偏好
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (saved === "en" || saved === "zh") {
      setLocaleState(saved);
    }
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(STORAGE_KEY, l);
    document.documentElement.lang = l === "zh" ? "zh-CN" : "en";
  }, []);

  // 设置 html lang 属性
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);

  const t = useCallback(
    (path: string, vars?: Record<string, string | number>) => {
      const dict = translations[locale] as unknown as Dict;
      const str = getByPath(dict, path);
      if (str === undefined) {
        // fallback 到英文
        const enStr = getByPath(translations.en, path);
        return enStr ? interpolate(enStr, vars) : path;
      }
      return interpolate(str, vars);
    },
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}

/** 便捷导出：只取 t 函数 */
export function useT() {
  return useI18n().t;
}
