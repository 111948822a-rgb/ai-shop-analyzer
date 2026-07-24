"""Pandas 数据预处理核心模块。

职责：把用户上传的原始大表（店铺销售数据 / 达人数据）清洗、聚合，
压缩成一份结构化 JSON 摘要 —— 这份摘要才是发给 LLM 的内容，
原始数据永远不出本地。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# 列名别名映射：兼容 TikTok Shop 后台导出 / 国内 ERP 导出的各种叫法
# ---------------------------------------------------------------------------
COLUMN_ALIASES: dict[str, list[str]] = {
    "gmv": ["gmv", "销售额", "成交金额", "支付金额", "总收入", "gross revenue", "total sales", "revenue"],
    "orders": ["orders", "订单数", "订单量", "成交订单数", "支付订单数", "total orders", "units sold", "销量"],
    "date": ["date", "日期", "统计日期", "下单日期", "时间", "order date"],
    "product": ["product", "商品名称", "商品名", "商品标题", "product name", "sku名称", "item name"],
    "visitors": ["visitors", "访客数", "浏览人数", "uv", "views", "曝光量", "page views", "商品访客数"],
    "conversion": ["conversion", "转化率", "支付转化率", "点击转化率", "conversion rate", "cvr"],
    "creator": ["creator", "达人昵称", "达人名称", "达人", "creator name", "kol", "influencer", "username", "账号昵称"],
    "roi": ["roi", "投产比", "投入产出比", "roas"],
    "commission": ["commission", "佣金率", "佣金比例", "commission rate"],
    "videos": ["videos", "视频数", "带货视频数", "发布视频数", "video count"],
    "followers": ["followers", "粉丝数", "粉丝量", "follower count", "粉丝数量"],
    "cost": ["cost", "花费", "投放金额", "成本", "spend", "样品成本"],
}


def _normalize(name: str) -> str:
    return re.sub(r"[\s_\-（）()]", "", str(name)).lower()


def map_columns(df: pd.DataFrame) -> dict[str, str]:
    """把原始列名映射为标准字段名，返回 {标准名: 原始列名}。"""
    mapping: dict[str, str] = {}
    normalized = {_normalize(c): c for c in df.columns}
    for std, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize(alias)
            if key in normalized:
                mapping[std] = normalized[key]
                break
    return mapping


# ---------------------------------------------------------------------------
# 加载与清洗
# ---------------------------------------------------------------------------

def load_dataframe(path: str | Path) -> pd.DataFrame:
    """读取 CSV / Excel，CSV 自动尝试常见中文编码。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError("无法识别 CSV 文件编码，请另存为 UTF-8 后重试")
    raise ValueError(f"不支持的文件格式: {suffix}")


def _to_numeric(series: pd.Series) -> pd.Series:
    """把 '¥1,234.5'、'12.3%'、'1.2万' 这类脏数字列转成 float。"""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)

    def parse(value: Any) -> float | None:
        if pd.isna(value):
            return None
        s = str(value).strip().replace(",", "").replace("¥", "").replace("￥", "").replace("$", "")
        multiplier = 1.0
        if s.endswith("%"):
            s, multiplier = s[:-1], 0.01
        elif s.endswith("万"):
            s, multiplier = s[:-1], 10000.0
        elif s.lower().endswith("k"):
            s, multiplier = s[:-1], 1000.0
        try:
            return float(s) * multiplier
        except ValueError:
            return None

    return series.map(parse)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """基础清洗：去空行空列、去重、列名去空格。"""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df.drop_duplicates()
    return df.reset_index(drop=True)


def _round2(value: float | None) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), 2)


# ---------------------------------------------------------------------------
# 店铺销售数据摘要
# ---------------------------------------------------------------------------

def summarize_shop(df: pd.DataFrame, mapping: dict[str, str]) -> dict:
    summary: dict[str, Any] = {"data_type": "shop"}

    gmv_col = mapping.get("gmv")
    if gmv_col:
        gmv = _to_numeric(df[gmv_col])
        summary["total_gmv"] = _round2(gmv.sum())
        summary["avg_daily_gmv"] = None

    orders_col = mapping.get("orders")
    if orders_col:
        orders = _to_numeric(df[orders_col])
        summary["total_orders"] = int(orders.sum() or 0)
        if gmv_col and summary["total_orders"]:
            summary["avg_order_value"] = _round2(summary["total_gmv"] / summary["total_orders"])

    visitors_col = mapping.get("visitors")
    if visitors_col:
        visitors = _to_numeric(df[visitors_col])
        summary["total_visitors"] = int(visitors.sum() or 0)
        if orders_col and summary.get("total_visitors"):
            summary["overall_conversion_rate"] = _round2(
                summary["total_orders"] / summary["total_visitors"] * 100
            )

    conv_col = mapping.get("conversion")
    if conv_col and "overall_conversion_rate" not in summary:
        conv = _to_numeric(df[conv_col])
        rate = conv.mean()
        if rate is not None and not pd.isna(rate):
            summary["overall_conversion_rate"] = _round2(rate * 100 if rate < 1 else rate)

    # Top10 商品
    product_col = mapping.get("product")
    if product_col and gmv_col:
        top = (
            df.assign(_gmv=_to_numeric(df[gmv_col]))
            .groupby(product_col)["_gmv"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        summary["top10_products"] = [
            {"product": str(name)[:60], "gmv": _round2(v)} for name, v in top.items()
        ]

    # 按日趋势（给前端画图 + 给 LLM 看走势）
    date_col = mapping.get("date")
    if date_col and gmv_col:
        tmp = df.assign(
            _date=pd.to_datetime(df[date_col], errors="coerce"),
            _gmv=_to_numeric(df[gmv_col]),
        ).dropna(subset=["_date"])
        if not tmp.empty:
            daily = tmp.groupby(tmp["_date"].dt.date)["_gmv"].sum().sort_index()
            summary["date_range"] = {"start": str(daily.index.min()), "end": str(daily.index.max())}
            summary["daily_gmv_trend"] = [
                {"date": str(d), "gmv": _round2(v)} for d, v in daily.items()
            ]
            summary["avg_daily_gmv"] = _round2(daily.mean())
            summary["best_day"] = {"date": str(daily.idxmax()), "gmv": _round2(daily.max())}
            summary["worst_day"] = {"date": str(daily.idxmin()), "gmv": _round2(daily.min())}

    return summary


# ---------------------------------------------------------------------------
# 达人数据摘要
# ---------------------------------------------------------------------------

def summarize_creator(df: pd.DataFrame, mapping: dict[str, str]) -> dict:
    summary: dict[str, Any] = {"data_type": "creator"}

    creator_col = mapping.get("creator")
    if creator_col:
        summary["creator_count"] = int(df[creator_col].nunique())

    gmv_col = mapping.get("gmv")
    if gmv_col:
        gmv = _to_numeric(df[gmv_col])
        summary["total_gmv"] = _round2(gmv.sum())
        # 出单达人占比：衡量建联质量的关键指标
        producing = int((gmv.fillna(0) > 0).sum())
        summary["producing_creators"] = producing
        if len(df):
            summary["producing_rate"] = _round2(producing / len(df) * 100)

    roi_col = mapping.get("roi")
    if roi_col:
        roi = _to_numeric(df[roi_col]).dropna()
        if not roi.empty:
            summary["avg_roi"] = _round2(roi.mean())
            summary["median_roi"] = _round2(roi.median())
            summary["roi_distribution"] = {
                "低于1（亏损）": int((roi < 1).sum()),
                "1到3": int(((roi >= 1) & (roi < 3)).sum()),
                "3到5": int(((roi >= 3) & (roi < 5)).sum()),
                "5以上": int((roi >= 5).sum()),
            }

    videos_col = mapping.get("videos")
    if videos_col:
        videos = _to_numeric(df[videos_col])
        summary["total_videos"] = int(videos.sum() or 0)

    # Top10 达人（优先按 GMV 排）
    if creator_col and gmv_col:
        agg: dict[str, Any] = {"_gmv": "sum"}
        tmp = df.assign(_gmv=_to_numeric(df[gmv_col]))
        if roi_col:
            tmp = tmp.assign(_roi=_to_numeric(df[roi_col]))
            agg["_roi"] = "mean"
        if videos_col:
            tmp = tmp.assign(_videos=_to_numeric(df[videos_col]))
            agg["_videos"] = "sum"
        top = tmp.groupby(creator_col).agg(agg).sort_values("_gmv", ascending=False).head(10)
        summary["top10_creators"] = [
            {
                "creator": str(name)[:40],
                "gmv": _round2(row["_gmv"]),
                **({"roi": _round2(row["_roi"])} if "_roi" in row else {}),
                **({"videos": int(row["_videos"] or 0)} if "_videos" in row else {}),
            }
            for name, row in top.iterrows()
        ]

    return summary


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_summary(path: str | Path, data_type: str) -> tuple[dict, int, list[str]]:
    """加载 → 清洗 → 聚合，返回 (摘要dict, 行数, 列名列表)。"""
    df = clean_dataframe(load_dataframe(path))
    if df.empty:
        raise ValueError("文件内容为空或全部是无效行")

    mapping = map_columns(df)
    if not mapping:
        raise ValueError(
            f"无法识别任何关键列。检测到的列: {list(df.columns)[:20]}，"
            "请确认表头包含 GMV/销售额、订单数、达人昵称 等常见字段"
        )

    if data_type == "creator":
        summary = summarize_creator(df, mapping)
    else:
        summary = summarize_shop(df, mapping)

    summary["row_count"] = len(df)
    summary["recognized_columns"] = mapping
    return summary, len(df), [str(c) for c in df.columns]
