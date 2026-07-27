"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getMiaodaReport, type MiaodaReport } from "@/lib/api";

const LANG_LABELS: Record<string, string> = {
  zh: "中文",
  en: "English",
};

function scoreColor(score: number): string {
  if (score >= 80) return "#16a34a"; // 绿
  if (score >= 60) return "#d97706"; // 琥珀
  return "#dc2626"; // 红
}

function fmtFollowers(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`;
  return n.toLocaleString("zh-CN");
}

export default function InfluencerReportPage() {
  const { record_id } = useParams<{ record_id: string }>();
  const [report, setReport] = useState<MiaodaReport | null>(null);
  const [error, setError] = useState("");
  const [lang, setLang] = useState<string>("zh");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const r = await getMiaodaReport(record_id);
        if (stopped) return;
        setReport(r);
        // 默认展示第一个可用语种的话术
        const langs = r.multilingual ? Object.keys(r.multilingual) : [];
        if (langs.length && !langs.includes(lang)) setLang(langs[0]);
        if (r.status === "processing") {
          timer = setTimeout(poll, 2500);
        }
      } catch (e) {
        if (!stopped) setError(e instanceof Error ? e.message : "加载失败");
      }
    }
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [record_id, lang]);

  const isProcessing = report?.status === "processing";
  const isFailed = report?.status === "failed";

  const radarData = useMemo(() => report?.radar ?? [], [report]);

  async function copyScript() {
    const text = report?.multilingual?.[lang] ?? report?.ai_outreach_script ?? "";
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 忽略剪贴板权限错误 */
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50 text-slate-900">
      <div className="mx-auto max-w-md px-4 py-6">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            ⚠️ {error}
          </div>
        )}

        {!report && !error && (
          <Loading text="正在加载达人分析报告…" />
        )}

        {isProcessing && (
          <Loading text="AI 正在分析达人数据…" sub="通常需要 10-30 秒，本页会自动刷新" />
        )}

        {isFailed && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
            分析失败：{report?.error || "未知错误"}
          </div>
        )}

        {report && report.status === "done" && (
          <div className="space-y-4">
            {/* ---- 头部：达人 + 匹配度 ---- */}
            <Card className="overflow-hidden border-0 shadow-md">
              <div className="bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-5 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-indigo-100">达人匹配分析报告</p>
                    <h1 className="mt-0.5 text-xl font-bold">{report.influencer_name}</h1>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {report.platform && (
                        <Badge className="bg-white/20 text-white border-transparent">
                          {report.platform}
                        </Badge>
                      )}
                      {report.followers > 0 && (
                        <Badge className="bg-white/20 text-white border-transparent">
                          {fmtFollowers(report.followers)} 粉丝
                        </Badge>
                      )}
                      {report.target_product && (
                        <Badge className="bg-white/20 text-white border-transparent">
                          目标货品：{report.target_product}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-center">
                    <div
                      className="flex h-16 w-16 items-center justify-center rounded-full bg-white/15 text-2xl font-extrabold"
                      style={{ color: "#fff" }}
                    >
                      {report.ai_match_score}
                    </div>
                    <span className="mt-1 text-[11px] text-indigo-100">匹配度</span>
                  </div>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/20">
                  <div
                    className="h-full rounded-full bg-white"
                    style={{ width: `${report.ai_match_score ?? 0}%` }}
                  />
                </div>
              </div>
            </Card>

            {/* ---- AI 匹配度雷达图 ---- */}
            <Card>
              <CardHeader>
                <CardTitle>AI 匹配度雷达</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={radarData} outerRadius="72%">
                      <PolarGrid stroke="#e2e8f0" />
                      <PolarAngleAxis
                        dataKey="dimension"
                        tick={{ fill: "#475569", fontSize: 12 }}
                      />
                      <PolarRadiusAxis
                        domain={[0, 100]}
                        tick={{ fill: "#94a3b8", fontSize: 10 }}
                        axisLine={false}
                      />
                      <Radar
                        name="匹配度"
                        dataKey="value"
                        stroke="#6366f1"
                        fill="#6366f1"
                        fillOpacity={0.35}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* ---- 人货匹配分析 ---- */}
            <Card>
              <CardHeader>
                <CardTitle>人货匹配分析</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-slate-600">
                  {report.fit_analysis}
                </p>
              </CardContent>
            </Card>

            {/* ---- 避坑预警（红色高亮）---- */}
            <Card className="border-red-200 bg-red-50/60">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <span>⚠️</span> 避坑预警
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm font-medium leading-relaxed text-red-700">
                  {report.ai_risk_warning}
                </p>
              </CardContent>
            </Card>

            {/* ---- 多语种建联话术 ---- */}
            <Card>
              <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle>建联话术</CardTitle>
                <button
                  onClick={copyScript}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-700"
                >
                  {copied ? "✓ 已复制" : "一键复制"}
                </button>
              </CardHeader>
              <CardContent>
                {report.multilingual && Object.keys(report.multilingual).length > 1 && (
                  <div className="mb-3 flex flex-wrap gap-1.5">
                    {Object.keys(report.multilingual).map((k) => (
                      <button
                        key={k}
                        onClick={() => setLang(k)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                          lang === k
                            ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                            : "border-slate-200 bg-white text-slate-500 hover:text-slate-700"
                        }`}
                      >
                        {LANG_LABELS[k] ?? k}
                      </button>
                    ))}
                  </div>
                )}
                <div className="rounded-lg bg-slate-50 p-3.5">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                    {report.multilingual?.[lang] ?? report.ai_outreach_script}
                  </p>
                </div>
              </CardContent>
            </Card>

            <p className="pb-4 text-center text-[11px] text-slate-400">
              由 AI Shop Analyzer 自动生成
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Loading({ text, sub }: { text: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center py-20 text-center">
      <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
      <p className="text-sm font-medium text-slate-700">{text}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}
