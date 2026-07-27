import sys
import os
import urllib.parse

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.services.tk_token_manager import exchange_auth_code, get_token_status, get_access_token
from app.adapters.tiktok_shop import sync_tiktok_data, get_tiktok_order_count, get_tiktok_product_count, get_tiktok_creator_count
from app.services.report_generator import generate_report


def extract_auth_code_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    return params.get("code", [""])[0]


def main():
    print("=" * 80)
    print("TikTok Token 自动换取与数据拉取测试")
    print("=" * 80)

    print(f"\n[Step 1] 验证 Token 状态...")
    status = get_token_status()
    print(f"  - has_access_token: {status['has_access_token']}")
    print(f"  - has_refresh_token: {status['has_refresh_token']}")
    print(f"  - expires_at: {status['expires_at']}")
    print(f"  - remaining_hours: {status.get('remaining_hours', 0):.1f}")
    print(f"  - is_expiring_soon: {status['is_expiring_soon']}")

    token = get_access_token()
    print(f"  - 当前 access_token: {token[:20]}..." if token else "  - 无有效 access_token")

    print(f"\n[Step 2] 开始同步 TikTok 真实数据...")
    try:
        result = sync_tiktok_data()
        print(f"\n同步结果：")
        print(f"  - 订单: 抓取 {result['orders']['total_fetched']} 条, 新增 {result['orders']['inserted']} 条, 更新 {result['orders']['updated']} 条")
        print(f"  - 商品: 抓取 {result['products']['total_fetched']} 条, 新增 {result['products']['inserted']} 条, 更新 {result['products']['updated']} 条")
        print(f"  - 达人: 抓取 {result['creators']['total_fetched']} 条, 新增 {result['creators']['inserted']} 条, 更新 {result['creators']['updated']} 条")
    except Exception as e:
        print(f"❌ 数据同步失败: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n[Step 3] 数据库统计...")
    print(f"  - 订单总数: {get_tiktok_order_count()}")
    print(f"  - 商品总数: {get_tiktok_product_count()}")
    print(f"  - 达人总数: {get_tiktok_creator_count()}")

    print(f"\n[Step 4] 生成周报...")
    try:
        report = generate_report(report_type="weekly")
        print(f"\n周报生成成功！")
        print(f"  - report_id: {report.get('report_id')}")
        
        report_data = report.get("report_data", {})
        if report_data:
            print(f"\n📊 核心业绩概览:")
            core_summary = report_data.get("core_summary", {})
            print(f"  - 总GMV: {core_summary.get('total_gmv', 0)}")
            print(f"  - 订单数: {core_summary.get('total_orders', 0)}")
            print(f"  - 客单价: {core_summary.get('avg_order_value', 0)}")
            
            print(f"\n🏆 商品红榜 (Top 5):")
            for idx, product in enumerate(report_data.get("product_red_list", []), 1):
                print(f"  {idx}. {product.get('product_name', '')} - 销售额: {product.get('total_sales', 0)}")
            
            print(f"\n🚨 达人预警:")
            for idx, influencer in enumerate(report_data.get("influencer_black_list", []), 1):
                print(f"  {idx}. {influencer.get('influencer_name', '')} - 互动率: {influencer.get('engagement_rate', 0):.2%}, 转化率: {influencer.get('conversion_rate', 0):.2%}")
    except Exception as e:
        print(f"❌ 周报生成失败: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
