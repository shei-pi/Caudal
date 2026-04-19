from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models.instrument import Instrument

BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
BYMA_EQUITIES_URL = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/bnown/securities/equities"


async def _fetch_binance_price(ticker: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(BINANCE_PRICE_URL, params={"symbol": ticker})
            r.raise_for_status()
            return float(r.json()["price"])
    except Exception:
        return None


async def refresh_prices(db: Session) -> int:
    instruments = db.query(Instrument).all()
    updated = 0
    now = datetime.now()

    for inst in instruments:
        price: float | None = None

        if inst.instrument_type in ("crypto", "usdt"):
            symbol = f"{inst.ticker.upper()}USDT"
            price = await _fetch_binance_price(symbol)
            if price is not None:
                inst.last_price = price
                inst.last_price_usd = price
                inst.last_updated = now
                updated += 1

    db.commit()
    return updated
