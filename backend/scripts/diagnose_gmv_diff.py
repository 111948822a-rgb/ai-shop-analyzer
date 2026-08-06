"""诊断脚本：找出 API 原始数据 / 数据库数据 / TikTok 后台数据 三者差异的根因。

核心验证三点：
1. 时区口径：TikTok 后台用 UTC，我们的系统全程用本地时区(UTC+8)。
   同一批订单用 UTC 近7天 vs 本地时区近7天 统计，GMV/件数会不同。
2. 指标定义：后台"成交件数"= Σquantity，我们看板常显示"订单数"= COUNT(行)。
3. 状态口径：cancelled/refunded 是否计入 GMV。

用法：python backend/scripts/diagnose_gmv_diff.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models.standard import OrderStatus, Platform, StandardOrder
from app.adapters.tiktok_shop import TikTokShopPartnerAPI, _norm_status

# 本地时区 (Asia/Shanghai = UTC+8)
LOCAL_TZ = timezone(timedelta(hours=8))
UTC_TZ = timezone.utc


def _ts_to_dt(ts) -> datetime:
    """把 TikTok create_time (秒级 UTC 时间戳) 转 aware datetime。"""
    t = int(ts)
    if t > 1_000_000_000_000:
        t //= 1000
    return datetime.fromtimestamp(t, tz=UTC_TZ)


def _is_cancelled_or_refunded(raw_order) -> bool:
    """判断订单是否为取消/退款（不计入 GMV）。"""
    line_items = raw_order.get("line_items") or raw_order.get("items") or []
    first = line_items[0] if line_items else {}
    raw_status = first.get("display_status") or raw_order.get("status") or ""
    s = str(raw_status).lower()
    return s in ("cancelled", "refund", "refunded")


def _gmv_of(raw_order) -> float:
    payment = raw_order.get("payment") or {}
    return float(payment.get("total_amount") or 0)


def _qty_of(raw_order) -> int:
    line_items = raw_order.get("line_items") or raw_order.get("items") or []
    if line_items:
        return sum(int(it.get("quantity") or 1) for it in line_items)
    return int(raw_order.get("quantity") or 1)


def main():
    now_local = datetime.now(LOCAL_TZ)
    now_utc = datetime.now(UTC_TZ)
    print("=" * 70)
    print("GMV 差异诊断")
    print(f"当前本地时间(UTC+8): {now_local:%Y-%m-%d %H:%M:%S}")
    print(f"当前 UTC 时间      : {now_utc:%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # ---- 拉取 API 原始订单（拉近 30 天，够宽，再本地分口径统计近 7 天）----
    print("\n[1] 拉取 TikTok API 原始订单（近 30 天）...")
    api = TikTokShopPartnerAPI()
    start_30 = (now_local - timedelta(days=30)).strftime("%Y-%m-%d")
    end_30 = now_local.strftime("%Y-%m-%d")
    raw_orders = api.fetch_orders(start_30, end_30)
    print(f"    API 返回订单数(本地时区过滤后): {len(raw_orders)}")

    # ---- 定义近7天窗口（两种时区口径）----
    # 本地口径: [now_local - 7天, now_local + 1天)  ← 我们系统用的
    local_start = (now_local - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start + timedelta(days=8)  # 含今天一整天，到明天0点
    # UTC 口径: [now_utc - 7天, now_utc + 1天)  ← TikTok 后台用的
    utc_start = (now_utc - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    utc_end = utc_start + timedelta(days=8)

    print(f"\n[2] 近7天窗口口径对比:")
    print(f"    本地时区窗口(我们系统): {local_start:%Y-%m-%d %H:%M} ~ {local_end:%Y-%m-%d %H:%M}")
    print(f"    UTC 时区窗口(TK后台)  : {utc_start:%Y-%m-%d %H:%M} ~ {utc_end:%Y-%m-%d %H:%M}")
    print(f"    窗口起点差: {(local_start - utc_start).total_seconds()/3600:.1f} 小时")

    def stats_for_window(orders, win_start, win_end):
        """统计落在 [win_start, win_end) 内的订单：单数/件数/GMV(排除取消退款)。"""
        n_orders = 0
        n_qty = 0
        gmv = 0.0
        gmv_all = 0.0  # 含取消退款的原始 GMV，用于对照
        for o in orders:
            ct = o.get("create_time") or o.get("paid_time")
            if not ct:
                continue
            dt = _ts_to_dt(ct)
            if win_start <= dt < win_end:
                n_orders += 1
                n_qty += _qty_of(o)
                gmv_all += _gmv_of(o)
                if not _is_cancelled_or_refunded(o):
                    gmv += _gmv_of(o)
        return n_orders, n_qty, gmv, gmv_all

    lo_orders, lo_qty, lo_gmv, lo_gmv_all = stats_for_window(raw_orders, local_start, local_end)
    uc_orders, uc_qty, uc_gmv, uc_gmv_all = stats_for_window(raw_orders, utc_start, utc_end)

    print(f"\n[3] API 原始数据按不同时区口径统计近7天:")
    print(f"    {'口径':<14}{'订单数':>8}{'件数(Σqty)':>12}{'GMV(排除退款)':>16}{'GMV(含退款)':>14}")
    print(f"    {'-'*64}")
    print(f"    {'本地时区(我们)':<14}{lo_orders:>8}{lo_qty:>12}{lo_gmv:>16.2f}{lo_gmv_all:>14.2f}")
    print(f"    {'UTC(TK后台)':<14}{uc_orders:>8}{uc_qty:>12}{uc_gmv:>16.2f}{uc_gmv_all:>14.2f}")
    print(f"    {'差异(本地-UTC)':<14}{lo_orders-uc_orders:>8}{lo_qty-uc_qty:>12}{lo_gmv-uc_gmv:>16.2f}")

    # ---- 数据库近7天统计（系统看板实际口径，按 UTC，与 TK 后台对齐）----
    print(f"\n[4] 数据库近7天统计（系统看板实际口径，按 paid_at UTC）:")
    db = SessionLocal()
    try:
        db_start = datetime.utcnow() - timedelta(days=7)
        db_end = datetime.utcnow() + timedelta(days=1)
        rows = db.query(StandardOrder).filter(
            StandardOrder.platform == Platform.TIKTOK,
            StandardOrder.paid_at >= db_start,
            StandardOrder.paid_at < db_end,
        ).all()
        db_orders = len(rows)
        db_qty = sum(int(r.quantity or 0) for r in rows)
        db_gmv = sum(float(r.gmv or 0) for r in rows if r.status != OrderStatus.REFUNDED)
        db_gmv_all = sum(float(r.gmv or 0) for r in rows)
        print(f"    订单数(含退款): {db_orders}")
        print(f"    件数(Σquantity): {db_qty}")
        print(f"    GMV(排除退款)  : {db_gmv:.2f}")
        print(f"    GMV(含退款)    : {db_gmv_all:.2f}")
        print(f"    状态分布:")
        from collections import Counter
        sc = Counter(r.status.value for r in rows)
        for s, c in sc.most_common():
            print(f"      {s}: {c}")
        # 对照 API 口径
        print(f"\n    对照 API 原始数据(本地时区口径):")
        print(f"      API 订单数={lo_orders}, DB 订单数={db_orders}, 差={lo_orders-db_orders} (同步延迟/丢失)")
        print(f"      API 件数={lo_qty}, DB 件数={db_qty}, 差={lo_qty-db_qty}")
        print(f"      API GMV={lo_gmv:.2f}, DB GMV={db_gmv:.2f}, 差={lo_gmv-db_gmv:.2f}")
    except Exception as e:
        print(f"    (本地无数据库或表未建，跳过: {e})")
        print(f"    提示: 在 Render 服务器上运行此脚本可获取完整对比。")
    finally:
        db.close()

    # ---- 结论 ----
    print(f"\n[5] 差异根因结论:")
    print(f"    a) 时区口径: 本地时区近7天 GMV={lo_gmv:.2f}, UTC近7天 GMV={uc_gmv:.2f},")
    print(f"       差 {lo_gmv-uc_gmv:.2f} (即 {(lo_gmv-uc_gmv)/max(uc_gmv,1)*100:.1f}%) ← 时区错位导致")
    print(f"    b) 件数 vs 单数: API 件数(Σqty)={lo_qty}, 后台若显示件数应与此对齐；")
    print(f"       若系统展示的是订单行数(COUNT)={db_orders}, 与后台件数不是同一指标。")
    print(f"    c) 取消退款: 含退款GMV={lo_gmv_all:.2f}, 排除退款GMV={lo_gmv:.2f},")
    print(f"       差 {lo_gmv_all-lo_gmv:.2f} ← 取消退款单的金额被排除。")


if __name__ == "__main__":
    main()
