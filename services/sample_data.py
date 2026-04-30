from extensions import db
from models import Coupon, Product, User


def create_sample_data():
    """Create sample products and admin user."""
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User()
        admin.username = "admin"
        admin.email = "admin@trendvibe.com"
        admin.is_admin = True
        admin.is_email_verified = True
        admin.set_password("Admin@123!")
        db.session.add(admin)

    sample_products = [
        {
            "name": "Niacinamide Serum 10%",
            "description": "Korean skincare serum with 10% niacinamide for pore refinement and oil control. Perfect for Indian skin.",
            "price": 599.0,
            "category": "beauty",
            "supplier": "K-Beauty India",
            "image_url": "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=400",
        },
        {
            "name": "Ceramide Moisturizer",
            "description": "Lightweight K-beauty moisturizer with ceramides and hyaluronic acid. Hydrates without greasiness.",
            "price": 699.0,
            "category": "beauty",
            "supplier": "Seoul Skincare Co.",
            "image_url": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=400",
        },
        {
            "name": "Korean Sheet Mask Set",
            "description": "Set of 10 Korean sheet masks with snail mucin, collagen, and vitamin C for glowing skin.",
            "price": 399.0,
            "category": "beauty",
            "supplier": "Asian Beauty Hub",
            "image_url": "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=400",
        },
        {
            "name": "Vitamin C Glow Serum",
            "description": "Brightening serum with 20% vitamin C, perfect for Indian skin tone enhancement and dark spot reduction.",
            "price": 799.0,
            "category": "beauty",
            "supplier": "Glow Essentials",
            "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400",
        },
        {
            "name": "Smart Fitness Watch",
            "description": "Waterproof fitness tracker with heart rate monitor, sleep tracking, and 7-day battery life.",
            "price": 1299.0,
            "category": "lifestyle",
            "supplier": "TechVibe India",
            "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400",
        },
        {
            "name": "Wireless Bluetooth Earbuds",
            "description": "True wireless earbuds with active noise cancellation and 24-hour battery case. Perfect for work and workouts.",
            "price": 899.0,
            "category": "lifestyle",
            "supplier": "Audio Pro Delhi",
            "image_url": "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=400",
        },
        {
            "name": "Eco-Friendly Water Bottle",
            "description": "Insulated stainless steel water bottle keeps drinks cold for 24 hours. BPA-free and leak-proof.",
            "price": 449.0,
            "category": "lifestyle",
            "supplier": "EcoLife Products",
            "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400",
        },
        {
            "name": "Portable Power Bank 20000mAh",
            "description": "High-capacity power bank with fast charging and multiple ports. Essential for busy urban lifestyle.",
            "price": 999.0,
            "category": "lifestyle",
            "supplier": "PowerTech Mumbai",
            "image_url": "/static/images/power_bank.svg",
        },
        {
            "name": "Brass Pooja Thali Set",
            "description": "Traditional brass pooja thali with diya, incense holder, and sacred symbols. Perfect for daily worship.",
            "price": 799.0,
            "category": "spiritual",
            "supplier": "Sacred Crafts Jaipur",
            "image_url": "/static/images/pooja_thali.svg",
        },
        {
            "name": "Premium Incense Stick Collection",
            "description": "Handcrafted incense sticks in 12 fragrances: Sandalwood, Jasmine, Rose, and traditional Indian scents.",
            "price": 399.0,
            "category": "spiritual",
            "supplier": "Mysore Agarbatti Co.",
            "image_url": "/static/images/incense_sticks.svg",
        },
        {
            "name": "Sacred Ganesha Idol",
            "description": "Beautiful handcrafted brass Ganesha idol for home temple. Brings prosperity and removes obstacles.",
            "price": 1199.0,
            "category": "spiritual",
            "supplier": "Divine Sculptures",
            "image_url": "/static/images/ganesha_idol.svg",
        },
        {
            "name": "Japa Mala Prayer Beads",
            "description": "Traditional 108-bead sandalwood mala for meditation and prayer. Handmade with authentic materials.",
            "price": 599.0,
            "category": "spiritual",
            "supplier": "Spiritual Beads India",
            "image_url": "/static/images/japa_mala.svg",
        },
        {
            "name": "Ashwagandha Capsules",
            "description": "Pure Ayurvedic ashwagandha extract capsules for stress relief and energy. 60 capsules, 1-month supply.",
            "price": 699.0,
            "category": "wellness",
            "supplier": "Ayur Wellness",
            "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400",
        },
        {
            "name": "Premium Yoga Mat",
            "description": "Non-slip eco-friendly yoga mat with alignment lines. Perfect for home workouts and yoga practice.",
            "price": 999.0,
            "category": "wellness",
            "supplier": "Yoga Essentials",
            "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400",
        },
        {
            "name": "Essential Oil Diffuser",
            "description": "Ultrasonic aromatherapy diffuser with LED lights and timer. Includes lavender and eucalyptus oils.",
            "price": 1299.0,
            "category": "wellness",
            "supplier": "Aroma India",
            "image_url": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=400",
        },
        {
            "name": "Resistance Band Set",
            "description": "Complete resistance band workout set with 5 resistance levels. Perfect for home fitness routines.",
            "price": 799.0,
            "category": "wellness",
            "supplier": "Fit Life India",
            "image_url": "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400",
        },
        {
            "name": "Interactive Pet Toy Set",
            "description": "Set of 5 interactive toys for dogs and cats. Includes puzzle feeders, rope toys, and catnip mice.",
            "price": 599.0,
            "category": "pets",
            "supplier": "Pet Paradise Mumbai",
            "image_url": "https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=400",
        },
        {
            "name": "Premium Pet Grooming Kit",
            "description": "Complete grooming kit with nail clippers, brushes, and shampoo. Suitable for dogs and cats.",
            "price": 899.0,
            "category": "pets",
            "supplier": "Pet Care Solutions",
            "image_url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=400",
        },
        {
            "name": "Portable Pet Water Bowl",
            "description": "Collapsible silicone water bowl for travel and outdoor activities with your pets. BPA-free and dishwasher safe.",
            "price": 299.0,
            "category": "pets",
            "supplier": "Travel Pets India",
            "image_url": "https://images.unsplash.com/photo-1615751072497-5f5169febe17?w=400",
        },
        {
            "name": "Eco-Friendly Pet Leash",
            "description": "Durable hemp-fiber pet leash with comfortable grip handle. Available in multiple colors and sizes.",
            "price": 399.0,
            "category": "pets",
            "supplier": "Green Pet Products",
            "image_url": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=400",
        },
    ]

    for product_data in sample_products:
        existing = Product.query.filter_by(name=product_data["name"]).first()
        if not existing:
            product = Product()
            product.name = product_data["name"]
            product.description = product_data["description"]
            product.price = product_data["price"]
            product.category = product_data["category"]
            product.supplier = product_data["supplier"]
            product.image_url = product_data["image_url"]
            db.session.add(product)

    db.session.commit()

    sample_coupons = [
        {"code": "WELCOME10", "discount_percent": 10.0, "max_uses": 500},
        {"code": "BEAUTY20", "discount_percent": 20.0, "max_uses": 100},
        {"code": "WELLNESS15", "discount_percent": 15.0, "max_uses": 200},
        {"code": "TRENDVIBE5", "discount_percent": 5.0, "max_uses": 1000},
    ]
    for coupon_data in sample_coupons:
        existing = Coupon.query.filter_by(code=coupon_data["code"]).first()
        if not existing:
            coupon = Coupon(**coupon_data)
            db.session.add(coupon)

    db.session.commit()
