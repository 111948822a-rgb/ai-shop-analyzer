"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import TimeSlicer, {
  type PeriodPreset,
  type DateRange,
  presetToRange,
} from "@/components/dashboard/TimeSlicer";
import {
  getMiaodaDashboard,
  generatePeriodReport,
  type MiaodaDashboard,
  type MiaodaInfluencer,
  type PeriodReport,
} from "@/lib/api";

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7"];

// ===== 排序类型 =====
type SortKey = "followers" | "engagement_rate" | "conversion_rate" | "roi";
type SortDir = "asc" | "desc";

function fmtFollowers(n: number | null): string {
  if (n == null) return "—";
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`;
  return n.toLocaleString("zh-CN");
}

export default function InfluencersDashboardPage() {
  const [data, setData] = useState<MiaodaDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 全局时间切片
  const [period, setPeriod] = useState<PeriodPreset>("30d");
  const [dateRange, setDateRange] = useState<DateRange>({});

  // 报告生成
  const [reportPeriod, setReportPeriod] = useState<PeriodPreset>("30d");
  const [reportRange, setReportRange] = useState<DateRange>({});
  const [report, setReport] = useState<PeriodReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

  // 达人明细列表排序
  const [sortKey, setSortKey] = useState<SortKey>("followers");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchData = useCallback(async (range: DateRange) => {
    setLoading(true);
    setError("");
    try {
      const d = await getMiaodaDashboard(undefined, range);
      setData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载达人数据看板失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(dateRange);
  }, [dateRange, fetchData]);

  const handlePeriodChange = useCallback((preset: PeriodPreset, range: DateRange) => {
    setPeriod(preset);
    setDateRange(range);
  }, []);

  const handleReportPeriodChange = useCallback((preset: PeriodPreset, range: DateRange) => {
    setReportPeriod(preset);
    setReportRange(range);
  }, []);

  const handleGenerateReport = async () => {
    setReportLoading(true);
    setReportError("");
    setReport(null);
    try {
      const r = await generatePeriodReport({
        start_date: reportRange.start_date,
        end_date: reportRange.end_date,
      });
      setReport(r);
    } catch (e) {
      setReportError(e instanceof Error ? e.message : "生成报告失败");
    } finally {
      setReportLoading(false);
    }
  };

  // 达人明细列表：按选中列排序（null 值排到最后）
  const sortedItems = useMemo<MiaodaInfluencer[]>(() => {
    const list = data?.items ?? [];
    const sorted = [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return sorted;
  }, [data?.items, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (loading && !data) return <p className="text-gray-500">正在加载达人数据看板…</p>;
  if (error && !data) return <p className="text-red-600">{error}</p>;
  if (!data) return null;

  const { summary, configured, source, error: miaodaError } = data;
  const suspiciousRate =
    summary.total > 0
      ? ((summary.suspicious_count / summary.total) * 100).toFixed(1)
      : "0.0";

  // 计算平均互动率/转化率（从 scatter 数据）
  const engagementValues = summary.scatter
    .map((s) => s.engagement_rate)
    .filter((v): v is number => v != null && v > 0);
  const avgEngagement =
    engagementValues.length > 0
      ? (engagementValues.reduce((a, b) => a + b, 0) / engagementValues.length).toFixed(1)
      : "0.0";

  const conversionValues = summary.scatter
    .map((s) => s.conversion_rate)
    .filter((v): v is number => v != null && v > 0);
  const avgConversion =
    conversionValues.length > 0
      ? (conversionValues.reduce((a, b) => a + b, 0) / conversionValues.length).toFixed(1)
      : "0.0";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="mb-2 flex items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
            >
              <span aria-hidden>←</span> 返回主页
            </Link>
          </div>
          <h1 className="text-2xl font-bold">达人数据看板</h1>
          <p className="text-sm text-gray-500 mt-1">
            数据来源：<span className="font-medium">{source === "miaoda" ? "秒搭系统" : "本地库"}</span>
            {!configured && (
              <span className="ml-2 text-amber-600">
                （秒搭数据源未配置，当前为本地/示例数据）
              </span>
            )}
            {loading && <span className="ml-2 text-indigo-500">刷新中…</span>}
          </p>
        </div>
      </div>

      {/* ---- 全局时间切片 ---- */}
      <Card>
        <CardContent className="pt-4">
          <TimeSlicer value={period} onChange={handlePeriodChange} />
        </CardContent>
      </Card>

      {/* ---- 秒搭拉取失败提示 ---- */}
      {configured && source !== "miaoda" && miaodaError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <strong>秒搭数据拉取失败：</strong> {miaodaError}
        </div>
      )}

      {/* ---- KPI 卡片 ---- */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="达人总数" value={summary.total.toLocaleString("zh-CN")} />
        <KpiCard label="总粉丝量" value={fmtFollowers(summary.total_followers)} />
        <KpiCard label="平均互动率" value={`${avgEngagement}%`} />
        <KpiCard
          label="异常占比"
          value={`${suspiciousRate}%`}
          danger={summary.suspicious_count > 0}
        />
      </div>

      {/* ---- 图表区 ---- */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>平台分布</CardTitle>
          </CardHeader>
          <CardContent>
            {summary.platform_distribution.length ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={summary.platform_distribution}
                      dataKey="count"
                      nameKey="platform"
                      outerRadius="80%"
                      label={(e: { platform: string; count: number }) =>
                        `${e.platform} (${e.count})`
                      }
                    >
                      {summary.platform_distribution.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <Empty />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>ROI 分布</CardTitle>
          </CardHeader>
          <CardContent>
            {summary.roi_buckets.some((b) => b.count > 0) ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={summary.roi_buckets}>
                    <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <Empty text="暂无 ROI 数据" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ---- 粉丝量 Top 10 达人 ---- */}
      {summary.top_by_followers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>粉丝量 Top 10</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-5">
              {summary.top_by_followers.map((inf, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-600">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">{inf.name}</p>
                    <p className="text-xs text-gray-400">
                      {inf.platform || "—"} · {fmtFollowers(inf.followers)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---- 达人明细列表 ---- */}
      <section className="ds-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="ds-title">达人明细列表</h2>
            <p className="ds-subtitle mt-1">
              点击列头排序 · 共 {sortedItems.length} 位达人
            </p>
          </div>
          <div className="flex items-center gap-1.5 ds-caption">
            <span>排序：</span>
            <span className="text-gray-700">
              {sortKey === "followers"
                ? "粉丝数"
                : sortKey === "engagement_rate"
                  ? "互动率"
                  : sortKey === "conversion_rate"
                    ? "转化率"
                    : "ROI"}
            </span>
            <span>({sortDir === "asc" ? "升序" : "降序"})</span>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {sortedItems.length > 0 ? (
            <table className="w-full text-left text-[13px]">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="px-3 py-2 text-left">头像 / 名称</th>
                  <th className="px-3 py-2 text-left">平台</th>
                  <Th
                    onClick={() => toggleSort("followers")}
                    active={sortKey === "followers"}
                    dir={sortDir}
                    align="right"
                  >
                    粉丝数
                  </Th>
                  <Th
                    onClick={() => toggleSort("engagement_rate")}
                    active={sortKey === "engagement_rate"}
                    dir={sortDir}
                    align="right"
                  >
                    互动率
                  </Th>
                  <Th
                    onClick={() => toggleSort("conversion_rate")}
                    active={sortKey === "conversion_rate"}
                    dir={sortDir}
                    align="right"
                  >
                    转化率
                  </Th>
                  <Th
                    onClick={() => toggleSort("roi")}
                    active={sortKey === "roi"}
                    dir={sortDir}
                    align="right"
                  >
                    ROI
                  </Th>
                  <th className="px-3 py-2 text-left">状态</th>
                  <th className="px-3 py-2 text-left">垂直领域</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sortedItems.map((inf) => (
                  <tr key={inf.influencer_id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        {inf.avatar_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={inf.avatar_url}
                            alt={inf.name}
                            className="h-8 w-8 shrink-0 rounded-full object-cover"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).style.display =
                                "none";
                            }}
                          />
                        ) : (
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-600">
                            {inf.name?.charAt(0) || "?"}
                          </span>
                        )}
                        <span className="max-w-[160px] truncate font-medium text-gray-900" title={inf.name}>
                          {inf.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-gray-700">
                      {inf.platform || "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                      {fmtFollowers(inf.followers)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                      {inf.engagement_rate != null
                        ? `${inf.engagement_rate.toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                      {inf.conversion_rate != null
                        ? `${inf.conversion_rate.toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                      {inf.roi != null ? inf.roi.toFixed(2) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {inf.is_suspicious ? (
                        <span className="ds-tag-down">异常</span>
                      ) : (
                        <span className="ds-tag-up">正常</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-700">
                      {inf.niche || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="ds-empty">
              <p className="ds-body">暂无达人明细数据，请先在秒搭中添加达人</p>
            </div>
          )}
        </div>
      </section>

      {/* ---- 手动生成报告 ---- */}
      <Card>
        <CardHeader>
          <CardTitle>手动生成报告</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 报告时间选择 */}
          <div>
            <p className="mb-2 text-sm font-medium text-gray-600">选择报告时间段：</p>
            <TimeSlicer value={reportPeriod} onChange={handleReportPeriodChange} />
          </div>

          {/* 生成按钮 */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerateReport}
              disabled={reportLoading}
              className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {reportLoading ? "生成中…" : "生成报告"}
            </button>
            {report && (
              <button
                onClick={() => {
                  const blob = new Blob([report.report_md], { type: "text/markdown" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `达人报告_${report.period.label}.md`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
              >
                下载 Markdown
              </button>
            )}
          </div>

          {/* 错误提示 */}
          {reportError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              {reportError}
            </div>
          )}

          {/* 报告内容展示 */}
          {report && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 border-b pb-2">
                <Badge className="bg-green-100 text-green-700 border-transparent">
                  已生成
                </Badge>
                <span className="text-sm text-gray-500">
                  {report.period.label} · 生成于 {new Date(report.generated_at).toLocaleString("zh-CN")}
                </span>
              </div>
              <div className="prose prose-sm max-w-none rounded-lg border border-gray-100 bg-gray-50 p-4">
                <ReactMarkdown
                  components={{
                    table: ({ children }) => (
                      <table className="w-full border-collapse text-sm">{children}</table>
                    ),
                    th: ({ children }) => (
                      <th className="border border-gray-200 bg-gray-100 px-3 py-1.5 text-left font-medium">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="border border-gray-200 px-3 py-1.5">{children}</td>
                    ),
                  }}
                >
                  {report.report_md}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KpiCard({
  label,
  value,
  danger,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p
        className={`mt-1 text-2xl font-bold ${
          danger ? "text-red-600" : "text-gray-900"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function Empty({ text = "暂无数据" }: { text?: string }) {
  return (
    <div className="flex h-64 items-center justify-center text-sm text-gray-400">
      {text}
    </div>
  );
}

// ===== 排序表头 =====
function Th({
  children,
  onClick,
  active,
  dir,
  align = "left",
}: {
  children: React.ReactNode;
  onClick: () => void;
  active: boolean;
  dir: SortDir;
  align?: "left" | "right";
}) {
  return (
    <th
      onClick={onClick}
      className={`cursor-pointer select-none px-3 py-2 ${
        align === "right" ? "text-right" : "text-left"
      } ${active ? "text-primary-600" : "text-gray-500"} hover:text-primary-600`}
    >
      <span
        className={`inline-flex items-center gap-1 ${
          align === "right" ? "flex-row-reverse" : ""
        }`}
      >
        {children}
        <span aria-hidden className="text-[10px]">
          {active ? (dir === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </span>
    </th>
  );
}
