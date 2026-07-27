import logging
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.report_generator import generate_report, get_weekly_date_range
from app.services.tk_token_manager import get_access_token
from app.adapters.tiktok_shop import get_tiktok_order_count, get_tiktok_product_count
from app.services.miaoda_data_fetcher import get_influencers_count

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_report(report):
    report_id = report.get('report_id')
    print("\n" + "=" * 80)
    print(f"📊 {report.get('report_title', '分析报告')}")
    print("=" * 80)
    
    print(f"\n📅 报告周期: {report.get('period', '')}")
    print(f"📝 报告类型: {report.get('report_type', '')}")
    print(f"🕐 生成时间: {report.get('generated_at', '')}")
    print(f"🆔 报告ID: {report_id}")
    
    core_summary = report.get('core_summary', {})
    print(f"\n--- 📈 核心业绩概览 ---")
    print(f"  总GMV: {core_summary.get('total_gmv', 0):,.2f}")
    print(f"  订单数: {core_summary.get('total_orders', 0):,}")
    print(f"  客单价: {core_summary.get('avg_order_value', 0):,.2f}")
    if core_summary.get('gmv_growth'):
        print(f"  GMV同比: {core_summary.get('gmv_growth'):.2f}%")
    if core_summary.get('order_growth'):
        print(f"  订单同比: {core_summary.get('order_growth'):.2f}%")
    
    product_red_list = report.get('product_red_list', [])
    if product_red_list:
        print(f"\n--- 🔥 商品红榜 (Top 5) ---")
        for i, product in enumerate(product_red_list[:5], 1):
            name = product.get('product_name', '')[:40] + '...' if len(product.get('product_name', '')) > 40 else product.get('product_name', '')
            print(f"  {i}. {name}")
            print(f"     销售额: {product.get('total_sales', 0):,.2f}, 订单数: {product.get('total_orders', 0)}, 单价: {product.get('price', 0):,.2f}")
    
    product_black_list = report.get('product_black_list', [])
    if product_black_list:
        print(f"\n--- ❌ 商品黑榜 ---")
        for product in product_black_list:
            name = product.get('product_name', '')[:40] + '...' if len(product.get('product_name', '')) > 40 else product.get('product_name', '')
            print(f"  • {name}")
            print(f"     销售额: {product.get('total_sales', 0):,.2f}")
    
    influencer_red_list = report.get('influencer_red_list', [])
    if influencer_red_list:
        print(f"\n--- ✅ 达人红榜 (Top 5) ---")
        for i, inf in enumerate(influencer_red_list[:5], 1):
            print(f"  {i}. {inf.get('influencer_name', '')}")
            print(f"     销售额: {inf.get('total_sales', 0):,.2f}, ROI: {inf.get('roi', 0):,.2f}, 粉丝数: {inf.get('follower_count', 0):,}")
    
    influencer_black_list = report.get('influencer_black_list', [])
    if influencer_black_list:
        print(f"\n--- 🚨 达人黑榜 (疑似水军) ---")
        for inf in influencer_black_list:
            print(f"  • {inf.get('influencer_name', '')}")
            print(f"     互动率: {(inf.get('engagement_rate', 0)*100):.2f}%, 转化率: {(inf.get('conversion_rate', 0)*100):.2f}%, 粉丝数: {inf.get('follower_count', 0):,}")
            if inf.get('risk_reason'):
                print(f"     风险原因: {inf.get('risk_reason')}")
    
    site_breakdown = report.get('site_breakdown', [])
    if site_breakdown:
        print(f"\n--- 🌍 跨站点分析 ---")
        for site in site_breakdown:
            print(f"  • {site.get('site_code', '')} ({site.get('currency', '')}):")
            print(f"     GMV: {site.get('total_gmv', 0):,.2f}, 订单数: {site.get('total_orders', 0)}, 客单价: {site.get('avg_order_value', 0):,.2f}")
    
    trend_analysis = report.get('trend_analysis', '')
    if trend_analysis:
        print(f"\n--- 📉 销售趋势分析 ---")
        print(f"  {trend_analysis}")
    
    anomaly_analysis = report.get('anomaly_analysis', '')
    if anomaly_analysis:
        print(f"\n--- 🔍 异动归因分析 ---")
        print(f"  {anomaly_analysis}")
    
    action_suggestions = report.get('action_suggestions', [])
    if action_suggestions:
        print(f"\n--- 💡 下一步行动建议 ---")
        for i, suggestion in enumerate(action_suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    print("\n" + "=" * 80)


def main():
    logger.info("=" * 60)
    logger.info("生成最终真实数据融合报告")
    logger.info("=" * 60)

    token = get_access_token()
    if not token:
        logger.error("无法获取 access_token")
        sys.exit(1)

    order_count = get_tiktok_order_count()
    product_count = get_tiktok_product_count()
    influencer_count = get_influencers_count()
    
    logger.info(f"\n数据库数据概览:")
    logger.info(f"  订单数: {order_count}")
    logger.info(f"  商品数: {product_count}")
    logger.info(f"  达人数: {influencer_count}")
    
    date_range = get_weekly_date_range()
    logger.info(f"报告日期范围: {date_range['start']} ~ {date_range['end']}")

    logger.info("\n--- 生成 AI 周报 ---")
    report = generate_report(report_type="weekly")
    logger.info(f"周报生成成功! report_id: {report.get('report_id')}")
    
    print_report(report)

    logger.info("\n" + "=" * 60)
    logger.info("报告打印完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
