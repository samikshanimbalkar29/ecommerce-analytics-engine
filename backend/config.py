"""Shared settings and the synthetic order generator used to seed Cassandra."""
import datetime
import os
import uuid
from decimal import Decimal

HOSTS = [h.strip() for h in os.getenv("CASSANDRA_HOSTS", "127.0.0.1").split(",")]
PORT = int(os.getenv("CASSANDRA_PORT", "9042"))
KEYSPACE = "ecommerce"
REGIONS = [r.strip() for r in os.getenv("REGIONS", "North,South").split(",") if r.strip()]
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5"))   # seconds, per query

# category -> [(product, unit price in INR)]
CATALOG = {
    "Electronics": [("Headphones", 2499), ("Smartwatch", 5999), ("Power bank", 1299)],
    "Fashion":     [("Jeans", 1799), ("Sneakers", 3299), ("Kurta", 1199)],
    "Home":        [("Mixer grinder", 3499), ("Bedsheet set", 1499), ("Lamp", 899)],
    "Books":       [("Novel", 399), ("Textbook", 899), ("Comic", 299)],
    "Grocery":     [("Rice 10kg", 799), ("Olive oil", 649), ("Tea 1kg", 549)],
    "Sports":      [("Cricket bat", 2799), ("Yoga mat", 699), ("Football", 999)],
}


def random_order(rng, region, today=None):
    """One synthetic order as a dict. `rng` is a random.Random instance."""
    today = today or datetime.date.today()
    category = rng.choice(list(CATALOG))
    product, price = rng.choice(CATALOG[category])
    qty = rng.randint(1, 4)
    amount = (Decimal(price * qty) * Decimal(str(round(rng.uniform(0.9, 1.1), 3)))).quantize(Decimal("0.01"))
    return {
        "region": region,
        "order_date": today - datetime.timedelta(days=rng.randint(0, 89)),
        "order_id": uuid.UUID(int=rng.getrandbits(128), version=4),
        "customer_id": rng.randint(1, 5000),
        "category": category,
        "product": product,
        "quantity": qty,
        "amount": amount,
    }
