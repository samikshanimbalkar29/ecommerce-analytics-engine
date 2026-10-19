"""Parallel, fault-tolerant analytics over Cassandra region partitions."""
import concurrent.futures as cf
import time
from collections import defaultdict
from decimal import Decimal
import config

RETRIES = 2
BACKOFF = 0.15


def _collect(backend, handle, query, region, delay_ms, down):
    started = time.perf_counter()
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            if delay_ms:
                time.sleep(delay_ms / 1000)
            if region in down:
                raise ConnectionError(f"{region} node unavailable (fault simulation)")
            future = handle if attempt == 0 and handle is not None else backend.submit(query, region)
            rows = future.result()
            return region, rows, {"status": "ok", "attempts": attempt + 1,
                                  "ms": round((time.perf_counter() - started) * 1000, 1)}
        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(BACKOFF * (2 ** attempt))
    return region, None, {"status": "failed", "attempts": RETRIES + 1,
                          "error": str(last_error),
                          "ms": round((time.perf_counter() - started) * 1000, 1)}


def fetch(backend, query, mode="parallel", delay_ms=0, down=()):
    regions = config.REGIONS
    started = time.perf_counter()
    if mode == "sequential":
        results = [_collect(backend, None, query, r, delay_ms, down) for r in regions]
    else:
        handles = {}
        for region in regions:
            try:
                handles[region] = backend.submit(query, region)
            except Exception:
                handles[region] = None
        with cf.ThreadPoolExecutor(max_workers=max(1, len(regions))) as pool:
            results = list(pool.map(
                lambda region: _collect(backend, handles[region], query, region, delay_ms, down), regions))
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    data = {region: rows for region, rows, _ in results if rows is not None}
    status = {region: info for region, _, info in results}
    failed = [r for r, info in status.items() if info["status"] == "failed"]
    meta = {"mode": mode, "elapsed_ms": elapsed, "regions": status, "partial": bool(failed),
            "warnings": [f"{r} partition unavailable; showing partial results" for r in failed]}
    return data, meta


def summary(backend, **opts):
    data, meta = fetch(backend, "summary", **opts)
    by_region = {}
    for region, rows in data.items():
        sales = sum((Decimal(str(row[0] or 0)) for row in rows), Decimal("0"))
        by_region[region] = {"sales": float(sales), "orders": len(rows)}
    total_sales = sum(v["sales"] for v in by_region.values())
    total_orders = sum(v["orders"] for v in by_region.values())
    return {"total_sales": total_sales, "total_orders": total_orders,
            "avg_order_value": total_sales / total_orders if total_orders else 0,
            "by_region": by_region, "meta": meta}


def categories(backend, **opts):
    data, meta = fetch(backend, "category", **opts)
    totals = defaultdict(lambda: defaultdict(float))
    for region, rows in data.items():
        for category, amount in rows:
            totals[str(category)][region] += float(amount or 0)
    cats = sorted(totals, key=lambda c: -sum(totals[c].values()))
    regions = list(data)
    return {"categories": cats, "regions": regions,
            "series": {r: [totals[c].get(r, 0) for c in cats] for r in regions}, "meta": meta}


def daily(backend, **opts):
    data, meta = fetch(backend, "daily", **opts)
    totals = defaultdict(lambda: defaultdict(float))
    for region, rows in data.items():
        for order_date, amount in rows:
            totals[str(order_date)][region] += float(amount or 0)
    days = sorted(totals)[-30:]
    regions = list(data)
    return {"days": days,
            "series": {r: [totals[d].get(r, 0) for d in days] for r in regions}, "meta": meta}


def benchmark(backend, runs=5, delay_ms=0):
    out = {}
    for mode in ("sequential", "parallel"):
        samples = []
        for i in range(runs + 1):
            _, meta = fetch(backend, "summary", mode=mode, delay_ms=delay_ms)
            if i:
                samples.append(meta["elapsed_ms"])
        out[mode] = {"avg_ms": round(sum(samples) / len(samples), 1),
                     "min_ms": min(samples), "max_ms": max(samples), "runs": samples}
    out["speedup"] = round(out["sequential"]["avg_ms"] / max(out["parallel"]["avg_ms"], 0.1), 2)
    out.update(runs=runs, delay_ms=delay_ms, regions=len(config.REGIONS))
    return out
