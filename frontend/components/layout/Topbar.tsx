"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// 路由 → 面包屑映射
const CRUMB_MAP: Record<string, string> = {
  "/dashboard": "数据概览",
  "/sales": "销售分析",
  "/traffic": "流量分析",
  "/products": "商品分析",
  "/users": "用户分析",
  "/marketing": "营销分析",
  "/influencers": "达人合作",
  "/realtime": "实时大屏",
  "/reports": "报表中心",
  "/settings": "设置",
};

export default function Topbar({
  shopName,
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

  useEffect(() => {
    const update = () =>
      setNow(new Date().toLocaleString("zh-CN", { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  const crumb = CRUMB_MAP[pathname ?? ""] ?? "数据概览";

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
        {/* 店铺 */}
        <div className="hidden items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 md:flex">
          <span className="text-xs text-gray-400">店铺</span>
          <span className="max-w-[160px] truncate text-sm font-medium text-gray-700">
            {shopName ?? "TikTok Shop"}
          </span>
        </div>

        {/* 数据更新时间 */}
        {lastSync && (
          <span className="hidden text-xs text-gray-400 lg:inline">
            更新于 {lastSync}
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
            刷新
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
