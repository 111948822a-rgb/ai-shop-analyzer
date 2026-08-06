"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useT } from "@/lib/i18n/context";

const MENU = [
  { key: "dashboard", href: "/dashboard", icon: "📊" },
  { key: "sales", href: "/sales", icon: "💰" },
  { key: "traffic", href: "/traffic", icon: "👥" },
  { key: "products", href: "/products", icon: "📦" },
  { key: "users", href: "/users", icon: "🎯" },
  { key: "marketing", href: "/marketing", icon: "📣" },
  { key: "influencers", href: "/influencers", icon: "⭐" },
  { key: "realtime", href: "/realtime", icon: "🖥️" },
  { key: "reports", href: "/reports", icon: "📑" },
  { key: "settings", href: "/settings", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const t = useT();

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
              title={collapsed ? t(`nav.${item.key}`) : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-sidebar-active text-white font-medium"
                  : "text-gray-400 hover:bg-sidebar-hover hover:text-white"
              }`}
            >
              <span className="text-base leading-none">{item.icon}</span>
              {!collapsed && <span className="truncate">{t(`nav.${item.key}`)}</span>}
            </Link>
          );
        })}
      </nav>

      {/* 折叠按钮 */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center gap-2 border-t border-white/5 py-3 text-xs text-gray-500 hover:text-white"
      >
        <span>{collapsed ? "▶" : "◀"}</span>
      </button>
    </aside>
  );
}
