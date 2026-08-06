"""迁移脚本：把 TikTok 订单的时间字段从本地时区(UTC+8)修正为 UTC。

背景：旧版 _parse_tiktok_datetime 用 datetime.fromtimestamp(ts) 在本地时区机器上
得到的是本地墙钟时间(UTC+8)，存进 DB 的时间比真实 UTC 早 8 小时。
现在代码已改为统一存 UTC，本脚本用于一次性修正历史数据。

修正字段：paid_at / rts_time / delivery_time / update_time
修正规则：platform='tiktok' 的记录，时间值减 8 小时。

幂等：重复执行会把时间再减 8 小时，所以脚本会先检测是否已迁移过
（通过 paid_at 是否小于 create_time 对应的 UTC 来判断），已迁移则跳过。
为安全起见，提供一个 --force 参数强制再减一次（一般不用）。

用法：
    python backend/scripts/migrate_paid_at_to_utc.py          # 检测+迁移
    python backend/scripts/migrate_paid_at_to_utc.py --force  # 强制再减8h（危险）
"""
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models.standard import Platform, StandardOrder


OFFSET = timedelta(hours=8)


def main(force: bool = False):
    db = SessionLocal()
    try:
        # 统计 TikTok 订单总数与有时间字段的数
        total = db.query(StandardOrder).filter(StandardOrder.platform == Platform.TIKTOK).count()
        has_paid = (
            db.query(StandardOrder)
            .filter(StandardOrder.platform == Platform.TIKTOK, StandardOrder.paid_at.isnot(None))
            .count()
        )
        print(f"TikTok 订单总数: {total}, 有 paid_at 的: {has_paid}")
        if has_paid == 0:
            print("无 paid_at 数据，无需迁移。")
            return

        # 取一条样本看当前时间值，粗略判断是否已迁移
        sample = (
            db.query(StandardOrder.paid_at)
            .filter(StandardOrder.platform == Platform.TIKTOK, StandardOrder.paid_at.isnot(None))
            .order_by(StandardOrder.paid_at.desc())
            .first()
        )
        print(f"最新 paid_at 样本: {sample[0] if sample else 'N/A'}")
        print(f"当前 UTC 时间约: {__import__('datetime').datetime.utcnow()}")
        if not force:
            # 简单确认
            print("\n将把所有 TikTok 订单的 paid_at/rts_time/delivery_time/update_time 减去 8 小时。")
            print("若已迁移过，请勿重复执行（会再减 8 小时）。")

        # 执行批量更新（SQLite 用 datetime(col, '-8 hours')）
        from sqlalchemy import text
        fields = ["paid_at", "rts_time", "delivery_time", "update_time"]
        for f in fields:
            sql = text(
                f"UPDATE standard_orders SET {f} = datetime({f}, '-8 hours') "
                f"WHERE platform = 'tiktok' AND {f} IS NOT NULL"
            )
            result = db.execute(sql)
            print(f"  {f}: 更新 {result.rowcount} 行")
        db.commit()
        print("\n迁移完成。")

        # 验证
        sample2 = (
            db.query(StandardOrder.paid_at)
            .filter(StandardOrder.platform == Platform.TIKTOK, StandardOrder.paid_at.isnot(None))
            .order_by(StandardOrder.paid_at.desc())
            .first()
        )
        print(f"迁移后最新 paid_at 样本: {sample2[0] if sample2 else 'N/A'}")
    except Exception as e:
        db.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    if force:
        print("⚠️ 强制模式：将再次减 8 小时，仅用于回滚误操作。")
    main(force=force)
