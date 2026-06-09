# 目的：マナトレ（投資学習ツール）のエントリポイント。処理フローのみ記述。
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit, plotly, yfinance

import os

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

# Streamlit Cloud: st.secrets → os.environ に転送（os.environ.get()で読む既存コードと互換）
# ⚠️ フラット形式のみ対応。[section]形式のネストセクションはスキップされる。
# secrets.toml は必ずフラット形式（ANTHROPIC_API_KEY = "..." 等）で記載すること。
try:
    for _key, _val in st.secrets.items():
        if isinstance(_val, str):
            os.environ.setdefault(_key, _val)
except Exception:
    pass  # ローカル環境で secrets.toml がない場合は .env から読む

from clients.claude_client import ClaudeClient
from clients.newsdata_client import NewsdataClient
from clients.twelve_data_client import (
    TwelveDataApiError,
    TwelveDataClient,
    TwelveDataNetworkError,
    TwelveDataRateLimitError,
)
from services.ai_explanation_service import AiExplanationService
from services.graduation_service import GraduationService
from services.news_search_service import NewsSearchService
from services.stock_profile_service import StockProfileService
from services.stock_quote_service import StockQuoteService
from services.stock_timeseries_service import StockTimeSeriesService
from ui import components, glossary, graduation_exam, lesson_beginner, lesson_stubs


def main() -> None:
    st.set_page_config(page_title="マナトレ — 投資学習ツール", page_icon="📈", layout="wide")
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stToolbar"] {display: none;}
        [data-testid="manage-app-button"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("📈 マナトレ — 投資学習ツール")

    glossary.load()

    # サービス初期化
    client = TwelveDataClient()
    quote_service = StockQuoteService(client)
    timeseries_service = StockTimeSeriesService(client)
    profile_service = StockProfileService(client)
    claude_client = ClaudeClient()
    explanation_service = AiExplanationService(claude_client)
    graduation_service = GraduationService(claude_client)
    news_service = NewsSearchService(NewsdataClient())

    # ① 免責バナー
    components.render_disclaimer_banner()

    # ② トラック選択
    track = components.render_track_selector()
    if track is None:
        components.render_daily_word()
        return

    # ③ トラック別処理
    if track == "beginner":
        _run_beginner_course(
            quote_service, timeseries_service,
            profile_service, explanation_service, news_service,
            graduation_service,
        )
    else:
        _run_free_mode(
            quote_service, timeseries_service,
            profile_service, explanation_service, news_service,
        )


def _run_free_mode(
    quote_service,
    timeseries_service,
    profile_service,
    explanation_service,
    news_service,
) -> None:
    """自由分析モード: 既存のmain()フローをそのまま実行。"""
    # ④ 銘柄選択
    symbol = components.render_stock_selector()
    if not symbol:
        st.info("上のボタンまたはコード入力で銘柄を選択してください。")
        components.render_daily_word()
        return

    # ⑤ バリデーション
    error_msg = components.validate_symbol(symbol)
    if error_msg:
        components.render_error(error_msg)
        components.render_daily_word()
        return

    # ⑥ データ取得
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

    # ⑦ 企業情報・株価表示
    components.render_company_info(profile)
    components.render_stock_price(quote)

    # ⑧ AI解説エリア
    components.render_ai_explanation_area(symbol, quote, profile, explanation_service)

    # ⑨ チャート
    components.render_chart_section(
        symbol, profile.name, timeseries_service, explanation_service
    )

    # ⑩ 主要指標
    components.render_indicators(quote)

    # ⑪ 投資スタートガイド
    components.render_investment_guide()

    # ⑫ ニュースエリア
    components.render_news_area(symbol, profile, news_service)

    # ⑬ 今日の学習用語
    components.render_daily_word()

    # フッター
    components.render_footer(quote.fetched_at)


def _run_beginner_course(
    quote_service,
    timeseries_service,
    profile_service,
    explanation_service,
    news_service,
    graduation_service,
) -> None:
    """初心者コース: Level Mapに応じたLessonを表示。"""
    current_level = st.session_state.get("current_level", 0)

    # graduation_done フラグと current_level の同期（リロード後の整合性保証）
    if st.session_state.get("graduation_done") and current_level != 9:
        st.session_state["current_level"] = 9
        st.rerun()

    # Level Map常時表示
    components.render_level_map(current_level)

    # GOAL到達済み
    if current_level == 9:
        graduation_exam.render_goal_screen()
        components.render_daily_word()
        return

    # Lesson 0-3: 銘柄データ不要
    if current_level == 0:
        lesson_beginner.render_lesson_0()
        components.render_daily_word()
        return
    if current_level == 1:
        lesson_beginner.render_lesson_1(explanation_service)
        components.render_daily_word()
        return
    if current_level == 2:
        lesson_beginner.render_lesson_2()
        components.render_daily_word()
        return
    if current_level == 3:
        lesson_beginner.render_lesson_3()
        components.render_daily_word()
        return

    # Level 8: 購入準備スタブ + 卒業試験（銘柄選択不要 — 卒業試験は GRADUATION_STOCKS 独自の3銘柄を使用するため）
    if current_level == 8:
        if lesson_stubs.render_lesson_8_stub():      # True = 購入準備未完了
            components.render_daily_word()
            return
        graduation_exam.render_graduation_exam(      # 購入準備完了済みのときのみ到達
            quote_service, timeseries_service, graduation_service
        )
        components.render_daily_word()
        return

    # Lesson 3-7: スタブ + 銘柄データ表示
    if current_level in (4, 5, 7):
        lesson_stubs.render_lesson_stub(current_level)
    elif current_level == 6:
        lesson_stubs.render_lesson_6_stub()  # 2段階進行（RSI + MACD）

    # 銘柄選択・データ取得（初心者コース用プリセット推奨メッセージ付き）
    symbol = components.render_stock_selector(beginner_mode=True)
    if not symbol:
        st.info("上のボタンから銘柄を選択してください。プリセット5銘柄がおすすめです。")
        components.render_daily_word()
        return

    error_msg = components.validate_symbol(symbol)
    if error_msg:
        components.render_error(error_msg)
        components.render_daily_word()
        return

    with st.spinner("データを取得中..."):
        try:
            profile = profile_service.get(symbol)
            quote = quote_service.get(symbol)
        except (TwelveDataRateLimitError, TwelveDataNetworkError, TwelveDataApiError) as e:
            st.error(str(e))
            components.render_daily_word()
            return

    if quote is None:
        components.render_error(f"銘柄コード「{symbol}」が見つかりませんでした。")
        components.render_daily_word()
        return

    # 既存コンポーネント表示
    components.render_company_info(profile)
    components.render_stock_price(quote)
    components.render_ai_explanation_area(symbol, quote, profile, explanation_service)

    components.render_chart_section(
        symbol, profile.name, timeseries_service, explanation_service
    )

    components.render_indicators(quote)
    components.render_investment_guide()
    components.render_news_area(symbol, profile, news_service)

    components.render_daily_word()
    components.render_footer(quote.fetched_at)


if __name__ == "__main__":
    main()
