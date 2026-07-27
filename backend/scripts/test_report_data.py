import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.report_generator import (
    get_weekly_date_range,
    get_sales_summary,
    get_product_sales_ranking,
    get_influencer_performance,
    get_site_breakdown,
    get_daily_sales_trend,
    get_influencer_product_analysis,
)


def main():
    db = SessionLocal()
    date_range = get_weekly_date_range()
    
    print(f"日期范围: {date_range}")
    
    print("\n1. 测试 get_sales_summary...")
    sales_summary = get_sales_summary(db, date_range=date_range)
    print(f"GMV: {sales_summary.get('total_gmv', 0)}")
    print(f"Orders: {sales_summary.get('total_orders', 0)}")
    
    print("\n2. 测试 get_product_sales_ranking...")
    products = get_product_sales_ranking(db, date_range=date_range, limit=5)
    print(f"热销商品: {len(products)}")
    for p in products[:3]:
        print(f"  - {p.get('product_name')}: ${p.get('total_sales', 0):,.2f}")
    
    print("\n3. 测试 get_influencer_performance...")
    influencers = get_influencer_performance(db, date_range=date_range, limit=5)
    print(f"达人表现: {len(influencers)}")
    for i in influencers[:3]:
        print(f"  - {i.get('influencer_name')}: ${i.get('total_sales', 0):,.2f}")
    
    print("\n4. 测试 get_site_breakdown...")
    sites = get_site_breakdown(db, date_range=date_range)
    print(f"站点数量: {len(sites)}")
    for s in sites:
        print(f"  - {s.get('site_code')}: ${s.get('total_gmv', 0):,.2f}")
    
    print("\n5. 测试 get_daily_sales_trend...")
    trend = get_daily_sales_trend(db, date_range=date_range)
    print(f"趋势数据: {len(trend)} 天")
    for t in trend[:5]:
        print(f"  - {t.get('date')}: ${t.get('daily_gmv', 0):,.2f}")
    
    db.close()


if __name__ == "__main__":
    main()