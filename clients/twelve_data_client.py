# 目的：yfinance を使った株価データ取得クライアント（Twelve Data から移行）
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：yfinance

import re

import pandas as pd
import requests
import yfinance as yf


class TwelveDataApiError(Exception):
    """データ取得エラー用例外"""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TwelveDataRateLimitError(TwelveDataApiError):
    """レート制限用例外（yfinance では通常発生しない）"""


class TwelveDataNetworkError(TwelveDataApiError):
    """ネットワーク接続エラー用例外"""


class TwelveDataClient:
    """yfinance を使った株価データクライアント。API キー不要。"""

    def __init__(self, api_key: str = ""):
        pass

    def get_quote(self, symbol: str) -> dict:
        normalized = self._normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(normalized)
            fi = ticker.fast_info
            info = _safe_info(ticker)

            try:
                price = fi.last_price
                prev_close = fi.previous_close
            except (KeyError, AttributeError):
                return {}  # 存在しない銘柄 → service 側で None として扱う

            if price is None or prev_close is None:
                return {}

            # market_cap は fast_info から取得（info より安定。Cloud環境でも動く）
            try:
                market_cap = fi.market_cap
            except (KeyError, AttributeError):
                market_cap = info.get("marketCap")

            # 配当利回り：info 失敗時は dividends（chart エンドポイント）から計算
            div_yield = info.get("dividendYield") or _calc_div_yield(ticker, price)

            # PER/PBR：info が取れない環境ではブラウザ風リクエストでフォールバック
            pe_value = info.get("trailingPE")
            pb_value = info.get("priceToBook")
            if pe_value is None or pb_value is None:
                fundamentals = _fetch_fundamentals(normalized)
                pe_value = pe_value or fundamentals.get("trailingPE")
                pb_value = pb_value or fundamentals.get("priceToBook")

            return {
                "close": price,
                "previous_close": prev_close,
                "volume": fi.last_volume,
                "market_cap": market_cap,
                "pe": pe_value,
                "pb": pb_value,
                "dividend_yield": div_yield if div_yield else None,
            }
        except TwelveDataApiError:
            raise
        except Exception as e:
            raise TwelveDataApiError(f"データの取得に失敗しました: {e}")

    def get_time_series(self, symbol: str, outputsize: int) -> dict:
        normalized = self._normalize_symbol(symbol)
        period = _outputsize_to_period(outputsize)
        try:
            ticker = yf.Ticker(normalized)
            hist = ticker.history(period=period)
            if hist.empty:
                return {"values": []}
            values = [
                {
                    "datetime": dt.strftime("%Y-%m-%d"),
                    "close": str(row["Close"]),
                    "volume": int(row.get("Volume", 0)),
                }
                for dt, row in hist.iterrows()
            ]
            values.reverse()  # サービス層が reversed() するため新しい順で返す
            return {"values": values}
        except TwelveDataApiError:
            raise
        except Exception as e:
            raise TwelveDataApiError(f"チャートデータの取得に失敗しました: {e}")

    def get_profile(self, symbol: str) -> dict:
        normalized = self._normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(normalized)
            info = _safe_info(ticker)
            return {
                "name": info.get("longName") or info.get("shortName", ""),
                "sector": info.get("sector") or info.get("industry", ""),
                "description": info.get("longBusinessSummary", ""),
            }
        except Exception:
            return {}

    def _normalize_symbol(self, symbol: str) -> str:
        """日本株コードに .T サフィックスを付与する。アルファベット含む場合はそのまま。"""
        if re.search(r"[A-Za-z]", symbol):
            return symbol
        return f"{symbol}.T"


def _safe_info(ticker: yf.Ticker) -> dict:
    try:
        info = ticker.info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def _calc_div_yield(ticker: yf.Ticker, price: float) -> float | None:
    """ticker.infoが取れない環境向けに、配当履歴から利回りを計算する。"""
    try:
        divs = ticker.dividends
        if divs is None or len(divs) == 0:
            return None
        one_year_ago = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=1)
        recent = divs[divs.index >= one_year_ago]
        if len(recent) == 0:
            return None
        annual_div = float(recent.sum())
        if price > 0 and annual_div > 0:
            return (annual_div / price) * 100
        return None
    except Exception:
        return None


def _fetch_fundamentals(symbol: str) -> dict:
    """Kabutan（株探）からPER・PBRを取得する（日本株専用）。
    Yahoo Finance US の quoteSummary はクラウド環境でIP制限されるため、
    クラウド環境でも安定してアクセスできる国内サイトを使用する。
    """
    if not symbol.endswith(".T"):
        return {}
    code = symbol[:-2]  # ".T" を除去して4桁コードにする
    url = f"https://kabutan.jp/stock/?code={code}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}
        html = resp.text
        # PER・PBRテーブル: data-help="PER" ヘッダーの直後のtbody最初のtr
        m = re.search(
            r'data-help="PER".*?<tbody[^>]*>\s*<tr[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        if not m:
            return {}
        tds = re.findall(r"<td>(.*?)</td>", m.group(1), re.DOTALL)

        def _parse(td_html: str) -> float | None:
            n = re.search(r"[\d.]+", td_html)
            return float(n.group()) if n else None

        result = {}
        if len(tds) >= 1:
            v = _parse(tds[0])
            if v is not None:
                result["trailingPE"] = v
        if len(tds) >= 2:
            v = _parse(tds[1])
            if v is not None:
                result["priceToBook"] = v
        return result
    except Exception:
        return {}


def _outputsize_to_period(outputsize: int) -> str:
    if outputsize <= 30:
        return "1mo"
    elif outputsize <= 90:
        return "3mo"
    elif outputsize <= 180:
        return "6mo"
    return "1y"
