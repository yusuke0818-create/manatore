# 目的：マナトレ（投資学習ツール）のエントリポイント。処理フローのみ記述。
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit, plotly, yfinance

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from clients.claude_client import ClaudeClient
from clients.newsdata_client import NewsdataClient
from clients.twelve_data_client import (
    TwelveDataApiError,
    TwelveDataClient,
    TwelveDataNetworkError,
    TwelveDataRateLimitError,
)
from config import CHART_DEFAULT_PERIOD
from services.ai_explanation_service import AiExplanationService
from services.news_search_service import NewsSearchService
from services.stock_profile_service import StockProfileService
from services.stock_quote_service import StockQuoteService
from services.stock_timeseries_service import StockTimeSeriesService
from ui import components, glossary


def main() -> None:
    st.set_page_config(page_title="マナトレ — 投資学習ツール", page_icon="📈", layout="wide")
    st.title("📈 マナトレ — 投資学習ツール")

    glossary.load()

    # サービス初期化
    client = TwelveDataClient()
    quote_service = StockQuoteService(client)
    timeseries_service = StockTimeSeriesService(client)
    profile_service = StockProfileService(client)
    explanation_service = AiExplanationService(ClaudeClient())
    news_service = NewsSearchService(NewsdataClient())

    # ① 免責バナー
    components.render_disclaimer_banner()

    # ② 銘柄選択
    symbol = components.render_stock_selector()
    if not symbol:
        st.info("上のボタンまたはコード入力で銘柄を選択してください。")
        components.render_daily_word()
        return

    # ③ バリデーション
    error_msg = components.validate_symbol(symbol)
    if error_msg:
        components.render_error(error_msg)
        components.render_daily_word()
        return

    # ④ データ取得
    with st.spinner("データを取得中..."):
        try:
            profile = profile_service.get(symbol)
            quote = quote_service.get(symbol)
        except TwelveDataRateLimitError as e:
            st.error(str(e))
            components.render_daily_word()
            return
        except TwelveDataNetworkError as e:
            st.error(str(e))
            components.render_daily_word()
            return
        except TwelveDataApiError as e:
            st.error(str(e))
            components.render_daily_word()
            return

    if quote is None:
        components.render_error(
            f"銘柄コード「{symbol}」が見つかりませんでした。例: 7203（トヨタ）"
        )
        components.render_daily_word()
        return

    # ⑤ 企業情報・株価表示
    components.render_company_info(profile)
    components.render_stock_price(quote)

    # ⑥ AI解説エリア（ボタン押下時のみ生成）
    components.render_ai_explanation_area(symbol, quote, profile, explanation_service)

    # ⑦ チャート（期間をセッションステートで管理）
    if "chart_period" not in st.session_state:
        st.session_state["chart_period"] = CHART_DEFAULT_PERIOD

    with st.spinner("チャートを読み込み中..."):
        try:
            series = timeseries_service.get(symbol, st.session_state["chart_period"])
        except (TwelveDataApiError, TwelveDataNetworkError):
            series = None

    new_period = components.render_chart_tabs(series, st.session_state["chart_period"])
    if new_period != st.session_state["chart_period"]:
        st.session_state["chart_period"] = new_period
        st.rerun()

    # ⑧ 主要指標
    components.render_indicators(quote)

    # ⑨ ニュースエリア
    components.render_news_area(symbol, profile, news_service)

    # ⑩ 今日の学習用語
    components.render_daily_word()

    # フッター
    components.render_footer(quote.fetched_at)


if __name__ == "__main__":
    main()
