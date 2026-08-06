"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useT } from "@/lib/i18n/context";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ShopSelector } from "@/components/ShopSelector";

const CRUMB_KEYS: Record<string, string> = {
  "/dashboard": "nav.dashboard",
  "/sales": "nav.sales",
  "/traffic": "nav.traffic",
  "/products": "nav.products",
  "/users": "nav.users",
  "/marketing": "nav.marketing",
  "/influencers": "nav.influencers",
  "/realtime": "nav.realtime",
  "/reports": "nav.reports",
  "/settings": "nav.settings",
};

export default function Topbar({
  lastSync,
  onRefresh,
  refreshing,
}: {
  shopName?: string;
  lastSync?: string;
  onRefresh?: () => void;
  refreshing?: boolean;
}) {
  const pathname = usePathname();
  const [now, setNow] = useState("");
  const t = useT();

  useEffect(() => {
    const update = () =>
      setNow(new Date().toLocaleString("en-US", { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  const crumbKey = CRUMB_KEYS[pathname ?? ""] ?? "nav.dashboard";
  const crumb = t(crumbKey);

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      {/* 左：面包屑 */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-400">AI Shop Analyzer</span>
        <span className="text-gray-300">/</span>
        <span className="font-medium text-gray-800">{crumb}</span>
      </div>

      {/* 右：操作区 */}
      <div className="flex items-center gap-4">
        {/* 语言切换器 */}
        <LanguageSwitcher />

        {/* 店铺切换器 */}
        <ShopSelector />

        {/* 数据更新时间 */}
        {lastSync && (
          <span className="hidden text-xs text-gray-400 lg:inline">
            Updated {lastSync}
          </span>
        )}

        {/* 刷新 */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="ds-btn-secondary px-3 py-1.5 text-xs"
          >
            <span className={refreshing ? "animate-spin" : ""}>↻</span>
            {t("common.refresh")}
          </button>
        )}

        {/* 当前时间 */}
        <span className="hidden text-xs tabular-nums text-gray-400 xl:inline">
          {now}
        </span>
      </div>
    </header>
  );
}
