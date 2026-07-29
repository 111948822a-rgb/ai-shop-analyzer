import logging
import time
from typing import List, Dict, Any, Optional

import requests

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.standard import StandardInfluencer

logger = logging.getLogger(__name__)

SITE_CODE_MAP = {
    "US": "US",
    "TH": "TH",
    "MY": "MY",
    "us": "US",
    "th": "TH",
    "my": "MY",
}

LANGUAGE_MAP = {
    "en": "en",
    "th": "th",
    "id": "id",
    "English": "en",
    "Thai": "th",
    "Indonesian": "id",
}


def _is_html_response(content: str) -> bool:
    lower_content = content.lower().strip()
    return lower_content.startswith("<!doctype") or \
           lower_content.startswith("<html") or \
           lower_content.startswith("<head") or \
           lower_content.startswith("<body")


def _to_number(val: Any, cast: type = int) -> Any:
    """将秒搭可能返回的字符串数字（含 1,200 / 12.3k / 3.4m / 末尾 %）安全转为数字。

    无法解析时返回 0，绝不抛异常，保证整条数据管道不中断。
    """
    if val is None or val == "":
        return 0
    mult = 1
    if isinstance(val, str):
        s = val.strip().replace(",", "").replace("%", "")
        low = s.lower()
        if low.endswith("k"):
            s, mult = s[:-1], 1_000
        elif low.endswith("m"):
            s, mult = s[:-1], 1_000_000
        try:
            return cast(float(s) * mult)
        except ValueError:
            return 0
    try:
        return cast(float(val) * mult)
    except (ValueError, TypeError):
        return 0


def fetch_influencers_from_miaoda(
    site_id: Optional[str] = None,
    platform_id: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.MIAODA_API_KEY or not settings.MIAODA_API_URL:
        logger.error("MIAODA_API_KEY or MIAODA_API_URL is not configured")
        return []

    all_influencers = []
    page = 1
    page_size = 100
    retry_count = 0
    last_error = None

    while True:
        if retry_count >= max_retries:
            logger.error(f"Max retries ({max_retries}) reached, stopping fetch")
            break

        try:
            # 秒搭契约：MIAODA_API_URL 本身即完整地址 https://<域名>/openapi/influencers
            # 这里兼容「只填域名」的写法，避免重复拼接路径。
            base = settings.MIAODA_API_URL.rstrip("/")
            url = base if base.endswith("/openapi/influencers") else f"{base}/openapi/influencers"
            headers = {"X-API-Key": settings.MIAODA_API_KEY}
            params = {"page": page, "pageSize": page_size}

            if site_id:
                params["siteId"] = site_id
            if platform_id:
                params["platformId"] = platform_id
            if status:
                params["status"] = status
            if keyword:
                params["keyword"] = keyword
            if category:
                params["category"] = category

            logger.info(f"Fetching page {page} from Miaoda API...")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            content = response.text

            if _is_html_response(content):
                last_error = f"秒搭返回 HTML 而非 JSON（多为未授权或路径错误）: {content[:200]}"
                logger.error(f"API returned HTML response instead of JSON. URL: {url}")
                logger.error(f"HTML content preview: {content[:500]}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying... ({retry_count}/{max_retries})")
                    time.sleep(2 ** retry_count)
                continue

            try:
                data = response.json()
            except ValueError as e:
                last_error = f"秒搭返回非 JSON: {content[:200]}"
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {content[:500]}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying... ({retry_count}/{max_retries})")
                    time.sleep(2 ** retry_count)
                continue

            items = data.get("items", [])
            total = data.get("total", 0)

            logger.info(f"Page {page}: fetched {len(items)} items, total {total}")
            all_influencers.extend(items)

            retry_count = 0

            if len(all_influencers) >= total:
                break

            if not items:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            last_error = f"请求秒搭失败: {e}"
            logger.error(f"Failed to fetch page {page}: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying after network error... ({retry_count}/{max_retries})")
                time.sleep(2 ** retry_count)
                continue
            break

    if not all_influencers and last_error:
        # 拉取失败（非「无数据」），抛出以便上层向前端暴露真实原因
        raise RuntimeError(last_error)
    return all_influencers


def map_influencer_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "influencer_id": raw_data.get("influencer_id") or raw_data.get("id") or raw_data.get("uid"),
        "site_code": SITE_CODE_MAP.get(raw_data.get("site_code") or raw_data.get("site") or raw_data.get("country"), "US"),
        "platform": raw_data.get("platform") or raw_data.get("channel") or "TikTok",
        "influencer_name": raw_data.get("name") or raw_data.get("username") or raw_data.get("nickname") or "Unknown",
        "avatar_url": raw_data.get("avatar") or raw_data.get("avatar_url") or raw_data.get("profile_picture") or "",
        "follower_count": _to_number(raw_data.get("followers") or raw_data.get("follower_count") or raw_data.get("fans")),
        "engagement_rate": _to_number(raw_data.get("engagement_rate") or raw_data.get("engagement")),
        "conversion_rate": _to_number(raw_data.get("conversion_rate") or raw_data.get("conversion")),
        "roi": _to_number(raw_data.get("roi") or raw_data.get("return_on_investment")),
        "is_suspicious": bool(raw_data.get("is_suspicious") or raw_data.get("suspicious") or False),
        "suspicious_reason": raw_data.get("suspicious_reason") or raw_data.get("risk_reason") or "",
        "country": raw_data.get("country") or raw_data.get("region") or "",
        "language": LANGUAGE_MAP.get(raw_data.get("language") or raw_data.get("lang"), "en"),
        "niche": raw_data.get("niche") or raw_data.get("category") or raw_data.get("vertical") or "General",
        "total_posts": _to_number(raw_data.get("total_posts") or raw_data.get("posts") or raw_data.get("content_count")),
        "avg_likes": _to_number(raw_data.get("avg_likes") or raw_data.get("average_likes") or raw_data.get("likes")),
        "avg_comments": _to_number(raw_data.get("avg_comments") or raw_data.get("average_comments") or raw_data.get("comments")),
        "avg_shares": _to_number(raw_data.get("avg_shares") or raw_data.get("average_shares") or raw_data.get("shares")),
    }


def sync_influencers_from_miaoda(site_id: Optional[str] = None) -> Dict[str, int]:
    db = SessionLocal()
    try:
        raw_influencers = fetch_influencers_from_miaoda(site_id)

        if not raw_influencers:
            logger.warning("No influencers fetched from Miaoda API")
            return {"total_fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

        inserted = 0
        updated = 0
        skipped = 0

        for raw_data in raw_influencers:
            mapped_data = map_influencer_data(raw_data)
            influencer_id = mapped_data.get("influencer_id")

            if not influencer_id:
                skipped += 1
                continue

            existing = db.query(StandardInfluencer).filter(
                StandardInfluencer.influencer_id == influencer_id
            ).first()

            if existing:
                for key, value in mapped_data.items():
                    if key != "influencer_id":
                        setattr(existing, key, value)
                updated += 1
            else:
                influencer = StandardInfluencer(**mapped_data)
                db.add(influencer)
                inserted += 1

            if (inserted + updated) % 50 == 0:
                db.commit()
                logger.info(f"Committed {inserted + updated} records...")

        db.commit()

        logger.info(f"Sync completed: fetched={len(raw_influencers)}, inserted={inserted}, updated={updated}, skipped={skipped}")

        return {
            "total_fetched": len(raw_influencers),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Sync failed: {e}")
        raise
    finally:
        db.close()


def get_influencers_count() -> int:
    db = SessionLocal()
    try:
        return db.query(StandardInfluencer).count()
    finally:
        db.close()


def get_suspicious_influencers_count() -> int:
    db = SessionLocal()
    try:
        return db.query(StandardInfluencer).filter(
            StandardInfluencer.is_suspicious == True
        ).count()
    finally:
        db.close()