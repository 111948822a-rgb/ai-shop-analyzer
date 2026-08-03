"use client";

import { useCallback, useEffect, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import {
  getTikTokStatus,
  syncTikTokData,
  generateAIReport,
  getAIReport,
  type TikTokStatus,
  type TikTokSyncResult,
  type AIReportResponse,
} from "@/lib/api";

const DAY_OPTIONS = [7, 30, 90, 180];

/* ======================== 工具函数 ======================== */

function formatTime(s: string | null | undefined): string {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return s;
  return d.toLocaleString("zh-CN", { hour12: false });
}

function formatRemaining(hours: number | null): string {
  if (hours === null) return "—";
  if (hours <= 0) return "已过期";
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    const h = Math.round(hours % 24);
    return h > 0 ? `${days} 天 ${h} 小时` : `${days} 天`;
  }
  return `${hours.toFixed(1)} 小时`;
}

type TokenState = {
  label: string;
  badge: string;
  dot: string;
};

function getTokenState(t: TikTokStatus["token"]): TokenState {
  const expired =
    !t.has_access_token || (t.remaining_hours !== null && t.remaining_hours <= 0);
  if (expired) {
    return {
      label: "已过期",
      badge: "bg-decline-50 text-decline-600",
      dot: "bg-decline-500",
    };
  }
  if (t.is_expiring_soon) {
    return {
      label: "即将过期",
      badge: "bg-warning-50 text-warning-600",
      dot: "bg-warning-500",
    };
  }
  return {
    label: "有效",
    badge: "bg-growth-50 text-growth-600",
    dot: "bg-growth-500",
  };
}

/* ======================== Markdown 渲染样式 ======================== */

const mdComponents: Components = {
  h1: ({ node, ...props }) => (
    <h1 className="mb-3 mt-4 text-xl font-bold text-gray-900" {...props} />
  ),
  h2: ({ node, ...props }) => (
    <h2 className="mb-2 mt-4 text-lg font-bold text-primary-700" {...props} />
  ),
  h3: ({ node, ...props }) => (
    <h3 className="mb-2 mt-3 text-base font-semibold text-gray-900" {...props} />
  ),
  h4: ({ node, ...props }) => (
    <h4 className="mb-1 mt-3 text-sm font-semibold text-gray-800" {...props} />
  ),
  p: ({ node, ...props }) => (
    <p className="my-2 leading-relaxed text-gray-700" {...props} />
  ),
  ul: ({ node, ...props }) => (
    <ul className="my-2 list-disc space-y-1 pl-5" {...props} />
  ),
  ol: ({ node, ...props }) => (
    <ol className="my-2 list-decimal space-y-1 pl-5" {...props} />
  ),
  li: ({ node, ...props }) => (
    <li className="leading-relaxed text-gray-700" {...props} />
  ),
  strong: ({ node, ...props }) => (
    <strong className="font-semibold text-gray-900" {...props} />
  ),
  code: ({ node, className, children, ...props }) => {
    const isBlock = typeof className === "string" && className.includes("language-");
    if (isBlock) {
      return (
        <code className="text-inherit" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="rounded-datalabel bg-gray-200 px-1 py-0.5 text-[12px] text-gray-800"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ node, ...props }) => (
    <pre
      className="my-3 overflow-x-auto rounded-btn bg-gray-800 p-3 text-[12px] leading-relaxed text-gray-100"
      {...props}
    />
  ),
  blockquote: ({ node, ...props }) => (
    <blockquote
      className="my-2 border-l-4 border-primary-300 bg-primary-50/50 py-1 pl-3 text-gray-600"
      {...props}
    />
  ),
  table: ({ node, ...props }) => (
    <table className="my-3 w-full border-collapse text-sm" {...props} />
  ),
  thead: ({ node, ...props }) => <thead className="bg-gray-100" {...props} />,
  th: ({ node, ...props }) => (
    <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800" {...props} />
  ),
  td: ({ node, ...props }) => (
    <td className="border border-gray-200 px-2 py-1 text-gray-700" {...props} />
  ),
  hr: ({ node, ...props }) => <hr className="my-4 border-gray-200" {...props} />,
  a: ({ node, ...props }) => (
    <a
      className="text-primary-600 underline hover:text-primary-700"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
};

/* ======================== 小组件 ======================== */

function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  );
}

function DaySelector({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (d: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="inline-flex rounded-btn border border-gray-200 bg-gray-50 p-0.5">
      {DAY_OPTIONS.map((d) => (
        <button
          key={d}
          type="button"
          disabled={disabled}
          onClick={() => onChange(d)}
          className={`rounded-[6px] px-3 py-1 text-xs font-medium transition disabled:opacity-50 ${
            value === d
              ? "bg-white text-primary-600 shadow-sm"
              : "text-gray-500 hover:text-gray-800"
          }`}
        >
          {d}天
        </button>
      ))}
    </div>
  );
}

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="ds-caption">{label}</dt>
      <dd className="ds-body mt-0.5 font-medium text-gray-900">{children}</dd>
    </div>
  );
}

/* ======================== 页面 ======================== */

export default function SettingsPage() {
  // TikTok 状态
  const [tkStatus, setTkStatus] = useState<TikTokStatus | null>(null);
  const [tkLoading, setTkLoading] = useState(true);
  const [tkError, setTkError] = useState<string | null>(null);

  // 数据同步
  const [syncDays, setSyncDays] = useState(180);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<TikTokSyncResult | null>(null);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  // AI 报告
  const [reportDays, setReportDays] = useState(30);
  const [reportQuery, setReportQuery] = useState("");
  const [aiReport, setAiReport] = useState<AIReportResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setTkError(null);
    try {
      const s = await getTikTokStatus();
      setTkStatus(s);
    } catch (e) {
      setTkError(e instanceof Error ? e.message : "获取 TikTok 状态失败");
    } finally {
      setTkLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  async function handleSync(foreground: boolean) {
    setSyncing(true);
    setSyncError(null);
    setSyncMsg(null);
    setSyncResult(null);
    try {
      const r = await syncTikTokData(syncDays, foreground);
      setSyncResult(r);
      if (r.status === "done" && r.result) {
        const { orders, products } = r.result;
        setSyncMsg(
          `前台同步完成（${r.start} ~ ${r.end}）：订单 ${orders.inserted} 新增 / ${orders.updated} 更新 / ${orders.skipped} 跳过；商品 ${products.inserted} 新增 / ${products.updated} 更新 / ${products.skipped} 跳过。`
        );
      } else {
        setSyncMsg(
          r.message ??
            `同步任务已在后台启动（${r.start} ~ ${r.end}），稍后请刷新查看最近同步时间。`
        );
      }
      // 同步后刷新状态（更新最近同步时间）
      loadStatus();
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : "同步失败");
    } finally {
      setSyncing(false);
    }
  }

  // AI 报告轮询：status 非 done/failed 时 3 秒后重试
  useEffect(() => {
    if (!aiReport || aiReport.status === "done" || aiReport.status === "failed") return;
    const timer = setTimeout(async () => {
      try {
        const r = await getAIReport(aiReport.report_id);
        setAiReport(r);
      } catch {
        // 忽略轮询过程中的瞬时错误
      }
    }, 3000);
    return () => clearTimeout(timer);
  }, [aiReport]);

  async function handleGenerateReport() {
    setGenerating(true);
    setReportError(null);
    setAiReport(null);
    try {
      // 前台同步执行，数据量可控时直接等结果
      const r = await generateAIReport(reportDays, reportQuery, true);
      setAiReport(r);
    } catch (e) {
      setReportError(e instanceof Error ? e.message : "报告生成失败");
    } finally {
      setGenerating(false);
    }
  }

  const tokenState = tkStatus?.token ? getTokenState(tkStatus.token) : null;
  const reportRunning =
    aiReport && (aiReport.status === "pending" || aiReport.status === "running");

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* ============ 区块1：TikTok Shop 数据源配置 ============ */}
      <section className="ds-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="ds-title">TikTok Shop 数据源配置</h2>
            <p className="ds-subtitle mt-1">
              管理 TikTok Partner API 授权状态与订单 / 商品数据同步
            </p>
          </div>
          {tokenState && tkStatus?.configured && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-datalabel px-2 py-0.5 text-xs font-medium ${tokenState.badge}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${tokenState.dot}`} />
              Token {tokenState.label}
            </span>
          )}
        </div>

        {tkLoading ? (
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i}>
                <div className="ds-skeleton h-3 w-16" />
                <div className="ds-skeleton mt-2 h-4 w-28" />
              </div>
            ))}
          </div>
        ) : tkError ? (
          <div className="mt-5 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
            ⚠️ {tkError}
          </div>
        ) : (
          <dl className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <InfoRow label="店铺 ID">
              {tkStatus?.shop_id ? (
                <code className="rounded-datalabel bg-gray-100 px-1.5 py-0.5 text-[12px]">
                  {tkStatus.shop_id}
                </code>
              ) : (
                "—"
              )}
            </InfoRow>
            <InfoRow label="店铺名称">
              {tkStatus?.shop_name || "—"}
            </InfoRow>
            <InfoRow label="Token 状态">
              {tokenState ? tokenState.label : "—"}
            </InfoRow>
            <InfoRow label="剩余有效时长">
              {tkStatus?.token ? formatRemaining(tkStatus.token.remaining_hours) : "—"}
            </InfoRow>
            <InfoRow label="到期时间">
              {tkStatus?.token ? formatTime(tkStatus.token.expires_at) : "—"}
            </InfoRow>
            <InfoRow label="最近同步时间">
              {tkStatus?.last_sync ? formatTime(tkStatus.last_sync) : "从未同步"}
            </InfoRow>
          </dl>
        )}

        {/* Token 即将过期预警（橙色） */}
        {tkStatus?.configured &&
          tkStatus.token.has_access_token &&
          tkStatus.token.is_expiring_soon && (
            <div className="mt-4 flex items-start gap-2 rounded-btn border border-warning-100 bg-warning-50 px-3 py-2 text-sm text-warning-600">
              <span aria-hidden>⚠️</span>
              <span>
                Token 即将过期，剩余 {formatRemaining(tkStatus.token.remaining_hours)}，建议尽快续期以免数据同步中断。
              </span>
            </div>
          )}

        {/* Token 已过期 / 未授权提示 */}
        {tkStatus?.configured &&
          !tkStatus.token.has_access_token && (
            <div className="mt-4 flex items-start gap-2 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
              <span aria-hidden>⚠️</span>
              <span>
                未检测到有效 Access Token，请在后端 .env 配置 <code className="rounded-datalabel bg-white/60 px-1">TK_AUTH_ACCESS_TOKEN</code> / <code className="rounded-datalabel bg-white/60 px-1">TK_AUTH_REFRESH_TOKEN</code> 并完成授权。
              </span>
            </div>
          )}

        {/* 未配置 Partner API */}
        {tkStatus && !tkStatus.configured && (
          <div className="mt-4 rounded-btn border border-warning-100 bg-warning-50 px-3 py-2 text-sm text-warning-600">
            未配置 TikTok Partner API。请在后端 .env 配置 <code className="rounded-datalabel bg-white/60 px-1">TK_PARTNER_APP_KEY</code> / <code className="rounded-datalabel bg-white/60 px-1">TK_PARTNER_APP_SECRET</code> / <code className="rounded-datalabel bg-white/60 px-1">TK_AUTH_SHOP_ID</code>，并完成授权后重启服务。
          </div>
        )}

        {/* 同步控件 */}
        {tkStatus?.configured && (
          <div className="mt-5 border-t border-gray-100 pt-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className="ds-body text-gray-600">同步范围</span>
              <DaySelector value={syncDays} onChange={setSyncDays} disabled={syncing} />
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleSync(true)}
                  disabled={syncing}
                  className="ds-btn-secondary"
                  title="前台同步执行，立即返回结果（适合小数据量）"
                >
                  {syncing ? (
                    <>
                      <Spinner /> 立即同步中…
                    </>
                  ) : (
                    "立即同步"
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => handleSync(false)}
                  disabled={syncing}
                  className="ds-btn-primary"
                  title="后台异步执行，立即返回，稍后刷新查看结果"
                >
                  {syncing ? (
                    <>
                      <Spinner /> 后台同步中…
                    </>
                  ) : (
                    "后台同步"
                  )}
                </button>
              </div>
            </div>

            {/* 同步进度 / 结果 */}
            {syncing && (
              <div className="mt-4 flex items-center gap-2 rounded-btn border border-primary-100 bg-primary-50 px-3 py-2 text-sm text-primary-700">
                <Spinner className="text-primary-600" />
                正在同步近 {syncDays} 天数据，请稍候…
              </div>
            )}

            {!syncing && syncMsg && (
              <div className="mt-4 rounded-btn border border-primary-100 bg-primary-50 px-3 py-2 text-sm text-primary-700">
                {syncMsg}
              </div>
            )}

            {!syncing && syncError && (
              <div className="mt-4 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
                ⚠️ {syncError}
              </div>
            )}

            {syncResult?.result && !syncing && (
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-btn border border-gray-100 bg-gray-50 p-3">
                  <div className="ds-caption">订单同步</div>
                  <div className="mt-1.5 flex flex-wrap gap-3 text-xs">
                    <span className="text-growth-600">新增 +{syncResult.result.orders.inserted}</span>
                    <span className="text-primary-600">更新 {syncResult.result.orders.updated}</span>
                    <span className="text-gray-400">跳过 {syncResult.result.orders.skipped}</span>
                  </div>
                </div>
                <div className="rounded-btn border border-gray-100 bg-gray-50 p-3">
                  <div className="ds-caption">商品同步</div>
                  <div className="mt-1.5 flex flex-wrap gap-3 text-xs">
                    <span className="text-growth-600">新增 +{syncResult.result.products.inserted}</span>
                    <span className="text-primary-600">更新 {syncResult.result.products.updated}</span>
                    <span className="text-gray-400">跳过 {syncResult.result.products.skipped}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ============ 区块2：AI 经营分析报告 ============ */}
      <section className="ds-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="ds-title">AI 经营分析报告</h2>
            <p className="ds-subtitle mt-1">
              基于已同步的看板数据，由大模型自动生成经营分析报告
            </p>
          </div>
        </div>

        <div className="mt-5 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="ds-body text-gray-600">数据范围</span>
            <DaySelector value={reportDays} onChange={setReportDays} disabled={generating} />
          </div>

          <input
            type="text"
            value={reportQuery}
            onChange={(e) => setReportQuery(e.target.value)}
            placeholder="可选：额外关注点，如「重点分析退款原因」「达人 ROI 优化建议」"
            className="w-full rounded-btn border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
          />

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleGenerateReport}
              disabled={generating}
              className="ds-btn-primary"
            >
              {generating ? (
                <>
                  <Spinner /> AI 分析中…
                </>
              ) : (
                "生成报告"
              )}
            </button>
            {aiReport && !reportRunning && aiReport.status !== "done" && (
              <span className="ds-caption">report_id: {aiReport.report_id}</span>
            )}
          </div>
        </div>

        {/* 生成中（前台等待） */}
        {generating && !aiReport && (
          <div className="mt-4 flex items-center gap-2 rounded-btn border border-primary-100 bg-primary-50 px-3 py-2 text-sm text-primary-700">
            <Spinner className="text-primary-600" />
            AI 正在分析数据并生成报告，请稍候…
          </div>
        )}

        {/* 轮询中（pending / running） */}
        {aiReport && reportRunning && (
          <div className="mt-4 flex items-center gap-2 rounded-btn border border-primary-100 bg-primary-50 px-3 py-2 text-sm text-primary-700">
            <Spinner className="text-primary-600" />
            报告生成中（状态：{aiReport.status}），3 秒后自动刷新…
          </div>
        )}

        {/* 生成失败 */}
        {aiReport?.status === "failed" && (
          <div className="mt-4 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
            ⚠️ 报告生成失败{aiReport.error ? `：${aiReport.error}` : ""}
          </div>
        )}

        {/* 生成完成：Markdown 渲染 */}
        {aiReport?.status === "done" && aiReport.content_md && (
          <div className="mt-4 rounded-btn border border-gray-100 bg-white p-4">
            <div className="mb-3 flex items-center justify-between border-b border-gray-100 pb-2">
              <span className="ds-caption">报告内容</span>
              <span className="ds-caption">report_id: {aiReport.report_id}</span>
            </div>
            <div className="text-[13px]">
              <ReactMarkdown components={mdComponents}>
                {aiReport.content_md}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* 调用接口失败 */}
        {reportError && (
          <div className="mt-4 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
            ⚠️ {reportError}
          </div>
        )}
      </section>

      {/* ============ 区块3：系统信息 ============ */}
      <section className="ds-card p-6">
        <h2 className="ds-title">系统信息</h2>
        <p className="ds-subtitle mt-1">当前系统版本与运行环境</p>
        <dl className="mt-4 divide-y divide-gray-100">
          <div className="flex py-2.5">
            <dt className="ds-caption w-32 shrink-0">数据来源</dt>
            <dd className="ds-body text-gray-900">TikTok Shop Partner API</dd>
          </div>
          <div className="flex py-2.5">
            <dt className="ds-caption w-32 shrink-0">版本号</dt>
            <dd className="ds-body text-gray-900">v0.2.0</dd>
          </div>
          <div className="flex py-2.5">
            <dt className="ds-caption w-32 shrink-0">数据库</dt>
            <dd className="ds-body text-gray-900">
              PostgreSQL（生产） / SQLite（开发）
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
