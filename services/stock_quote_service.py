# 目的：株価・指標データの取得とモデル変換
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（標準ライブラリのみ）

from datetime import datetime

import streamlit as st

from clients.twelve_data_client import TwelveDataClient
from config import CACHE_TTL
from models.stock_models import StockQuote


class StockQuoteService:
    def __init__(self, client: TwelveDataClient):
        self._client = client

    def get(self, symbol: str) -> StockQuote | None:
        """株価情報を取得する。APIエラー時は None を返す（呼び出し元でエラー処理）。"""
        return _fetch_quote(self._client, symbol)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_quote(_client: TwelveDataClient, symbol: str) -> StockQuote | None:
    raw = _client.get_quote(symbol)

    price = _to_float(raw.get("close") or raw.get("price"))
    prev_close = _to_float(raw.get("previous_close"))

    if price is None or prev_close is None:
        return None

    change = _to_float(raw.get("change"))
    change_pct = _to_float(raw.get("percent_change"))
    volume = _to_int(raw.get("volume"))

    # 指標（取得できない場合は None）
    market_cap = _to_float(raw.get("market_cap"))
    pe_ratio = _to_float(raw.get("pe"))
    pb_ratio = _to_float(raw.get("pb"))
    dividend_yield = _to_float(raw.get("dividend_yield"))

    return StockQuote(
        symbol=symbol,
        price=price,
        prev_close=prev_close,
        change=change if change is not None else (price - prev_close),
        change_percent=change_pct if change_pct is not None else ((price - prev_close) / prev_close * 100),
        volume=volume if volume is not None else 0,
        market_cap=market_cap,
        pe_ratio=pe_ratio,
        pb_ratio=pb_ratio,
        dividend_yield=dividend_yield,
        fetched_at=datetime.now(),
    )


def _to_float(value) -> float | None:
    if value is None or value == "N/A" or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value) -> int | None:
    if value is None or value == "N/A" or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
