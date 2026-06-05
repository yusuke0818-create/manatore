# 目的：株価時系列データの取得とモデル変換（チャート用）
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（標準ライブラリのみ）

from datetime import date

import streamlit as st

from clients.twelve_data_client import TwelveDataClient
from config import CACHE_TTL, CHART_PERIODS
from models.stock_models import TimeSeries, TimeSeriesPoint


class StockTimeSeriesService:
    def __init__(self, client: TwelveDataClient):
        self._client = client

    def get(self, symbol: str, period_label: str) -> TimeSeries | None:
        """指定期間の時系列データを取得する。APIエラー時は None を返す。"""
        outputsize = _period_label_to_outputsize(period_label)
        return _fetch_timeseries(self._client, symbol, outputsize)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_timeseries(_client: TwelveDataClient, symbol: str, outputsize: int) -> TimeSeries | None:
    raw = _client.get_time_series(symbol, outputsize)
    values = raw.get("values")
    if not values:
        return None

    points: list[TimeSeriesPoint] = []
    for item in reversed(values):  # Twelve Data は新しい順なので反転して古い順にする
        try:
            d = date.fromisoformat(item["datetime"])
            close = float(item["close"])
            volume = int(item.get("volume", 0))
            points.append(TimeSeriesPoint(date=d, close=close, volume=volume))
        except (KeyError, ValueError):
            continue

    if not points:
        return None

    return TimeSeries(symbol=symbol, interval="1day", data=points)


def _period_label_to_outputsize(period_label: str) -> int:
    for p in CHART_PERIODS:
        if p["label"] == period_label:
            return p["outputsize"]
    return 90  # デフォルト3ヶ月
