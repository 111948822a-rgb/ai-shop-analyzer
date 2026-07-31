import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Shop Analyzer',
  description: '跨境电商店铺数据分析与达人评估平台',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {children}
      </body>
    </html>
  )
}
