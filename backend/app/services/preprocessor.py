from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, desc, cast, Float
from sqlalchemy.orm import Session

from app.models.standard import StandardOrder, StandardProduct, StandardInfluencer


def get_sales_summary(db: Session, site_code: Optional[str] = None, date_range: Optional[Dict[str, str]] = None) -> Dict:
    query = db.query(
        func.sum(StandardOrder.order_amount).label("total_gmv"),
        func.count(StandardOrder.order_id).label("total_orders"),
        func.avg(StandardOrder.order_amount).label("avg_order_value"),
        func.sum(StandardOrder.quantity).label("total_units_sold"),
    )

    if site_code:
        query = query.filter(StandardOrder.site_code == site_code)

    if date_range:
        start_date = datetime.fromisoformat(date_range.get("start", ""))
        end_date = datetime.fromisoformat(date_range.get("end", ""))
        query = query.filter(StandardOrder.order_date.between(start_date, end_date))

    summary = query.first()

    top_products = db.query(
        StandardProduct.product_id,
        StandardProduct.product_name,
        func.sum(StandardOrder.order_amount).label("product_gmv"),
        func.count(StandardOrder.order_id).label("product_orders"),
    ).join(StandardOrder)

    if site_code:
        top_products = top_products.filter(StandardProduct.site_code == site_code)

    if date_range:
        top_products = top_products.filter(StandardOrder.order_date.between(start_date, end_date))

    top_products = top_products.group_by(
        StandardProduct.product_id, StandardProduct.product_name
    ).order_by(desc("product_gmv")).limit(5).all()

    return {
        "total_gmv": round(summary.total_gmv or 0, 2),
        "total_orders": summary.total_orders or 0,
        "avg_order_value": round(summary.avg_order_value or 0, 2),
        "total_units_sold": summary.total_units_sold or 0,
        "top_products": [
            {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "gmv": round(p.product_gmv or 0, 2),
                "orders": p.product_orders or 0,
            }
            for p in top_products
        ],
        "site_code": site_code or "all",
        "date_range": date_range or {},
    }


def get_influencer_metrics(db: Session, platform: Optional[str] = None, site_code: Optional[str] = None) -> List[Dict]:
    query = db.query(
        StandardInfluencer.influencer_id,
        StandardInfluencer.influencer_name,
        StandardInfluencer.platform,
        StandardInfluencer.site_code,
        StandardInfluencer.follower_count,
        StandardInfluencer.engagement_rate,
        StandardInfluencer.conversion_rate,
        StandardInfluencer.roi,
        StandardInfluencer.is_suspicious,
        StandardInfluencer.suspicious_reason,
        StandardInfluencer.niche,
        StandardInfluencer.country,
        StandardInfluencer.language,
    )

    if platform:
        query = query.filter(StandardInfluencer.platform == platform)

    if site_code:
        query = query.filter(StandardInfluencer.site_code == site_code)

    influencers = query.all()

    return [
        {
            "influencer_id": i.influencer_id,
            "influencer_name": i.influencer_name,
            "platform": i.platform,
            "site_code": i.site_code,
            "follower_count": i.follower_count,
            "engagement_rate": round(i.engagement_rate, 4) if i.engagement_rate else 0,
            "conversion_rate": round(i.conversion_rate, 4) if i.conversion_rate else 0,
            "roi": round(i.roi, 2) if i.roi else 0,
            "is_suspicious": i.is_suspicious,
            "suspicious_reason": i.suspicious_reason,
            "niche": i.niche,
            "country": i.country,
            "language": i.language,
        }
        for i in influencers
    ]


def get_influencer_orders_summary(db: Session, influencer_id: str, date_range: Optional[Dict[str, str]] = None) -> Dict:
    query = db.query(
        func.sum(StandardOrder.order_amount).label("total_sales"),
        func.count(StandardOrder.order_id).label("total_orders"),
        func.avg(StandardOrder.order_amount).label("avg_order_value"),
        func.sum(StandardOrder.quantity).label("total_units"),
    ).filter(StandardOrder.influencer_id == influencer_id)

    if date_range:
        start_date = datetime.fromisoformat(date_range.get("start", ""))
        end_date = datetime.fromisoformat(date_range.get("end", ""))
        query = query.filter(StandardOrder.order_date.between(start_date, end_date))

    summary = query.first()

    return {
        "influencer_id": influencer_id,
        "total_sales": round(summary.total_sales or 0, 2),
        "total_orders": summary.total_orders or 0,
        "avg_order_value": round(summary.avg_order_value or 0, 2),
        "total_units": summary.total_units or 0,
        "date_range": date_range or {},
    }


def get_influencer_by_id(db: Session, influencer_id: str) -> Optional[Dict]:
    influencer = db.query(StandardInfluencer).filter(
        StandardInfluencer.influencer_id == influencer_id
    ).first()

    if not influencer:
        return None

    return {
        "influencer_id": influencer.influencer_id,
        "influencer_name": influencer.influencer_name,
        "platform": influencer.platform,
        "site_code": influencer.site_code,
        "follower_count": influencer.follower_count,
        "engagement_rate": round(influencer.engagement_rate, 4) if influencer.engagement_rate else 0,
        "conversion_rate": round(influencer.conversion_rate, 4) if influencer.conversion_rate else 0,
        "roi": round(influencer.roi, 2) if influencer.roi else 0,
        "is_suspicious": influencer.is_suspicious,
        "suspicious_reason": influencer.suspicious_reason,
        "niche": influencer.niche,
        "country": influencer.country,
        "language": influencer.language,
        "total_posts": influencer.total_posts,
        "avg_likes": influencer.avg_likes,
        "avg_comments": influencer.avg_comments,
        "avg_shares": influencer.avg_shares,
        "avatar_url": influencer.avatar_url,
    }


def get_top_suspicious_influencers(db: Session, site_code: Optional[str] = None, limit: int = 10) -> List[Dict]:
    query = db.query(
        StandardInfluencer.influencer_id,
        StandardInfluencer.influencer_name,
        StandardInfluencer.platform,
        StandardInfluencer.site_code,
        StandardInfluencer.follower_count,
        StandardInfluencer.engagement_rate,
        StandardInfluencer.conversion_rate,
        StandardInfluencer.suspicious_reason,
    ).filter(StandardInfluencer.is_suspicious == True)

    if site_code:
        query = query.filter(StandardInfluencer.site_code == site_code)

    influencers = query.order_by(desc(StandardInfluencer.follower_count)).limit(limit).all()

    return [
        {
            "influencer_id": i.influencer_id,
            "influencer_name": i.influencer_name,
            "platform": i.platform,
            "site_code": i.site_code,
            "follower_count": i.follower_count,
            "engagement_rate": round(i.engagement_rate, 4) if i.engagement_rate else 0,
            "conversion_rate": round(i.conversion_rate, 4) if i.conversion_rate else 0,
            "suspicious_reason": i.suspicious_reason,
        }
        for i in influencers
    ]