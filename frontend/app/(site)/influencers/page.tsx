"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  evaluateInfluencer,
  getMiaodaInfluencers,
  type MiaodaInfluencer,
} from "@/lib/api";

function fmtFollowers(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`;
  return n.toLocaleString("zh-CN");
}

function pct(v: number | null): string {
  return v == null ? "—" : `${v}%`;
}

export default function InfluencersPage() {
  const router = useRouter();
  const [items, setItems] = useState<MiaodaInfluencer[]>([]);
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [evaluating, setEvaluating] = useState<string | null>(null);

  useEffect(() => {
    getMiaodaInfluencers()
      .then((d) => {
        setItems(d.items);
        setSource(d.source);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "加载达人数据失败");
        setLoading(false);
      });
  }, []);

  async function evaluate(inf: MiaodaInfluencer) {
    setEvaluating(inf.influencer_id);
    try {
      const r = await evaluateInfluencer({
        influencer_id: inf.influencer_id,
        influencer_name: inf.name,
        platform: inf.platform,
        followers: inf.followers,
        target_product: "",
      });
      router.push(`/report/influencer/${r.record_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "评估失败");
      setEvaluating(null);
    }
  }

  if (loading) return <p className="text-gray-500">正在从秒搭拉取达人数据…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <div className="flex items-end justify-between mb-2">
        <h1 className="text-2xl font-bold">达人评估</h1>
        <span className="text-xs text-gray-400">
          数据来源：{source === "miaoda" ? "秒搭系统" : "本地库"}
        </span>
      </div>
      <p className="text-gray-500 mb-6 text-sm">
        基于秒搭达人数据，点击「评估」即触发 AI 匹配度分析与避坑预警。
      </p>

      {items.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-400">
          暂无达人数据。请确认秒搭 OpenAPI 已配置，或本地已同步达人。
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((inf) => (
            <div
              key={inf.influencer_id}
              className="rounded-xl border border-gray-200 bg-white p-5 flex flex-col"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{inf.name}</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {inf.platform || "—"} · {inf.niche || "未知类目"}
                  </p>
                </div>
                {inf.is_suspicious && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-medium text-red-600">
                    疑似异常
                  </span>
                )}
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
                <dt className="text-gray-400">粉丝</dt>
                <dd className="text-right text-gray-800">{fmtFollowers(inf.followers)}</dd>
                <dt className="text-gray-400">互动率</dt>
                <dd className="text-right text-gray-800">{pct(inf.engagement_rate)}</dd>
                <dt className="text-gray-400">转化率</dt>
                <dd className="text-right text-gray-800">{pct(inf.conversion_rate)}</dd>
                <dt className="text-gray-400">ROI</dt>
                <dd className="text-right text-gray-800">
                  {inf.roi == null ? "—" : inf.roi.toFixed(2)}
                </dd>
              </dl>

              <button
                onClick={() => evaluate(inf)}
                disabled={evaluating === inf.influencer_id}
                className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
              >
                {evaluating === inf.influencer_id ? "评估中…" : "评估"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
