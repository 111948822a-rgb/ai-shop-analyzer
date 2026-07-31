"""统一内部数据模型（持久化层）。

本模块同时提供两类对象：
- SQLAlchemy ORM 模型 `StandardOrder` / `StandardProduct` / `StandardInfluencer`：
  物理表，供数据库存储与 AI 工具的数据库层聚合查询。
- Pydantic DTO（`StandardOrderDTO` / `StandardProductDTO` / `StandardInfluencerDTO`）：
  适配器与外部系统之间的传输结构，不落地；适配器产出 DTO 后由 ETL 写入 ORM。

上层（Preprocessor / AI Engine / 报表）只认 Standard* ORM，适配器产出 *DTO，
新增平台只需写适配器把原始数据转成 DTO —— 上层完全不感知平台差异。
"""
from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Platform(str, enum.Enum):
    DOUYIN = "douyin"   # 抖店
    TAOBAO = "taobao"   # 淘宝
    TIKTOK = "tiktok"   # TikTok Shop（全球店铺 Partner API）
    MANUAL = "manual"   # 手动上传


class OrderStatus(str, enum.Enum):
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    REFUNDED = "refunded"


# 统一用 VARCHAR + CHECK 约束，避免 PostgreSQL 原生 enum 类型不可变
# （新增枚举值时无需 ALTER TYPE，create_all 即可生效）
_platform_enum = SAEnum(
    Platform, native_enum=False, length=32,
    values_callable=lambda x: [e.value for e in x],
)
_status_enum = SAEnum(
    OrderStatus, native_enum=False, length=32,
    values_callable=lambda x: [e.value for e in x],
)


# =========================================================================
# 一、SQLAlchemy ORM —— 物理表（AI 工具在此做数据库层聚合）
# =========================================================================
class StandardProduct(Base):
    """标准商品维度表。"""

    __tablename__ = "standard_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[Platform] = mapped_column(_platform_enum, nullable=False, default=Platform.MANUAL)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_gmv: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_sold: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "platform", name="uq_product_platform"),
        Index("ix_products_platform", "platform"),
        Index("ix_products_category", "category"),
    )


class StandardOrder(Base):
    """标准订单事实表（量大，AI 工具在此做 SUM/COUNT/GROUP BY 聚合，不拉明细）。"""

    __tablename__ = "standard_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    shop_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[Platform] = mapped_column(SAEnum(Platform), nullable=False, default=Platform.MANUAL)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gmv: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creator_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 带货达人
    status: Mapped[OrderStatus] = mapped_column(_status_enum, default=OrderStatus.PAID)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    province: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("order_id", "platform", name="uq_order_platform"),
        # —— 高频查询维度的索引（AI 工具按时间/店铺/商品/达人聚合）——
        Index("ix_orders_paid_at", "paid_at"),
        Index("ix_orders_shop_id", "shop_id"),
        Index("ix_orders_product_id", "product_id"),
        Index("ix_orders_creator_id", "creator_id"),
        Index("ix_orders_platform", "platform"),
    )


class StandardInfluencer(Base):
    """标准达人维度表。含 ROI / 互动率 / 转化率 / 疑似水军标记，供 AI 避坑预警。"""

    __tablename__ = "standard_influencers"

    creator_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    platform: Mapped[Platform] = mapped_column(_platform_enum, nullable=False, default=Platform.MANUAL)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    gmv: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # 投放成本（用于算 ROI）
    roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)   # 互动率 %
    conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)   # 转化率 %
    avg_views: Mapped[int | None] = mapped_column(Integer, nullable=True)          # 平均观看/播放
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)            # 疑似水军/刷量
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_influencers_platform", "platform"),
        Index("ix_influencers_roi", "roi"),
        Index("ix_influencers_suspicious", "is_suspicious"),
    )


# =========================================================================
# 二、Pydantic DTO —— 适配器传输结构（不落库）
# =========================================================================
class StandardOrderDTO(BaseModel):
    platform: Platform
    order_id: str
    product_id: str
    product_name: str
    gmv: float
    quantity: int = 1
    customer_id: str | None = None
    creator_id: str | None = None
    status: OrderStatus = OrderStatus.PAID
    paid_at: datetime | None = None
    province: str | None = None
    shop_id: str | None = None


class StandardProductDTO(BaseModel):
    platform: Platform
    product_id: str
    name: str
    category: str | None = None
    price: float | None = None
    total_gmv: float = 0
    total_sold: int = 0


class StandardInfluencerDTO(BaseModel):
    platform: Platform
    creator_id: str
    name: str
    category: str | None = None
    followers: int = 0
    gmv: float = 0
    orders: int = 0
    cost: float = 0
    roi: float | None = None
    engagement_rate: float | None = None
    conversion_rate: float | None = None
    avg_views: int | None = None
    is_suspicious: bool = False


# =========================================================================
# 三、秒搭 -> AI 分析 -> 回写 的持久化结果
# 前端 H5 报告页按 record_id 读取此处数据；多维表格回写也读这里。
# =========================================================================
class MiaodaAnalysis(Base):
    """秒搭触发的达人 AI 分析结果（按 record_id 唯一）。"""

    __tablename__ = "miaoda_analysis"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    influencer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    target_product: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # AI 产出
    ai_match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 0-100
    ai_risk_warning: Mapped[str | None] = mapped_column(Text, nullable=True)        # 避坑预警
    ai_outreach_script: Mapped[str | None] = mapped_column(Text, nullable=True)      # 中文建联话术
    fit_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)            # 人货匹配分析

    # 结构化字段（JSON 落地，前端直接渲染）
    radar: Mapped[dict | None] = mapped_column(JSON, nullable=True)                  # 雷达图维度
    multilingual: Mapped[dict | None] = mapped_column(JSON, nullable=True)           # 多语种话术

    ai_report_url: Mapped[str | None] = mapped_column(String(512), nullable=True)    # H5 链接

    # 任务状态
    status: Mapped[str] = mapped_column(String(16), default="processing")           # processing/done/failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_miaoda_status", "status"),)
