from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class StandardOrder(Base):
    __tablename__ = "standard_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(64), unique=True, index=True)
    site_code = Column(String(8), index=True)
    currency = Column(String(8))
    product_id = Column(String(64), ForeignKey("standard_products.product_id"))
    influencer_id = Column(String(64), ForeignKey("standard_influencers.influencer_id"))
    order_amount = Column(Float)
    order_amount_local = Column(Float)
    quantity = Column(Integer)
    order_status = Column(String(32))
    order_date = Column(DateTime)
    customer_id = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("StandardProduct", back_populates="orders")
    influencer = relationship("StandardInfluencer", back_populates="orders")


class StandardProduct(Base):
    __tablename__ = "standard_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(64), unique=True, index=True)
    site_code = Column(String(8), index=True)
    currency = Column(String(8))
    product_name = Column(String(512))
    product_category = Column(String(128))
    product_price = Column(Float)
    product_price_local = Column(Float)
    stock_quantity = Column(Integer)
    sales_volume = Column(Integer)
    rating = Column(Float)
    review_count = Column(Integer)
    image_url = Column(String(512))
    brand = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("StandardOrder", back_populates="product")
    influencers = relationship(
        "StandardInfluencer", secondary="product_influencer_association", back_populates="products"
    )


class StandardInfluencer(Base):
    __tablename__ = "standard_influencers"

    id = Column(Integer, primary_key=True, index=True)
    influencer_id = Column(String(64), unique=True, index=True)
    site_code = Column(String(8), index=True)
    platform = Column(String(32))
    influencer_name = Column(String(256))
    avatar_url = Column(String(512))
    follower_count = Column(Integer)
    engagement_rate = Column(Float)
    conversion_rate = Column(Float)
    roi = Column(Float)
    is_suspicious = Column(Boolean, default=False)
    suspicious_reason = Column(Text)
    country = Column(String(32))
    language = Column(String(16))
    niche = Column(String(128))
    total_posts = Column(Integer)
    avg_likes = Column(Integer)
    avg_comments = Column(Integer)
    avg_shares = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("StandardOrder", back_populates="influencer")
    products = relationship(
        "StandardProduct", secondary="product_influencer_association", back_populates="influencers"
    )


class ProductInfluencerAssociation(Base):
    __tablename__ = "product_influencer_association"

    product_id = Column(String(64), ForeignKey("standard_products.product_id"), primary_key=True)
    influencer_id = Column(String(64), ForeignKey("standard_influencers.influencer_id"), primary_key=True)
    association_date = Column(DateTime, default=datetime.utcnow)
    campaign_name = Column(String(256))


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(64), unique=True, index=True)
    influencer_id = Column(String(64), ForeignKey("standard_influencers.influencer_id"))
    site_code = Column(String(8), index=True)
    status = Column(String(32), default="pending")
    analysis_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    influencer = relationship("StandardInfluencer")


class ReportRecord(Base):
    __tablename__ = "report_records"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True)
    report_type = Column(String(32), index=True)
    site_code = Column(String(8), index=True)
    status = Column(String(32), default="pending")
    report_data = Column(Text)
    start_date = Column(String(32))
    end_date = Column(String(32))
    generated_at = Column(DateTime, default=datetime.utcnow)

    @property
    def period(self) -> str:
        return f"{self.start_date} ~ {self.end_date}"