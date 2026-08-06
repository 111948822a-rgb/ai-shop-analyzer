"use client";

import { useEffect, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import {
  generateAIReport,
  getAIReport,
  type AIReportResponse,
} from "@/lib/api";
import { useT } from "@/lib/i18n/context";

const DAY_OPTIONS = [7, 30, 90, 180];

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
  const t = useT();
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
          {t("common.lastNDays", { n: d })}
        </button>
      ))}
    </div>
  );
}

/* ======================== 页面 ======================== */

export default function ReportsPage() {
  const t = useT();
  const [days, setDays] = useState(30);
  const [query, setQuery] = useState("");
  const [aiReport, setAiReport] = useState<AIReportResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reportRunning =
    aiReport && (aiReport.status === "pending" || aiReport.status === "running");

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

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    setAiReport(null);
    try {
      // 前台同步执行，数据量可控时直接等结果
      const r = await generateAIReport(days, query, true);
      setAiReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.reportFailed"));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* ============ 区块1：生成报告 ============ */}
      <section className="ds-card p-6">
        <div>
          <h1 className="ds-title">{t("reports.title")}</h1>
          <p className="ds-subtitle mt-1">
            {t("reports.subtitle")}
          </p>
        </div>

        <div className="mt-5 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="ds-body text-gray-600">{t("reports.timeRange")}</span>
            <DaySelector value={days} onChange={setDays} disabled={generating} />
          </div>

          <div>
            <label htmlFor="report-query" className="ds-body text-gray-600">
              {t("reports.focusPoint")}
            </label>
            <textarea
              id="report-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={generating}
              rows={3}
              placeholder={t("reports.focusPlaceholder")}
              className="mt-1.5 w-full resize-y rounded-btn border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition placeholder:text-gray-400 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 disabled:bg-gray-50"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={generating}
              className="ds-btn-primary"
            >
              {generating ? (
                <>
                  <Spinner /> {t("reports.aiAnalyzing")}
                </>
              ) : (
                t("reports.generate")
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
            {t("reports.aiWait")}
          </div>
        )}

        {/* 调用接口失败 */}
        {error && (
          <div className="mt-4 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
            ⚠️ {error}
          </div>
        )}
      </section>

      {/* ============ 区块2：报告内容 ============ */}
      <section className="ds-card p-6">
        <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-2">
          <h2 className="ds-title">{t("reports.contentTitle")}</h2>
          {aiReport && (
            <span className="ds-caption">report_id: {aiReport.report_id}</span>
          )}
        </div>

        {/* 空状态：尚未生成报告 */}
        {!aiReport && !generating && (
          <div className="ds-empty">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-400">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="9" y1="13" x2="15" y2="13" />
                <line x1="9" y1="17" x2="13" y2="17" />
              </svg>
            </div>
            <p className="ds-body text-gray-500">{t("reports.noReport")}</p>
            <p className="ds-caption mt-1">
              {t("reports.noReportHint")}
            </p>
          </div>
        )}

        {/* 生成中加载状态：pending / running */}
        {aiReport && reportRunning && (
          <div className="flex flex-col items-center py-10 text-center">
            <span
              aria-hidden="true"
              className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-primary-600 border-t-transparent"
            />
            <p className="ds-body mt-3 font-medium text-gray-700">
              {t("reports.aiProcessing")}
            </p>
            <p className="ds-caption mt-1">
              {t("reports.statusHint", { status: aiReport.status })}
            </p>
            {/* 骨架屏占位 */}
            <div className="mt-5 w-full max-w-2xl space-y-2.5">
              <div className="ds-skeleton h-4 w-3/4" />
              <div className="ds-skeleton h-4 w-full" />
              <div className="ds-skeleton h-4 w-5/6" />
              <div className="ds-skeleton h-4 w-2/3" />
              <div className="ds-skeleton h-4 w-full" />
              <div className="ds-skeleton h-4 w-4/5" />
            </div>
          </div>
        )}

        {/* 生成失败 */}
        {aiReport?.status === "failed" && (
          <div className="flex items-start gap-2 rounded-btn border border-decline-100 bg-decline-50 px-3 py-2 text-sm text-decline-600">
            <span aria-hidden>⚠️</span>
            <span>
              {aiReport.error ? t("reports.failed", { error: aiReport.error }) : t("reports.failedUnknown")}
            </span>
          </div>
        )}

        {/* 生成完成：Markdown 渲染 */}
        {aiReport?.status === "done" && aiReport.content_md && (
          <div className="text-[13px]">
            <ReactMarkdown components={mdComponents}>
              {aiReport.content_md}
            </ReactMarkdown>
          </div>
        )}
      </section>
    </div>
  );
}
