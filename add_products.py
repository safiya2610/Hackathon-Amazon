import os
import django
import sys
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')
django.setup()

from core.models import Item, Category

# Ensure category exists
cat, _ = Category.objects.get_or_create(
    title="Fashion & Accessories",
    slug="fashion-accessories",
    defaults={'description': 'Fashion items'}
)

products = [
    {
        'title': 'Sonata Sleek Blue Dial Watch',
        'price': 150.0,
        'discount_price': 120.0,
        'category': cat,
        'label': 'N',
        'slug': 'sonata-sleek-blue',
        'stock_no': 'W001',
        'description_short': 'Elegant blue men watch.',
        'description_long': 'A beautiful Sonata Sleek watch with a dark dial and blue metallic strap.',
        'image_path': r'C:\Users\safiy\.gemini\antigravity\brain\b26f8923-4c83-4425-9db8-5f524fe3f30c\watch_1781610667969.png'
    },
    {
        'title': 'White Embroidered Kurti Tunic',
        'price': 45.0,
        'discount_price': 39.0,
        'category': cat,
        'label': 'S',
        'slug': 'white-embroidered-kurti',
        'stock_no': 'K001',
        'description_short': 'Beautiful ethnic wear.',
        'description_long': 'White kurti with floral embroidery.',
        'image_path': r'C:\Users\safiy\.gemini\antigravity\brain\b26f8923-4c83-4425-9db8-5f524fe3f30c\kurti_1781610698044.png'
    },
    {
        'title': 'Gold Diamond Cluster Ring',
        'price': 500.0,
        'discount_price': 450.0,
        'category': cat,
        'label': 'P',
        'slug': 'gold-diamond-ring',
        'stock_no': 'R001',
        'description_short': 'Four diamonds gold ring.',
        'description_long': 'Premium gold ring with a square cluster of 4 diamonds.',
        'image_path': r'C:\Users\safiy\.gemini\antigravity\brain\b26f8923-4c83-4425-9db8-5f524fe3f30c\ring_1781610716187.png'
    }
]

for p in products:
    with open(p['image_path'], 'rb') as f:
        item = Item(
            title=p['title'],
            price=p['price'],
            discount_price=p['discount_price'],
            category=p['category'],
            label=p['label'],
            slug=p['slug'],
            stock_no=p['stock_no'],
            description_short=p['description_short'],
            description_long=p['description_long']
        )
        item.image.save(os.path.basename(p['image_path']), File(f), save=True)
        print(f"Saved {item.title}")
