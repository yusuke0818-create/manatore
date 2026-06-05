# 目的：企業プロフィール情報の取得とフォールバック処理
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（標準ライブラリのみ）

import json
from pathlib import Path

import streamlit as st

from clients.twelve_data_client import TwelveDataClient
from config import CACHE_TTL
from models.stock_models import StockProfile

_PRESET_PATH = Path(__file__).parent.parent / "data" / "preset_companies.json"


class StockProfileService:
    def __init__(self, client: TwelveDataClient):
        self._client = client
        self._preset: dict = _load_preset()

    def get(self, symbol: str) -> StockProfile:
        """企業情報を取得する。APIエラー・データなしでもフォールバックで返す（None にしない）。"""
        return _fetch_profile(self._client, symbol, self._preset)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_profile(_client: TwelveDataClient, symbol: str, preset: dict) -> StockProfile:
    # プリセットのフォールバック（API呼び出し前に確保）
    fallback = preset.get(symbol)

    try:
        raw = _client.get_profile(symbol)
    except Exception:
        raw = {}

    # プリセット（日本語）がある場合は優先。ない場合のみ yfinance（英語）を使う
    name = (fallback["name"] if fallback else None) or raw.get("name") or symbol
    sector = (fallback["sector"] if fallback else None) or raw.get("sector") or ""
    description = (fallback["description"] if fallback else None) or raw.get("description") or "企業概要を取得できませんでした。"

    return StockProfile(
        symbol=symbol,
        name=name,
        sector=sector,
        description=description,
    )


def _load_preset() -> dict:
    try:
        with open(_PRESET_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
