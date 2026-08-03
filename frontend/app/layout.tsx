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
      <body className="min-h-screen bg-gray-50">
        {children}
      </body>
    </html>
  )
}
