import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Shop Analyzer",
  description: "店铺与达人数据智能分析",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // 根布局只保留 html/body/globals；站点导航放到 (site) 路由组，
  // 这样 /report/influencer/[record_id] 等「嵌入式 H5 页」可脱离站点 chrome，适合 iframe 内嵌。
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
