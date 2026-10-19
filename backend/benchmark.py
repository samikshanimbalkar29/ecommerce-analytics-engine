"""Command-line benchmark for your report:  python backend/benchmark.py --delay 100 --runs 10"""
import argparse

import analytics
from db import make_backend

p = argparse.ArgumentParser()
p.add_argument("--runs", type=int, default=10)
p.add_argument("--delay", type=int, default=0, help="simulated network latency per region, ms")
a = p.parse_args()

b = make_backend()
r = analytics.benchmark(b, runs=a.runs, delay_ms=a.delay)
print(f"backend={b.name}  regions={r['regions']}  runs={r['runs']}  simulated latency={r['delay_ms']} ms/region")
print(f"{'mode':<12}{'avg ms':>10}{'min':>10}{'max':>10}")
for m in ("sequential", "parallel"):
    s = r[m]
    print(f"{m:<12}{s['avg_ms']:>10}{s['min_ms']:>10}{s['max_ms']:>10}")
print(f"speed-up: {r['speedup']}x")
