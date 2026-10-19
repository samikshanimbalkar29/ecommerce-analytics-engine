# E-Commerce Analytics Engine

A three-tier e-commerce analytics dashboard powered by **Apache Cassandra**. All dashboard figures are queried from Cassandra; the application does not silently substitute sample or in-memory data.

## Architecture

- **Tier 1 — Frontend:** `frontend/index.html`, responsive dashboard with sales KPIs, regional/category charts, daily sales, benchmark and partition health.
- **Tier 2 — API:** `backend/app.py` and `backend/analytics.py`, Flask endpoints, parallel asynchronous region queries, retries, timeouts and partial-result reporting.
- **Tier 3 — Database:** `docker-compose.yml` and `schema.cql`, two-node Cassandra cluster with region-partitioned tables.

## Requirements

- Python 3.9 or newer
- Docker Desktop / Docker Engine with Docker Compose
- Approximately 2 GB RAM available for Cassandra

## Run on Windows (VS Code)

Open a terminal in the project folder and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d
```

Wait for Cassandra to become healthy. Check the cluster with:

```powershell
docker exec cass1 nodetool status
```

Both nodes should show `UN`. Create the schema and load sample orders into Cassandra:

```powershell
python backend/seed.py --per-region 20000
```

Start the API and dashboard:

```powershell
python backend/app.py
```

Open **http://127.0.0.1:5000**. On macOS/Linux, activate the environment with `source .venv/bin/activate` instead.

## Configuration

Environment variables:

- `CASSANDRA_HOSTS` — comma-separated contact points; default `127.0.0.1`
- `CASSANDRA_PORT` — native transport port; default `9042`
- `REGIONS` — comma-separated region partitions; default `North,South`
- `REQUEST_TIMEOUT` — Cassandra request timeout in seconds; default `5`

If Cassandra is not available or the schema has not been loaded, the dashboard displays a connection/error message. Start the database and run the seed command before opening the dashboard.

## Dashboard features

- Total sales, order count, and average order value calculated from Cassandra rows.
- Regional and category revenue distributions and daily revenue trends.
- Parallel (async) versus sequential query mode and a benchmark chart.
- Configurable simulated network latency and partition fault simulation.
- Retry attempts, per-partition query latency, and graceful partial results when a partition fails.

## Data model

The partition key is `region`. `orders` supports summary and daily queries; `orders_by_category` is a denormalized table designed for category analytics. Cassandra does not provide general SQL `SUM/GROUP BY` aggregation in CQL, so the API sums the returned partition rows. The browser calls only the Flask API and never connects directly to Cassandra.

## Troubleshooting

- **Connection refused / 503:** run `docker compose ps`, wait for Cassandra health checks to pass, then run the seed command.
- **Check node status:** `docker exec cass1 nodetool status`.
- **Stop services:** `docker compose down`.
- **Reset data:** rerun `python backend/seed.py`; it truncates and reloads the two project tables.
