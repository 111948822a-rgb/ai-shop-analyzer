"""补建远程数据库缺失的扩展字段（idempotent，已有列则跳过）。

远程 standard_orders 表是旧结构（13列），代码已扩展到 29 列。
本脚本用 ADD COLUMN IF NOT EXISTS 安全补齐，不删不改已有数据。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db import engine

# 需要补建的扩展字段（DDL 定义与 ORM 一致）
EXT_COLUMNS = [
    ("sku_id", "VARCHAR(64)"),
    ("seller_sku", "VARCHAR(128)"),
    ("sku_name", "VARCHAR(255)"),
    ("currency", "VARCHAR(16)"),
    ("original_price", "NUMERIC(14,2)"),
    ("platform_discount", "NUMERIC(14,2)"),
    ("seller_discount", "NUMERIC(14,2)"),
    ("shipping_fee", "NUMERIC(14,2)"),
    ("is_cod", "BOOLEAN DEFAULT FALSE"),
    ("is_sample_order", "BOOLEAN DEFAULT FALSE"),
    ("delivery_type", "VARCHAR(32)"),
    ("shipping_provider", "VARCHAR(64)"),
    ("tracking_number", "VARCHAR(128)"),
    ("rts_time", "TIMESTAMP"),
    ("delivery_time", "TIMESTAMP"),
    ("update_time", "TIMESTAMP"),
]

print("=" * 60)
print("补建远程数据库缺失的扩展字段")
print("=" * 60)

con = engine.connect()
# 先查现有列
existing = {
    r[0]
    for r in con.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='standard_orders'"
        )
    ).fetchall()
}
print(f"现有列: {sorted(existing)}")

added = 0
for col_name, col_type in EXT_COLUMNS:
    if col_name in existing:
        print(f"  ✓ {col_name} 已存在，跳过")
        continue
    sql = f"ALTER TABLE standard_orders ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
    con.execute(text(sql))
    print(f"  + 新增 {col_name} ({col_type})")
    added += 1

con.commit()
print(f"\n完成：新增 {added} 列，共 {len(EXT_COLUMNS)} 个扩展字段。")

# 补建索引（与 ORM 一致）
print("\n补建索引:")
INDEXES = [
    ("ix_orders_sku_id", "sku_id"),
    ("ix_orders_creator_id", "creator_id"),
    ("ix_orders_status", "status"),
]
existing_idx = {
    r[0]
    for r in con.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE tablename='standard_orders'"
        )
    ).fetchall()
}
for idx_name, col in INDEXES:
    if idx_name in existing_idx:
        print(f"  ✓ {idx_name} 已存在")
        continue
    con.execute(text(f"CREATE INDEX {idx_name} ON standard_orders ({col})"))
    print(f"  + 新建索引 {idx_name} on {col}")
con.commit()
con.close()
print("\n全部完成。")
