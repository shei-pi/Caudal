from datetime import date, datetime

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate

DOLAR_API_URL = "https://dolarapi.com/v1/dolares"

RATE_TYPE_MAP = {
    "Oficial": "oficial",
    "Blue": "blue",
    "Bolsa": "mep",
    "Contado con liquidación": "ccl",
    "Cripto": "cripto",
    "Mayorista": "mayorista",
    "Tarjeta": "tarjeta",
}


async def fetch_and_store_rates(db: Session) -> int:
    stored = 0
    today = date.today()
    now = datetime.now()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(DOLAR_API_URL)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return 0

    for item in data:
        nombre = item.get("nombre", "")
        rate_type = RATE_TYPE_MAP.get(nombre)
        if not rate_type:
            continue

        buy = item.get("compra")
        sell = item.get("venta")
        mid = ((buy or 0) + (sell or 0)) / 2 if buy and sell else (buy or sell or 0)
        if mid == 0:
            continue

        rate = ExchangeRate(
            date=today,
            rate_type=rate_type,
            currency_from="USD",
            currency_to="ARS",
            buy_rate=buy,
            sell_rate=sell,
            mid_rate=mid,
            source="dolarapi",
            fetched_at=now,
        )
        try:
            db.add(rate)
            db.commit()
            stored += 1
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(ExchangeRate)
                .filter(
                    ExchangeRate.date == today,
                    ExchangeRate.rate_type == rate_type,
                    ExchangeRate.source == "dolarapi",
                )
                .first()
            )
            if existing:
                existing.buy_rate = buy
                existing.sell_rate = sell
                existing.mid_rate = mid
                existing.fetched_at = now
                db.commit()
                stored += 1

    return stored
