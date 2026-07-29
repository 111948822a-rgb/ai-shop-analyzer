'use client'

import { BarChart3, Users } from 'lucide-react'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="max-w-3xl w-full">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <h1 className="text-4xl md:text-5xl font-bold gradient-text">
              AI Shop Analyzer
            </h1>
          </div>
          <p className="text-slate-400 text-lg">
            跨境电商店铺数据 AI 分析 · 达人深度评估
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link href="/shops" className="glass-card-hover p-8 text-center block">
            <BarChart3 className="w-12 h-12 text-primary-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">销售数据分析</h3>
            <p className="text-slate-400 text-sm">GMV、订单、客单价、爆款商品，支持多店铺</p>
          </Link>

          <Link href="/influencers" className="glass-card-hover p-8 text-center block">
            <Users className="w-12 h-12 text-purple-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">达人评估</h3>
            <p className="text-slate-400 text-sm">基于秒搭达人数据，AI 匹配度与避坑预警</p>
          </Link>
        </div>
      </div>
    </div>
  )
}
