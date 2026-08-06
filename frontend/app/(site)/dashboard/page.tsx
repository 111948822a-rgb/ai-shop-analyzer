"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
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
  getGeoDistribution,
  getGmvTrend,
  getOrderStatus,
  getOrderTypes,
  getShippingStats,
  getTopProducts,
  syncTikTokData,
  type DashboardOverview,
  type GeoDistributionItem,
  type GmvPoint,
  type Kpi,
  type OrderStatusItem,
  type OrderTypeItem,
  type ShippingStats,
  type TopProduct,
} from "@/lib/api";
import { useT } from "@/lib/i18n/context";
import { useShop } from "@/lib/shop/context";

const CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"];
const TRAFFIC_COLORS = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#9CA3AF"];

const fmtCurrency = (v: number) => (v ? `฿${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}` : "-");
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
  const [geo, setGeo] = useState<GeoDistributionItem[]>([]);
  const [orderStatus, setOrderStatus] = useState<OrderStatusItem[]>([]);
  const [orderTypes, setOrderTypes] = useState<OrderTypeItem[]>([]);
  const [shipping, setShipping] = useState<ShippingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const t = useT();
  const { shopIds } = useShop();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, tr, tp, gd, os, ot, sh] = await Promise.all([
        getDashboardOverview(days, shopIds),
        getGmvTrend(days, shopIds),
        getTopProducts(10, days, shopIds),
        getGeoDistribution(days, shopIds),
        getOrderStatus(days, shopIds),
        getOrderTypes(days, shopIds),
        getShippingStats(days, shopIds),
      ]);
      setOverview(ov);
      setTrend(tr);
      setProducts(tp);
      setGeo(gd);
      setOrderStatus(os);
      setOrderTypes(ot);
      setShipping(sh);
    } catch (e: any) {
      setError(e.message ?? t("common.dataLoadFailed"));
    } finally {
      setLoading(false);
    }
  }, [days, t, shopIds]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const r = await syncTikTokData(days, true);
      const o = r.result?.orders;
      const p = r.result?.products;
      setSyncMsg(
        t("sync.resultOrder", {
          inserted: o?.inserted ?? 0,
          updated: o?.updated ?? 0,
          pInserted: p?.inserted ?? 0,
          pUpdated: p?.updated ?? 0,
        })
      );
      await load();
    } catch (e: any) {
      setSyncMsg(`${t("common.syncFailed")}: ${e.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const kpis = overview?.kpis ?? [];
  const dataRange = overview?.data_range;
  const trendData = trend.map((p) => ({
    date: p.date.slice(5),
    gmv: Math.round(p.gmv * 100) / 100,
    orders: 0,
  }));

  // 当前窗口内是否有数据
  const hasData = kpis.some((k) => k.value > 0);

  // 地域分布 Top 10（按 GMV 降序）
  const geoTop10 = geo
    .slice()
    .sort((a, b) => b.gmv - a.gmv)
    .slice(0, 10);

  // 订单类型总数（用于计算占比）
  const orderTypesTotal = orderTypes.reduce((s, ot) => s + ot.orders, 0) || 1;

  // 物流商订单总数（用于计算占比）
  const shippingTotal = shipping?.providers.reduce((s, p) => s + p.orders, 0) || 1;

  return (
    <div className="space-y-5">
      {/* 顶部筛选栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="ds-title">{t("dashboard.title")}</h1>
          <p className="ds-caption mt-0.5">
            {overview
              ? t("dashboard.period", { start: overview.period.start, end: overview.period.end, days: overview.period.days })
              : t("common.loading")}
            {dataRange?.earliest && !hasData && (
              <span className="text-warning-600">
                {" "}· {t("dashboard.noOrderData", { range: `${dataRange.earliest} ~ ${dataRange.latest}` })}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* 时间范围 */}
          <div className="flex rounded-[8px] border border-gray-200 bg-white p-0.5">
            {[
              { d: 7, l: t("common.last7days") },
              { d: 30, l: t("common.last30days") },
              { d: 90, l: t("common.last90days") },
              { d: 180, l: t("common.last180days") },
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
            {syncing ? t("common.syncing") : t("common.sync")}
          </button>
        </div>
      </div>

      {/* 同步提示 */}
      {syncMsg && (
        <div
          className={`rounded-card px-4 py-2.5 text-sm ${
            syncMsg.startsWith(t("common.syncFailed"))
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
          ⚠️ {error} · {t("dashboard.syncHint")}
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
                  <span className="ds-caption">{t("common.vsPrev")}</span>
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
            <h2 className="ds-title text-base">{t("dashboard.gmvTrendTitle")}</h2>
            <span className="ds-caption">{t("dashboard.gmvTrendSub")}</span>
          </div>
          {loading ? (
            <div className="ds-skeleton h-[280px] w-full" />
          ) : trendData.length === 0 ? (
            <div className="ds-empty">
              <div className="mb-3 text-4xl opacity-30">📈</div>
              <p className="ds-subtitle text-gray-400">{t("dashboard.noTrendData")}</p>
              <p className="ds-caption mt-1">{t("dashboard.noTrendHint")}</p>
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
                  tickFormatter={(v) => `฿${Math.round(v / 1000)}k`}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [`฿${v.toLocaleString()}`, "GMV"]}
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

        {/* 订单状态分布 (1/3) */}
        <div className="ds-card p-5">
          <h2 className="ds-title mb-4 text-base">{t("dashboard.orderStatusTitle")}</h2>
          {loading ? (
            <div className="ds-skeleton h-[240px] w-full" />
          ) : orderStatus.length === 0 ? (
            <div className="ds-empty">
              <div className="mb-3 text-4xl opacity-30">🥧</div>
              <p className="ds-subtitle text-gray-400">{t("dashboard.noStatusData")}</p>
              <p className="ds-caption mt-1">{t("dashboard.noStatusHint")}</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={orderStatus}
                  dataKey="orders"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {orderStatus.map((_, i) => (
                    <Cell key={i} fill={TRAFFIC_COLORS[i % TRAFFIC_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                  }}
                  formatter={(v: number, n: string) => [`${Number(v).toLocaleString()} ${t("common.orderUnit")}`, n]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* 2.4 订单类型分析 */}
      <div className="ds-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="ds-title text-base">{t("dashboard.orderTypeTitle")}</h2>
          <span className="ds-caption">{t("dashboard.orderTypeSub")}</span>
        </div>
        {loading ? (
          <div className="ds-skeleton h-[220px] w-full" />
        ) : orderTypes.length === 0 ? (
          <div className="ds-empty">
            <div className="mb-3 text-4xl opacity-30">🧾</div>
            <p className="ds-subtitle text-gray-400">{t("dashboard.noTypeData")}</p>
            <p className="ds-caption mt-1">{t("dashboard.noTypeHint")}</p>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={orderTypes}
                  dataKey="orders"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {orderTypes.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                  }}
                  formatter={(v: number, n: string) => [`${Number(v).toLocaleString()} ${t("common.orderUnit")}`, n]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col justify-center gap-2.5">
              {orderTypes.map((ot, i) => {
                const pct = (ot.orders / orderTypesTotal) * 100;
                return (
                  <div key={ot.type} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                      />
                      <span className="text-gray-600">{ot.label}</span>
                    </span>
                    <span className="tabular-nums text-gray-900">
                      {ot.orders.toLocaleString()} {t("common.orderUnit")} · {pct.toFixed(1)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 2.5 商品销量排行 + 2.6 地域销售分布 */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* 商品排行 */}
        <div className="ds-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="ds-title text-base">{t("dashboard.topProductsTitle")}</h2>
            <span className="ds-caption">{t("dashboard.topProductsSub")}</span>
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
              <p className="ds-subtitle text-gray-400">{t("dashboard.noProductData")}</p>
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
            <h2 className="ds-title text-base">{t("dashboard.geoTitle")}</h2>
            <span className="ds-caption">{t("dashboard.geoSub")}</span>
          </div>
          {loading ? (
            <div className="ds-skeleton h-[300px] w-full" />
          ) : geoTop10.length === 0 ? (
            <div className="ds-empty">
              <div className="mb-3 text-4xl opacity-30">🗺️</div>
              <p className="ds-subtitle text-gray-400">{t("dashboard.noGeoData")}</p>
              <p className="ds-caption mt-1">{t("dashboard.noGeoHint")}</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={geoTop10}
                layout="vertical"
                margin={{ left: 10, right: 20, top: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 12, fill: "#94a3b8" }}
                  tickFormatter={(v) => `฿${Math.round(v / 1000)}k`}
                />
                <YAxis
                  type="category"
                  dataKey="province"
                  tick={{ fontSize: 12, fill: "#64748b" }}
                  width={70}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [`฿${Number(v).toLocaleString()}`, "GMV"]}
                />
                <Bar dataKey="gmv" fill="#2563EB" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* 2.7 物流配送统计 */}
      <div className="ds-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="ds-title text-base">{t("dashboard.shippingTitle")}</h2>
          <span className="ds-caption">{t("dashboard.shippingSub")}</span>
        </div>
        {loading ? (
          <div className="ds-skeleton h-[200px] w-full" />
        ) : !shipping || shipping.providers.length === 0 ? (
          <div className="ds-empty">
            <div className="mb-3 text-4xl opacity-30">🚚</div>
            <p className="ds-subtitle text-gray-400">{t("dashboard.noShippingData")}</p>
            <p className="ds-caption mt-1">{t("dashboard.noShippingHint")}</p>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={shipping.providers} margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      fontSize: 12,
                    }}
                    formatter={(v: number) => [`${Number(v).toLocaleString()} ${t("common.orderUnit")}`, t("common.orders")]}
                  />
                  <Bar dataKey="orders" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col justify-center rounded-lg bg-gray-50 p-4">
              <p className="ds-caption">{t("dashboard.avgDeliveryTime")}</p>
              <p className="mt-1 text-[32px] font-bold tabular-nums text-gray-900">
                {shipping.avg_delivery_hours != null
                  ? shipping.avg_delivery_hours.toFixed(1)
                  : "-"}
                <span className="ml-1 text-base font-normal text-gray-500">{t("common.hours")}</span>
              </p>
              <div className="mt-3 space-y-1.5">
                {shipping.providers.slice(0, 5).map((p, i) => {
                  const pct = (p.orders / shippingTotal) * 100;
                  return (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="truncate text-gray-600">{p.name}</span>
                      <span className="ml-2 flex-shrink-0 tabular-nums text-gray-500">
                        {pct.toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
