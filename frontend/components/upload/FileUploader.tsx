"use client";

import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { uploadFile, type Dataset } from "@/lib/api";

const ACCEPTED = [".csv", ".xlsx", ".xls"];
const MAX_MB = 20;

type Status = "idle" | "uploading" | "done" | "error";

interface Props {
  onUploaded?: (dataset: Dataset) => void;
}

export default function FileUploader({ onUploaded }: Props) {
  const [dataType, setDataType] = useState<"shop" | "creator">("shop");
  const [status, setStatus] = useState<Status>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      const suffix = "." + (file.name.split(".").pop() ?? "").toLowerCase();
      if (!ACCEPTED.includes(suffix)) {
        setError(`仅支持 ${ACCEPTED.join(" / ")} 格式`);
        setStatus("error");
        return;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`文件不能超过 ${MAX_MB}MB`);
        setStatus("error");
        return;
      }

      setStatus("uploading");
      setProgress(0);
      setError("");
      try {
        const res = await uploadFile(file, dataType, setProgress);
        setDataset(res.dataset);
        setStatus("done");
        onUploaded?.(res.dataset);
      } catch (e) {
        setError(e instanceof Error ? e.message : "上传失败");
        setStatus("error");
      }
    },
    [dataType, onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const summary = dataset?.summary;

  return (
    <div className="w-full max-w-2xl space-y-4">
      <div className="flex gap-2">
        {(
          [
            { key: "shop", label: "店铺销售数据" },
            { key: "creator", label: "达人数据" },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            onClick={() => setDataType(t.key)}
            className={cn(
              "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
              dataType === t.key
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:border-blue-400"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 text-center transition-colors",
          dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:border-blue-400"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
        <svg className="mb-3 h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        <p className="text-sm font-medium text-gray-700">拖拽文件到这里，或点击选择</p>
        <p className="mt-1 text-xs text-gray-400">
          支持 CSV / Excel，最大 {MAX_MB}MB · 当前类型：{dataType === "shop" ? "店铺销售数据" : "达人数据"}
        </p>
      </div>

      {status === "uploading" && (
        <div className="space-y-1">
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-600 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">
            {progress < 100 ? `上传中 ${progress}%` : "服务端正在清洗和聚合数据…"}
          </p>
        </div>
      )}

      {status === "error" && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {status === "done" && dataset && summary && (
        <div className="rounded-xl border border-green-200 bg-white p-5">
          <p className="mb-3 text-sm font-medium text-green-700">
            ✓ {dataset.filename} 预处理完成（{dataset.row_count} 行）
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {summary.total_gmv != null && <Metric label="总 GMV" value={`¥${fmt(summary.total_gmv)}`} />}
            {summary.total_orders != null && <Metric label="订单数" value={fmt(summary.total_orders)} />}
            {summary.avg_order_value != null && <Metric label="客单价" value={`¥${fmt(summary.avg_order_value)}`} />}
            {summary.overall_conversion_rate != null && (
              <Metric label="转化率" value={`${summary.overall_conversion_rate}%`} />
            )}
            {summary.creator_count != null && <Metric label="达人数" value={fmt(summary.creator_count)} />}
            {summary.avg_roi != null && <Metric label="平均 ROI" value={String(summary.avg_roi)} />}
            {summary.producing_rate != null && <Metric label="出单率" value={`${summary.producing_rate}%`} />}
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-base font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function fmt(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(2)}万` : n.toLocaleString("zh-CN");
}
