"""小白一键迁移工具：连到 Render 远程数据库，执行 UTC 迁移 + 验证。

使用方式：双击同目录下的 run_migrate_remote.bat 即可，无需手敲命令。
脚本会提示你粘贴 Render 数据库的 External Database URL。
"""
import os
import sys

# 必须在 import app.* 之前设置 DATABASE_URL，否则会用 .env 里的 SQLite
print("=" * 64)
print("  TikTok 数据 UTC 迁移工具（连 Render 远程数据库）")
print("=" * 64)
print()
print("第 1 步：去 Render 控制台拿数据库连接地址")
print("  1) 打开 https://dashboard.render.com")
print("  2) 左侧选 Databases → 点 ai-shop-analyzer-db")
print("  3) 页面下方找 Connections → External → External Database URL")
print("  4) 点 Copy 复制（形如 postgres://用户:密码@host:5432/库）")
print()
print("第 2 步：把刚才复制的地址粘贴到下面，按回车")
print()
db_url = input("  粘贴 External Database URL > ").strip()

if not db_url:
    print("\n未输入 URL，已退出。")
    sys.exit(1)

# 设置环境变量，让 app.db 优先用这个远程地址（覆盖 .env 里的 SQLite）
os.environ["DATABASE_URL"] = db_url
print(f"\n已接收 URL（前 40 字符）: {db_url[:40]}...")
print()

# 把 backend 目录加入 sys.path，让脚本能 import app
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# 确认能连上
print("正在连接远程数据库...")
try:
    from app.db import SessionLocal
    from app.models.standard import Platform, StandardOrder
    db = SessionLocal()
    total = db.query(StandardOrder).filter(StandardOrder.platform == Platform.TIKTOK).count()
    has_paid = (
        db.query(StandardOrder)
        .filter(StandardOrder.platform == Platform.TIKTOK, StandardOrder.paid_at.isnot(None))
        .count()
    )
    db.close()
    print(f"连接成功！TikTok 订单 {total} 条，其中有 paid_at 的 {has_paid} 条。")
except Exception as e:
    print(f"\n连接失败：{e}")
    print("\n常见原因：")
    print("  - URL 复制错了（要用 External，不是 Internal）")
    print("  - URL 粘贴时少了字符")
    print("\n请重新运行本脚本，重新粘贴。")
    sys.exit(1)

print()
print("=" * 64)
print("  开始迁移：把 TikTok 订单时间字段减 8 小时转 UTC")
print("=" * 64)
print()
print("⚠️  本操作只执行一次。重复执行会把时间再减 8 小时。")
print("   如果之前没跑过，直接继续；跑过就别再跑。")
print()
confirm = input("确认执行迁移？输入 y 继续，其他键退出 > ").strip().lower()
if confirm != "y":
    print("已取消。")
    sys.exit(0)

# 执行迁移
from sqlalchemy import text
from app.db import engine
from datetime import datetime

fields = ["paid_at", "rts_time", "delivery_time", "update_time"]
db = SessionLocal()
try:
    for f in fields:
        # Postgres 用 (col - interval '8 hours')
        sql = text(
            f"UPDATE standard_orders SET {f} = ({f} - interval '8 hours') "
            f"WHERE platform = 'tiktok' AND {f} IS NOT NULL"
        )
        result = db.execute(sql)
        print(f"  {f}: 更新 {result.rowcount} 行")
    db.commit()
    print("\n迁移完成。")
except Exception as e:
    db.rollback()
    print(f"\n迁移失败：{e}")
    sys.exit(1)
finally:
    db.close()

print()
print("=" * 64)
print("  验证：最新 paid_at 是否已转为 UTC")
print("=" * 64)
db = SessionLocal()
try:
    row = (
        db.query(StandardOrder.paid_at)
        .filter(StandardOrder.platform == Platform.TIKTOK, StandardOrder.paid_at.isnot(None))
        .order_by(StandardOrder.paid_at.desc())
        .first()
    )
    if row:
        print(f"  最新 paid_at: {row[0]}")
        print(f"  当前 UTC 时间: {datetime.utcnow()}")
        print()
        print("✅ 如果最新 paid_at 接近当前 UTC 时间，说明迁移正确。")
finally:
    db.close()

print()
print("=" * 64)
print("  全部完成！")
print("=" * 64)
print()
print("下一步：去 Render 控制台重启 ai-shop-analyzer-backend 服务。")
print("  1) Render Dashboard → ai-shop-analyzer-backend")
print("  2) 右上角 Manual Deploy → Suspend web service → 再 Resume")
print("     或直接点 Restart")
print()
input("按回车键关闭本窗口...")
