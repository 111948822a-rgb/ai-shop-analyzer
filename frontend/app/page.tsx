'use client'

import { useState } from 'react'
import { ArrowRight, Sparkles, BarChart3, Users, TrendingUp } from 'lucide-react'
import Link from 'next/link'

export default function Home() {
  const [taskId, setTaskId] = useState('')

  const quickTaskIds = ['INF_US_001', 'INF_TH_007', 'INF_MY_015']

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="relative">
              <Sparkles className="w-12 h-12 text-primary-400 animate-float" />
              <div className="absolute inset-0 bg-primary-400/30 blur-xl rounded-full" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold gradient-text">
              AI Shop Analyzer
            </h1>
          </div>
          <p className="text-slate-400 text-lg">
            跨境电商店铺数据 AI 分析 · 达人深度评估 · 多语种建联话术
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="glass-card-hover p-6 text-center">
            <BarChart3 className="w-10 h-10 text-primary-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">销售数据分析</h3>
            <p className="text-slate-400 text-sm">GMV、订单数、客单价、爆款商品</p>
          </div>
          <div className="glass-card-hover p-6 text-center">
            <Users className="w-10 h-10 text-purple-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">达人质量评估</h3>
            <p className="text-slate-400 text-sm">ROI、互动率、转化率、水军识别</p>
          </div>
          <div className="glass-card-hover p-6 text-center">
            <TrendingUp className="w-10 h-10 text-green-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">智能建联话术</h3>
            <p className="text-slate-400 text-sm">多语种自动生成、一键复制</p>
          </div>
        </div>

        <div className="glass-card p-8">
          <h2 className="text-xl font-semibold mb-6 text-center">查看分析报告</h2>
          <div className="flex flex-col sm:flex-row gap-4">
            <input
              type="text"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="输入任务ID或达人ID..."
              className="flex-1 px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg focus:outline-none focus:border-primary-500 transition-colors"
            />
            <Link
              href={`/report/${taskId}`}
              className="btn-primary flex items-center justify-center gap-2"
              disabled={!taskId}
            >
              查看报告
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="mt-6">
            <p className="text-slate-400 text-sm mb-3">快速体验（点击直接查看）：</p>
            <div className="flex flex-wrap gap-2">
              {quickTaskIds.map((id) => (
                <Link
                  key={id}
                  href={`/report/${id}`}
                  className="px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 rounded-lg text-sm transition-colors"
                >
                  {id}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}