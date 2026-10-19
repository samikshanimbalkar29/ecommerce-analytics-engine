"""Tier 2: Flask API + static hosting of the Tier 1 dashboard.   python backend/app.py"""
import os
import threading

from flask import Flask, jsonify, request, send_from_directory

import analytics
import config
from db import make_backend

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
app = Flask(__name__, static_folder=None)

_backend = None
_lock = threading.Lock()


def backend():
    global _backend
    with _lock:
        if _backend is None:
            _backend = make_backend()
        return _backend


def opts():
    mode = request.args.get("mode", "parallel")
    delay = max(0, min(int(request.args.get("delay", 0)), 5000))
    down = {r for r in request.args.get("down", "").split(",") if r}
    return {"mode": mode if mode in ("parallel", "sequential") else "parallel",
            "delay_ms": delay, "down": down}


@app.errorhandler(Exception)
def on_error(exc):
    return jsonify(error=f"{type(exc).__name__}: {exc}",
                   hint="Start Cassandra with docker compose up -d, wait for it to become healthy, then run python backend/seed.py."), 503


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", backend=backend().name, regions=config.REGIONS,
                   timeout_s=config.REQUEST_TIMEOUT)


@app.get("/api/summary")
def summary():
    return jsonify(analytics.summary(backend(), **opts()))


@app.get("/api/categories")
def categories():
    return jsonify(analytics.categories(backend(), **opts()))


@app.get("/api/daily")
def daily():
    return jsonify(analytics.daily(backend(), **opts()))


@app.get("/api/benchmark")
def benchmark():
    runs = max(1, min(int(request.args.get("runs", 5)), 20))
    delay = max(0, min(int(request.args.get("delay", 0)), 2000))
    return jsonify(analytics.benchmark(backend(), runs=runs, delay_ms=delay))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
