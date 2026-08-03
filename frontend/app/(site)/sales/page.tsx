"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Brush,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getDashboardOverview,
  getGmvTrend,
  type DashboardOverview,
  type GmvPoint,
  type Kpi,
} from "@/lib/api";

// ===== 设计规范常量 =====
const CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"];
const COLOR_PRIMARY = "#2563EB";
const COLOR_GROWTH = "#10B981";
const COLOR_DECLINE = "#EF4444";
const COLOR_WARNING = "#F59E0B";

// ===== 时间筛选器（API 仅支持 days 参数，故按天数映射）=====
const TIME_FILTERS: { label: string; days: number }[] = [
  { label: "今日", days: 1 },
  { label: "昨日", days: 1 },
  { label: "近7天", days: 7 },
  { label: "近30天", days: 30 },
  { label: "本月", days: 30 },
  { label: "上月", days: 30 },
];

// 趋势维度切换（当前 API 仅 GMV 有序列数据，其余维度展示空状态）
const TREND_METRICS = [
  { key: "gmv", label: "GMV" },
  { key: "orders", label: "订单数" },
  { key: "buyers", label: "买家数" },
  { key: "aov", label: "客单价" },
] as const;
type TrendMetric = (typeof TREND_METRICS)[number]["key"];

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

// ===== 工具函数 =====
function fmtCurrency(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return "-";
  return "$" + Math.round(n).toLocaleString("en-US");
}

function fmtInt(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return "-";
  return Math.round(n).toLocaleString("en-US");
}

function fmtPercent(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return "-";
  return n.toFixed(1) + "%";
}

function formatKpiValue(k: Kpi): string {
  if (k.value === 0) return "-";
  if (k.format === "currency") return fmtCurrency(k.value);
  if (k.format === "percent") return fmtPercent(k.value);
  return fmtInt(k.value);
}

function fmtDateShort(d: string): string {
  // YYYY-MM-DD → MM-DD
  return d ? d.slice(5) : d;
}

// ISO week 分组键（用于"按周"聚合）
function isoWeekKey(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  if (Number.isNaN(d.getTime())) return dateStr;
  const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = tmp.getUTCDay() || 7;
  tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(
    ((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7
  );
  return `${tmp.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

// ===== 主页面 =====
export default function SalesPage() {
  const [filterIdx, setFilterIdx] = useState(3); // 默认"近30天"
  const days = TIME_FILTERS[filterIdx].days;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [gmvTrend, setGmvTrend] = useState<GmvPoint[]>([]);

  const [metric, setMetric] = useState<TrendMetric>("gmv");
  const [granularity, setGranularity] = useState<"day" | "week">("day");
  const [comparePrev, setComparePrev] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [o, g] = await Promise.all([
        getDashboardOverview(days),
        getGmvTrend(days),
      ]);
      setOverview(o);
      setGmvTrend(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "数据加载失败");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  // 趋势数据（按粒度聚合；仅 GMV 维度有数据）
  const trendData = useMemo(() => {
    if (metric !== "gmv") return [];
    if (granularity === "day") {
      return gmvTrend.map((p) => ({
        date: p.date,
        label: fmtDateShort(p.date),
        value: p.gmv,
      }));
    }
    // 按周聚合
    const map = new Map<string, number>();
    gmvTrend.forEach((p) => {
      const k = isoWeekKey(p.date);
      map.set(k, (map.get(k) ?? 0) + p.gmv);
    });
    return Array.from(map.entries())
      .sort(([a], [b]) => (a < b ? -1 : 1))
      .map(([k, v]) => ({ date: k, label: k, value: v }));
  }, [gmvTrend, metric, granularity]);

  // 24 小时分布（从 date 字段尝试提取小时，无小时信息则返回空）
  const hourlyData = useMemo(() => {
    const map = new Map<number, number>();
    let hasHour = false;
    gmvTrend.forEach((p) => {
      const tIdx = p.date.indexOf("T");
      if (tIdx < 0 || tIdx + 3 > p.date.length) return;
      const hour = parseInt(p.date.slice(tIdx + 1, tIdx + 3), 10);
      if (!Number.isNaN(hour) && hour >= 0 && hour <= 23) {
        hasHour = true;
        map.set(hour, (map.get(hour) ?? 0) + p.gmv);
      }
    });
    if (!hasHour) return [];
    return Array.from({ length: 24 }, (_, h) => ({
      hour: h,
      label: `${h}点`,
      value: map.get(h) ?? 0,
    }));
  }, [gmvTrend]);

  const hourlyPeak = useMemo(() => {
    if (!hourlyData.length) return null;
    return hourlyData.reduce(
      (max, cur) => (cur.value > max.value ? cur : max),
      hourlyData[0]
    );
  }, [hourlyData]);

  // 周度分布（按 weekday 聚合）
  const weeklyData = useMemo(() => {
    const sums = new Array(7).fill(0);
    const counts = new Array(7).fill(0);
    gmvTrend.forEach((p) => {
      const d = new Date(p.date + "T00:00:00");
      if (Number.isNaN(d.getTime())) return;
      const w = d.getDay();
      sums[w] += p.gmv;
      counts[w] += 1;
    });
    return WEEKDAYS.map((name, i) => ({
      weekday: name,
      value: sums[i],
      avg: counts[i] ? sums[i] / counts[i] : 0,
      count: counts[i],
    }));
  }, [gmvTrend]);

  const weeklyMax = useMemo(() => {
    if (!weeklyData.length) return null;
    return weeklyData.reduce(
      (max, cur) => (cur.value > max.value ? cur : max),
      weeklyData[0]
    );
  }, [weeklyData]);

  const weeklyMin = useMemo(() => {
    const filtered = weeklyData.filter((d) => d.value > 0);
    if (!filtered.length) return null;
    return filtered.reduce(
      (min, cur) => (cur.value < min.value ? cur : min),
      filtered[0]
    );
  }, [weeklyData]);

  const weeklyAvg =
    weeklyData.filter((d) => d.count > 0).length > 0
      ? weeklyData.reduce((s, d) => s + d.avg, 0) /
        weeklyData.filter((d) => d.count > 0).length
      : 0;

  // 导出 JSON
  function handleExport() {
    const payload = {
      exported_at: new Date().toISOString(),
      filter: TIME_FILTERS[filterIdx].label,
      days,
      period: overview?.period ?? null,
      previous_period: overview?.previous_period ?? null,
      kpis: overview?.kpis ?? [],
      gmv_trend: gmvTrend,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sales-${TIME_FILTERS[filterIdx].label}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      {/* 顶部工具栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="ds-title">销售分析</h1>
          <p className="ds-subtitle mt-1">
            {overview
              ? `统计区间 ${overview.period.start} ~ ${overview.period.end}（近 ${overview.period.days} 天）`
              : "加载中…"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-btn border border-gray-200 bg-white p-0.5">
            {TIME_FILTERS.map((f, i) => (
              <button
                key={f.label}
                onClick={() => setFilterIdx(i)}
                className={`rounded-[6px] px-3 py-1.5 text-xs font-medium transition ${
                  filterIdx === i
                    ? "bg-primary-600 text-white"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button onClick={handleExport} className="ds-btn-secondary">
            <span aria-hidden>⭳</span> 导出 JSON
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-card border border-decline-100 bg-decline-50 px-4 py-3 text-sm text-decline-600">
          ⚠️ {error}
        </div>
      )}

      {/* 3.1 顶部指标卡（5列） */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="ds-card p-5">
              <div className="ds-skeleton h-4 w-20" />
              <div className="ds-skeleton mt-3 h-7 w-28" />
              <div className="ds-skeleton mt-3 h-4 w-24" />
              <div className="ds-skeleton mt-4 h-10 w-full" />
            </div>
          ))}
        </div>
      ) : overview && overview.kpis.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {overview.kpis.slice(0, 5).map((k) => (
            <KpiCard key={k.key} kpi={k} spark={gmvTrend} />
          ))}
        </div>
      ) : (
        <div className="ds-card ds-empty">
          <p className="ds-body">暂无 KPI 数据</p>
        </div>
      )}

      {/* 3.2 销售趋势分析 */}
      <section className="ds-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="ds-title">销售趋势明细</h2>
            <p className="ds-subtitle mt-1">支持区间缩放，可切换维度与时间粒度</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-btn border border-gray-200 bg-white p-0.5">
              {TREND_METRICS.map((m) => (
                <button
                  key={m.key}
                  onClick={() => setMetric(m.key)}
                  className={`rounded-[6px] px-3 py-1.5 text-xs font-medium transition ${
                    metric === m.key
                      ? "bg-primary-600 text-white"
                      : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <div className="flex rounded-btn border border-gray-200 bg-white p-0.5">
              {(
                [
                  { k: "day", l: "按日" },
                  { k: "week", l: "按周" },
                ] as const
              ).map((g) => (
                <button
                  key={g.k}
                  onClick={() => setGranularity(g.k)}
                  className={`rounded-[6px] px-3 py-1.5 text-xs font-medium transition ${
                    granularity === g.k
                      ? "bg-primary-600 text-white"
                      : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {g.l}
                </button>
              ))}
            </div>
            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={comparePrev}
                onChange={(e) => setComparePrev(e.target.checked)}
                className="h-3.5 w-3.5"
              />
              叠加上期
            </label>
          </div>
        </div>

        <div className="mt-4">
          {loading ? (
            <div className="ds-skeleton h-[320px] w-full" />
          ) : trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart
                data={trendData}
                margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="gradGmv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={COLOR_PRIMARY} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={COLOR_PRIMARY} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 12, fill: "#94a3b8" }}
                  minTickGap={24}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: "#94a3b8" }}
                  tickFormatter={(v: number) => "$" + Math.round(v / 1000) + "k"}
                  width={56}
                />
                <Tooltip
                  formatter={(v: number) => [fmtCurrency(v), "GMV"]}
                  labelFormatter={(l: string) => `时间：${l}`}
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={COLOR_PRIMARY}
                  strokeWidth={2}
                  fill="url(#gradGmv)"
                  dot={false}
                  activeDot={{ r: 4 }}
                />
                {comparePrev && (
                  <Area
                    type="monotone"
                    dataKey="prev"
                    stroke={COLOR_WARNING}
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    fill="none"
                    dot={false}
                  />
                )}
                {trendData.length > 14 && (
                  <Brush
                    dataKey="label"
                    height={20}
                    stroke={COLOR_PRIMARY}
                    travellerWidth={8}
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="ds-empty">
              <p className="ds-body">
                {metric === "gmv"
                  ? "暂无 GMV 趋势数据"
                  : "暂无该维度的趋势数据，需同步更多维度数据"}
              </p>
            </div>
          )}
          {comparePrev && (
            <p className="ds-caption mt-2">
              ⓘ 当前 API 仅返回本期 GMV 序列，环比上期数据暂不可用
            </p>
          )}
        </div>
      </section>

      {/* 3.3 & 3.4 时段分布 + 周度分布 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* 3.3 时段分布 */}
        <section className="ds-card p-5">
          <div>
            <h2 className="ds-title">24小时销售分布</h2>
            <p className="ds-subtitle mt-1">按小时聚合 GMV，高亮高峰时段</p>
          </div>
          <div className="mt-4">
            {loading ? (
              <div className="ds-skeleton h-[260px] w-full" />
            ) : hourlyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={hourlyData}
                  margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11, fill: "#94a3b8" }}
                    interval={1}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#94a3b8" }}
                    tickFormatter={(v: number) => "$" + Math.round(v / 1000) + "k"}
                    width={56}
                  />
                  <Tooltip
                    formatter={(v: number) => [fmtCurrency(v), "GMV"]}
                    labelFormatter={(l: string) => `${l}`}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {hourlyData.map((d) => (
                      <Cell
                        key={d.hour}
                        fill={
                          hourlyPeak && d.hour === hourlyPeak.hour
                            ? COLOR_DECLINE
                            : COLOR_PRIMARY
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="ds-empty">
                <p className="ds-body">数据不足以按小时聚合</p>
                <p className="ds-caption mt-1">
                  当前 GMV 趋势仅含日期维度，无小时信息
                </p>
              </div>
            )}
          </div>
          {hourlyPeak && hourlyPeak.value > 0 && (
            <p className="ds-body mt-3">
              高峰时段：
              <span className="font-semibold text-decline-600">
                {hourlyPeak.label}
              </span>
              ，GMV {fmtCurrency(hourlyPeak.value)}
            </p>
          )}
        </section>

        {/* 3.4 周度分布 */}
        <section className="ds-card p-5">
          <div>
            <h2 className="ds-title">周度销售规律</h2>
            <p className="ds-subtitle mt-1">周一至周日 GMV 总量与日均</p>
          </div>
          <div className="mt-4">
            {loading ? (
              <div className="ds-skeleton h-[260px] w-full" />
            ) : weeklyData.some((d) => d.value > 0) ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={weeklyData}
                  margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                  <XAxis
                    dataKey="weekday"
                    tick={{ fontSize: 12, fill: "#94a3b8" }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#94a3b8" }}
                    tickFormatter={(v: number) => "$" + Math.round(v / 1000) + "k"}
                    width={56}
                  />
                  <Tooltip
                    formatter={(v: number) => [fmtCurrency(v), "GMV"]}
                    labelFormatter={(l: string) => `${l}`}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {weeklyData.map((d) => {
                      let fill = COLOR_PRIMARY;
                      if (weeklyMax && d.weekday === weeklyMax.weekday)
                        fill = COLOR_GROWTH;
                      else if (weeklyMin && d.weekday === weeklyMin.weekday)
                        fill = COLOR_DECLINE;
                      return <Cell key={d.weekday} fill={fill} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="ds-empty">
                <p className="ds-body">暂无周度数据</p>
              </div>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-4 ds-body">
            <span>
              日均 GMV：
              <span className="font-semibold text-primary-600">
                {fmtCurrency(weeklyAvg)}
              </span>
            </span>
            {weeklyMax && weeklyMax.value > 0 && (
              <span>
                最高：
                <span className="font-semibold text-growth-600">
                  {weeklyMax.weekday}
                </span>
                （{fmtCurrency(weeklyMax.value)}）
              </span>
            )}
            {weeklyMin && weeklyMin.value > 0 && (
              <span>
                最低：
                <span className="font-semibold text-decline-600">
                  {weeklyMin.weekday}
                </span>
                （{fmtCurrency(weeklyMin.value)}）
              </span>
            )}
          </div>
        </section>
      </div>

      {/* 3.5 & 3.6 订单状态 + 支付方式 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 3.5 订单状态分布 */}
        <section className="ds-card p-5">
          <div>
            <h2 className="ds-title">订单状态占比</h2>
            <p className="ds-subtitle mt-1">各状态订单数量与金额</p>
          </div>
          <div className="mt-4">
            <div className="ds-empty">
              <p className="ds-body">暂无数据，需同步更多维度数据</p>
              <p className="ds-caption mt-1">后端暂未提供订单状态维度 API</p>
            </div>
          </div>
        </section>

        {/* 3.6 支付方式分析 */}
        <section className="ds-card p-5 lg:col-span-2">
          <div>
            <h2 className="ds-title">支付方式构成</h2>
            <p className="ds-subtitle mt-1">
              COD 货到付款 / 信用卡 / 电子钱包 / 银行转账
            </p>
          </div>
          <div className="mt-4">
            <div className="ds-empty">
              <p className="ds-body">暂无数据，需同步更多维度数据</p>
              <p className="ds-caption mt-1">后端暂未提供支付方式维度 API</p>
            </div>
          </div>
        </section>
      </div>

      {/* 配色说明（仅供调试/审查，保留为辅助信息） */}
      <p className="ds-caption" aria-hidden>
        图表配色：{CHART_COLORS.join(" · ")} · 主色 {COLOR_PRIMARY} · 增长 {COLOR_GROWTH} · 下降{" "}
        {COLOR_DECLINE} · 预警 {COLOR_WARNING}
      </p>
    </div>
  );
}

// ===== KPI 卡片（含迷你趋势图） =====
function KpiCard({ kpi, spark }: { kpi: Kpi; spark: GmvPoint[] }) {
  const hasDelta =
    kpi.delta_pct !== null && kpi.delta_pct !== undefined;
  const delta = kpi.delta_pct ?? 0;
  const isUp = delta >= 0;
  const isGood = hasDelta ? isUp === kpi.higher_is_better : true;
  const arrow = !hasDelta ? "—" : isUp ? "↑" : "↓";
  const tagClass = !hasDelta
    ? "ds-tag bg-gray-100 text-gray-500"
    : isGood
    ? "ds-tag-up"
    : "ds-tag-down";

  // 迷你趋势图：取近 14 个点（API 仅有 GMV 序列，作为整体销售趋势上下文）
  const sparkData = spark.slice(-14).map((p) => ({ v: p.gmv }));
  const gradId = `spark-${kpi.key}`;

  return (
    <div className="ds-card-hover p-5">
      <p className="ds-caption">{kpi.label}</p>
      <p className="mt-2 text-2xl font-bold tabular-nums text-gray-900">
        {formatKpiValue(kpi)}
      </p>
      <div className="mt-2 flex items-center gap-1.5">
        {hasDelta ? (
          <span className={tagClass}>
            <span aria-hidden>{arrow}</span>
            {Math.abs(delta).toFixed(1)}%
          </span>
        ) : (
          <span className={tagClass}>—</span>
        )}
        <span className="ds-caption">环比</span>
      </div>
      <div className="mt-3 h-10">
        {sparkData.length > 1 ? (
          <ResponsiveContainer width="100%" height={40}>
            <AreaChart
              data={sparkData}
              margin={{ top: 2, right: 0, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={COLOR_PRIMARY} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={COLOR_PRIMARY} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={COLOR_PRIMARY}
                strokeWidth={1.5}
                fill={`url(#${gradId})`}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="ds-skeleton h-10 w-full" />
        )}
      </div>
    </div>
  );
}
