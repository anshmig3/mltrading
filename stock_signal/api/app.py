import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.nlp_agent import run_agent
from api.websocket import broadcast, connect, disconnect
from config import API_HOST, API_PORT
from data.backfill import backfill_ticker
from data.db import db, init_db
from ml.predict import run_inference_for_all

logger = logging.getLogger(__name__)

app = FastAPI(title="Stock Signal API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(_inference_loop())


# ── Ticker endpoints ────────────────────────────────────────────────────────

class TickerIn(BaseModel):
    symbol: str
    up_threshold: Optional[float] = 0.60
    down_threshold: Optional[float] = 0.60


@app.post("/tickers", status_code=201)
async def add_ticker(body: TickerIn):
    symbol = body.symbol.upper().strip()
    with db() as conn:
        existing = conn.execute(
            "SELECT symbol, active FROM tickers WHERE symbol = ?", (symbol,)
        ).fetchone()
        if existing and existing["active"] == 1:
            raise HTTPException(status_code=409, detail=f"{symbol} already active")
        if existing:
            conn.execute(
                "UPDATE tickers SET active = 1, up_threshold = ?, down_threshold = ? WHERE symbol = ?",
                (body.up_threshold, body.down_threshold, symbol),
            )
        else:
            conn.execute(
                "INSERT INTO tickers (symbol, up_threshold, down_threshold) VALUES (?, ?, ?)",
                (symbol, body.up_threshold, body.down_threshold),
            )

    asyncio.create_task(asyncio.to_thread(backfill_ticker, symbol))
    return {"symbol": symbol, "status": "added"}


@app.delete("/tickers/{symbol}")
async def remove_ticker(symbol: str):
    symbol = symbol.upper()
    with db() as conn:
        row = conn.execute("SELECT symbol FROM tickers WHERE symbol = ?", (symbol,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"{symbol} not found")
        conn.execute("UPDATE tickers SET active = 0 WHERE symbol = ?", (symbol,))
    return {"symbol": symbol, "status": "removed"}


@app.get("/tickers")
async def list_tickers():
    with db() as conn:
        rows = conn.execute("SELECT * FROM tickers WHERE active = 1").fetchall()
    return [dict(r) for r in rows]


# ── Signal endpoints ─────────────────────────────────────────────────────────

@app.get("/signals/{symbol}")
async def get_signals(symbol: str, limit: int = 20):
    symbol = symbol.upper()
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM signals WHERE symbol = ? ORDER BY candle_ts DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("flags"):
            try:
                d["flags"] = json.loads(d["flags"])
            except Exception:
                d["flags"] = []
        results.append(d)
    return results


@app.get("/signals")
async def get_all_latest_signals():
    with db() as conn:
        rows = conn.execute(
            """SELECT s.* FROM signals s
               INNER JOIN (
                   SELECT symbol, MAX(candle_ts) as max_ts
                   FROM signals GROUP BY symbol
               ) latest ON s.symbol = latest.symbol AND s.candle_ts = latest.max_ts""",
        ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("flags"):
            try:
                d["flags"] = json.loads(d["flags"])
            except Exception:
                d["flags"] = []
        results.append(d)
    return results


# ── Model stats endpoint ─────────────────────────────────────────────────────

@app.get("/model-stats")
async def get_model_stats():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM model_meta WHERE is_current = 1"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/model-stats/{symbol}")
async def get_model_stats_ticker(symbol: str):
    symbol = symbol.upper()
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM model_meta WHERE symbol = ? AND is_current = 1", (symbol,)
        ).fetchone()
        override_count = conn.execute(
            """SELECT COUNT(*) as cnt FROM signals
               WHERE symbol = ? AND ml_overridden = 1
               AND candle_ts >= datetime('now', '-30 days')""",
            (symbol,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No model found")
    result = dict(row)
    result["overrides_30d"] = override_count["cnt"] if override_count else 0
    return result


# ── Health endpoint ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        with db() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        disconnect(ws)


# ── Inference loop ────────────────────────────────────────────────────────────

async def _inference_loop():
    while True:
        try:
            results = await asyncio.to_thread(run_inference_for_all)
            for inf in results:
                signal = await asyncio.to_thread(run_agent, inf)
                signal_payload = {k: v for k, v in signal.items()}
                if isinstance(signal_payload.get("flags"), str):
                    try:
                        signal_payload["flags"] = json.loads(signal_payload["flags"])
                    except Exception:
                        pass
                await broadcast({"type": "signal", "data": signal_payload})
        except Exception as e:
            logger.error("Inference loop error: %s", e)
        await asyncio.sleep(300)


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("api.app:app", host=API_HOST, port=API_PORT, reload=False)
