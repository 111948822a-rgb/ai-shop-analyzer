"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { getReport, type Report } from "@/lib/api";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;

    async function poll() {
      try {
        const r = await getReport(id);
        if (stopped) return;
        setReport(r);
        if (r.status === "pending" || r.status === "running") {
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
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!report) return <p className="text-sm text-gray-500">加载中…</p>;

  if (report.status === "pending" || report.status === "running") {
    return (
      <div className="flex flex-col items-center py-20 text-center">
        <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        <p className="text-sm font-medium text-gray-700">AI 正在分析数据…</p>
        <p className="mt-1 text-xs text-gray-400">通常需要 10-30 秒，页面会自动刷新</p>
      </div>
    );
  }

  if (report.status === "failed") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        分析失败：{report.error || "未知错误"}
      </div>
    );
  }

  return (
    <article className="prose prose-sm max-w-3xl rounded-xl border bg-white p-8 prose-headings:font-semibold prose-table:text-sm">
      <ReactMarkdown>{report.content_md}</ReactMarkdown>
    </article>
  );
}
