# 目的：株価・企業情報のデータクラス定義
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（標準ライブラリのみ）

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class StockQuote:
    """リアルタイム株価情報"""
    symbol: str
    price: float
    prev_close: float
    change: float          # 前日比（円）
    change_percent: float  # 前日比（%）
    volume: int
    market_cap: float | None  # 時価総額（円）。取得できない場合 None
    pe_ratio: float | None    # PER。取得できない場合 None
    pb_ratio: float | None    # PBR。取得できない場合 None
    dividend_yield: float | None  # 配当利回り（%）。取得できない場合 None
    fetched_at: datetime


@dataclass
class StockProfile:
    """企業プロフィール情報"""
    symbol: str
    name: str
    sector: str
    description: str


@dataclass
class TimeSeriesPoint:
    """時系列データの1点"""
    date: date
    close: float
    volume: int = 0


@dataclass
class TimeSeries:
    """時系列データ（チャート用）"""
    symbol: str
    interval: str
    data: list[TimeSeriesPoint]


@dataclass
class NewsItem:
    """ニュース1件分のデータ"""
    title: str
    description: str | None
    pub_date: str
    link: str
