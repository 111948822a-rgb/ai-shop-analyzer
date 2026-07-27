import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.standard import StandardOrder
from datetime import date, datetime

db = SessionLocal()

try:
    orders = db.query(StandardOrder).order_by(StandardOrder.order_date.desc()).limit(20).all()
    
    print("最近20条订单数据:")
    print("-" * 80)
    
    dates = []
    for order in orders:
        print(f"订单ID: {order.order_id}")
        print(f"  日期: {order.order_date}")
        print(f"  金额: {order.order_amount}")
        print(f"  站点: {order.site_code}")
        print(f"  币种: {order.currency}")
        print(f"  商品ID: {order.product_id}")
        print(f"  达人ID: {order.influencer_id}")
        print()
        dates.append(order.order_date)
    
    if dates:
        earliest = min(dates)
        latest = max(dates)
        print(f"订单日期范围: {earliest} ~ {latest}")
        
    today = date.today()
    print(f"今天日期: {today}")
    
    current_week_orders = db.query(StandardOrder).filter(
        StandardOrder.order_date >= datetime(today.year, today.month, today.day - today.weekday())
    ).count()
    print(f"本周订单数: {current_week_orders}")
    
finally:
    db.close()
