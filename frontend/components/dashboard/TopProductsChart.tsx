"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TopProduct } from "@/lib/api";

export function TopProductsChart({ data }: { data: TopProduct[] }) {
  // 按 GMV 计算排名，用于高亮 Top3
  const rank = new Map(
    [...data].sort((a, b) => b.gmv - a.gmv).map((it, i) => [it.product, i + 1])
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>商品销量 Top 10</CardTitle>
        <CardDescription>按 GMV 排序的爆款商品（横向柱状图）</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(360, data.length * 34)}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
            barCategoryGap={8}
          >
            <XAxis
              type="number"
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `¥${Math.round(v / 1000)}k`}
            />
            <YAxis
              type="category"
              dataKey="product"
              width={120}
              tick={{ fontSize: 12, fill: "#475569" }}
            />
            <Tooltip
              cursor={{ fill: "#f1f5f9" }}
              formatter={(v: number, _n, p: any) => {
                const row = p?.payload as TopProduct;
                return [`¥${v.toLocaleString("zh-CN")} · ${row.orders} 单`, "GMV"];
              }}
              labelFormatter={(l: string) => `商品：${l}`}
              contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }}
            />
            <Bar dataKey="gmv" radius={[0, 6, 6, 0]}>
              {data.map((d) => (
                <Cell key={d.product} fill={rank.get(d.product)! <= 3 ? "#f59e0b" : "#6366f1"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
