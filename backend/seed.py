"""Create the schema and load synthetic orders into Cassandra.
   python backend/seed.py [--per-region 20000]"""
import argparse
import os
import random
import sys
import time

from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args

import config

parser = argparse.ArgumentParser()
parser.add_argument("--per-region", type=int, default=20000)
args = parser.parse_args()

extra = {}
if sys.version_info >= (3, 12):
    from cassandra.io.asyncioreactor import AsyncioConnection
    extra["connection_class"] = AsyncioConnection

print(f"Connecting to {config.HOSTS}:{config.PORT} ...")
cluster = Cluster(config.HOSTS, port=config.PORT, **extra)
session = cluster.connect()

schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.cql")
lines = [l for l in open(schema_path, encoding="utf-8") if not l.strip().startswith("--")]
for stmt in "".join(lines).split(";"):
    if stmt.strip():
        session.execute(stmt, timeout=60)
session.set_keyspace(config.KEYSPACE)

for table in ("orders", "orders_by_category"):          # makes the script re-runnable
    session.execute(f"TRUNCATE {table}", timeout=120)

ins_orders = session.prepare(
    "INSERT INTO orders (region, order_date, order_id, customer_id, category, product, quantity, amount) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
ins_cat = session.prepare(
    "INSERT INTO orders_by_category (region, category, order_date, order_id, amount) VALUES (?, ?, ?, ?, ?)")

t0 = time.time()
for region in config.REGIONS:
    rng = random.Random(region)
    orders = [config.random_order(rng, region) for _ in range(args.per_region)]
    execute_concurrent_with_args(session, ins_orders, [
        (o["region"], o["order_date"], o["order_id"], o["customer_id"], o["category"],
         o["product"], o["quantity"], o["amount"]) for o in orders], concurrency=64)
    execute_concurrent_with_args(session, ins_cat, [
        (o["region"], o["category"], o["order_date"], o["order_id"], o["amount"]) for o in orders],
        concurrency=64)
    print(f"  {region}: {len(orders)} orders loaded")

print(f"Done in {time.time() - t0:.1f}s. Next: python backend/app.py")
cluster.shutdown()
