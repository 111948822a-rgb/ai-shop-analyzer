import os
import sys
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_db, SessionLocal
from app.models.standard import (
    StandardOrder, StandardProduct, StandardInfluencer,
    ProductInfluencerAssociation
)

SITE_CODES = ["US", "TH", "MY"]
CURRENCIES = {"US": "USD", "TH": "THB", "MY": "MYR"}
EXCHANGE_RATES = {"US": 1.0, "TH": 35.0, "MY": 4.5}
PLATFORMS = ["TikTok", "Shopee"]
PRODUCT_CATEGORIES = [
    "Electronics", "Fashion", "Beauty", "Home & Garden",
    "Sports & Outdoors", "Toys & Games", "Food & Beverages", "Health"
]
INFLUENCER_NICHES = [
    "Tech Review", "Fashion", "Beauty", "Fitness",
    "Cooking", "Travel", "Gaming", "Parenting", "Lifestyle"
]
COUNTRIES = {"US": "United States", "TH": "Thailand", "MY": "Malaysia"}
LANGUAGES = {"US": "en", "TH": "th", "MY": "id"}

PRODUCT_NAMES_EN = [
    "Wireless Bluetooth Headphones Pro",
    "Smart Watch Fitness Tracker",
    "Portable Power Bank 20000mAh",
    "LED Strip Lights RGB",
    "Phone Tripod Stand",
    "Waterproof Sports Camera",
    "Portable Blender",
    "Silicone Cooking Utensils Set",
    "Yoga Mat Non-Slip",
    "Travel Pillow Memory Foam",
]

PRODUCT_NAMES_TH = [
    "หูฟังบลูทูธไร้สาย Pro",
    "สมาร์ทวอชสุ่มติดตามการออกกำลังกาย",
    "พาวเวอร์แบงค์พกพา 20000mAh",
    "ไฟ LED สาย RGB",
    "ขาตั้งโทรศัพท์",
    "กล้องกีฬารักษ์น้ำ",
    "เครื่องปั่นน้ำพกพา",
    "ชุดเครื่องครัวซิลิโคน",
    "แผ่นโยคะกันลื่น",
    "หมอนท่องเที่ยวโฟมหน่วยความจำ",
]

PRODUCT_NAMES_MY = [
    "Headphones Bluetooth Tanpa Wayar Pro",
    "Jam Pintar Pengesan Kecergasan",
    "Bateri Boleh Bawa 20000mAh",
    "Lampu LED Strip RGB",
    "Stand Tripod Telefon",
    "Kamera Sukan Kalis Air",
    "Pengisar Boleh Bawa",
    "Set Alatan Memasak Silikon",
    "Tikar Yoga Tidak Licin",
    "Bantal Perjalanan Busa Memori",
]

INFLUENCER_NAMES_EN = [
    "TechReviewPro", "FashionGuruJen", "BeautyByEmma",
    "FitWithMike", "CookingMasterChef", "TravelVibesAlex",
    "GamingKingSam", "MomLifeDiaries", "LifestyleLuxe",
    "DigitalNomadLuna", "StyleHunterMax", "FoodieAdventures",
]

INFLUENCER_NAMES_TH = [
    "TechReviewTH", "FashionistaLuna", "BeautyQueenSarah",
    "FitLifeJames", "ChefEmily", "WanderlustAlex",
    "GamingProMax", "MomLifeLisa", "LifestyleChronicles",
    "DigitalNomadSam", "StyleHunterNina", "FoodieAdventuresTH",
]

INFLUENCER_NAMES_MY = [
    "TechGuruMikeMY", "FashionistaLunaMY", "BeautyQueenSarahMY",
    "FitLifeJamesMY", "ChefEmilyMY", "WanderlustAlexMY",
    "GamingProMaxMY", "MomLifeLisaMY", "LifestyleChroniclesMY",
    "DigitalNomadSamMY", "StyleHunterNinaMY", "FoodieAdventuresMY",
]


def generate_influencers(db, count=20):
    print("Generating influencers...")
    
    suspicious_count = 3
    generated_suspicious = 0
    
    for i in range(count):
        site_code = random.choice(SITE_CODES)
        platform = random.choice(PLATFORMS)
        
        if site_code == "US":
            names = INFLUENCER_NAMES_EN
        elif site_code == "TH":
            names = INFLUENCER_NAMES_TH
        else:
            names = INFLUENCER_NAMES_MY
        
        is_suspicious = generated_suspicious < suspicious_count and (i % 7 == 0)
        
        if is_suspicious:
            engagement_rate = random.uniform(0.30, 0.45)
            conversion_rate = random.uniform(0.001, 0.005)
            roi = random.uniform(-5.0, 0.5)
            suspicious_reason = f"异常数据模式：互动率{engagement_rate:.2%}远高于行业均值，但转化率{conversion_rate:.4%}极低，疑似购买虚假流量"
            generated_suspicious += 1
        else:
            engagement_rate = random.uniform(0.02, 0.15)
            conversion_rate = random.uniform(0.01, 0.08)
            roi = random.uniform(1.5, 8.0)
            suspicious_reason = None
        
        influencer_id = f"INF_{site_code}_{i+1:03d}"
        existing = db.query(StandardInfluencer).filter(
            StandardInfluencer.influencer_id == influencer_id
        ).first()
        
        if existing:
            existing.site_code = site_code
            existing.platform = platform
            existing.influencer_name = names[i % len(names)]
            existing.avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed=influencer_{i}"
            existing.follower_count = random.randint(10000, 500000)
            existing.engagement_rate = engagement_rate
            existing.conversion_rate = conversion_rate
            existing.roi = roi
            existing.is_suspicious = is_suspicious
            existing.suspicious_reason = suspicious_reason
            existing.country = COUNTRIES[site_code]
            existing.language = LANGUAGES[site_code]
            existing.niche = random.choice(INFLUENCER_NICHES)
            existing.total_posts = random.randint(50, 500)
            existing.avg_likes = random.randint(500, 15000) if not is_suspicious else random.randint(10000, 50000)
            existing.avg_comments = random.randint(50, 800) if not is_suspicious else random.randint(500, 3000)
            existing.avg_shares = random.randint(20, 300) if not is_suspicious else random.randint(200, 1500)
            existing.created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
        else:
            influencer = StandardInfluencer(
                influencer_id=influencer_id,
                site_code=site_code,
                platform=platform,
                influencer_name=names[i % len(names)],
                avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed=influencer_{i}",
                follower_count=random.randint(10000, 500000),
                engagement_rate=engagement_rate,
                conversion_rate=conversion_rate,
                roi=roi,
                is_suspicious=is_suspicious,
                suspicious_reason=suspicious_reason,
                country=COUNTRIES[site_code],
                language=LANGUAGES[site_code],
                niche=random.choice(INFLUENCER_NICHES),
                total_posts=random.randint(50, 500),
                avg_likes=random.randint(500, 15000) if not is_suspicious else random.randint(10000, 50000),
                avg_comments=random.randint(50, 800) if not is_suspicious else random.randint(500, 3000),
                avg_shares=random.randint(20, 300) if not is_suspicious else random.randint(200, 1500),
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365)),
            )
            db.add(influencer)
    
    db.commit()
    print(f"Generated {count} influencers ({generated_suspicious} suspicious)")


def generate_products(db, count=50):
    print("Generating products...")
    
    for i in range(count):
        site_code = random.choice(SITE_CODES)
        currency = CURRENCIES[site_code]
        exchange_rate = EXCHANGE_RATES[site_code]
        
        if site_code == "US":
            names = PRODUCT_NAMES_EN
        elif site_code == "TH":
            names = PRODUCT_NAMES_TH
        else:
            names = PRODUCT_NAMES_MY
        
        base_price = random.uniform(10, 200)
        product_id = f"PRD_{site_code}_{i+1:03d}"
        
        existing = db.query(StandardProduct).filter(
            StandardProduct.product_id == product_id
        ).first()
        
        if existing:
            existing.site_code = site_code
            existing.currency = currency
            existing.product_name = names[i % len(names)]
            existing.product_category = random.choice(PRODUCT_CATEGORIES)
            existing.product_price = round(base_price, 2)
            existing.product_price_local = round(base_price * exchange_rate, 2)
            existing.stock_quantity = random.randint(100, 1000)
            existing.sales_volume = random.randint(10, 500)
            existing.rating = round(random.uniform(3.5, 4.9), 1)
            existing.review_count = random.randint(10, 500)
            existing.image_url = f"https://api.dicebear.com/7.x/shop/svg?seed=product_{i}"
            existing.brand = random.choice(["BrandX", "GlobalTech", "StylePlus", "BeautyLab", "HomeComfort"])
        else:
            product = StandardProduct(
                product_id=product_id,
                site_code=site_code,
                currency=currency,
                product_name=names[i % len(names)],
                product_category=random.choice(PRODUCT_CATEGORIES),
                product_price=round(base_price, 2),
                product_price_local=round(base_price * exchange_rate, 2),
                stock_quantity=random.randint(100, 1000),
                sales_volume=random.randint(10, 500),
                rating=round(random.uniform(3.5, 4.9), 1),
                review_count=random.randint(10, 500),
                image_url=f"https://api.dicebear.com/7.x/shop/svg?seed=product_{i}",
                brand=random.choice(["BrandX", "GlobalTech", "StylePlus", "BeautyLab", "HomeComfort"]),
            )
            db.add(product)
    
    db.commit()
    print(f"Generated {count} products")


def generate_orders(db, count=500):
    print("Generating orders...")
    
    products = db.query(StandardProduct).all()
    influencers = db.query(StandardInfluencer).all()
    
    for i in range(count):
        product = random.choice(products)
        
        available_influencers = [
            inf for inf in influencers
            if inf.site_code == product.site_code
        ]
        
        if not available_influencers:
            continue
        
        influencer = random.choice(available_influencers)
        
        order_id = f"ORD_{product.site_code}_{i+1:04d}"
        existing = db.query(StandardOrder).filter(
            StandardOrder.order_id == order_id
        ).first()
        
        order_amount = product.product_price * random.uniform(1, 3)
        order_date = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 6))
        
        if existing:
            existing.site_code = product.site_code
            existing.currency = product.currency
            existing.product_id = product.product_id
            existing.influencer_id = influencer.influencer_id
            existing.order_amount = round(order_amount, 2)
            existing.order_amount_local = round(product.product_price_local * random.uniform(1, 3), 2)
            existing.quantity = random.randint(1, 5)
            existing.order_status = random.choice(["completed", "shipped", "pending"])
            existing.order_date = order_date
            existing.customer_id = f"CUST_{random.randint(1000, 9999)}"
            existing.created_at = datetime.now(timezone.utc)
        else:
            order = StandardOrder(
                order_id=order_id,
                site_code=product.site_code,
                currency=product.currency,
                product_id=product.product_id,
                influencer_id=influencer.influencer_id,
                order_amount=round(order_amount, 2),
                order_amount_local=round(product.product_price_local * random.uniform(1, 3), 2),
                quantity=random.randint(1, 5),
                order_status=random.choice(["completed", "shipped", "pending"]),
                order_date=order_date,
                customer_id=f"CUST_{random.randint(1000, 9999)}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(order)
    
    db.commit()
    print(f"Generated {count} orders")


def generate_associations(db):
    print("Generating product-influencer associations...")
    
    products = db.query(StandardProduct).all()
    influencers = db.query(StandardInfluencer).all()
    
    for product in products:
        available_influencers = [
            inf for inf in influencers
            if inf.site_code == product.site_code
        ]
        
        num_associations = random.randint(1, 3)
        selected_influencers = random.sample(available_influencers, min(num_associations, len(available_influencers)))
        
        for influencer in selected_influencers:
            existing = db.query(ProductInfluencerAssociation).filter(
                ProductInfluencerAssociation.product_id == product.product_id,
                ProductInfluencerAssociation.influencer_id == influencer.influencer_id
            ).first()
            
            if not existing:
                association = ProductInfluencerAssociation(
                    product_id=product.product_id,
                    influencer_id=influencer.influencer_id,
                    association_date=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60)),
                    campaign_name=f"Campaign_{product.product_category}_{random.randint(1, 10)}",
                )
                db.add(association)
    
    db.commit()
    print("Generated associations")


def main():
    print("=" * 50)
    print("AI Shop Analyzer - Mock Data Generator")
    print("=" * 50)
    
    init_db()
    db = SessionLocal()
    
    try:
        generate_influencers(db, count=20)
        generate_products(db, count=50)
        generate_orders(db, count=500)
        generate_associations(db)
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("Mock data generation completed!")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        print("\nSummary:")
        print(f"  Total Influencers: {db.query(StandardInfluencer).count()}")
        print(f"  Suspicious Influencers: {db.query(StandardInfluencer).filter(StandardInfluencer.is_suspicious == True).count()}")
        print(f"  Total Products: {db.query(StandardProduct).count()}")
        print(f"  Total Orders: {db.query(StandardOrder).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()