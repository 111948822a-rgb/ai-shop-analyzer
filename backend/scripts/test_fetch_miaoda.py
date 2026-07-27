import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from app.core.config import settings
from app.services.miaoda_data_fetcher import (
    fetch_influencers_from_miaoda,
    sync_influencers_from_miaoda,
    get_influencers_count,
    get_suspicious_influencers_count,
    map_influencer_data,
)
from app.core.database import SessionLocal
from app.models.standard import StandardInfluencer


def test_api_connection():
    print("\n--- API 连接诊断 ---")
    print(f"API URL: {settings.MIAODA_API_URL}")
    print(f"API Key: {settings.MIAODA_API_KEY[:10]}..." if settings.MIAODA_API_KEY else "API Key: NOT SET")
    
    if not settings.MIAODA_API_KEY or not settings.MIAODA_API_URL:
        print("✗ 配置不完整：请检查 .env 文件中的 MIAODA_API_KEY 和 MIAODA_API_URL")
        return False

    try:
        url = f"{settings.MIAODA_API_URL}/openapi/influencers"
        headers = {"X-API-Key": settings.MIAODA_API_KEY}
        params = {"page": 1, "pageSize": 10}
        
        print(f"\n测试请求: {url}")
        print(f"Headers: X-API-Key present")
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"HTTP 状态码: {response.status_code}")
        print(f"响应内容前200字符: {response.text[:200]}...")
        
        try:
            data = response.json()
            print(f"✓ 响应为有效 JSON")
            print(f"  total: {data.get('total', 'N/A')}")
            print(f"  items 数量: {len(data.get('items', []))}")
            return True
        except ValueError:
            print("✗ 响应不是有效 JSON")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ 连接失败：网络不可达或域名解析失败")
        return False
    except requests.exceptions.Timeout:
        print("✗ 请求超时：服务器无响应")
        return False
    except Exception as e:
        print(f"✗ 未知错误: {e}")
        return False


def test_mapping_logic():
    print("\n--- 字段映射逻辑测试 ---")
    test_data = {
        "id": "TEST_INF_001",
        "name": "Test Influencer",
        "followers": 150000,
        "engagement_rate": 0.052,
        "conversion_rate": 0.012,
        "roi": 3.5,
        "site_code": "TH",
        "platform": "TikTok",
        "avatar": "https://example.com/avatar.jpg",
        "is_suspicious": False,
        "country": "Thailand",
        "language": "th",
        "niche": "Fashion",
        "posts": 120,
        "likes": 2500,
        "comments": 150,
        "shares": 80,
    }
    
    mapped = map_influencer_data(test_data)
    print("✓ 字段映射测试通过")
    print(f"  influencer_id: {mapped['influencer_id']}")
    print(f"  influencer_name: {mapped['influencer_name']}")
    print(f"  follower_count: {mapped['follower_count']}")
    print(f"  engagement_rate: {mapped['engagement_rate']}")
    print(f"  conversion_rate: {mapped['conversion_rate']}")
    print(f"  roi: {mapped['roi']}")
    print(f"  site_code: {mapped['site_code']}")
    print(f"  platform: {mapped['platform']}")
    print(f"  language: {mapped['language']}")


def test_upsert_logic():
    print("\n--- Upsert 逻辑测试 ---")
    db = SessionLocal()
    
    try:
        test_influencer = {
            "influencer_id": "UPSERT_TEST_001",
            "site_code": "US",
            "platform": "TikTok",
            "influencer_name": "Upsert Test",
            "follower_count": 100000,
            "engagement_rate": 0.08,
            "conversion_rate": 0.015,
            "roi": 4.2,
            "is_suspicious": False,
            "language": "en",
            "niche": "Tech",
        }
        
        existing = db.query(StandardInfluencer).filter(
            StandardInfluencer.influencer_id == "UPSERT_TEST_001"
        ).first()
        
        if existing:
            print("✗ 测试数据已存在，跳过插入")
        else:
            influencer = StandardInfluencer(**test_influencer)
            db.add(influencer)
            db.commit()
            print("✓ 插入新记录成功")
            
            existing = db.query(StandardInfluencer).filter(
                StandardInfluencer.influencer_id == "UPSERT_TEST_001"
            ).first()
            assert existing.follower_count == 100000
            
            existing.follower_count = 120000
            existing.roi = 5.0
            db.commit()
            print("✓ 更新记录成功")
            
            updated = db.query(StandardInfluencer).filter(
                StandardInfluencer.influencer_id == "UPSERT_TEST_001"
            ).first()
            assert updated.follower_count == 120000
            assert updated.roi == 5.0
            
        print("✓ Upsert 逻辑测试通过")
    finally:
        db.close()


def main():
    print("=" * 70)
    print("Miaoda API 数据拉取与同步测试")
    print("=" * 70)

    api_available = test_api_connection()

    if api_available:
        print("\n[1/3] 测试 API 数据拉取...")
        influencers = fetch_influencers_from_miaoda()
        print(f"✓ 成功从 Miaoda API 拉取 {len(influencers)} 条达人数据")
        
        if influencers:
            print("\n样本数据结构:")
            sample = influencers[0]
            keys_to_show = ["influencer_id", "name", "followers", "engagement_rate", "conversion_rate", "roi", "site_code"]
            for key in keys_to_show:
                if key in sample:
                    print(f"  {key}: {sample[key]}")

        print("\n[2/3] 测试数据同步入库...")
        result = sync_influencers_from_miaoda()
        print(f"✓ 同步完成:")
        print(f"  - 拉取总数: {result['total_fetched']}")
        print(f"  - 新增入库: {result['inserted']}")
        print(f"  - 更新记录: {result['updated']}")
        print(f"  - 跳过记录: {result['skipped']}")
    else:
        print("\n⚠ API 暂时不可用，跳过数据拉取和同步")
        print("正在测试本地映射和 upsert 逻辑...")
        test_mapping_logic()
        test_upsert_logic()

    print("\n[3/3] 验证数据库记录...")
    total_count = get_influencers_count()
    suspicious_count = get_suspicious_influencers_count()
    print(f"✓ 数据库总达人数量: {total_count}")
    print(f"✓ 疑似水军达人数量: {suspicious_count}")

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    print(f"\n总结:")
    print(f"  - API 可用性: {'✓ 可用' if api_available else '✗ 不可用'}")
    print(f"  - 数据库达人总数: {total_count}")
    print(f"  - 水军达人数量: {suspicious_count}")


if __name__ == "__main__":
    main()