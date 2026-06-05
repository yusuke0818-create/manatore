# 目的：newsdata.io を使ったニュース検索サービス
# 作成日：2026-06-04
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（clients/newsdata_client.py に依存）

from clients.newsdata_client import NewsdataClient
from models.stock_models import NewsItem


class NewsSearchService:
    def __init__(self, client: NewsdataClient) -> None:
        self._client = client

    def get(self, symbol: str, company_name: str) -> list[NewsItem]:
        """会社名でニュースを検索し、最大5件を返す。会社名が空の場合はシンボルで検索。"""
        query = company_name.strip() if company_name else symbol
        results = self._client.search(query)
        items = []
        for r in results[:5]:
            items.append(NewsItem(
                title=r.get("title") or "タイトルなし",
                description=r.get("description"),
                pub_date=r.get("pubDate", ""),
                link=r.get("link", ""),
            ))
        return items
