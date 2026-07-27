import logging
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tk_token_manager import get_token_status, get_access_token, validate_and_refresh
from app.adapters.tiktok_shop import sync_tiktok_data, get_tiktok_order_count, get_tiktok_product_count, get_tiktok_creator_count
from app.services.report_generator import generate_report, get_report_by_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_report(report):
    report_id = report.get('report_id')
    print("\n" + "=" * 70)
    print(f"📊 {report.get('report_title', '分析报告')}")
    print("=" * 70)
    
    print(f"\n📅 报告周期: {report.get('period', '')}")
    print(f"📝 报告类型: {report.get('report_type', '')}")
    print(f"🕐 生成时间: {report.get('generated_at', '')}")
    
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
            print(f"  {i}. {product.get('product_name', '')[:30]}...")
            print(f"     销售额: {product.get('total_sales', 0):,.2f}, 订单数: {product.get('total_orders', 0)}")
    
    product_black_list = report.get('product_black_list', [])
    if product_black_list:
        print(f"\n--- ❌ 商品黑榜 ---")
        for product in product_black_list:
            print(f"  • {product.get('product_name', '')[:30]}...")
            print(f"     销售额: {product.get('total_sales', 0):,.2f}")
    
    influencer_red_list = report.get('influencer_red_list', [])
    if influencer_red_list:
        print(f"\n--- ✅ 达人红榜 (Top 5) ---")
        for i, inf in enumerate(influencer_red_list[:5], 1):
            print(f"  {i}. {inf.get('influencer_name', '')}")
            print(f"     销售额: {inf.get('total_sales', 0):,.2f}, ROI: {inf.get('roi', 0):,.2f}")
    
    influencer_black_list = report.get('influencer_black_list', [])
    if influencer_black_list:
        print(f"\n--- 🚨 达人黑榜 (疑似水军) ---")
        for inf in influencer_black_list:
            print(f"  • {inf.get('influencer_name', '')}")
            print(f"     互动率: {(inf.get('engagement_rate', 0)*100):.2f}%, 转化率: {(inf.get('conversion_rate', 0)*100):.2f}%")
            if inf.get('risk_reason'):
                print(f"     风险原因: {inf.get('risk_reason')}")
    
    site_breakdown = report.get('site_breakdown', [])
    if site_breakdown:
        print(f"\n--- 🌍 跨站点分析 ---")
        for site in site_breakdown:
            print(f"  • {site.get('site_code', '')} ({site.get('currency', '')}):")
            print(f"     GMV: {site.get('total_gmv', 0):,.2f}, 订单数: {site.get('total_orders', 0)}")
    
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
    
    print("\n" + "=" * 70)


def main():
    logger.info("=" * 60)
    logger.info("TikTok 真实数据拉取与周报生成测试")
    logger.info("=" * 60)

    logger.info("\n--- 步骤 1: 检查现有 Token 状态 ---")
    token_status = get_token_status()
    logger.info(f"Token 状态: {token_status}")

    logger.info("\n--- 步骤 2: 获取并验证 Access Token ---")
    token = validate_and_refresh()
    if not token:
        logger.error("无法获取有效的 access_token，请确认 TikTok 服务商配置")
        sys.exit(1)

    logger.info(f"获取到 access_token: {token[:20]}...")

    logger.info("\n--- 步骤 3: 拉取 TikTok 真实数据 ---")
    try:
        sync_result = sync_tiktok_data()
        logger.info(f"数据同步结果:")
        logger.info(f"  订单: 拉取 {sync_result['orders']['total_fetched']} 条, 插入 {sync_result['orders']['inserted']} 条, 更新 {sync_result['orders']['updated']} 条")
        logger.info(f"  商品: 拉取 {sync_result['products']['total_fetched']} 条, 插入 {sync_result['products']['inserted']} 条, 更新 {sync_result['products']['updated']} 条")
        logger.info(f"  达人: 拉取 {sync_result['creators']['total_fetched']} 条, 插入 {sync_result['creators']['inserted']} 条, 更新 {sync_result['creators']['updated']} 条")
    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n--- 步骤 4: 检查数据库数据量 ---")
    order_count = get_tiktok_order_count()
    product_count = get_tiktok_product_count()
    creator_count = get_tiktok_creator_count()
    logger.info(f"数据库中订单数: {order_count}")
    logger.info(f"数据库中商品数: {product_count}")
    logger.info(f"数据库中达人数: {creator_count}")

    logger.info("\n--- 步骤 5: 生成周报 ---")
    try:
        report = generate_report(report_type="weekly")
        logger.info(f"周报生成成功! report_id: {report.get('report_id')}")
        
        print_report(report)
        
    except Exception as e:
        logger.error(f"周报生成失败: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n" + "=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
