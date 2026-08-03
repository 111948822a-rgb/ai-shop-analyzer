"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getTikTokStatus } from "@/lib/api";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [shopName, setShopName] = useState<string>();
  const [lastSync, setLastSync] = useState<string>();
  const [refreshing, setRefreshing] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const s = await getTikTokStatus();
      if (s.shop_id) setShopName(`TikTok · ${s.shop_id}`);
      if (s.last_sync) setLastSync(s.last_sync);
    } catch {
      /* 静默 */
    }
  }, []);

  useEffect(() => {
    loadStatus();
    const t = setInterval(loadStatus, 60000);
    return () => clearInterval(t);
  }, [loadStatus]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    loadStatus().finally(() => setTimeout(() => setRefreshing(false), 800));
  }, [loadStatus]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <div className={`flex flex-col transition-all duration-300 ${collapsed ? "ml-16" : "ml-60"}`}>
        <Topbar
          shopName={shopName}
          lastSync={lastSync}
          onRefresh={handleRefresh}
          refreshing={refreshing}
        />
        <main className="flex-1 px-6 py-6">{children}</main>
        {/* 底部状态栏 */}
        <footer className="flex h-8 items-center justify-between border-t border-gray-200 bg-gray-100 px-6 text-xs text-gray-400">
          <span>
            数据来源：TikTok Shop Partner API
            {lastSync ? ` · 最近同步 ${lastSync}` : ""}
          </span>
          <span>AI Shop Analyzer v0.2.0</span>
        </footer>
      </div>
    </div>
  );
}
