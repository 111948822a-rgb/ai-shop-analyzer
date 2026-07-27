"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { GmvPoint } from "@/lib/api";

const fmtDate = (d: string) => d.slice(5); // MM-DD

export function GmvTrendChart({ data }: { data: GmvPoint[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>GMV 趋势（近 30 天）</CardTitle>
        <CardDescription>每日成交总额（单位：元）</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis
              dataKey="date"
              tickFormatter={fmtDate}
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              minTickGap={24}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `¥${Math.round(v / 1000)}k`}
              width={56}
            />
            <Tooltip
              formatter={(v: number) => [`¥${v.toLocaleString("zh-CN")}`, "GMV"]}
              labelFormatter={(l: string) => `日期：${l}`}
              contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }}
            />
            <Line
              type="monotone"
              dataKey="gmv"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
