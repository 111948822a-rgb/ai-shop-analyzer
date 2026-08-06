"use client";

import { useI18n } from "@/lib/i18n/context";

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <div className="flex items-center gap-1 rounded-btn border border-gray-200 bg-white p-0.5">
      <button
        onClick={() => setLocale("en")}
        className={`rounded-[6px] px-2.5 py-1 text-xs font-medium transition ${
          locale === "en" ? "bg-primary-600 text-white" : "text-gray-500 hover:text-gray-800"
        }`}
      >
        EN
      </button>
      <button
        onClick={() => setLocale("zh")}
        className={`rounded-[6px] px-2.5 py-1 text-xs font-medium transition ${
          locale === "zh" ? "bg-primary-600 text-white" : "text-gray-500 hover:text-gray-800"
        }`}
      >
        中文
      </button>
    </div>
  );
}
