"use client";

import { useState, useEffect, useCallback } from "react";
import { useT } from "@/lib/i18n/context";

export type PeriodPreset = "7d" | "30d" | "90d" | "all" | "custom";

export interface DateRange {
  start_date?: string;
  end_date?: string;
}

interface TimeSlicerProps {
  value: PeriodPreset;
  onChange: (preset: PeriodPreset, range: DateRange) => void;
}

const PRESET_KEYS: PeriodPreset[] = ["7d", "30d", "90d", "all", "custom"];

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function presetToRange(preset: PeriodPreset): DateRange {
  if (preset === "all") return {};
  if (preset === "custom") return {};
  const days = preset === "7d" ? 7 : preset === "30d" ? 30 : 90;
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - days);
  return { start_date: toISODate(start), end_date: toISODate(end) };
}

export default function TimeSlicer({ value, onChange }: TimeSlicerProps) {
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const t = useT();

  const presetLabels: Record<PeriodPreset, string> = {
    "7d": t("common.last7days"),
    "30d": t("common.last30days"),
    "90d": t("common.last90days"),
    all: t("common.all"),
    custom: t("common.custom"),
  };

  const handlePreset = useCallback(
    (preset: PeriodPreset) => {
      if (preset === "custom") {
        // 如果已有自定义值则保持，否则默认近30天
        if (!customStart || !customEnd) {
          const r = presetToRange("30d");
          setCustomStart(r.start_date || "");
          setCustomEnd(r.end_date || "");
          onChange("custom", { start_date: r.start_date, end_date: r.end_date });
        } else {
          onChange("custom", { start_date: customStart, end_date: customEnd });
        }
      } else {
        onChange(preset, presetToRange(preset));
      }
    },
    [customStart, customEnd, onChange]
  );

  useEffect(() => {
    // 初始触发一次
    handlePreset(value);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-sm font-medium text-gray-600">{t("common.dataTime")}:</span>
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {PRESET_KEYS.map((p) => (
          <button
            key={p}
            onClick={() => handlePreset(p)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              value === p
                ? "bg-white text-indigo-600 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {presetLabels[p]}
          </button>
        ))}
      </div>
      {value === "custom" && (
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={customStart}
            onChange={(e) => {
              setCustomStart(e.target.value);
              onChange("custom", { start_date: e.target.value, end_date: customEnd });
            }}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
          <span className="text-gray-400">~</span>
          <input
            type="date"
            value={customEnd}
            onChange={(e) => {
              setCustomEnd(e.target.value);
              onChange("custom", { start_date: customStart, end_date: e.target.value });
            }}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
        </div>
      )}
    </div>
  );
}
