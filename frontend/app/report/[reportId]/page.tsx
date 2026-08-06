'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  Loader2,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  ShoppingBag,
  Users,
  Globe,
  Award,
  AlertCircle,
  ArrowLeft,
  Calendar,
  DollarSign,
  Target,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import { useT } from '@/lib/i18n/context'

interface ReportData {
  report_id: string
  report_title: string
  report_type: 'weekly' | 'monthly'
  period: string
  generated_at: string
  core_summary: {
    total_gmv: number
    total_orders: number
    avg_order_value: number
    gmv_growth?: number
    order_growth?: number
  }
  product_red_list: Array<{
    product_id: string
    product_name: string
    category: string
    price: number
    total_sales: number
    total_orders: number
  }>
  product_black_list: Array<{
    product_id: string
    product_name: string
    total_sales: number
    total_orders: number
  }>
  influencer_red_list: Array<{
    influencer_id: string
    influencer_name: string
    follower_count: number
    engagement_rate: number
    conversion_rate: number
    roi: number
    total_sales: number
    total_orders: number
  }>
  influencer_black_list: Array<{
    influencer_id: string
    influencer_name: string
    follower_count: number
    engagement_rate: number
    conversion_rate: number
    risk_reason: string
  }>
  site_breakdown: Array<{
    site_code: string
    currency: string
    total_gmv: number
    total_orders: number
    avg_order_value: number
  }>
  trend_analysis: string
  anomaly_analysis: string
  action_suggestions: string[]
}

interface ReportStatus {
  status: 'loading' | 'completed' | 'failed'
  data?: ReportData
  error?: string
}

export default function ReportPage({ params }: { params: { reportId: string } }) {
  const t = useT()
  const [reportStatus, setReportStatus] = useState<ReportStatus>({ status: 'loading' })

  const fetchReport = useCallback(async () => {
    try {
      const response = await fetch(`/api/reports/${params.reportId}`)
      if (!response.ok) {
        throw new Error('Report not found')
      }
      const data = await response.json()
      setReportStatus({ status: 'completed', data })
    } catch (error) {
      setReportStatus({ status: 'failed', error: error instanceof Error ? error.message : 'Failed to fetch report' })
    }
  }, [params.reportId])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  if (reportStatus.status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="relative w-20 h-20">
            <div className="absolute inset-0 bg-gradient-to-r from-primary-500 to-purple-500 rounded-full animate-ping opacity-20" />
            <Loader2 className="w-12 h-12 text-primary-400 animate-spin" />
          </div>
          <p className="mt-4 text-slate-400">{t("report.loading")}</p>
        </div>
      </div>
    )
  }

  if (reportStatus.status === 'failed') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <div className="max-w-lg w-full">
          <div className="glass-card p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-red-500/20 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-xl font-semibold mb-4 text-red-400">{t("report.loadFailed")}</h2>
            <p className="text-slate-400 mb-6">{reportStatus.error}</p>
            <button onClick={fetchReport} className="btn-primary">
              {t("report.reload")}
            </button>
          </div>
        </div>
      </div>
    )
  }

  const report = reportStatus.data!

  const trendData = report.site_breakdown.map(site => ({
    name: site.site_code,
    GMV: site.total_gmv,
    Orders: site.total_orders,
  }))

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/" className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" />
              {t("report.backHome")}
            </Link>
            <div>
              <h1 className="text-2xl font-bold gradient-text">{report.report_title}</h1>
              <div className="flex items-center gap-4 mt-1 text-sm text-slate-400">
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {report.period}
                </span>
                <span className={`px-2 py-1 rounded text-xs ${report.report_type === 'weekly' ? 'bg-blue-500/20 text-blue-400' : 'bg-purple-500/20 text-purple-400'}`}>
                  {report.report_type === 'weekly' ? t("report.weekly") : t("report.monthly")}
                </span>
              </div>
            </div>
          </div>
          <span className="status-completed">{t("report.completed")}</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="glass-card p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <div className="text-xs text-slate-400">{t("report.totalGMV")}</div>
                <div className="text-xl font-bold text-green-400">{formatCurrency(report.core_summary.total_gmv)}</div>
              </div>
            </div>
            {report.core_summary.gmv_growth !== undefined && (
              <div className={`mt-2 text-xs flex items-center gap-1 ${report.core_summary.gmv_growth >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {report.core_summary.gmv_growth >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {t("report.yoyGrowth", { growth: `${report.core_summary.gmv_growth >= 0 ? '+' : ''}${formatPercent(report.core_summary.gmv_growth)}` })}
              </div>
            )}
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <ShoppingBag className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <div className="text-xs text-slate-400">{t("report.orderCount")}</div>
                <div className="text-xl font-bold text-blue-400">{report.core_summary.total_orders.toLocaleString()}</div>
              </div>
            </div>
            {report.core_summary.order_growth !== undefined && (
              <div className={`mt-2 text-xs flex items-center gap-1 ${report.core_summary.order_growth >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {report.core_summary.order_growth >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {t("report.yoyGrowth", { growth: `${report.core_summary.order_growth >= 0 ? '+' : ''}${formatPercent(report.core_summary.order_growth)}` })}
              </div>
            )}
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Target className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <div className="text-xs text-slate-400">{t("report.aov")}</div>
                <div className="text-xl font-bold text-purple-400">{formatCurrency(report.core_summary.avg_order_value)}</div>
              </div>
            </div>
          </div>

          <div className="glass-card p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <div className="text-xs text-slate-400">{t("report.influencerCount")}</div>
                <div className="text-xl font-bold text-orange-400">{report.influencer_red_list.length + report.influencer_black_list.length}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-green-400" />
              {t("report.redList")}
            </h2>
            <div className="space-y-3">
              {report.product_red_list.slice(0, 5).map((product, index) => (
                <div key={product.product_id} className="flex items-center gap-4 p-3 bg-slate-700/30 rounded-lg">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    index === 0 ? 'bg-yellow-500 text-yellow-900' :
                    index === 1 ? 'bg-slate-400 text-slate-900' :
                    index === 2 ? 'bg-orange-400 text-orange-900' :
                    'bg-slate-600 text-slate-300'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-200 truncate">{product.product_name}</div>
                    <div className="text-xs text-slate-400">{product.category} | ${product.price.toFixed(2)}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-400">{formatCurrency(product.total_sales)}</div>
                    <div className="text-xs text-slate-400">{product.total_orders} {t("report.orderUnit")}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-400" />
              {t("report.blackList")}
            </h2>
            <div className="space-y-3">
              {report.product_black_list.slice(0, 3).map((product, index) => (
                <div key={product.product_id} className="flex items-center gap-4 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold bg-red-500/20 text-red-400">
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-200 truncate">{product.product_name}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-red-400">{formatCurrency(product.total_sales)}</div>
                    <div className="text-xs text-slate-400">{product.total_orders} {t("report.orderUnit")}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              {t("report.influencerRed")}
            </h2>
            <div className="space-y-3">
              {report.influencer_red_list.slice(0, 5).map((influencer, index) => (
                <div key={influencer.influencer_id} className="flex items-center gap-4 p-3 bg-slate-700/30 rounded-lg">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    index === 0 ? 'bg-yellow-500 text-yellow-900' :
                    index === 1 ? 'bg-slate-400 text-slate-900' :
                    index === 2 ? 'bg-orange-400 text-orange-900' :
                    'bg-slate-600 text-slate-300'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-200 truncate">{influencer.influencer_name}</div>
                    <div className="text-xs text-slate-400">
                      {t("report.followers", { n: influencer.follower_count.toLocaleString() })} | {t("report.engagement", { v: formatPercent(influencer.engagement_rate) })}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-400">{formatCurrency(influencer.total_sales)}</div>
                    <div className="text-xs text-slate-400">ROI {influencer.roi.toFixed(2)}x</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              {t("report.influencerBlack")}
            </h2>
            <div className="space-y-3">
              {report.influencer_black_list.slice(0, 5).map((influencer, index) => (
                <div key={influencer.influencer_id} className="flex items-start gap-4 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold bg-red-500/20 text-red-400 flex-shrink-0">
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-200">{influencer.influencer_name}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      {t("report.followers", { n: influencer.follower_count.toLocaleString() })} | 
                      <span className="text-orange-400"> {t("report.engagement", { v: formatPercent(influencer.engagement_rate) })}</span> | 
                      <span className="text-red-400"> {t("report.conversion", { v: formatPercent(influencer.conversion_rate) })}</span>
                    </div>
                    <div className="text-xs text-red-300 mt-2 line-clamp-2">{influencer.risk_reason}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5 text-blue-400" />
              {t("report.crossSite")}
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      color: '#f1f5f9',
                    }}
                    formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
                  />
                  <Bar dataKey="GMV" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              {report.site_breakdown.map(site => (
                <div key={site.site_code} className="text-center">
                  <div className="text-lg font-bold text-blue-400">{site.site_code}</div>
                  <div className="text-xs text-slate-400">{formatCurrency(site.total_gmv)}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              {t("report.trendAnalysis")}
            </h2>
            <div className="bg-slate-700/30 rounded-lg p-4 mb-4">
              <p className="text-slate-300">{report.trend_analysis || t("report.noTrend")}</p>
            </div>
            <h3 className="text-sm font-medium text-orange-400 mb-3">{t("report.anomaly")}</h3>
            <div className="bg-orange-500/10 rounded-lg p-4 border border-orange-500/20">
              <p className="text-orange-300">{report.anomaly_analysis || t("report.noAnomaly")}</p>
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            {t("report.nextSteps")}
          </h2>
          <div className="space-y-3">
            {report.action_suggestions.map((suggestion, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg">
                <div className="w-6 h-6 rounded-full flex items-center justify-center font-bold bg-yellow-500/20 text-yellow-400 flex-shrink-0">
                  {index + 1}
                </div>
                <p className="text-slate-300">{suggestion}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 text-center text-slate-500 text-sm">
          {t("report.generatedAt", { time: new Date(report.generated_at).toLocaleString() })}
        </div>
      </div>
    </div>
  )
}