-- Tier 3: Cassandra schema
-- replication_factor = 1: each partition is stored on exactly ONE node (pure horizontal
-- partitioning). Raise it to 2 on the 2-node cluster to keep a copy of every region on both nodes.
CREATE KEYSPACE IF NOT EXISTS ecommerce
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Partition key = region  ->  horizontal partitioning. Cassandra hashes "North" / "South"
-- to a token and the token decides which node owns that partition.
CREATE TABLE IF NOT EXISTS ecommerce.orders (
  region      text,
  order_date  date,
  order_id    uuid,
  customer_id int,
  category    text,
  product     text,
  quantity    int,
  amount      decimal,
  PRIMARY KEY ((region), order_date, order_id)
) WITH CLUSTERING ORDER BY (order_date DESC, order_id ASC);

-- Query-driven design: Cassandra can only GROUP BY clustering columns, so the category
-- breakdown gets its own table (same partition key, category as first clustering column).
CREATE TABLE IF NOT EXISTS ecommerce.orders_by_category (
  region     text,
  category   text,
  order_date date,
  order_id   uuid,
  amount     decimal,
  PRIMARY KEY ((region), category, order_date, order_id)
);
