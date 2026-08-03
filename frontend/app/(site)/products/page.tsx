"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getTopProducts, type TopProduct } from "@/lib/api";

// ===== 设计规范常量 =====
const CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"];
const COLOR_PRIMARY = "#2563EB";
const COLOR_GROWTH = "#10B981";
const COLOR_DECLINE = "#EF4444";
const COLOR_WARNING = "#F59E0B";

// ===== 顶部时间筛选器 =====
const TIME_FILTERS: { label: string; days: number }[] = [
  { label: "近7天", days: 7 },
  { label: "近30天", days: 30 },
  { label: "近90天", days: 90 },
  { label: "近180天", days: 180 },
];

// ===== 价格带分桶 =====
const PRICE_BANDS = [
  { key: "0-10", label: "$0-10", min: 0, max: 10 },
  { key: "10-20", label: "$10-20", min: 10, max: 20 },
  { key: "20-50", label: "$20-50", min: 20, max: 50 },
  { key: "50+", label: "$50+", min: 50, max: Infinity },
];

const PRICE_FILTERS = [
  { label: "全部价格", value: "" },
  ...PRICE_BANDS.map((b) => ({ label: b.label, value: b.key })),
];

// ===== 工具函数 =====
function fmtCurrency(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return "-";
  return "$" + Math.round(n).toLocaleString("en-US");
}

function fmtInt(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return "-";
  return Math.round(n).toLocaleString("en-US");
}

function fmtPercent(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return "-";
  return n.toFixed(1) + "%";
}

// ===== 兼容多种返回结构（TopProduct[] | { products } | { items } | { data }）=====
async function fetchTopProducts(limit: number, days: number): Promise<TopProduct[]> {
  const r = await getTopProducts(limit, days);
  if (Array.isArray(r)) return r as TopProduct[];
  if (r && typeof r === "object") {
    const obj = r as unknown as Record<string, unknown>;
    for (const k of ["products", "items", "data", "list", "result"]) {
      const v = obj[k];
      if (Array.isArray(v)) return v as TopProduct[];
    }
  }
  return [];
}

// ===== 排序类型 =====
type SortKey = "product" | "orders" | "gmv";
type SortDir = "asc" | "desc";

export default function ProductsPage() {
  const [filterIdx, setFilterIdx] = useState(1); // 默认近30天
  const days = TIME_FILTERS[filterIdx].days;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<TopProduct[]>([]);

  // 表格筛选 & 排序
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [priceFilter, setPriceFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("gmv");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // 价格带图表 Y 轴指标
  const [priceMetric, setPriceMetric] = useState<"orders" | "gmv">("orders");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchTopProducts(100, days);
      setProducts(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "数据加载失败");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  // ===== 5.1 总览指标 =====
  const overview = useMemo(() => {
    const total = products.length;
    const sold = products.filter((p) => p.orders > 0).length;
    const sellThrough = total > 0 ? (sold / total) * 100 : 0;
    const hot = products.filter((p) => p.orders / days > 50).length;
    return { total, sold, sellThrough, hot };
  }, [products, days]);

  // ===== 含估算客单价的商品列表 =====
  const pricedProducts = useMemo(() => {
    return products.map((p) => ({
      ...p,
      price: p.orders > 0 ? p.gmv / p.orders : 0,
    }));
  }, [products]);

  // ===== 5.2 表格数据（筛选 + 排序）=====
  const tableData = useMemo(() => {
    let list = [...pricedProducts];
    // 价格区间筛选（按估算客单价）
    if (priceFilter) {
      const band = PRICE_BANDS.find((b) => b.key === priceFilter);
      if (band) {
        list = list.filter((p) => p.price >= band.min && p.price < band.max);
      }
    }
    // 分类筛选：TopProduct 无品类字段，"all" 时不过滤
    void categoryFilter;
    // 排序
    list.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "product") cmp = a.product.localeCompare(b.product);
      else if (sortKey === "orders") cmp = a.orders - b.orders;
      else if (sortKey === "gmv") cmp = a.gmv - b.gmv;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [pricedProducts, priceFilter, categoryFilter, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  // ===== 5.4 价格带聚合 =====
  const priceBandData = useMemo(() => {
    const buckets = PRICE_BANDS.map((b) => ({
      label: b.label,
      orders: 0,
      gmv: 0,
      count: 0,
    }));
    pricedProducts.forEach((p) => {
      const idx = PRICE_BANDS.findIndex((b) => p.price >= b.min && p.price < b.max);
      if (idx >= 0) {
        buckets[idx].orders += p.orders;
        buckets[idx].gmv += p.gmv;
        buckets[idx].count += 1;
      }
    });
    return buckets;
  }, [pricedProducts]);

  const mainPriceBand = useMemo(() => {
    if (!priceBandData.length) return null;
    return priceBandData.reduce(
      (max, cur) => (cur[priceMetric] > max[priceMetric] ? cur : max),
      priceBandData[0]
    );
  }, [priceBandData, priceMetric]);

  // ===== 导出 JSON =====
  function handleExport() {
    const payload = {
      exported_at: new Date().toISOString(),
      filter: TIME_FILTERS[filterIdx].label,
      days,
      overview,
      products: pricedProducts,
      table: tableData,
      price_band: priceBandData,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `products-${TIME_FILTERS[filterIdx].label}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const sortLabel =
    sortKey === "product" ? "商品名称" : sortKey === "orders" ? "销量" : "GMV";

  return (
    <div className="space-y-6">
      {/* 顶部工具栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="ds-title">商品分析</h1>
          <p className="ds-subtitle mt-1">
            {loading
              ? "加载中…"
              : `统计区间：近 ${days} 天 · 共 ${products.length} 个商品`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-btn border border-gray-200 bg-white p-0.5">
            {TIME_FILTERS.map((f, i) => (
              <button
                key={f.label}
                onClick={() => setFilterIdx(i)}
                className={`rounded-[6px] px-3 py-1.5 text-xs font-medium transition ${
                  filterIdx === i
                    ? "bg-primary-600 text-white"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button onClick={handleExport} className="ds-btn-secondary">
            <span aria-hidden>⭳</span> 导出 JSON
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-card border border-decline-100 bg-decline-50 px-4 py-3 text-sm text-decline-600">
          ⚠️ {error}
        </div>
      )}

      {/* 5.1 商品总览指标（4列） */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="ds-card p-5">
              <div className="ds-skeleton h-4 w-20" />
              <div className="ds-skeleton mt-3 h-7 w-28" />
              <div className="ds-skeleton mt-3 h-4 w-24" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <OverviewCard
            label="在售商品数"
            value={fmtInt(overview.total)}
            hint="商品总数"
          />
          <OverviewCard
            label="动销商品数"
            value={fmtInt(overview.sold)}
            hint="有成交商品数"
          />
          <OverviewCard
            label="动销率"
            value={fmtPercent(overview.sellThrough)}
            hint="动销 / 在售"
            tone={overview.sellThrough >= 50 ? "up" : "down"}
          />
          <OverviewCard
            label="爆款商品数"
            value={fmtInt(overview.hot)}
            hint="日均订单 > 50 单（估算）"
            tone={overview.hot > 0 ? "up" : undefined}
          />
        </div>
      )}

      {/* 5.2 商品销售明细 + 5.3 品类销售占比 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* 5.2 商品销售明细（左侧 2/3） */}
        <section className="ds-card p-5 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="ds-title">商品销售明细</h2>
              <p className="ds-subtitle mt-1">
                点击列头排序 · 曝光/点击/加购/库存等暂无字段显示 "-"
              </p>
            </div>
            <button onClick={handleExport} className="ds-btn-secondary">
              导出完整报表
            </button>
          </div>

          {/* 顶部筛选 */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-btn border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-primary-400"
            >
              <option value="all">全部分类</option>
            </select>
            <select
              value={priceFilter}
              onChange={(e) => setPriceFilter(e.target.value)}
              className="rounded-btn border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-primary-400"
            >
              {PRICE_FILTERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-1.5 ds-caption">
              <span>排序：</span>
              <span className="text-gray-700">{sortLabel}</span>
              <span>({sortDir === "asc" ? "升序" : "降序"})</span>
            </div>
          </div>

          {/* 表格 */}
          <div className="mt-4 overflow-x-auto">
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="ds-skeleton h-8 w-full" />
                ))}
              </div>
            ) : tableData.length > 0 ? (
              <table className="w-full text-left text-[13px]">
                <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <Th
                      onClick={() => toggleSort("product")}
                      active={sortKey === "product"}
                      dir={sortDir}
                    >
                      商品名称
                    </Th>
                    <th className="px-3 py-2 text-right">SKU数</th>
                    <th className="px-3 py-2 text-right">曝光量</th>
                    <th className="px-3 py-2 text-right">点击量</th>
                    <th className="px-3 py-2 text-right">点击率</th>
                    <th className="px-3 py-2 text-right">加购数</th>
                    <Th
                      onClick={() => toggleSort("orders")}
                      active={sortKey === "orders"}
                      dir={sortDir}
                      align="right"
                    >
                      销量
                    </Th>
                    <Th
                      onClick={() => toggleSort("gmv")}
                      active={sortKey === "gmv"}
                      dir={sortDir}
                      align="right"
                    >
                      GMV
                    </Th>
                    <th className="px-3 py-2 text-right">转化率</th>
                    <th className="px-3 py-2 text-right">库存</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {tableData.map((p, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td
                        className="max-w-[220px] truncate px-3 py-2 text-gray-900"
                        title={p.product}
                      >
                        {p.product}
                      </td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                      <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                        {fmtInt(p.orders)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-gray-900">
                        {fmtCurrency(p.gmv)}
                      </td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                      <td className="px-3 py-2 text-right text-gray-400">-</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="ds-empty">
                <p className="ds-body">
                  {products.length === 0
                    ? "暂无商品数据"
                    : "无匹配商品，请调整筛选条件"}
                </p>
                {products.length === 0 && (
                  <p className="ds-caption mt-1">后端暂未返回 Top 商品列表</p>
                )}
              </div>
            )}
          </div>
        </section>

        {/* 5.3 品类销售占比（右侧 1/3） */}
        <section className="ds-card p-5">
          <div>
            <h2 className="ds-title">品类销售占比</h2>
            <p className="ds-subtitle mt-1">按一级品类划分 GMV 占比</p>
          </div>
          <div className="mt-4">
            <div className="ds-empty">
              <p className="ds-body">暂无品类数据</p>
              <p className="ds-caption mt-1">
                TopProduct 接口未返回品类字段，需对接商品分类接口
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* 5.4 价格带销售分布 + 5.5 库存预警商品 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* 5.4 价格带销售分布 */}
        <section className="ds-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="ds-title">价格带销售分布</h2>
              <p className="ds-subtitle mt-1">
                按估算客单价（GMV / 销量）分桶
              </p>
            </div>
            <div className="flex rounded-btn border border-gray-200 bg-white p-0.5">
              {(
                [
                  { k: "orders", l: "订单量" },
                  { k: "gmv", l: "GMV" },
                ] as const
              ).map((m) => (
                <button
                  key={m.k}
                  onClick={() => setPriceMetric(m.k)}
                  className={`rounded-[6px] px-3 py-1.5 text-xs font-medium transition ${
                    priceMetric === m.k
                      ? "bg-primary-600 text-white"
                      : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {m.l}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4">
            {loading ? (
              <div className="ds-skeleton h-[280px] w-full" />
            ) : priceBandData.some((d) => d[priceMetric] > 0) ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={priceBandData}
                  margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
                >
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 12, fill: "#94a3b8" }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#94a3b8" }}
                    tickFormatter={(v: number) =>
                      priceMetric === "gmv"
                        ? "$" + Math.round(v / 1000) + "k"
                        : Math.round(v).toLocaleString("en-US")
                    }
                    width={56}
                  />
                  <Tooltip
                    formatter={(v: number) => [
                      priceMetric === "gmv" ? fmtCurrency(v) : fmtInt(v),
                      priceMetric === "gmv" ? "GMV" : "订单量",
                    ]}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey={priceMetric} radius={[4, 4, 0, 0]}>
                    {priceBandData.map((d) => (
                      <Cell
                        key={d.label}
                        fill={
                          mainPriceBand && d.label === mainPriceBand.label
                            ? COLOR_GROWTH
                            : COLOR_PRIMARY
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="ds-empty">
                <p className="ds-body">暂无价格带数据</p>
                <p className="ds-caption mt-1">需商品带有销量与 GMV 数据</p>
              </div>
            )}
          </div>
          {mainPriceBand && mainPriceBand[priceMetric] > 0 && (
            <p className="ds-body mt-3">
              主力价格带：
              <span className="font-semibold text-growth-600">
                {mainPriceBand.label}
              </span>
              ，{priceMetric === "gmv" ? "GMV" : "订单量"}{" "}
              {priceMetric === "gmv"
                ? fmtCurrency(mainPriceBand.gmv)
                : fmtInt(mainPriceBand.orders)}
              （共 {mainPriceBand.count} 个商品）
            </p>
          )}
        </section>

        {/* 5.5 库存预警商品 */}
        <section className="ds-card p-5">
          <div>
            <h2 className="ds-title">库存预警商品</h2>
            <p className="ds-subtitle mt-1">
              红色预警 &lt; 10 件 · 黄色预警 &lt; 30 件 · 按紧急程度排序
            </p>
          </div>
          <div className="mt-4">
            <div className="ds-empty">
              <p className="ds-body">暂无库存数据，需对接库存接口</p>
              <p className="ds-caption mt-1">
                TopProduct 接口未返回库存与近7日销量字段
              </p>
            </div>
          </div>
          {/* 图例（仅用于说明预警分级，对接库存后启用） */}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="ds-tag bg-decline-50 text-decline-600">
              <span
                aria-hidden
                className="mr-1 inline-block h-2 w-2 rounded-full bg-decline-500"
              />
              红色预警 &lt; 10
            </span>
            <span className="ds-tag bg-warning-50 text-warning-600">
              <span
                aria-hidden
                className="mr-1 inline-block h-2 w-2 rounded-full bg-warning-500"
              />
              黄色预警 &lt; 30
            </span>
          </div>
        </section>
      </div>

      {/* 配色说明（辅助信息） */}
      <p className="ds-caption" aria-hidden>
        图表配色：{CHART_COLORS.join(" · ")} · 主色 {COLOR_PRIMARY} · 增长{" "}
        {COLOR_GROWTH} · 下降 {COLOR_DECLINE} · 预警 {COLOR_WARNING}
      </p>
    </div>
  );
}

// ===== 总览卡片 =====
function OverviewCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "up" | "down";
}) {
  return (
    <div className="ds-card-hover p-5">
      <p className="ds-caption">{label}</p>
      <p className="mt-2 text-2xl font-bold tabular-nums text-gray-900">{value}</p>
      <div className="mt-2 flex items-center gap-1.5">
        {tone === "up" && <span className="ds-tag-up">↑ 良好</span>}
        {tone === "down" && <span className="ds-tag-down">↓ 偏低</span>}
        {hint && <span className="ds-caption">{hint}</span>}
      </div>
    </div>
  );
}

// ===== 排序表头 =====
function Th({
  children,
  onClick,
  active,
  dir,
  align = "left",
}: {
  children: React.ReactNode;
  onClick: () => void;
  active: boolean;
  dir: SortDir;
  align?: "left" | "right";
}) {
  return (
    <th
      onClick={onClick}
      className={`cursor-pointer select-none px-3 py-2 ${
        align === "right" ? "text-right" : "text-left"
      } ${active ? "text-primary-600" : "text-gray-500"} hover:text-primary-600`}
    >
      <span
        className={`inline-flex items-center gap-1 ${
          align === "right" ? "flex-row-reverse" : ""
        }`}
      >
        {children}
        <span aria-hidden className="text-[10px]">
          {active ? (dir === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </span>
    </th>
  );
}
