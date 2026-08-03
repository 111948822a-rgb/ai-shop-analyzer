export interface DatasetSummary {
  data_type: string;
  row_count: number;
  total_gmv?: number;
  total_orders?: number;
  avg_order_value?: number;
  overall_conversion_rate?: number;
  creator_count?: number;
  avg_roi?: number;
  producing_rate?: number;
  top10_products?: { product: string; gmv: number }[];
  top10_creators?: { creator: string; gmv: number; roi?: number }[];
  daily_gmv_trend?: { date: string; gmv: number }[];
  [key: string]: unknown;
}

export interface Dataset {
  id: string;
  filename: string;
  data_type: "shop" | "creator";
  row_count: number;
  columns: string[];
  summary: DatasetSummary;
  created_at: string;
}

export interface Report {
  id: string;
  dataset_id: string;
  report_type: "weekly" | "monthly";
  status: "pending" | "running" | "done" | "failed";
  content_md: string;
  error: string;
  created_at: string;
}

// 生产：从环境变量 NEXT_PUBLIC_API_URL 读取后端基址（如 https://ai-shop-backend.onrender.com）
// 开发：未设置时为空字符串，请求走 next.config.mjs 的 rewrite 代理到 localhost:8000
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function createAnalysis(datasetId: string, reportType: "weekly" | "monthly") {
  const res = await fetch(`${BASE}/api/analyze/${datasetId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_type: reportType }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "创建分析任务失败");
  return (await res.json()) as Report;
}

export async function getReport(reportId: string) {
  const res = await fetch(`${BASE}/api/reports/${reportId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取报告失败");
  return (await res.json()) as Report;
}

/** 上传文件，带进度回调（fetch 不支持上传进度，用 XHR） */
export function uploadFile(
  file: File,
  dataType: "shop" | "creator",
  onProgress: (percent: number) => void
): Promise<{ dataset: Dataset; message: string }> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    form.append("data_type", dataType);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/upload`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) resolve(body);
        else reject(new Error(body.detail ?? `上传失败 (${xhr.status})`));
      } catch {
        reject(new Error(`上传失败 (${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error("网络错误，请确认后端已启动"));
    xhr.send(form);
  });
}

// ===================== 店铺（销售数据分析前置选择）=====================
export interface Shop {
  shop_id: string;
  name: string;
  order_count: number;
  gmv: number;
}

export async function getShops(): Promise<Shop[]> {
  const res = await fetch(`${BASE}/api/dashboard/shops`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取店铺列表失败");
  const d = (await res.json()) as { shops: Shop[] };
  return d.shops;
}

// ===================== Dashboard 看板 =====================
export interface Kpi {
  key: string;
  label: string;
  value: number;
  delta_pct: number | null;
  higher_is_better: boolean;
  format: "currency" | "int" | "percent";
}

export interface DashboardOverview {
  period: { start: string; end: string; days: number; fallback?: boolean };
  previous_period: { start: string; end: string };
  kpis: Kpi[];
}

export interface GmvPoint {
  date: string;
  gmv: number;
}

export interface TopProduct {
  product: string;
  gmv: number;
  orders: number;
}

export interface InfluencerPoint {
  creator_id: string;
  name: string;
  category: string;
  engagement_rate: number; // 百分比数值，如 4.0 表示 4%
  conversion_rate: number; // 百分比数值，如 0.40 表示 0.4%
  gmv: number;
  roi: number | null;
  followers: number;
  is_suspicious: boolean;
}

export async function getDashboardOverview(
  days = 30,
  shopIds?: string[]
): Promise<DashboardOverview> {
  const qs =
    shopIds && shopIds.length
      ? `&shop_ids=${encodeURIComponent(shopIds.join(","))}`
      : "";
  const res = await fetch(`${BASE}/api/dashboard/overview?days=${days}${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取 KPI 失败");
  return (await res.json()) as DashboardOverview;
}

export async function getGmvTrend(days = 30, shopIds?: string[]): Promise<GmvPoint[]> {
  const qs =
    shopIds && shopIds.length
      ? `&shop_ids=${encodeURIComponent(shopIds.join(","))}`
      : "";
  const res = await fetch(`${BASE}/api/dashboard/gmv-trend?days=${days}${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取 GMV 趋势失败");
  const d = (await res.json()) as { series: GmvPoint[] };
  return d.series;
}

export async function getTopProducts(limit = 10, days = 30, shopIds?: string[]): Promise<TopProduct[]> {
  const qs =
    shopIds && shopIds.length
      ? `&shop_ids=${encodeURIComponent(shopIds.join(","))}`
      : "";
  const res = await fetch(`${BASE}/api/dashboard/top-products?limit=${limit}&days=${days}${qs}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("获取 Top 商品失败");
  const d = (await res.json()) as { items: TopProduct[] };
  return d.items;
}

export async function getInfluencers(): Promise<{
  points: InfluencerPoint[];
  suspicious_count: number;
}> {
  const res = await fetch(`${BASE}/api/dashboard/influencers`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取达人数据失败");
  return (await res.json()) as { points: InfluencerPoint[]; suspicious_count: number };
}

// ===================== 秒搭 H5 报告页 =====================
export interface RadarDim {
  dimension: string;
  key: string;
  value: number;
}

export interface MiaodaReport {
  record_id: string;
  status: "processing" | "done" | "failed";
  influencer_name: string;
  platform: string | null;
  followers: number;
  target_product: string | null;
  ai_match_score: number | null;
  ai_risk_warning: string | null;
  ai_outreach_script: string | null;
  fit_analysis: string | null;
  radar: RadarDim[] | null;
  multilingual: Record<string, string> | null;
  ai_report_url: string | null;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export async function getMiaodaReport(recordId: string): Promise<MiaodaReport> {
  const res = await fetch(`${BASE}/api/miaoda/report/${recordId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取达人分析报告失败");
  return (await res.json()) as MiaodaReport;
}

// ===================== 达人评估（秒搭数据）=====================
export interface MiaodaInfluencer {
  influencer_id: string;
  name: string;
  platform: string;
  followers: number;
  engagement_rate: number | null;
  conversion_rate: number | null;
  roi: number | null;
  is_suspicious: boolean;
  niche: string | null;
  avatar_url?: string;
  avg_likes?: number;
  avg_comments?: number;
  total_posts?: number;
  created_at?: string | null;
  status?: string;
}

export async function getMiaodaInfluencers(
  siteId?: string
): Promise<{ source: string; items: MiaodaInfluencer[] }> {
  const url = siteId
    ? `${BASE}/api/miaoda/influencers?site_id=${encodeURIComponent(siteId)}`
    : `${BASE}/api/miaoda/influencers`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("获取达人数据失败");
  return (await res.json()) as { source: string; items: MiaodaInfluencer[] };
}

export async function evaluateInfluencer(payload: {
  influencer_id?: string;
  influencer_name: string;
  platform?: string;
  followers?: number;
  target_product?: string;
}): Promise<{ success: boolean; record_id: string; report_url: string }> {
  const res = await fetch(`${BASE}/api/miaoda/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "触发评估失败");
  return (await res.json()) as { success: boolean; record_id: string; report_url: string };
}

// ===================== 达人数据看板（秒搭）=====================
export interface MiaodaSummary {
  total: number;
  total_followers: number;
  avg_roi: number;
  suspicious_count: number;
  platform_distribution: { platform: string; count: number }[];
  top_by_followers: { name: string; platform: string | null; followers: number | null }[];
  roi_buckets: { range: string; count: number }[];
  scatter: {
    name: string;
    followers: number | null;
    engagement_rate: number | null;
    conversion_rate: number | null;
    roi: number | null;
    is_suspicious: boolean;
  }[];
}

export interface MiaodaDashboard {
  configured: boolean;
  source: string;
  error: string | null;
  summary: MiaodaSummary;
  items: MiaodaInfluencer[];
}

export async function getMiaodaDashboard(
  siteId?: string,
  dateRange?: { start_date?: string; end_date?: string }
): Promise<MiaodaDashboard> {
  const params = new URLSearchParams();
  if (siteId) params.set("site_id", siteId);
  if (dateRange?.start_date) params.set("start_date", dateRange.start_date);
  if (dateRange?.end_date) params.set("end_date", dateRange.end_date);
  const qs = params.toString();
  const url = qs
    ? `${BASE}/api/miaoda/dashboard?${qs}`
    : `${BASE}/api/miaoda/dashboard`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("获取达人数据看板失败");
  return (await res.json()) as MiaodaDashboard;
}

// ===================== 达人时间段报告生成 =====================
export interface PeriodReport {
  success: boolean;
  period: { start_date: string | null; end_date: string | null; label: string };
  summary: MiaodaSummary;
  report_md: string;
  generated_at: string;
}

export async function generatePeriodReport(
  payload: { start_date?: string; end_date?: string; site_id?: string }
): Promise<PeriodReport> {
  const res = await fetch(`${BASE}/api/miaoda/report/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "生成报告失败");
  return (await res.json()) as PeriodReport;
}

// ===================== TikTok Shop 数据同步 =====================
export interface TikTokStatus {
  configured: boolean;
  shop_id: string | null;
  shop_name?: string | null;
  last_sync?: string | null;
  token: {
    has_access_token: boolean;
    has_refresh_token: boolean;
    is_expiring_soon: boolean;
    expires_at: string | null;
    remaining_hours: number | null;
  };
}

export interface TikTokSyncResult {
  status: "scheduled" | "done";
  start: string;
  end: string;
  message?: string;
  result?: {
    orders: { total_fetched: number; inserted: number; updated: number; skipped: number };
    products: { total_fetched: number; inserted: number; updated: number; skipped: number };
  };
}

export async function getTikTokStatus(): Promise<TikTokStatus> {
  const res = await fetch(`${BASE}/api/tiktok/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取 TikTok 状态失败");
  return (await res.json()) as TikTokStatus;
}

export async function syncTikTokData(
  days = 7,
  foreground = false
): Promise<TikTokSyncResult> {
  const res = await fetch(
    `${BASE}/api/tiktok/sync?foreground=${foreground}&days=${days}`,
    { method: "POST", cache: "no-store" }
  );
  if (!res.ok) throw new Error((await res.json()).detail ?? "同步失败");
  return (await res.json()) as TikTokSyncResult;
}

// ===================== AI 分析报告 =====================
export interface AIReportResponse {
  report_id: string;
  status: "pending" | "running" | "done" | "failed";
  content_md: string;
  error: string;
}

export async function generateAIReport(
  days: number,
  query = "",
  foreground = false
): Promise<AIReportResponse> {
  const res = await fetch(
    `${BASE}/api/ai-report/generate?foreground=${foreground}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days, query }),
      cache: "no-store",
    }
  );
  if (!res.ok) throw new Error((await res.json()).detail ?? "生成报告失败");
  return (await res.json()) as AIReportResponse;
}

export async function getAIReport(reportId: string): Promise<AIReportResponse> {
  const res = await fetch(`${BASE}/api/ai-report/${reportId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("获取报告失败");
  return (await res.json()) as AIReportResponse;
}
