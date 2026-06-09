# 目的：テクニカル指標の計算ユーティリティ（RSI・MACD）
# 作成日：2026-06-08
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：pandas

import math

import pandas as pd


def calc_rsi(closes: list[float], period: int = 14) -> list[float]:
    """Wilder法でRSI(14)を計算して返す。期間不足の先頭はNaN。"""
    s = pd.Series(closes)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.tolist()


def calc_macd(closes: list[float]) -> tuple[list[float], list[float], list[float]]:
    """MACD・シグナル・ヒストグラムを計算して返す。データ26件未満は全要素NaN。"""
    if len(closes) < 26:
        nan_list = [float("nan")] * len(closes)
        return nan_list, nan_list[:], nan_list[:]
    s = pd.Series(closes)
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd.tolist(), signal.tolist(), histogram.tolist()


def get_latest_rsi(closes: list[float]) -> float | None:
    """closes から最新のRSI値（NaN除く）を返す。取得不可の場合は None。"""
    rsi_values = calc_rsi(closes)
    return next((v for v in reversed(rsi_values) if not math.isnan(v)), None)


def get_macd_direction(closes: list[float]) -> str:
    """closes から最新のMACD方向を返す。「上向き」|「下向き」|「不明」。"""
    _, _, histogram = calc_macd(closes)
    last_hist = next((v for v in reversed(histogram) if not math.isnan(v)), None)
    if last_hist is None:
        return "不明"
    return "上向き" if last_hist >= 0 else "下向き"
