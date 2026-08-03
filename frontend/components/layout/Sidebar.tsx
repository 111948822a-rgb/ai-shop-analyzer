"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const MENU = [
  { label: "数据概览", href: "/dashboard", icon: "📊" },
  { label: "销售分析", href: "/sales", icon: "💰" },
  { label: "流量分析", href: "/traffic", icon: "👥" },
  { label: "商品分析", href: "/products", icon: "📦" },
  { label: "用户分析", href: "/users", icon: "🎯" },
  { label: "营销分析", href: "/marketing", icon: "📣" },
  { label: "达人合作", href: "/influencers", icon: "⭐" },
  { label: "实时大屏", href: "/realtime", icon: "🖥️" },
  { label: "报表中心", href: "/reports", icon: "📑" },
  { label: "设置", href: "/settings", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`fixed left-0 top-0 z-30 flex h-screen flex-col bg-sidebar transition-all duration-300 ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-white/5 px-4">
        <span className="text-xl">🛍️</span>
        {!collapsed && (
          <span className="text-sm font-bold text-white">AI Shop Analyzer</span>
        )}
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-3">
        {MENU.map((item) => {
          const active = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-sidebar-active text-white font-medium"
                  : "text-gray-400 hover:bg-sidebar-hover hover:text-white"
              }`}
            >
              <span className="text-base leading-none">{item.icon}</span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* 折叠按钮 */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center gap-2 border-t border-white/5 py-3 text-xs text-gray-500 hover:text-white"
      >
        <span>{collapsed ? "▶" : "◀ 折叠"}</span>
      </button>
    </aside>
  );
}
