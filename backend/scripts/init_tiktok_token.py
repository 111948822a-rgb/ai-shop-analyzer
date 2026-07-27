import logging
import sys
import os
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tk_token_manager import exchange_auth_code, get_token_status, get_access_token
from app.adapters.tiktok_shop import sync_tiktok_data
from app.services.report_generator import generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AUTH_CALLBACK_URL = "https://www.hitechasia.top/?app_key=6ko1408lr2817&code=ROW_cVSE_wAAAABrwJNUsB-xdeUyijP_4FDdDPGcZ8atHaHMmqXcGzZ7rDTOOpR1dLYYYQHFCze6bGqrCUX7t76hv79aopQTlFKOHnHJjdtMXi_fWOLyjvlH-f-XKFoFSh6BMiqCQ83dPasizRRnx-C37cEOa2TaJ5Ai09Pdi20xPE_vqRjLK5cb_A&locale=zh-CN&shop_region=TH"


def extract_auth_code_from_url(url: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    return query_params.get("code", [None])[0]


def main():
    logger.info("=" * 60)
    logger.info("TikTok Token 初始化与数据拉取测试")
    logger.info("=" * 60)

    auth_code = extract_auth_code_from_url(AUTH_CALLBACK_URL)
    if not auth_code:
        logger.error("无法从授权回调 URL 中提取 auth_code")
        sys.exit(1)

    logger.info(f"提取到 auth_code: {auth_code[:20]}...")

    logger.info("\n--- 步骤 1: 使用 auth_code 换取 Access Token ---")
    success = exchange_auth_code(auth_code)
    if not success:
        logger.error("Token 换取失败，请检查 TikTok 服务商配置")
        sys.exit(1)

    logger.info("\n--- 步骤 2: 验证 Token 状态 ---")
    token_status = get_token_status()
    logger.info(f"Token 状态: {token_status}")

    access_token = get_access_token()
    if not access_token:
        logger.error("获取 access_token 失败")
        sys.exit(1)

    logger.info(f"获取到 access_token: {access_token[:20]}...")

    logger.info("\n--- 步骤 3: 拉取 TikTok 真实数据 ---")
    try:
        sync_result = sync_tiktok_data()
        logger.info(f"数据同步结果: {sync_result}")
    except Exception as e:
        logger.error(f"数据同步失败: {e}")

    logger.info("\n--- 步骤 4: 生成周报 ---")
    try:
        report = generate_report(report_type="weekly")
        logger.info(f"周报生成成功! report_id: {report.get('report_id')}")
        logger.info(f"报告状态: {report.get('status')}")
        if report.get('report_data'):
            logger.info("\n--- AI 生成的周报内容 ---")
            print(report.get('report_data'))
            logger.info("--- 周报内容结束 ---")
    except Exception as e:
        logger.error(f"周报生成失败: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
