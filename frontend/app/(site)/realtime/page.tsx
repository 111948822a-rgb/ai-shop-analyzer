"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getDashboardOverview,
  getGmvTrend,
  getTopProducts,
  type DashboardOverview,
  type GmvPoint,
  type TopProduct,
} from "@/lib/api";
import { useT } from "@/lib/i18n/context";

// ===== 设计规范常量（深色科技风） =====
const COLOR_NEON = "#60A5FA"; // primary-400 霓虹蓝
const COLOR_GRID = "#334155"; // slate-700 网格线
const COLOR_TEXT = "#94A3B8"; // slate-400 坐标文字

type Kpi = DashboardOverview["kpis"][number];

// ===== 工具函数 =====
function fmtCurrency(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "-";
  return "฿" + Math.round(n).toLocaleString("en-US");
}

function fmtInt(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "-";
  return Math.round(n).toLocaleString("en-US");
}

function fmtPercent(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "-";
  return n.toFixed(2) + "%";
}

function findKpi(
  overview: DashboardOverview | null,
  keys: string[]
): Kpi | undefined {
  if (!overview) return undefined;
  for (const k of keys) {
    const hit = overview.kpis.find((x) => x.key === k);
    if (hit) return hit;
  }
  return undefined;
}

function formatKpiValue(k: Kpi | undefined): string {
  if (!k || k.value === 0) return "-";
  if (k.format === "currency") return fmtCurrency(k.value);
  if (k.format === "percent") return fmtPercent(k.value);
  return fmtInt(k.value);
}

// 兼容 getTopProducts 可能返回数组或 { products } / { items }
function normalizeTopProducts(res: unknown): TopProduct[] {
  if (Array.isArray(res)) return res as TopProduct[];
  if (res && typeof res === "object") {
    const r = res as Record<string, unknown>;
    if (Array.isArray(r.products)) return r.products as TopProduct[];
    if (Array.isArray(r.items)) return r.items as TopProduct[];
  }
  return [];
}

// ===== 大数字计数器（带缓动滚动动画） =====
function AnimatedNumber({
  value,
  format,
}: {
  value: number;
  format: (n: number) => string;
}) {
  const [display, setDisplay] = useState(value);
  const curRef = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = curRef.current;
    const to = value;
    if (Math.abs(from - to) < 0.5) {
      curRef.current = to;
      setDisplay(to);
      return;
    }
    const duration = 800;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      const cur = from + (to - from) * eased;
      curRef.current = cur;
      setDisplay(cur);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        curRef.current = to;
        setDisplay(to);
        rafRef.current = null;
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value]);

  return <span className="tabular-nums">{format(display)}</span>;
}

// ===== 空状态 =====
function EmptyBlock({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="mb-2 text-2xl tracking-widest text-slate-600 opacity-60">
        · · ·
      </div>
      <p className="text-xs text-slate-500">{text}</p>
    </div>
  );
}

// ===== 核心指标卡 =====
function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "primary" | "emerald" | "amber" | "slate";
}) {
  const colorMap: Record<string, string> = {
    primary: "text-primary-300",
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    slate: "text-slate-300",
  };
  return (
    <div className="screen-card relative overflow-hidden p-4">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`screen-number mt-2 ${colorMap[accent]}`}>{value}</div>
    </div>
  );
}

// ===== 主页面 =====
export default function RealtimeScreenPage() {
  const t = useT();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [gmvTrend, setGmvTrend] = useState<GmvPoint[]>([]);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [timeStr, setTimeStr] = useState("--");

  // 当前时间（精确到秒），每秒刷新
  useEffect(() => {
    const pad = (n: number) => String(n).padStart(2, "0");
    const fmt = () => {
      const d = new Date();
      setTimeStr(
        `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
          d.getHours()
        )}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
      );
    };
    fmt();
    const t = setInterval(fmt, 1000);
    return () => clearInterval(t);
  }, []);

  // 数据加载：KPI 取今日，趋势/商品取近 7 天以保证曲线与榜单有数据
  const load = useCallback(async () => {
    try {
      const [o, g, p] = await Promise.all([
        getDashboardOverview(1),
        getGmvTrend(7),
        getTopProducts(5, 7),
      ]);
      setOverview(o);
      setGmvTrend(g);
      setTopProducts(normalizeTopProducts(p));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.dataLoadFailed"));
    }
  }, [t]);

  // 每 3 秒自动刷新
  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  // KPI 提取
  const gmvKpi = findKpi(overview, ["gmv", "total_gmv", "GMV"]);
  const ordersKpi = findKpi(overview, [
    "orders",
    "order_count",
    "total_orders",
  ]);
  const cvrKpi = findKpi(overview, [
    "conversion_rate",
    "cvr",
    "overall_conversion_rate",
  ]);
  const aovKpi = findKpi(overview, ["aov", "avg_order_value"]);
  const todayGmv = gmvKpi?.value ?? 0;

  // 趋势数据（面积图）
  const trendData = useMemo(
    () =>
      gmvTrend.map((p) => ({
        date: p.date,
        label: p.date.slice(5), // MM-DD
        value: p.gmv,
      })),
    [gmvTrend]
  );

  // 实时订单流水（从 gmvTrend 模拟最新 10 条）
  const orderRows = useMemo(() => {
    if (gmvTrend.length === 0) return [];
    const sorted = [...gmvTrend].sort((a, b) => (a.date < b.date ? 1 : -1));
    return Array.from({ length: 10 }, (_, i) => {
      const p = sorted[i % sorted.length];
      return {
        id: `#TTK-${String(100000 + i * 137).slice(-6)}`,
        date: p.date.slice(5),
        gmv: p.gmv,
      };
    });
  }, [gmvTrend]);

  // 跑马灯内容
  const marqueeItems = useMemo(() => {
    const items: { icon: string; text: string }[] = [];
    if (todayGmv > 0)
      items.push({ icon: "🎉", text: t("realtime.marqueeGMV", { value: fmtCurrency(todayGmv) }) });
    if (ordersKpi && ordersKpi.value > 0)
      items.push({ icon: "📦", text: t("realtime.marqueeOrders", { value: fmtInt(ordersKpi.value) }) });
    if (topProducts[0])
      items.push({ icon: "🏆", text: t("realtime.marqueeHot", { name: topProducts[0].product }) });
    items.push({ icon: "💡", text: t("realtime.marqueeRefresh") });
    items.push({ icon: "⚠️", text: t("realtime.marqueeNoAlert") });
    items.push({ icon: "🚀", text: t("realtime.marqueeRunning") });
    return items.length
      ? items
      : [{ icon: "📊", text: t("realtime.marqueeDefault") }];
  }, [todayGmv, ordersKpi, topProducts, t]);

  return (
    <div className="relative min-h-screen flex flex-col gap-3 overflow-hidden bg-screen p-3 text-slate-100 lg:p-4 lg:gap-4">
      {/* 自定义滚动动画（订单流水） */}
      <style>{`
        @keyframes rt-scroll-up {
          0% { transform: translateY(0); }
          100% { transform: translateY(-50%); }
        }
        .rt-scroll { animation: rt-scroll-up 18s linear infinite; }
        .rt-scroll:hover { animation-play-state: paused; }
      `}</style>

      {/* 环境光晕（科技感） */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 18% 0%, rgba(37,99,235,0.18), transparent 42%), radial-gradient(circle at 82% 100%, rgba(16,185,129,0.10), transparent 42%)",
        }}
      />

      {/* ============ 顶部标题栏 ============ */}
      <header className="screen-card relative flex items-center justify-between gap-4 px-4 py-3 lg:px-6">
        <div className="absolute left-0 right-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-primary-400 to-transparent opacity-70" />
        {/* 左侧：时间 + 在线人数 */}
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-2 text-sm">
            <span aria-hidden>🕐</span>
            <span className="font-medium tabular-nums text-primary-300">
              {timeStr}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>{t("realtime.online")}</span>
            <span className="tabular-nums text-primary-300">-</span>
          </div>
        </div>

        {/* 中间标题 */}
        <div className="flex flex-col items-center">
          <h1 className="gradient-text text-xl font-bold tracking-wide lg:text-3xl">
            {t("realtime.title")}
          </h1>
          <p className="mt-0.5 text-[11px] tracking-wider text-slate-400">
            {t("realtime.subtitle")}
          </p>
        </div>

        {/* 右侧：今日 GMV + 状态灯 */}
        <div className="flex min-w-0 flex-col items-end gap-1">
          <div className="text-[11px] text-slate-400">{t("realtime.todayGMV")}</div>
          <div className="text-2xl font-bold tabular-nums text-emerald-400 lg:text-3xl">
            <AnimatedNumber value={todayGmv} format={fmtCurrency} />
          </div>
          <div className="flex items-center gap-1.5 text-xs">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-emerald-400">{t("realtime.realtimeStatus")}</span>
          </div>
        </div>
      </header>

      {/* ============ 主体三列 ============ */}
      <div className="relative z-10 grid flex-1 grid-cols-1 gap-3 xl:grid-cols-3 lg:gap-4">
        {/* ---------- 左侧列：实时交易 ---------- */}
        <div className="flex flex-col gap-3 lg:gap-4">
          {/* 实时 GMV 计数器 */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-primary-400 to-primary-600" />
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">{t("realtime.liveGMV")}</span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                Live GMV
              </span>
            </div>
            <div
              className="mt-3 text-4xl font-bold tabular-nums text-primary-300 lg:text-5xl"
              style={{ textShadow: "0 0 20px rgba(96,165,250,0.5)" }}
            >
              <AnimatedNumber value={todayGmv} format={fmtCurrency} />
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs">
              <span className="text-slate-400">{t("realtime.vsPrev")}</span>
              {gmvKpi && gmvKpi.delta_pct != null ? (
                <span
                  className={
                    gmvKpi.delta_pct >= 0 ? "text-emerald-400" : "text-red-400"
                  }
                >
                  {gmvKpi.delta_pct >= 0 ? "↑" : "↓"}{" "}
                  {Math.abs(gmvKpi.delta_pct).toFixed(1)}%
                </span>
              ) : (
                <span className="text-slate-500">—</span>
              )}
              <span className="ml-auto text-slate-500">{t("realtime.today")}</span>
            </div>
          </section>

          {/* 实时订单流水 */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">{t("realtime.liveOrders")}</span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                Live Orders
              </span>
            </div>
            <div className="relative h-[260px] overflow-hidden">
              {orderRows.length > 0 ? (
                <div className="rt-scroll">
                  {[...orderRows, ...orderRows].map((row, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between border-b border-slate-700/40 py-2"
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="rounded bg-primary-500/20 px-1.5 py-0.5 text-[10px] text-primary-300">
                          NEW
                        </span>
                        <span className="tabular-nums text-xs text-slate-300">
                          {row.id}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="tabular-nums text-xs text-slate-400">
                          {row.date}
                        </span>
                        <span className="text-sm font-semibold tabular-nums text-emerald-400">
                          {fmtCurrency(row.gmv)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyBlock text={t("realtime.noOrders")} />
              )}
            </div>
          </section>

          {/* 今日实时趋势 */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">{t("realtime.trendTitle")}</span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                GMV Trend
              </span>
            </div>
            <div className="h-[200px]">
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={trendData}
                    margin={{ top: 5, right: 8, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="rtGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="0%"
                          stopColor={COLOR_NEON}
                          stopOpacity={0.5}
                        />
                        <stop
                          offset="100%"
                          stopColor={COLOR_NEON}
                          stopOpacity={0.02}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={COLOR_GRID}
                      vertical={false}
                    />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 11, fill: COLOR_TEXT }}
                      minTickGap={20}
                      axisLine={{ stroke: COLOR_GRID }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: COLOR_TEXT }}
                      tickFormatter={(v: number) =>
                        "$" + Math.round(v / 1000) + "k"
                      }
                      width={48}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(v: number) => [fmtCurrency(v), "GMV"]}
                      labelFormatter={(l: string) => t("realtime.date", { label: l })}
                      contentStyle={{
                        background: "#1E293B",
                        border: "1px solid #334155",
                        borderRadius: 8,
                        fontSize: 12,
                        color: "#e2e8f0",
                      }}
                      labelStyle={{ color: "#94a3b8" }}
                      itemStyle={{ color: "#e2e8f0" }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke={COLOR_NEON}
                      strokeWidth={2}
                      fill="url(#rtGrad)"
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyBlock text={t("realtime.noTrendData")} />
              )}
            </div>
          </section>
        </div>

        {/* ---------- 中间列：核心指标 ---------- */}
        <div className="flex flex-col gap-3 lg:gap-4">
          {/* 三行大数字卡片（订单 / 访客 / 转化率 / 客单价） */}
          <section className="grid grid-cols-2 gap-3 lg:gap-4">
            <MetricCard
              label={t("realtime.kpiOrders")}
              value={formatKpiValue(ordersKpi)}
              accent="primary"
            />
            <MetricCard label={t("realtime.kpiVisitors")} value="-" accent="slate" />
            <MetricCard
              label={t("realtime.kpiCVR")}
              value={formatKpiValue(cvrKpi)}
              accent="emerald"
            />
            <MetricCard
              label={t("realtime.kpiAOV")}
              value={formatKpiValue(aovKpi)}
              accent="amber"
            />
          </section>

          {/* 实时商品销量榜 TOP5 */}
          <section className="screen-card relative flex-1 overflow-hidden p-4 lg:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {t("realtime.top5Title")}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                Top Products
              </span>
            </div>
            {topProducts.length > 0 ? (
              <div className="space-y-2.5">
                {topProducts.slice(0, 5).map((p, i) => {
                  const maxGmv = topProducts[0]?.gmv || 1;
                  const pct = Math.max(
                    4,
                    Math.round((p.gmv / maxGmv) * 100)
                  );
                  return (
                    <div key={i} className="relative">
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="flex min-w-0 items-center gap-2">
                          <span
                            className={`flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold ${
                              i < 3
                                ? "bg-primary-500 text-white"
                                : "bg-slate-700 text-slate-300"
                            }`}
                          >
                            {i + 1}
                          </span>
                          <span className="truncate text-slate-200">
                            {p.product}
                          </span>
                        </span>
                        <span className="tabular-nums text-emerald-400">
                          {fmtCurrency(p.gmv)}
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-slate-700/60">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-300"
                          style={{ width: pct + "%" }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyBlock text={t("realtime.noTopData")} />
            )}
          </section>

          {/* 地域热力分布 */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">{t("realtime.geoTitle")}</span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                Geo Heatmap
              </span>
            </div>
            <EmptyBlock text={t("realtime.noGeoData")} />
          </section>
        </div>

        {/* ---------- 右侧列：流量与互动 ---------- */}
        <div className="flex flex-col gap-3 lg:gap-4">
          {/* 实时流量来源 */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">{t("realtime.trafficTitle")}</span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                Traffic Source
              </span>
            </div>
            <EmptyBlock text={t("realtime.noTrafficData")} />
          </section>

          {/* 实时评论 / 咨询数 */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {t("realtime.commentTitle")}
              </span>
              <span className="text-[10px] uppercase tracking-wider text-primary-300">
                Comments
              </span>
            </div>
            <div className="screen-number text-slate-400">0</div>
            <p className="mt-2 text-xs text-slate-500">{t("realtime.noCommentData")}</p>
          </section>

          {/* 库存预警（红色闪烁） */}
          <section className="screen-card relative overflow-hidden p-4 lg:p-5">
            <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-red-500 to-red-700" />
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">{t("realtime.stockTitle")}</span>
              <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-red-400">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
                Alert
              </span>
            </div>
            <EmptyBlock text={t("realtime.noStockData")} />
          </section>
        </div>
      </div>

      {/* ============ 底部跑马灯 ============ */}
      <div className="screen-card relative overflow-hidden py-2.5">
        <div className="marquee-track text-sm">
          {marqueeItems.concat(marqueeItems).map((m, i) => (
            <span
              key={i}
              className="mx-6 inline-flex items-center gap-2 text-slate-300"
            >
              <span aria-hidden>{m.icon}</span>
              <span>{m.text}</span>
            </span>
          ))}
        </div>
      </div>

      {/* 错误提示（不阻断大屏） */}
      {error && (
        <div className="pointer-events-none fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-lg border border-red-500/40 bg-slate-900/90 px-4 py-2 text-xs text-red-300 shadow-lg">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}
