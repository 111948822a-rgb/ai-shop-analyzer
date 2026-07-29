"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  getDashboardOverview,
  getGmvTrend,
  getInfluencers,
  getTopProducts,
  type DashboardOverview,
  type GmvPoint,
  type InfluencerPoint,
  type TopProduct,
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

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">AI Shop Analyzer · 销售数据分析</h1>
            <p className="text-sm text-gray-500">
              {shopIds ? `已选店铺：${shopIds.join("、")} · ` : "全部店铺 · "}
              {overview
                ? `统计区间：${overview.period.start} ~ ${overview.period.end}（近 ${overview.period.days} 天）`
                : "加载中…"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
              {[7, 30, 90].map((d) => (
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
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            ⚠️ {error}（请确认后端已启动，且 dashboard 路由已注册）
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
