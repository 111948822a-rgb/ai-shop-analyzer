/** @type {import('next').NextConfig} */
// 开发：NEXT_PUBLIC_API_URL 未设置 -> rewrite 到 localhost:8000（本地后端）
// 生产：Render 构建时注入 NEXT_PUBLIC_API_URL=https://ai-shop-backend.onrender.com
//       -> 所有 /api/* 直接代理到线上后端，前端与后端分离部署也能正常工作
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
