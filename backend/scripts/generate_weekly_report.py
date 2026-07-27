import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.report_generator import generate_report, get_report_by_id, list_reports


def print_report(report_data: dict):
    print("\n" + "=" * 80)
    print(f"📊 {report_data.get('report_title', '分析报告')}")
    print("=" * 80)
    print(f"报告类型: {report_data.get('report_type', 'N/A')}")
    print(f"日期范围: {report_data.get('period', 'N/A')}")
    print(f"生成时间: {report_data.get('generated_at', 'N/A')}")
    print(f"报告ID: {report_data.get('report_id', 'N/A')}")

    print("\n" + "-" * 80)
    print("💰 核心业绩概览")
    print("-" * 80)
    core = report_data.get("core_summary", {})
    print(f"总GMV: ${core.get('total_gmv', 0):,.2f}")
    print(f"订单数: {core.get('total_orders', 0):,}")
    print(f"客单价: ${core.get('avg_order_value', 0):,.2f}")
    if core.get("gmv_growth") is not None:
        print(f"GMV增长率: {core['gmv_growth']:.2%}")
    if core.get("order_growth") is not None:
        print(f"订单增长率: {core['order_growth']:.2%}")

    print("\n" + "-" * 80)
    print("🏆 商品红榜 (Top 5 热销商品)")
    print("-" * 80)
    for i, product in enumerate(report_data.get("product_red_list", []), 1):
        print(f"\n{i}. {product.get('product_name', 'N/A')}")
        print(f"   分类: {product.get('category', 'N/A')}")
        print(f"   价格: ${product.get('price', 0):,.2f}")
        print(f"   销售额: ${product.get('total_sales', 0):,.2f}")
        print(f"   订单数: {product.get('total_orders', 0):,}")

    print("\n" + "-" * 80)
    print("⚠️ 商品黑榜 (表现不佳商品)")
    print("-" * 80)
    for i, product in enumerate(report_data.get("product_black_list", []), 1):
        print(f"\n{i}. {product.get('product_name', 'N/A')}")
        print(f"   销售额: ${product.get('total_sales', 0):,.2f}")
        print(f"   订单数: {product.get('total_orders', 0):,}")

    print("\n" + "-" * 80)
    print("✅ 达人红榜 (Top 5 优质达人)")
    print("-" * 80)
    for i, influencer in enumerate(report_data.get("influencer_red_list", []), 1):
        print(f"\n{i}. {influencer.get('influencer_name', 'N/A')}")
        print(f"   粉丝数: {influencer.get('follower_count', 0):,}")
        print(f"   互动率: {influencer.get('engagement_rate', 0):.2%}")
        print(f"   转化率: {influencer.get('conversion_rate', 0):.2%}")
        print(f"   ROI: {influencer.get('roi', 0):.2f}")
        print(f"   带货销售额: ${influencer.get('total_sales', 0):,.2f}")

    print("\n" + "-" * 80)
    print("🚨 达人黑榜 (疑似水军达人)")
    print("-" * 80)
    for i, influencer in enumerate(report_data.get("influencer_black_list", []), 1):
        print(f"\n{i}. {influencer.get('influencer_name', 'N/A')}")
        print(f"   粉丝数: {influencer.get('follower_count', 0):,}")
        print(f"   互动率: {influencer.get('engagement_rate', 0):.2%}")
        print(f"   转化率: {influencer.get('conversion_rate', 0):.2%}")
        print(f"   风险原因: {influencer.get('risk_reason', 'N/A')}")

    print("\n" + "-" * 80)
    print("🌍 跨站点分析")
    print("-" * 80)
    for site in report_data.get("site_breakdown", []):
        print(f"\n站点 {site.get('site_code', 'N/A')} ({site.get('currency', 'USD')}):")
        print(f"   GMV: ${site.get('total_gmv', 0):,.2f}")
        print(f"   订单数: {site.get('total_orders', 0):,}")
        print(f"   客单价: ${site.get('avg_order_value', 0):,.2f}")

    print("\n" + "-" * 80)
    print("📈 销售趋势分析")
    print("-" * 80)
    print(report_data.get("trend_analysis", "暂无分析数据"))

    print("\n" + "-" * 80)
    print("🔍 异动归因分析")
    print("-" * 80)
    print(report_data.get("anomaly_analysis", "暂无异动数据"))

    print("\n" + "-" * 80)
    print("💡 下一步行动建议")
    print("-" * 80)
    for i, suggestion in enumerate(report_data.get("action_suggestions", []), 1):
        print(f"\n{i}. {suggestion}")

    print("\n" + "=" * 80)


def main():
    print("=" * 80)
    print("AI Shop Analyzer - 周报生成测试")
    print("=" * 80)

    print("\n[1/2] 生成周报...")
    try:
        report_data = generate_report(report_type="weekly")
        print(f"✓ 周报生成成功!")
        print(f"  报告ID: {report_data.get('report_id')}")
        print(f"  日期范围: {report_data.get('period')}")

        print("\n[2/2] 打印报告内容...")
        print_report(report_data)

    except Exception as e:
        print(f"✗ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()