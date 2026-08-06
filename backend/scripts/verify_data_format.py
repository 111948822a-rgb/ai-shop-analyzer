"""验证订单ID/商品ID格式是否符合 TikTok 要求。"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db import engine

print("=" * 60)
print("数据格式验证（TikTok 审核要求）")
print("=" * 60)

con = engine.connect()

# 订单ID：应为18位数字，以57或58开头
print("\n[1] 订单ID格式验证（要求：18位数字，57/58开头）:")
rows = con.execute(
    text(
        "SELECT order_id, product_id, product_name FROM standard_orders "
        "WHERE platform='tiktok' ORDER BY paid_at DESC LIMIT 10"
    )
).fetchall()
print(f"  {'order_id':<22} {'长度':<6} {'开头':<6} {'product_id':<20} {'p长度':<6} {'商品名'}")
ok_orders = 0
ok_products = 0
for r in rows:
    oid = str(r[0])
    pid = str(r[1])
    olen = len(oid)
    ohead = oid[:2]
    plen = len(pid)
    phead = pid[:2]
    o_ok = "✓" if (olen == 18 and ohead in ("57", "58")) else "✗"
    p_ok = "✓" if (plen == 17 and phead in ("1", "2", "3", "4", "5", "6", "7", "8", "9")) else "✗"
    if o_ok == "✓":
        ok_orders += 1
    if p_ok == "✓":
        ok_products += 1
    print(f"  {oid:<22} {olen:<6} {ohead:<6} {pid:<20} {plen:<6} {r[2][:25]}")
    print(f"    订单{o_ok} 商品{p_ok}")

# 统计全表合规率
print("\n[2] 全表合规率:")
total = con.execute(text("SELECT count(*) FROM standard_orders WHERE platform='tiktok'")).scalar()
order_ok = con.execute(
    text(
        "SELECT count(*) FROM standard_orders WHERE platform='tiktok' "
        "AND length(order_id)=18 AND (order_id LIKE '57%' OR order_id LIKE '58%')"
    )
).scalar()
prod_ok = con.execute(
    text(
        "SELECT count(*) FROM standard_orders WHERE platform='tiktok' "
        "AND length(product_id)=17"
    )
).scalar()
print(f"  订单总数: {total}")
print(f"  订单ID合规(18位57/58开头): {order_ok}/{total} = {order_ok/total*100:.1f}%")
print(f"  商品ID合规(17位): {prod_ok}/{total} = {prod_ok/total*100:.1f}%")

# 商品表
print("\n[3] 商品表(standard_products)验证:")
ptotal = con.execute(text("SELECT count(*) FROM standard_products WHERE platform='tiktok'")).scalar()
p_ok = con.execute(
    text(
        "SELECT count(*) FROM standard_products WHERE platform='tiktok' "
        "AND length(product_id)=17"
    )
).scalar()
print(f"  商品总数: {ptotal}")
print(f"  商品ID合规(17位): {p_ok}/{ptotal}")
if ptotal > 0:
    samples = con.execute(
        text("SELECT product_id, name FROM standard_products WHERE platform='tiktok' LIMIT 5")
    ).fetchall()
    for s in samples:
        print(f"    {s[0]} (len={len(str(s[0]))}) {s[1][:30]}")

con.close()
