"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { InfluencerPoint } from "@/lib/api";

interface ScatterDatum {
  x: number; // 互动率 %
  y: number; // 转化率 %
  z: number; // GMV
  name: string;
  category: string;
  roi: number | null;
  followers: number;
  is_suspicious: boolean;
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null;
  const d: ScatterDatum = payload[0].payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-lg">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-semibold text-gray-900">{d.name}</span>
        {d.is_suspicious && (
          <span className="text-red-600">🚨 疑似水军</span>
        )}
      </div>
      <div className="text-gray-500">类目：{d.category}</div>
      <div className="text-gray-500">粉丝：{d.followers.toLocaleString("zh-CN")}</div>
      <div className="text-gray-700">互动率：{d.x.toFixed(1)}%</div>
      <div className="text-gray-700">转化率：{d.y.toFixed(2)}%</div>
      <div className="text-gray-700">GMV：¥{d.z.toLocaleString("zh-CN")}</div>
      <div className="text-gray-700">ROI：{d.roi !== null ? d.roi.toFixed(2) : "—"}</div>
      {d.is_suspicious && (
        <div className="mt-1 rounded bg-red-50 p-1.5 text-red-600">
          ⚠️ 互动率高但转化率极低，疑似刷量水军，建议暂停合作
        </div>
      )}
    </div>
  );
}

export function InfluencerScatter({
  points,
  suspiciousCount,
}: {
  points: InfluencerPoint[];
  suspiciousCount: number;
}) {
  const toDatum = (p: InfluencerPoint): ScatterDatum => ({
    x: p.engagement_rate,
    y: p.conversion_rate,
    z: p.gmv,
    name: p.name,
    category: p.category,
    roi: p.roi,
    followers: p.followers,
    is_suspicious: p.is_suspicious,
  });

  const normal = points.filter((p) => !p.is_suspicious).map(toDatum);
  const suspicious = points.filter((p) => p.is_suspicious).map(toDatum);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>达人 ROI 与风险散点</CardTitle>
            <CardDescription>
              X：互动率 · Y：转化率 · 气泡大小：GMV · 红色为疑似水军
            </CardDescription>
          </div>
          <Badge variant={suspiciousCount > 0 ? "danger" : "success"}>
            {suspiciousCount > 0 ? `🚨 命中 ${suspiciousCount} 个水军` : "全部健康"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 12, right: 24, left: 8, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis
              type="number"
              dataKey="x"
              name="互动率"
              unit="%"
              domain={[0, "dataMax + 4"]}
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              label={{ value: "互动率 %", position: "insideBottom", offset: -6, fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="转化率"
              unit="%"
              domain={[0, "dataMax + 1"]}
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              label={{ value: "转化率 %", angle: -90, position: "insideLeft", fontSize: 12 }}
            />
            <ZAxis type="number" dataKey="z" range={[80, 600]} name="GMV" />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
            <Scatter name="正常达人" data={normal} fill="#3b82f6" fillOpacity={0.75} />
            <Scatter name="疑似水军" data={suspicious} fill="#ef4444" fillOpacity={0.9} />
          </ScatterChart>
        </ResponsiveContainer>
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-3 w-3 rounded-full bg-blue-500" /> 正常达人
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-3 w-3 rounded-full bg-red-500" /> 疑似水军（高互动 / 低转化）
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
