# 目的：Lesson 10 卒業試験のUI
# 作成日：2026-06-08
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit, random

import random

import streamlit as st

from config import GRADUATION_STOCKS
from ui import indicator_helpers


def render_graduation_exam(
    quote_service,
    timeseries_service,
    graduation_service,
) -> None:
    """
    卒業試験セクションを表示する。
    - 試験未開始: 「卒業試験を開始する」ボタン
    - 試験中: 3銘柄カード + 選択 + 理由入力 + フィードバック
    - 完了: graduation_done=True, current_level=9 をセットして rerun
    """
    st.divider()
    st.markdown("## 🎓 Lesson 10: 卒業試験")

    if "graduation_stocks" not in st.session_state:
        _render_exam_intro()
        return

    _render_exam_questions(quote_service, timeseries_service, graduation_service)


def _render_exam_intro() -> None:
    """試験開始前の案内（評価観点チェックリスト + 開始ボタン）。"""
    st.markdown("""
おめでとうございます！9つのLessonを修了しました。
最後に、学んだ指標を使って実際の銘柄分析をしてみましょう。

「知識を持っている」ではなく「判断して行動できる」を確認します。
正解・不正解はありません。根拠の質を評価します。
""")

    with st.container(border=True):
        st.markdown("#### 📋 評価の観点（事前に確認しておきましょう）")
        st.write("AIは以下の観点でフィードバックします：")
        st.write("☐ PER・PBRなどのファンダメンタル指標に触れているか")
        st.write("☐ RSIまたはMACDなどのテクニカル指標に触れているか")
        st.write("☐ トレンドの方向（上向き・下向きなど）に触れているか")
        st.write("☐ 自分の言葉で選んだ理由を説明しているか")

    if st.button("卒業試験を開始する", key="graduation_start_btn", type="primary"):
        st.session_state["graduation_stocks"] = _select_exam_stocks()
        st.rerun()


def _select_exam_stocks() -> list[str]:
    """GRADUATION_STOCKS から3銘柄をランダムに選んでコードリストを返す。"""
    pool = GRADUATION_STOCKS[:]
    random.shuffle(pool)
    return [s["code"] for s in pool[:3]]


def _fetch_exam_stock_data(
    symbols: list[str],
    quote_service,
    timeseries_service,
    period_label: str = "3ヶ月",
) -> dict[str, dict]:
    """
    3銘柄の quote・RSI・MACD方向を取得して dict 形式で返す。
    取得失敗の場合は各フィールドを None にする（クラッシュ回避）。

    ⚠️ period_label は "3ヶ月"（90日）以上を必須とする。
       RSI計算に最低14日、MACD計算に最低26日が必要なため、30日（1ヶ月）では不足する。

    戻り値例:
    {
        "7203": {
            "name": "トヨタ自動車",
            "price": 3400.0,
            "pe_ratio": 8.2,
            "pb_ratio": 1.1,
            "rsi": 55.0,
            "macd_direction": "上向き",
        },
        ...
    }
    """
    if "graduation_stocks_data" in st.session_state:
        return st.session_state["graduation_stocks_data"]

    stock_names = {s["code"]: s["name"] for s in GRADUATION_STOCKS}
    result: dict[str, dict] = {}

    for symbol in symbols:
        data: dict = {
            "name": stock_names.get(symbol, symbol),
            "price": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "rsi": None,
            "macd_direction": "―",
        }
        try:
            quote = quote_service.get(symbol)
            if quote:
                data["price"] = quote.price
                data["pe_ratio"] = quote.pe_ratio
                data["pb_ratio"] = quote.pb_ratio
        except Exception:
            pass

        try:
            series = timeseries_service.get(symbol, period_label)
            if series and series.data:
                closes = [p.close for p in series.data]
                data["rsi"] = indicator_helpers.get_latest_rsi(closes)
                data["macd_direction"] = indicator_helpers.get_macd_direction(closes)
        except Exception:
            pass

        result[symbol] = data

    st.session_state["graduation_stocks_data"] = result
    return result


def _render_stock_card(symbol: str, data: dict) -> None:
    """1銘柄のカード（名前・株価・PER・PBR・RSI・MACD方向）を表示する。"""
    with st.container(border=True):
        st.markdown(f"**{data.get('name', symbol)}**")
        st.caption(symbol)
        st.divider()
        price = f"¥{data['price']:,.0f}" if data.get("price") is not None else "―"
        per = f"{data['pe_ratio']:.1f}倍" if data.get("pe_ratio") is not None else "―"
        pbr = f"{data['pb_ratio']:.2f}倍" if data.get("pb_ratio") is not None else "―"
        rsi = f"{data['rsi']:.0f}" if data.get("rsi") is not None else "―"
        macd = data.get("macd_direction", "―")
        st.write(f"株価: {price}")
        st.write(f"PER: {per}")
        st.write(f"PBR: {pbr}")
        st.write(f"RSI: {rsi}")
        st.write(f"MACD: {macd}")


def _render_exam_questions(quote_service, timeseries_service, graduation_service) -> None:
    """試験中の表示: 3銘柄カード + 選択 + 理由入力 + フィードバックボタン。"""
    symbols: list[str] = st.session_state["graduation_stocks"]

    if "graduation_stocks_data" not in st.session_state:
        with st.spinner("銘柄データを取得中... しばらくお待ちください"):
            stocks_data = _fetch_exam_stock_data(symbols, quote_service, timeseries_service)
    else:
        stocks_data = _fetch_exam_stock_data(symbols, quote_service, timeseries_service)

    all_failed = all(data.get("price") is None for data in stocks_data.values())

    st.markdown("#### 今日の分析対象（本日のランダム3銘柄）")
    cols = st.columns(3)
    for i, (symbol, data) in enumerate(stocks_data.items()):
        with cols[i]:
            _render_stock_card(symbol, data)

    st.caption("⚠️ このデータは学習目的のリアルタイムデータです。投資判断には使用しないでください。")

    if all_failed:
        st.error("データを取得できませんでした。ページをリロードして再試行してください。")
        return

    st.markdown("#### あなたが今日1株買うとしたら、どれを選びますか？")

    stock_options = [
        f"{data['name']}（{symbol}）" for symbol, data in stocks_data.items()
    ]
    symbol_by_option = {
        f"{data['name']}（{symbol}）": symbol for symbol, data in stocks_data.items()
    }
    name_by_symbol = {symbol: data["name"] for symbol, data in stocks_data.items()}

    st.radio(
        "銘柄を選択",
        options=stock_options,
        key="graduation_selected_option",
        label_visibility="collapsed",
        index=None,
    )

    st.text_area(
        "なぜそう判断しましたか？（複数の指標を使って説明してください）",
        placeholder="例：「RSIが50付近で中立、MACDが上向きのため上昇トレンドの可能性があると判断しました。またPERが低く割安候補と考えました...」",
        key="graduation_input",
        height=150,
        max_chars=500,
    )

    if st.button("AIにフィードバックをもらう", key="graduation_feedback_btn", type="primary"):
        selected_option = st.session_state.get("graduation_selected_option")
        user_input = st.session_state.get("graduation_input", "").strip()

        if not selected_option:
            st.warning("銘柄を選択してください。")
            return
        if not user_input:
            st.warning("判断理由を入力してください。")
            return

        selected_symbol = symbol_by_option[selected_option]
        selected_name = name_by_symbol[selected_symbol]

        with st.spinner("AIがフィードバックを生成中...（最大10秒）"):
            try:
                feedback = graduation_service.get_feedback(
                    selected_symbol, selected_name, user_input, stocks_data
                )
                st.session_state["graduation_feedback"] = feedback
                st.session_state["graduation_done"] = True
                st.session_state["current_level"] = 9
                st.rerun()
            except Exception:
                st.error("フィードバックの生成に失敗しました。しばらく待ってから再試行してください。")
                return


def render_goal_screen() -> None:
    """GOAL達成画面を表示する。自由分析モードへの切り替えボタン付き。"""
    feedback = st.session_state.get("graduation_feedback")
    if feedback:
        with st.container(border=True):
            st.markdown("### 🤖 AIからのフィードバック")
            st.write(feedback)
            st.caption("※ このフィードバックは学習目的のものです。投資の推奨・売買の助言ではありません。")

    st.divider()
    st.markdown("## 🎉 おめでとうございます！マナトレ卒業！")

    with st.container(border=True):
        st.markdown("""
全10Lessonを修了し、卒業試験をクリアしました。

あなたは:
✅ 株の基礎を理解しました
✅ PER・PBRでファンダメンタル分析ができます
✅ テクニカル指標（ローソク足・MA・RSI・MACD）を使えます
✅ 複数の指標を組み合わせて分析できます
✅ 最初の1株を買う準備ができています！
""")

    if st.button("もう一度分析する（自由分析モードへ）", key="goal_to_free_btn", type="primary"):
        st.session_state["track"] = "free"
        st.rerun()
