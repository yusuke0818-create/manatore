# 目的：newsdata.io REST API クライアント
# 作成日：2026-06-04
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：requests

import os

import requests


class NewsdataApiError(Exception):
    """newsdata.io API エラー用例外"""


class NewsdataNetworkError(NewsdataApiError):
    """ネットワーク接続エラー用例外"""


class NewsdataClient:
    """newsdata.io REST API クライアント。環境変数 NEWSDATA_API_KEY を使用。"""

    _BASE_URL = "https://newsdata.io/api/1/news"

    def __init__(self) -> None:
        self._api_key: str = os.environ.get("NEWSDATA_API_KEY", "")

    def search(self, query: str, language: str | None = None) -> list[dict]:
        """指定クエリでニュースを検索し、生の結果リストを返す。最大5件。"""
        if not self._api_key:
            raise NewsdataApiError("NEWSDATA_API_KEY が設定されていません。.env に追記してください。")
        try:
            params: dict = {"apikey": self._api_key, "q": query, "size": 5}
            if language:
                params["language"] = language
            response = requests.get(
                self._BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                raise NewsdataApiError(f"ニュースの取得に失敗しました: {data.get('message', '不明なエラー')}")
            return data.get("results", [])
        except requests.exceptions.ConnectionError as e:
            raise NewsdataNetworkError(f"ネットワーク接続エラー: {e}")
        except requests.exceptions.Timeout:
            raise NewsdataNetworkError("タイムアウト: ニュースの取得に時間がかかりすぎました。")
        except requests.exceptions.HTTPError as e:
            raise NewsdataApiError(f"HTTP エラー: {e}")
        except NewsdataApiError:
            raise
        except Exception as e:
            raise NewsdataApiError(f"ニュースの取得中に予期しないエラーが発生しました: {e}")
