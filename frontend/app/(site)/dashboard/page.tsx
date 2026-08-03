"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getDashboardOverview,
  getGmvTrend,
  getTopProducts,
  syncTikTokData,
  type DashboardOverview,
  type GmvPoint,
  type Kpi,
  type TopProduct,
} from "@/lib/api";

const CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"];
const TRAFFIC_COLORS = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#9CA3AF"];

const fmtCurrency = (v: number) => (v ? `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}` : "-");
const fmtInt = (v: number) => (v ? v.toLocaleString("en-US") : "-");
const fmtPercent = (v: number) => (v ? `${v.toFixed(2)}%` : "-");
const fmtValue = (v: number, fmt?: string) => {
  if (fmt === "currency") return fmtCurrency(v);
  if (fmt === "percent") return fmtPercent(v);
  return fmtInt(v);
};

export default function DashboardPage() {
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [trend, setTrend] = useState<GmvPoint[]>([]);
  const [products, setProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, tr, tp] = await Promise.all([
        getDashboardOverview(days),
        getGmvTrend(days),
        getTopProducts(10, days),
      ]);
      setOverview(ov);
      setTrend(tr);
      setProducts(tp);
    } catch (e: any) {
      setError(e.message ?? "数据加载失败");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const r = await syncTikTokData(days, true);
      const o = r.orders ?? (r as any).result?.orders;
      const p = r.products ?? (r as any).result?.products;
      setSyncMsg(
        `同步完成：订单 ${o?.inserted ?? 0} 新增 / ${o?.updated ?? 0} 更新，商品 ${p?.inserted ?? 0} 新增 / ${p?.updated ?? 0} 更新`
      );
      await load();
    } catch (e: any) {
      setSyncMsg(`同步失败: ${e.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const kpis = overview?.kpis ?? [];
  const fallback = overview?.period.fallback;
  const trendData = trend.map((p) => ({
    date: p.date.slice(5),
    gmv: Math.round(p.gmv * 100) / 100,
    orders: 0,
  }));

  // 流量来源（暂无数据，显示占位）
  const trafficData = [
    { name: "推荐流量 For You", value: 0 },
    { name: "搜索流量 Search", value: 0 },
    { name: "达人带货 Affiliate", value: 0 },
    { name: "广告投放 Ads", value: 0 },
    { name: "店铺首页 Shop Profile", value: 0 },
    { name: "其他 Other", value: 0 },
  ];

  return (
    <div className="space-y-5">
      {/* 顶部筛选栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="ds-title">数据概览</h1>
          <p className="ds-caption mt-0.5">
            {overview
              ? `统计区间 ${overview.period.start} ~ ${overview.period.end}${
                  fallback ? "（近N天无数据，已显示全部已同步数据）" : `（近 ${overview.period.days} 天）`
                }`
              : "加载中…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* 时间范围 */}
          <div className="flex rounded-btn border border-gray-200 bg-white p-0.5">
            {[
              { d: 7, l: "近7天" },
              { d: 30, l: "近30天" },
              { d: 90, l: "近90天" },
              { d: 180, l: "近180天" },
            ].map((o) => (
              <button
                key={o.d}
                onClick={() => setDays(o.d)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                  days === o.d ? "bg-primary-600 text-white" : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {o.l}
              </button>
            ))}
          </div>
          <button onClick={handleSync} disabled={syncing} className="ds-btn-secondary text-xs">
            <span className={syncing ? "animate-spin" : ""}>↻</span>
            {syncing ? "同步中" : "同步数据"}
          </button>
        </div>
      </div>

      {/* 同步提示 */}
      {syncMsg && (
        <div
          className={`rounded-card px-4 py-2.5 text-sm ${
            syncMsg.startsWith("同步失败")
              ? "bg-decline-50 text-decline-600"
              : "bg-primary-50 text-primary-700"
          }`}
        >
          {syncMsg}
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="rounded-card bg-decline-50 px-4 py-2.5 text-sm text-decline-600">
          ⚠️ {error}，请先在「设置」页同步数据
        </div>
      )}

      {/* 2.1 核心指标卡片 */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="ds-card p-5">
              <div className="ds-skeleton mb-3 h-4 w-24" />
              <div className="ds-skeleton mb-2 h-8 w-32" />
              <div className="ds-skeleton h-3 w-20" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {kpis.map((k: Kpi, i) => {
            const up = (k.delta_pct ?? 0) >= 0;
            return (
              <div key={k.key} className="ds-card-hover p-5">
                <p className="ds-caption">{k.label}</p>
                <p className="mt-1.5 text-[28px] font-bold tabular-nums text-gray-900">
                  {fmtValue(k.value, k.format)}
                </p>
                <div className="mt-2 flex items-center gap-1.5">
                  <span className={up ? "ds-tag-up" : "ds-tag-down"}>
                    {up ? "↑" : "↓"} {Math.abs(k.delta_pct ?? 0).toFixed(1)}%
                  </span>
                  <span className="ds-caption">较上期</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 2.2 销售趋势图 + 2.3 流量来源 */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* 趋势图 (2/3) */}
        <div className="ds-card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="ds-title text-base">GMV 与订单量趋势</h2>
            <span className="ds-caption">按日</span>
          </div>
          {loading ? (
            <div className="ds-skeleton h-[280px] w-full" />
          ) : trendData.length === 0 ? (
            <div className="ds-empty">
              <div className="mb-3 text-4xl opacity-30">📈</div>
              <p className="ds-subtitle text-gray-400">暂无趋势数据</p>
              <p className="ds-caption mt-1">请先同步 TikTok 数据</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="gmvGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#94a3b8" }} />
                <YAxis
                  tick={{ fontSize: 12, fill: "#94a3b8" }}
                  tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [`$${v.toLocaleString()}`, "GMV"]}
                />
                <Area
                  type="monotone"
                  dataKey="gmv"
                  stroke="#2563EB"
                  strokeWidth={2}
                  fill="url(#gmvGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* 流量来源 (1/3) */}
        <div className="ds-card p-5">
          <h2 className="ds-title mb-4 text-base">流量来源占比</h2>
          <div className="ds-empty">
            <div className="mb-3 text-4xl opacity-30">🥧</div>
            <p className="ds-subtitle text-gray-400">暂无流量数据</p>
            <p className="ds-caption mt-1">需对接 TikTok 流量分析接口</p>
          </div>
          <div className="mt-4 space-y-2">
            {trafficData.map((t, i) => (
              <div key={t.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: TRAFFIC_COLORS[i] }}
                  />
                  <span className="text-gray-600">{t.name}</span>
                </span>
                <span className="text-gray-400">-</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 2.5 商品销量排行 + 2.6 地域销售分布 */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* 商品排行 */}
        <div className="ds-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="ds-title text-base">商品销量 TOP10</h2>
            <span className="ds-caption">按 GMV</span>
          </div>
          {loading ? (
            <div className="space-y-2">
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="ds-skeleton h-10 w-full" />
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="ds-empty">
              <div className="mb-3 text-4xl opacity-30">📦</div>
              <p className="ds-subtitle text-gray-400">暂无商品数据</p>
            </div>
          ) : (
            <div className="space-y-1">
              {products.map((p, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-gray-50"
                >
                  <span
                    className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      i < 3 ? "bg-warning-100 text-warning-600" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span className="flex-1 truncate text-sm text-gray-700">{p.product}</span>
                  <span className="text-sm font-medium tabular-nums text-gray-900">
                    {fmtCurrency(p.gmv)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 地域分布 */}
        <div className="ds-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="ds-title text-base">销售地域分布</h2>
            <span className="ds-caption">按 GMV</span>
          </div>
          <div className="ds-empty">
            <div className="mb-3 text-4xl opacity-30">🗺️</div>
            <p className="ds-subtitle text-gray-400">暂无地域数据</p>
            <p className="ds-caption mt-1">需同步订单收货地区数据</p>
          </div>
        </div>
      </div>
    </div>
  );
}
