"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import { getTikTokStatus, syncTikTokData } from "@/lib/api";
import { useT } from "@/lib/i18n/context";
import { ShopProvider } from "@/lib/shop/context";

// 数据自动同步阈值：若 last_sync 距今超过此毫秒数，自动触发后台同步
const AUTO_SYNC_THRESHOLD_MS = 60 * 60 * 1000; // 1 小时

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [shopName, setShopName] = useState<string>();
  const [lastSync, setLastSync] = useState<string>();
  const [refreshing, setRefreshing] = useState(false);
  const t = useT();
  // 防止自动同步重复触发
  const autoSyncTriggeredRef = useRef(false);

  const loadStatus = useCallback(async () => {
    try {
      const s = await getTikTokStatus();
      if (s.shop_id) setShopName(`TikTok · ${s.shop_id}`);
      if (s.last_sync) setLastSync(s.last_sync);

      // 自动同步：配置好 + 未在本次会话触发过 + last_sync 为空或超过 1 小时
      if (s.configured && !autoSyncTriggeredRef.current) {
        const stale =
          !s.last_sync ||
          Date.now() - new Date(s.last_sync).getTime() > AUTO_SYNC_THRESHOLD_MS;
        if (stale) {
          autoSyncTriggeredRef.current = true;
          // 后台模式，不阻塞 UI；失败静默（用户点刷新时再看错误）
          syncTikTokData(7, false).catch(() => {});
        }
      }
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
    <ShopProvider>
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
              {t("footer.dataSource")}
              {lastSync ? ` · ${t("footer.lastSync", { time: lastSync })}` : ""}
            </span>
            <span>AI Shop Analyzer v0.2.0</span>
          </footer>
        </div>
      </div>
    </ShopProvider>
  );
}
