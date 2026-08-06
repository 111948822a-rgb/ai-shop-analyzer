"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { getReport, type Report } from "@/lib/api";
import { useT } from "@/lib/i18n/context";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const t = useT();
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
        if (!stopped) setError(e instanceof Error ? e.message : t("reports.loadingFailed"));
      }
    }
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!report) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;

  if (report.status === "pending" || report.status === "running") {
    return (
      <div className="flex flex-col items-center py-20 text-center">
        <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        <p className="text-sm font-medium text-gray-700">{t("reports.loadingHint")}</p>
        <p className="mt-1 text-xs text-gray-400">{t("reports.loadingSub")}</p>
      </div>
    );
  }

  if (report.status === "failed") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {t("reports.analysisFailed", { error: report.error || t("common.unknown") })}
      </div>
    );
  }

  return (
    <article className="prose prose-sm max-w-3xl rounded-xl border bg-white p-8 prose-headings:font-semibold prose-table:text-sm">
      <ReactMarkdown>{report.content_md}</ReactMarkdown>
    </article>
  );
}
