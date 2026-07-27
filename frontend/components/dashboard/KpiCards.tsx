"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { Kpi } from "@/lib/api";

function formatValue(value: number, format: Kpi["format"]): string {
  if (format === "currency") {
    return `¥${Math.round(value).toLocaleString("zh-CN")}`;
  }
  if (format === "percent") return `${value.toFixed(1)}%`;
  return Math.round(value).toLocaleString("zh-CN");
}

export function KpiCards({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpis.map((k) => {
        const hasDelta = k.delta_pct !== null;
        const isUp = (k.delta_pct ?? 0) >= 0;
        const isGood = hasDelta ? isUp === k.higher_is_better : true;
        const arrow = !hasDelta ? "→" : isUp ? "▲" : "▼";
        const color = hasDelta
          ? isGood
            ? "text-green-600 bg-green-50"
            : "text-red-600 bg-red-50"
          : "text-gray-400 bg-gray-50";

        return (
          <Card key={k.key}>
            <CardContent className="pt-5">
              <p className="text-sm text-gray-500">{k.label}</p>
              <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900">
                {formatValue(k.value, k.format)}
              </p>
              <div className="mt-2 flex items-center gap-1">
                <span
                  className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${color}`}
                >
                  <span aria-hidden>{arrow}</span>
                  {hasDelta ? `${Math.abs(k.delta_pct as number).toFixed(1)}%` : "—"}
                </span>
                <span className="text-xs text-gray-400">环比上一周期</span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
