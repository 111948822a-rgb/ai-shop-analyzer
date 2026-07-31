"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  getDashboardOverview,
  getGmvTrend,
  getInfluencers,
  getTopProducts,
  getTikTokStatus,
  syncTikTokData,
  generateAIReport,
  getAIReport,
  type DashboardOverview,
  type GmvPoint,
  type InfluencerPoint,
  type TikTokStatus,
  type TopProduct,
  type AIReportResponse,
} from "@/lib/api";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { GmvTrendChart } from "@/components/dashboard/GmvTrendChart";
import { TopProductsChart } from "@/components/dashboard/TopProductsChart";
import { InfluencerScatter } from "@/components/dashboard/InfluencerScatter";

function DashboardInner() {
  const searchParams = useSearchParams();
  const shopIds = useMemo(() => {
    const raw = searchParams.get("shops");
    if (!raw) return undefined;
    const arr = raw.split(",").filter(Boolean);
    return arr.length ? arr : undefined;
  }, [searchParams]);

  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [gmvTrend, setGmvTrend] = useState<GmvPoint[]>([]);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [influencers, setInfluencers] = useState<{
    points: InfluencerPoint[];
    suspicious_count: number;
  } | null>(null);

  // TikTok 同步状态
  const [tkStatus, setTkStatus] = useState<TikTokStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [syncDays, setSyncDays] = useState(180);

  // AI 报告状态
  const [aiReport, setAiReport] = useState<AIReportResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [reportQuery, setReportQuery] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [o, g, t, inf] = await Promise.all([
        getDashboardOverview(days, shopIds),
        getGmvTrend(days, shopIds),
        getTopProducts(10, days, shopIds),
        getInfluencers(),
      ]);
      setOverview(o);
      setGmvTrend(g);
      setTopProducts(t);
      setInfluencers(inf);
    } catch (e) {
      setError(e instanceof Error ? e.message : "数据加载失败");
    } finally {
      setLoading(false);
    }
  }, [days, shopIds]);

  useEffect(() => {
    load();
  }, [load]);

  // 单独拉 TikTok 配置状态（不阻塞看板渲染）
  useEffect(() => {
    getTikTokStatus()
      .then(setTkStatus)
      .catch(() => setTkStatus(null));
  }, []);

  async function handleSync(foreground: boolean) {
    setSyncing(true);
    setSyncMsg(null);
    setError(null);
    try {
      const r = await syncTikTokData(syncDays, foreground);
      if (r.status === "done" && r.result) {
        const { orders, products } = r.result;
        setSyncMsg(
          `同步完成：订单 ${orders.inserted} 新增 / ${orders.updated} 更新；商品 ${products.inserted} 新增 / ${products.updated} 更新。`
        );
        // 同步完成后刷新看板
        await load();
      } else {
        setSyncMsg(r.message ?? "同步任务已在后台启动，稍后点「刷新」查看数据。");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步失败");
    } finally {
      setSyncing(false);
    }
  }

  // AI 报告轮询
  useEffect(() => {
    if (!aiReport || aiReport.status === "done" || aiReport.status === "failed") return;
    const timer = setTimeout(async () => {
      try {
        const r = await getAIReport(aiReport.report_id);
        setAiReport(r);
      } catch {
        // 忽略轮询错误
      }
    }, 3000);
    return () => clearTimeout(timer);
  }, [aiReport]);

  async function handleGenerateReport() {
    setGenerating(true);
    setError(null);
    setAiReport(null);
    try {
      // 前台同步执行（数据量小，直接等结果）
      const r = await generateAIReport(days, reportQuery, true);
      setAiReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "报告生成失败");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <div className="mb-1 flex items-center gap-3">
              <Link
                href="/"
                className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
              >
                <span aria-hidden>←</span> 返回主页
              </Link>
            </div>
            <h1 className="text-xl font-bold text-gray-900">AI Shop Analyzer · 销售数据分析</h1>
            <p className="text-sm text-gray-500">
              {shopIds ? `已选店铺：${shopIds.join("、")} · ` : "全部店铺 · "}
              {overview
                ? `统计区间：${overview.period.start} ~ ${overview.period.end}${overview.period.fallback ? "（近N天无数据，已显示全部已同步数据）" : `（近 ${overview.period.days} 天）`}`
                : "加载中…"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
              {[7, 30, 90, 180].map((d) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    days === d
                      ? "bg-white text-blue-600 shadow-sm"
                      : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {d}天
                </button>
              ))}
            </div>
            <button
              onClick={load}
              disabled={loading}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "刷新中…" : "刷新"}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 px-6 py-6">
        {/* TikTok 数据同步区 */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-gray-900">数据源 · TikTok Shop</h2>
              <p className="mt-1 text-sm text-gray-500">
                {tkStatus?.configured ? (
                  <>
                    店铺 <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">{tkStatus.shop_id}</code>
                    {tkStatus.token.has_access_token ? (
                      tkStatus.token.is_expiring_soon ? (
                        <span className="ml-2 text-amber-600">Token 即将过期，刷新前请先续期</span>
                      ) : (
                        <span className="ml-2 text-green-600">
                          Token 有效（剩余 {tkStatus.token.remaining_hours?.toFixed(1)} 小时）
                        </span>
                      )
                    ) : (
                      <span className="ml-2 text-red-600">未授权，请在 .env 配置 access_token / refresh_token</span>
                    )}
                  </>
                ) : (
                  <span className="text-amber-600">未配置 TikTok Partner API（缺 app_key/app_secret/shop_id）</span>
                )}
              </p>
            </div>
            {tkStatus?.configured && (
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
                  {[7, 30, 90, 180].map((d) => (
                    <button
                      key={d}
                      onClick={() => setSyncDays(d)}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                        syncDays === d
                          ? "bg-white text-blue-600 shadow-sm"
                          : "text-gray-500 hover:text-gray-800"
                      }`}
                    >
                      {d}天
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => handleSync(true)}
                  disabled={syncing}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
                  title="前台同步执行，立即返回结果（适合小数据量）"
                >
                  {syncing ? "同步中…" : "立即同步"}
                </button>
                <button
                  onClick={() => handleSync(false)}
                  disabled={syncing}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
                  title="后台异步执行，立即返回，稍后刷新看板"
                >
                  后台同步
                </button>
              </div>
            )}
          </div>
          {syncMsg && (
            <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700">
              {syncMsg}
            </div>
          )}
          {!tkStatus?.configured && (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              请在后端 <code>.env</code> 配置 <code>TK_PARTNER_APP_KEY</code> /{" "}
              <code>TK_PARTNER_APP_SECRET</code> / <code>TK_AUTH_SHOP_ID</code>，并完成授权拿到{" "}
              <code>TK_AUTH_ACCESS_TOKEN</code> / <code>TK_AUTH_REFRESH_TOKEN</code> 后重启服务。
            </div>
          )}
        </section>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            ⚠️ {error}
          </div>
        )}

        {loading && !overview ? (
          <div className="flex h-64 items-center justify-center text-gray-400">
            正在加载看板数据…
          </div>
        ) : (
          <>
            {overview && <KpiCards kpis={overview.kpis} />}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <GmvTrendChart data={gmvTrend} />
              <InfluencerScatter
                points={influencers?.points ?? []}
                suspiciousCount={influencers?.suspicious_count ?? 0}
              />
            </div>

            <TopProductsChart data={topProducts} />

            {/* AI 分析报告生成区 */}
            <section className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-gray-900">AI 经营分析报告</h2>
                  <p className="mt-1 text-sm text-gray-500">
                    通义千问基于上述看板数据自动生成分析报告（数据范围：近 {days} 天）
                  </p>
                </div>
                <button
                  onClick={handleGenerateReport}
                  disabled={generating}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {generating ? "AI 分析中…" : "生成 AI 报告"}
                </button>
              </div>

              <div className="mt-3">
                <input
                  type="text"
                  value={reportQuery}
                  onChange={(e) => setReportQuery(e.target.value)}
                  placeholder="可选：额外关注点，如「重点分析退款原因」「达人 ROI 优化建议」"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-400"
                />
              </div>

              {aiReport && (
                <div className="mt-4">
                  {aiReport.status === "done" && aiReport.content_md ? (
                    <div className="prose prose-sm max-w-none rounded-lg border border-gray-100 bg-gray-50 p-4 text-gray-800">
                      <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                        {aiReport.content_md}
                      </pre>
                    </div>
                  ) : aiReport.status === "failed" ? (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      报告生成失败：{aiReport.error}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">
                      <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-blue-500" />
                      AI 正在分析数据并生成报告，请稍候…
                    </div>
                  )}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-gray-400">加载中…</div>}>
      <DashboardInner />
    </Suspense>
  );
}
