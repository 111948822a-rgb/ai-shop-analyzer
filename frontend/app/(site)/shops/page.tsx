"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getShops, type Shop } from "@/lib/api";

function yuan(n: number): string {
  return "¥" + n.toLocaleString("zh-CN");
}

export default function ShopsPage() {
  const router = useRouter();
  const [shops, setShops] = useState<Shop[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getShops()
      .then((s) => {
        setShops(s);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "加载店铺失败");
        setLoading(false);
      });
  }, []);

  function toggle(id: string) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  function go() {
    const ids = Array.from(selected);
    const qs = ids.length ? `?shops=${encodeURIComponent(ids.join(","))}` : "";
    router.push(`/analysis${qs}`);
  }

  if (loading) return <p className="text-gray-500">加载店铺列表中…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">选择店铺</h1>
      <p className="text-gray-500 mb-6 text-sm">
        可多选店铺进入销售数据分析（当前数据可能只有一个店铺，也支持全选）。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {shops.map((shop) => {
          const checked = selected.has(shop.shop_id);
          return (
            <button
              key={shop.shop_id}
              onClick={() => toggle(shop.shop_id)}
              className={`text-left rounded-xl border p-5 transition ${
                checked
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-900">{shop.name}</span>
                <span
                  className={`w-5 h-5 rounded border flex items-center justify-center text-xs ${
                    checked ? "bg-blue-600 text-white border-blue-600" : "border-gray-300"
                  }`}
                >
                  {checked ? "✓" : ""}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                订单 {shop.order_count} · GMV {yuan(shop.gmv)}
              </p>
            </button>
          );
        })}
      </div>

      <div className="mt-8 flex items-center gap-3">
        <button
          onClick={go}
          disabled={selected.size === 0}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-white font-medium disabled:opacity-50 hover:bg-blue-700 transition"
        >
          查看分析{selected.size ? `（已选 ${selected.size} 个）` : ""}
        </button>
        {selected.size === 0 && (
          <span className="text-sm text-gray-400">请至少选择一个店铺</span>
        )}
      </div>
    </div>
  );
}
