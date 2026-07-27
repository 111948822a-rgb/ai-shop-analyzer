import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.standard import StandardOrder, StandardProduct, StandardInfluencer
from datetime import datetime, timedelta


def main():
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("数据检查")
        print("=" * 60)
        
        print(f"\n今日日期: {datetime.now()}")
        
        start_date = datetime.now() - timedelta(days=6)
        print(f"\n本周开始日期: {start_date}")
        
        orders = db.query(StandardOrder).all()
        print(f"\n总订单数: {len(orders)}")
        
        recent_orders = db.query(StandardOrder).filter(
            StandardOrder.order_date >= start_date
        ).all()
        print(f"本周订单数: {len(recent_orders)}")
        
        if orders:
            print("\n订单日期分布:")
            for i, order in enumerate(orders[:10]):
                print(f"  {i+1}. {order.order_date}")
        
        products = db.query(StandardProduct).count()
        influencers = db.query(StandardInfluencer).count()
        
        print(f"\n商品总数: {products}")
        print(f"达人总数: {influencers}")
        
        suspicious = db.query(StandardInfluencer).filter(
            StandardInfluencer.is_suspicious == True
        ).count()
        print(f"水军达人: {suspicious}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()