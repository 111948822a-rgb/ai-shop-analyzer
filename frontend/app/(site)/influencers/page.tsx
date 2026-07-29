"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import {
  evaluateInfluencer,
  getMiaodaDashboard,
  type MiaodaDashboard,
  type MiaodaInfluencer,
} from "@/lib/api";

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7"];

function fmtFollowers(n: number | null): string {
  if (n == null) return "—";
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`;
  return n.toLocaleString("zh-CN");
}

function pct(v: number | null): string {
  if (v == null) return "—";
  return `${v}%`;
}

export default function InfluencersDashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<MiaodaDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [evaluating, setEvaluating] = useState<string | null>(null);

  useEffect(() => {
    getMiaodaDashboard()
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "加载达人数据看板失败");
        setLoading(false);
      });
  }, []);

  async function generateReport(inf: MiaodaInfluencer) {
    setEvaluating(inf.influencer_id);
    try {
      const r = await evaluateInfluencer({
        influencer_id: inf.influencer_id,
        influencer_name: inf.name,
        platform: inf.platform,
        followers: inf.followers,
        target_product: "",
      });
      router.push(`/report/influencer/${r.record_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成报告失败");
      setEvaluating(null);
    }
  }

  if (loading) return <p className="text-gray-500">正在加载达人数据看板…</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return null;

  const { summary, items, configured, source, error: miaodaError } = data;
  const suspiciousRate =
    summary.total > 0
      ? ((summary.suspicious_count / summary.total) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">达人数据看板</h1>
          <p className="text-sm text-gray-500 mt-1">
            数据来源：
            <span className="font-medium">
              {source === "miaoda" ? "秒搭系统" : "本地库"}
            </span>
            {!configured && (
              <span className="ml-2 text-amber-600">
                （秒搭数据源未配置，当前为本地/示例数据）
              </span>
            )}
          </p>
        </div>
      </div>

      {!configured && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <strong>提示：</strong> 后端尚未配置 <code>MIAODA_API_URL</code> 与{" "}
          <code>MIAODA_API_KEY</code>，因此目前看不到秒搭实时达人数据。请在 Render 后端环境变量中填好这两项（
          <code>MIAODA_API_URL</code> 填完整地址，例如{" "}
          <code>https://&lt;域名&gt;/app/&lt;appId&gt;/openapi/influencers</code>
          ），并在秒搭后台确认该 OpenAPI 已发布、所用 Key 已授权，重新部署后即可在此看到真实看板。
        </div>
      )}

      {configured && source !== "miaoda" && miaodaError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <strong>秒搭数据拉取失败：</strong> 后端已配置数据源，但秒搭拒绝了请求。真实原因：
          <div className="mt-1 font-mono text-xs break-all">{miaodaError}</div>
          <div className="mt-2">
            通常是以下原因之一：① 秒搭 API Key 无效 / 未授权 / 与 appId 不匹配；② 该 OpenAPI 接口未发布。请到秒搭后台核对 Key 与接口权限。
          </div>
        </div>
      )}

      {/* ---- KPI 卡片 ---- */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="达人总数" value={summary.total.toLocaleString("zh-CN")} />
        <KpiCard label="总粉丝量" value={fmtFollowers(summary.total_followers)} />
        <KpiCard label="平均 ROI" value={summary.avg_roi.toFixed(2)} />
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
              <Empty />
            )}
          </CardContent>
        </Card>
      </div>

      {/* ---- 达人明细表 + 生成报告 ---- */}
      <Card>
        <CardHeader>
          <CardTitle>达人明细（手动生成报告）</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <Empty text="暂无达人数据" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-400">
                    <th className="py-2 pr-4 font-medium">达人</th>
                    <th className="py-2 pr-4 font-medium">平台</th>
                    <th className="py-2 pr-4 text-right font-medium">粉丝</th>
                    <th className="py-2 pr-4 text-right font-medium">ROI</th>
                    <th className="py-2 pr-4 font-medium">状态</th>
                    <th className="py-2 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((inf) => (
                    <tr key={inf.influencer_id} className="border-b last:border-0">
                      <td className="py-3 pr-4">
                        <div className="font-medium text-gray-900">{inf.name}</div>
                        <div className="text-xs text-gray-400">
                          {inf.niche || "未知类目"}
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-gray-600">{inf.platform || "—"}</td>
                      <td className="py-3 pr-4 text-right text-gray-800">
                        {fmtFollowers(inf.followers)}
                      </td>
                      <td className="py-3 pr-4 text-right text-gray-800">
                        {inf.roi == null ? "—" : inf.roi.toFixed(2)}
                      </td>
                      <td className="py-3 pr-4">
                        {inf.is_suspicious ? (
                          <Badge className="bg-red-100 text-red-600 border-transparent">
                            疑似异常
                          </Badge>
                        ) : (
                          <span className="text-gray-400">正常</span>
                        )}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => generateReport(inf)}
                          disabled={evaluating === inf.influencer_id}
                          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {evaluating === inf.influencer_id ? "生成中…" : "生成报告"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
