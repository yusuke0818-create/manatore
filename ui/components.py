# 目的：Streamlit 画面コンポーネント群
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit, plotly, pandas

import json
import math
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as psp
import streamlit as st

from clients.twelve_data_client import TwelveDataApiError, TwelveDataNetworkError
from config import APP_LAUNCH_DATE, CHART_DEFAULT_PERIOD, CHART_PERIODS, PRESET_SYMBOLS
from models.stock_models import StockProfile, StockQuote, TimeSeries
from ui import glossary
from ui.indicator_helpers import calc_macd, calc_rsi


def _safe_url(url: str) -> str:
    """http/https 以外のスキームを除去する（XSS対策）。"""
    return url if re.match(r"^https?://", url, re.IGNORECASE) else "#"

_DISCLAIMER_PATH = Path(__file__).parent.parent / "data" / "disclaimer.txt"
_LEARNING_WORDS_PATH = Path(__file__).parent.parent / "data" / "learning_words.json"


def render_disclaimer_banner() -> None:
    """免責バナーを常時表示する。"""
    try:
        text = _DISCLAIMER_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        text = "⚠️ このツールは学習・情報提供を目的としています。投資助言・売買の推奨は一切行いません。"
    st.warning(text)


_LEVEL_LABELS = ["L0\n入門", "L1\n基礎", "L2\n企業", "L3\nファンダ", "L4\nチャート", "L5\nトレンド", "L6\n指標", "L7\n総合", "L8\n準備", "GOAL\n卒業"]
_LEVEL_NAMES = {
    0: "マナトレ入門", 1: "株の基礎", 2: "企業価値の見方", 3: "ファンダメンタル分析",
    4: "チャート基礎", 5: "トレンド分析", 6: "モメンタム分析", 7: "総合分析",
    8: "購入準備", 9: "GOAL",
}


def render_track_selector() -> str | None:
    """
    2トラック選択UIを表示する。
    - 未選択の場合: ホーム画面を表示し None を返す
    - 選択済みの場合: 選択中のトラック名（"beginner" | "free"）を返す
    """
    track = st.session_state.get("track")

    if track is None:
        st.markdown("## 📈 マナトレへようこそ")
        st.markdown("**あなたはどちらですか？**")
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("#### 🎓 投資初心者")
                st.write("Lesson 0から順番に投資を学ぶ")
                if st.button("学習コースを始める", key="track_beginner_btn", type="primary", use_container_width=True):
                    st.session_state["track"] = "beginner"
                    st.session_state["symbol"] = None
                    if "manual_input" in st.session_state:
                        del st.session_state["manual_input"]
                    st.rerun()
        with col2:
            with st.container(border=True):
                st.markdown("#### 📊 経験者・確認用")
                st.write("銘柄・チャートをすぐに確認したい方")
                if st.button("自由分析を始める", key="track_free_btn", type="primary", use_container_width=True):
                    st.session_state["track"] = "free"
                    st.rerun()
        return None

    if track == "free":
        if st.button("← コース選択に戻る", key="back_to_home_btn"):
            st.session_state["track"] = None
            st.rerun()

    return track


def render_level_map(current_level: int) -> None:
    """
    Level Mapを表示する。current_level は 0〜9（9=GOAL）。
    - 完了（< current_level）: ✅
    - 現在（== current_level、ただし 9 は 🎉）: 🔵
    - 未到達（> current_level）: ⬜
    - 「自由分析モードへ切り替える」ボタン付き
    """
    with st.container(border=True):
        st.markdown("##### 📍 学習マップ")
        cols = st.columns(10)
        for i, label in enumerate(_LEVEL_LABELS):
            if i < current_level:
                icon = "✅"
            elif i == current_level:
                icon = "🎉" if i == 9 else "🔵"
            else:
                icon = "⬜"
            cols[i].markdown(f"<div style='text-align:center'>{icon}<br><small>{label}</small></div>", unsafe_allow_html=True)

        if current_level == 9:
            level_name = "GOAL — 卒業完了！"
        else:
            level_name = f"Level {current_level} — {_LEVEL_NAMES.get(current_level, '')}"
        st.caption(f"現在: {level_name}")

        if st.button("自由分析モードへ切り替える", key="level_map_to_free_btn"):
            st.session_state["track"] = "free"
            st.rerun()


def render_stock_selector(beginner_mode: bool = False) -> str | None:
    """プリセットボタン + 手入力で銘柄コードを返す。未選択時は None。"""
    if beginner_mode:
        st.info("📌 おすすめ銘柄（プリセット）で練習しましょう。下のボタンから選択してください。")
    st.subheader("銘柄を選択")

    st.write("よく使う銘柄:")
    cols = st.columns(len(PRESET_SYMBOLS))
    for i, item in enumerate(PRESET_SYMBOLS):
        if cols[i].button(item["label"], key=f"preset_{item['code']}"):
            st.session_state["symbol"] = item["code"]

    st.write("銘柄コードで直接検索:")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        manual_input = st.text_input(
            "銘柄コード",
            placeholder="例: 7203",
            label_visibility="collapsed",
            key="manual_input",
        )
    with col_btn:
        if st.button("検索", key="search_btn"):
            code = manual_input.strip()
            if code:
                st.session_state["symbol"] = code
            else:
                st.session_state["symbol"] = None

    return st.session_state.get("symbol")


def validate_symbol(symbol: str) -> str | None:
    """シンボルバリデーション。問題がある場合はエラーメッセージ文字列を返す。問題なければ None。"""
    import re
    if re.search(r"[A-Za-z]", symbol):
        return "日本株のみ対応しています。銘柄コードは数字4桁（例: 7203）で入力してください。"
    if not re.fullmatch(r"\d{4}", symbol):
        return "銘柄コードは数字4桁で入力してください（例: 7203）。"
    return None


def render_company_info(profile: StockProfile) -> None:
    """企業情報カードを表示する。"""
    with st.container(border=True):
        st.markdown(f"### 🏢 {profile.name}（{profile.symbol}）")
        if profile.sector:
            st.caption(f"業種: {profile.sector}")
        st.write(profile.description)


def render_stock_price(quote: StockQuote) -> None:
    """株価情報を3カラムで表示する。前日比は色分けする。"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("現在株価", f"¥{quote.price:,.0f}")

    with col2:
        sign = "+" if quote.change >= 0 else ""
        delta_str = f"{sign}{quote.change:,.0f}円 ({sign}{quote.change_percent:.2f}%)"
        st.metric("前日比", delta_str, delta=quote.change_percent)

    with col3:
        st.metric("出来高", f"{quote.volume:,}")

    st.caption(f"取得時刻: {quote.fetched_at.strftime('%Y-%m-%d %H:%M')} JST")


def render_ai_explanation_area(
    symbol: str,
    quote,
    profile,
    explanation_service,
) -> None:
    """AI解説エリアを表示する。ボタン押下時のみ Claude API を呼び出す。"""
    if st.session_state.get("_ai_symbol") != symbol:
        st.session_state["_ai_symbol"] = symbol
        st.session_state.pop("ai_explanation", None)

    with st.container(border=True):
        st.markdown("#### 💡 この銘柄をAIが解説します")
        st.caption("🤖 AIによる解説（Claude Haiku 4.5）")

        explanation = st.session_state.get("ai_explanation")
        if explanation is None:
            if st.button("解説を見る", key="btn_ai_explanation"):
                with st.spinner("AI解説を生成中...（最大10秒）"):
                    try:
                        text = explanation_service.get(symbol, quote, profile)
                        st.session_state["ai_explanation"] = text
                    except Exception:
                        st.error("AI解説の生成に失敗しました。しばらく待ってから再試行してください。")
                        return
                st.rerun()
        else:
            st.write(explanation)
            st.caption("※ AIによる解説です。投資判断の根拠に使用しないでください。")


def render_chart_tabs(
    series: TimeSeries | None,
    period_label: str,
    symbol: str = "",
    company_name: str = "",
    explanation_service=None,
) -> str:
    """チャートエリア（期間ボタン＋7タブ）を表示する。選択中の期間ラベルを返す。"""
    st.subheader("📊 チャート")

    # 期間切り替えボタン
    period_labels = [p["label"] for p in CHART_PERIODS]
    cols = st.columns(len(period_labels))
    selected = period_label
    for i, label in enumerate(period_labels):
        btn_type = "primary" if label == period_label else "secondary"
        if cols[i].button(label, key=f"period_{label}", type=btn_type):
            selected = label

    tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["ローソク足", "株価推移", "移動平均線", "出来高", "RSI", "MACD", "複数指標"]
    )

    with tab0:
        _render_candlestick_chart(series)
        _render_understanding_check_candlestick()

    with tab1:
        _render_timeseries_chart(series)

    with tab2:
        _render_ma_chart(series)
        _render_understanding_check_ma()

    with tab3:
        _render_guidance_card(
            tab_name="出来高",
            prerequisites=["株価推移（Step1）", "移動平均線（Step2）"],
        )
        _render_volume_chart(series)
        _render_understanding_check_volume()

    with tab4:
        _render_guidance_card(
            tab_name="RSI",
            prerequisites=["株価推移（Step1）", "移動平均線（Step2）", "出来高（Step3）"],
        )
        _render_rsi_chart(series)
        _render_understanding_check_rsi()

    with tab5:
        _render_guidance_card(
            tab_name="MACD",
            prerequisites=["株価推移（Step1）", "移動平均線（Step2）", "出来高（Step3）", "RSI（Step4）"],
        )
        _render_macd_chart(series)
        _render_understanding_check_macd()

    with tab6:
        st.markdown("### あなたはどのタイプの投資家？")
        _render_investment_methods()
        st.divider()
        st.markdown("### Part 2: 現在の状況を6指標で確認する")
        _render_step6_integrated_chart(series)
        snapshot = _compute_step6_snapshot(series)
        _render_step6_snapshot(snapshot)
        st.divider()
        _render_step6_case_study(snapshot, symbol, company_name, explanation_service)

    return selected


@st.fragment
def render_chart_section(
    symbol: str,
    company_name: str,
    timeseries_service,
    explanation_service,
) -> None:
    """チャートセクション（期間選択 + タブ）をfragmentとして描画。
    期間ボタン押下時はfragmentのみrerunし、ページ全体のスクロールトップを防ぐ。
    """
    if "chart_period" not in st.session_state:
        st.session_state["chart_period"] = CHART_DEFAULT_PERIOD

    with st.spinner("チャートを読み込み中..."):
        try:
            series = timeseries_service.get(symbol, st.session_state["chart_period"])
        except (TwelveDataApiError, TwelveDataNetworkError):
            series = None

    new_period = render_chart_tabs(
        series, st.session_state["chart_period"],
        symbol=symbol, company_name=company_name, explanation_service=explanation_service,
    )
    if new_period != st.session_state["chart_period"]:
        st.session_state["chart_period"] = new_period
        st.rerun(scope="fragment")


def _render_candlestick_chart(series: TimeSeries | None) -> None:
    """ローソク足チャート（陽線#26a69a・陰線#ef5350）を表示する。"""
    st.markdown("#### 📊 Step0: ローソク足チャート")
    st.markdown("**── まずここから！チャートの基本を身につけよう ──**")

    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
    else:
        dates = [p.date for p in series.data]
        opens = [p.open for p in series.data]
        highs = [p.high for p in series.data]
        lows = [p.low for p in series.data]
        closes = [p.close for p in series.data]

        fig = go.Figure(data=[
            go.Candlestick(
                x=dates,
                open=opens,
                high=highs,
                low=lows,
                close=closes,
                increasing_line_color="#26a69a",
                increasing_fillcolor="#26a69a",
                decreasing_line_color="#ef5350",
                decreasing_fillcolor="#ef5350",
                name="ローソク足",
            )
        ])
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=400,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("陽線（緑）: 終値 > 始値（上昇した日） / 陰線（赤）: 終値 < 始値（下落した日）")

    with st.container(border=True):
        st.markdown("#### ローソク足の見方")
        st.markdown("""
```
  上ヒゲ    ← その日の最高値
    ┃
  ┌─┃─┐  ← 始値（始まりの価格）
  │ ┃ │  ← 実体（始値と終値の差）
  └─┃─┘  ← 終値（終わりの価格）
    ┃
  下ヒゲ    ← その日の最安値
```

**■ ヒゲが長いと何を意味する？**
上ヒゲが長い → 高値まで上がったが売られて押し返された
下ヒゲが長い → 安値まで下がったが買われて戻した
""")

    with st.container(border=True):
        st.markdown("#### 酒田五法（主要パターン概要）")
        st.markdown("""
・**三山（さんざん）**: 3回の高値山形 → 天井のサイン
・**三川（さんせん）**: 3回の安値谷形 → 底値のサイン
・**三空（さんくう）**: 連続する窓開け → 転換のサイン
・**三兵（さんぺい）**: 陽線/陰線が3本続く → トレンド継続
・**三法（さんぽう）**: 持ち合いからの放れ → 次のトレンドへ
""")
        st.caption("※ 酒田五法はパターンの概要紹介です。詳細は専門書で学習してください。")


def _render_understanding_check_candlestick() -> None:
    """ローソク足タブ末尾の理解チェック（任意参加・選択式1問）。"""
    st.divider()
    st.markdown("#### ✅ ローソク足 理解チェック（任意）")

    state_key = "check_state_candlestick"
    current_state = st.session_state.get(state_key)

    if current_state == "passed":
        with st.container(border=True):
            st.success("🎉 正解！")
            st.write("「終値が始値より高い状態」が正解です。")
            st.write(
                "陽線は1日の取引で株価が上昇したことを示します。"
                "上ヒゲ・下ヒゲの長さを見ることで、その日の値動きの勢いや反発の強さも読み取れます。"
            )
            st.markdown("**ローソク足の理解チェック 合格 ✅**")
        return

    if current_state == "failed":
        with st.container(border=True):
            st.warning("もう一度考えてみましょう")
            st.write(
                "陽線は「始値より終値が高い」＝その日に株価が上昇した状態です。"
                "陰線は逆に「始値より終値が低い」＝下落した状態を表します。"
            )
            if st.button("もう一度チャレンジ", key="check_retry_candlestick"):
                del st.session_state[state_key]
                st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. 陽線（緑のローソク）とはどのような状態ですか？**")
        answer = st.radio(
            "回答を選んでください",
            options=[
                "始値が終値より高い状態",
                "終値が始値より高い状態",
                "高値と安値の差が大きい状態",
                "出来高が多い状態",
            ],
            key="check_radio_candlestick",
            label_visibility="collapsed",
            index=None,
        )
        if st.button("回答する", key="check_submit_candlestick"):
            if answer is None:
                st.warning("回答を選んでください。")
            elif answer == "終値が始値より高い状態":
                st.session_state[state_key] = "passed"
                st.rerun()
            else:
                st.session_state[state_key] = "failed"
                st.rerun()


def _render_timeseries_chart(series: TimeSeries | None) -> None:
    """株価推移チャート（シンプルライン）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=closes,
        mode="lines",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="%{x}<br>¥%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="日付",
        yaxis_title="株価（円）",
        showlegend=False,
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_ma_chart(series: TimeSeries | None) -> None:
    """移動平均線チャート（5日・25日・75日MA オーバーレイ）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]
    s = pd.Series(closes)
    ma5 = s.rolling(window=5).mean().tolist()
    ma25 = s.rolling(window=25).mean().tolist()
    ma75 = s.rolling(window=75).mean().tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=closes, mode="lines", name="株価",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="%{x}<br>株価 ¥%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=ma5, mode="lines", name="MA5（短期）",
        line=dict(color="#ff7f0e", width=1.5, dash="dot"),
        hovertemplate="%{x}<br>MA5 ¥%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=ma25, mode="lines", name="MA25（中期）",
        line=dict(color="#2ca02c", width=1.5),
        hovertemplate="%{x}<br>MA25 ¥%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=ma75, mode="lines", name="MA75（長期）",
        line=dict(color="#d62728", width=1.5, dash="dash"),
        hovertemplate="%{x}<br>MA75 ¥%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="日付",
        yaxis_title="株価（円）",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("MA5=5日移動平均（短期）/ MA25=25日移動平均（中期）/ MA75=75日移動平均（長期）")


def _render_macd_chart(series: TimeSeries | None) -> None:
    """MACDチャート（株価推移＋MACD/シグナル/ヒストグラムの2段サブプロット）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]
    macd, signal, histogram = calc_macd(closes)

    colors = []
    for v in histogram:
        if isinstance(v, float) and math.isnan(v):
            colors.append("#aaaaaa")
        elif v >= 0:
            colors.append("#4c72b0")
        else:
            colors.append("#c44e52")

    fig = psp.make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=dates, y=closes, mode="lines", name="株価",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="%{x}<br>株価 ¥%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=macd, mode="lines", name="MACDライン",
        line=dict(color="orange", width=2),
        hovertemplate="%{x}<br>MACD %{y:.2f}<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=signal, mode="lines", name="シグナルライン",
        line=dict(color="red", width=1.5, dash="dash"),
        hovertemplate="%{x}<br>Signal %{y:.2f}<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        x=dates, y=histogram, name="ヒストグラム",
        marker_color=colors,
        hovertemplate="%{x}<br>Hist %{y:.2f}<extra></extra>",
    ), row=2, col=1)

    fig.add_hline(
        y=0, line_dash="dot", line_color="gray", line_width=1,
        row=2, col=1,
    )

    fig.update_yaxes(title_text="株価（円）", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=480,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
**MACD（Moving Average Convergence Divergence / 移動平均収束拡散法）とは？**
短期EMA（12日）と長期EMA（26日）の差（MACDライン）を使って、トレンドの転換点を見極めるテクニカル指標です。
シグナルラインはMACDの9日EMAで、両者の交差がシグナルとなります。

| シグナル | 意味 |
|---------|------|
| **ゴールデンクロス**（MACDがシグナルを下から上に突き抜け） | 買いシグナル |
| **デッドクロス**（MACDがシグナルを上から下に突き抜け） | 売りシグナル |
| **ゼロライン上**（MACD > 0） | 強気トレンド |

📌 **ポイント**: MACDは遅行指標のため、RSIや移動平均線と組み合わせて使うと精度が上がります。偽シグナルに注意しましょう。
""")


def _render_understanding_check_macd() -> None:
    """MACDタブ末尾の理解チェック（任意参加・選択式1問）。"""
    st.divider()
    st.markdown("#### ✅ MACD 理解チェック（任意）")

    state_key = "check_state_macd"
    current_state = st.session_state.get(state_key)

    if current_state == "passed":
        with st.container(border=True):
            st.success("🎉 正解！")
            st.write("「ゴールデンクロス」が正解です。")
            st.write(
                "ゴールデンクロスはMACDラインがシグナルラインを下から上に突き抜けた状態で、"
                "買いシグナルとみなされることが多いです。"
                "ただし偽シグナルもあるため、他の指標と組み合わせて判断することが大切です。"
            )
            st.markdown("**MACDの理解チェック 合格 ✅**")
        st.info(
            "✅ Step5 MACDの理解チェック 合格！\n\n"
            "Step6「複数指標の組み合わせ実践」に進みましょう。\n"
            "ここまで学んだ6つの指標を組み合わせて、実際に銘柄を分析する練習ができます。\n\n"
            "「複数指標」タブを選択してください。"
        )
        return

    if current_state == "failed":
        with st.container(border=True):
            st.warning("もう一度考えてみましょう")
            st.write(
                "デッドクロスはMACDラインがシグナルラインを上から下に突き抜けた場合（売りシグナル）です。"
                "問題の「下から上に突き抜けた」動きはその逆、ゴールデンクロスです。"
            )
            if st.button("もう一度チャレンジ", key="check_retry_macd"):
                del st.session_state[state_key]
                st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. MACDラインがシグナルラインを下から上に突き抜けた場合、これは何と呼ばれますか？**")
        answer = st.radio(
            "回答を選んでください",
            options=["デッドクロス", "ゴールデンクロス"],
            key="check_radio_macd",
            label_visibility="collapsed",
        )
        if st.button("回答する", key="check_submit_macd"):
            if answer == "ゴールデンクロス":
                st.session_state[state_key] = "passed"
            else:
                st.session_state[state_key] = "failed"
            st.rerun()


def _render_rsi_chart(series: TimeSeries | None) -> None:
    """RSIチャート（株価推移＋RSI(14)の2段サブプロット）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]
    rsi = calc_rsi(closes)

    fig = psp.make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=dates, y=closes, mode="lines", name="株価",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="%{x}<br>株価 ¥%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=rsi, mode="lines", name="RSI(14)",
        line=dict(color="#9467bd", width=2),
        hovertemplate="%{x}<br>RSI %{y:.1f}<extra></extra>",
    ), row=2, col=1)

    fig.add_hline(
        y=70, line_dash="dash", line_color="red", line_width=1,
        annotation_text="買われすぎ(70)", annotation_position="bottom right",
        row=2, col=1,
    )
    fig.add_hline(
        y=30, line_dash="dash", line_color="green", line_width=1,
        annotation_text="売られすぎ(30)", annotation_position="top right",
        row=2, col=1,
    )

    fig.update_yaxes(title_text="株価（円）", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
**RSI（Relative Strength Index / 相対力指数）とは？**
株の「買われすぎ」「売られすぎ」を0〜100の数値で表すテクニカル指標です（14日間の値動きをもとに計算）。

| RSI値 | 意味 |
|-------|------|
| **70以上** | 買われすぎ（反落の可能性） |
| **30以下** | 売られすぎ（反発の可能性） |
| 50付近 | 中立 |

📌 **ポイント**: 強いトレンドが続く局面では、70以上・30以下の状態が長続きすることもあります。RSIだけで判断せず、移動平均線や出来高と組み合わせて参考にしましょう。
""")


def _render_understanding_check_rsi() -> None:
    """RSIタブ末尾の理解チェック（任意参加・選択式1問）。"""
    st.divider()
    st.markdown("#### ✅ RSI 理解チェック（任意）")

    state_key = "check_state_rsi"
    current_state = st.session_state.get(state_key)

    if current_state == "passed":
        with st.container(border=True):
            st.success("🎉 正解！")
            st.write("「買われすぎの状態」が正解です。")
            st.write(
                "RSIが70以上になると「買われすぎ」とみなされ、価格が反落する可能性があることを示します。"
                "ただし、強いトレンドが続く場合は70以上の状態が続くこともあるため、"
                "他の指標と組み合わせて判断することが大切です。"
            )
            st.markdown("**RSIの理解チェック 合格 ✅**")
        return

    if current_state == "failed":
        with st.container(border=True):
            st.warning("もう一度考えてみましょう")
            st.write(
                "RSIは0〜100で株の「勢い」を表します。"
                "70以上は「買われすぎ（過熱状態）」、30以下は「売られすぎ」を示します。"
                "80はその逆ではなく、さらに強い買われすぎの状態です。"
            )
            if st.button("もう一度チャレンジ", key="check_retry_rsi"):
                del st.session_state[state_key]
                st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. RSIが80を示している場合、株は通常どのような状態ですか？**")
        answer = st.radio(
            "回答を選んでください",
            options=["売られすぎの状態", "買われすぎの状態"],
            key="check_radio_rsi",
            label_visibility="collapsed",
        )
        if st.button("回答する", key="check_submit_rsi"):
            if answer == "買われすぎの状態":
                st.session_state[state_key] = "passed"
            else:
                st.session_state[state_key] = "failed"
            st.rerun()


def _render_volume_chart(series: TimeSeries | None) -> None:
    """出来高チャート（株価推移＋出来高バーの2段サブプロット）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]
    volumes = [p.volume for p in series.data]

    fig = psp.make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.08,
    )

    fig.add_trace(go.Scatter(
        x=dates, y=closes, mode="lines", name="株価",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="%{x}<br>株価 ¥%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=dates, y=volumes, name="出来高",
        marker_color="#aec7e8",
        hovertemplate="%{x}<br>出来高 %{y:,}<extra></extra>",
    ), row=2, col=1)

    fig.update_yaxes(title_text="株価（円）", row=1, col=1)
    fig.update_yaxes(title_text="出来高", row=2, col=1)
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
**出来高とは？**
1日に取引された株の「量」を表します。出来高が多い日は多くの投資家が売買に参加しており、
株価の動きに信頼性があると考えられます。逆に出来高が少ない日は、少数の取引で株価が動きやすいため注意が必要です。

📌 **ポイント**: 株価が大きく動いた日に出来高も増えている → 多くの投資家が同じ方向に動いたサイン
""")


def _render_understanding_check_volume() -> None:
    """出来高タブ末尾の理解チェック（任意参加・選択式1問）。"""
    st.divider()
    st.markdown("#### ✅ 出来高 理解チェック（任意）")

    state_key = "check_state_volume"
    current_state = st.session_state.get(state_key)

    if current_state == "passed":
        with st.container(border=True):
            st.success("🎉 正解！")
            st.write("「多くの投資家が売買に参加している」が正解です。")
            st.write(
                "出来高が急増するということは、多くの人がその銘柄に注目し売買していることを示します。"
                "ただし、上昇・下落どちらの場面でも起こりうるため、出来高だけで判断しないことが大切です。"
            )
            st.markdown("**出来高の理解チェック 合格 ✅**")
        return

    if current_state == "failed":
        with st.container(border=True):
            st.warning("もう一度考えてみましょう")
            st.write(
                "出来高は「取引された量」を表します。急増した場合、「株価が必ず上昇する」のではなく、"
                "「多くの投資家が関心を持って参加している」ことを意味します。"
            )
            if st.button("もう一度チャレンジ", key="check_retry_volume"):
                del st.session_state[state_key]
                st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. 出来高が急増した場合、それは通常何を示しますか？**")
        answer = st.radio(
            "回答を選んでください",
            options=["株価が必ず上昇する", "多くの投資家が売買に参加している"],
            key="check_radio_volume",
            label_visibility="collapsed",
        )
        if st.button("回答する", key="check_submit_volume"):
            if answer == "多くの投資家が売買に参加している":
                st.session_state[state_key] = "passed"
            else:
                st.session_state[state_key] = "failed"
            st.rerun()


def _render_understanding_check_ma() -> None:
    """移動平均線タブ末尾の理解チェック（任意参加・選択式1問）。"""
    st.divider()
    st.markdown("#### ✅ 移動平均線 理解チェック（任意）")

    state_key = "check_state_ma"
    current_state = st.session_state.get(state_key)

    if current_state == "passed":
        with st.container(border=True):
            st.success("🎉 正解！")
            st.write("「いいえ」が正解です。")
            st.write("移動平均線はあくまで傾向を示す目安です。「上回ったから買う」という判断は危険です。")
            st.markdown("**移動平均線の理解チェック 合格 ✅**")
        return

    if current_state == "failed":
        with st.container(border=True):
            st.warning("もう一度考えてみましょう")
            st.write(
                "移動平均線はトレンドの傾向を示す「目安」です。"
                "株価が上回ったからといって必ず上昇するわけではありません。"
            )
            if st.button("もう一度チャレンジ", key="check_retry_ma"):
                del st.session_state[state_key]
                st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. 株価が移動平均線を上回った場合、必ず買うべきですか？**")
        answer = st.radio(
            "回答を選んでください",
            options=["はい、上回ったら買うべきだ", "いいえ、あくまで目安のひとつだ"],
            key="check_radio_ma",
            label_visibility="collapsed",
        )
        if st.button("回答する", key="check_submit_ma"):
            if answer == "いいえ、あくまで目安のひとつだ":
                st.session_state[state_key] = "passed"
            else:
                st.session_state[state_key] = "failed"
            st.rerun()


def _render_investment_methods() -> None:
    """Step6 Part1: 投資手法解説（テクニカル/ファンダメンタル・4スタイル）。"""
    with st.container(border=True):
        st.markdown("**【分析手法の違い】**")
        st.markdown("""
**■ テクニカル分析（本ツールで学んだ内容）**
チャート・指標を使って売買タイミングを判断する手法
→ MA・RSI・MACDなどがここに含まれる

**■ ファンダメンタル分析**
企業の業績・財務・ビジネスモデルを分析して本来の価値を判断する手法
→ PER・PBR・配当利回りなどがここに含まれる
""")

    with st.container(border=True):
        st.markdown("**【投資スタイルの違い】**")
        st.markdown("""
**■ 長期積立投資**
毎月一定額を積み立てて長期で運用する。リスクが分散され、初心者に最もおすすめ。

**■ バリュー投資**
割安（PBR1倍未満など）な銘柄を探して買い、本来の価値に戻るのを待つ手法。

**■ 成長株投資**
高い成長が期待できる企業に早期から投資する手法。リターンは大きいがリスクも高い。

**■ 短期売買（スイングトレード等）**
数日〜数週間単位で売買する手法。テクニカル分析を重視する。
""")


def _render_step6_integrated_chart(series: TimeSeries | None) -> None:
    """Step6 Part2: 4段統合チャート（ローソク足+MA / 出来高 / RSI / MACD）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    opens = [p.open for p in series.data]
    highs = [p.high for p in series.data]
    lows = [p.low for p in series.data]
    closes = [p.close for p in series.data]
    volumes = [p.volume for p in series.data]

    s = pd.Series(closes)
    ma5 = s.rolling(window=5).mean().tolist()
    ma25 = s.rolling(window=25).mean().tolist()
    rsi = calc_rsi(closes)
    macd_line, signal_line, histogram = calc_macd(closes)

    hist_colors = [
        "#aaaaaa" if (isinstance(v, float) and math.isnan(v)) else ("#4c72b0" if v >= 0 else "#c44e52")
        for v in histogram
    ]

    fig = psp.make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.20, 0.20, 0.15],
        vertical_spacing=0.04,
        subplot_titles=("ローソク足 + 移動平均", "出来高", "RSI", "MACD"),
    )

    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        increasing_line_color="#26a69a", increasing_fillcolor="#26a69a",
        decreasing_line_color="#ef5350", decreasing_fillcolor="#ef5350",
        name="ローソク足", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=ma5, mode="lines", name="MA5",
        line=dict(color="#ff7f0e", width=1.5, dash="dot"),
        hovertemplate="%{x}<br>MA5 ¥%{y:,.0f}<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=ma25, mode="lines", name="MA25",
        line=dict(color="#2ca02c", width=1.5),
        hovertemplate="%{x}<br>MA25 ¥%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=dates, y=volumes, name="出来高",
        marker_color="#90caf9", showlegend=False,
        hovertemplate="%{x}<br>出来高 %{y:,}<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=rsi, mode="lines", name="RSI(14)",
        line=dict(color="#9467bd", width=2),
        hovertemplate="%{x}<br>RSI %{y:.1f}<extra></extra>",
    ), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", line_width=1, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", line_width=1, row=3, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=macd_line, mode="lines", name="MACD",
        line=dict(color="orange", width=2),
        hovertemplate="%{x}<br>MACD %{y:.2f}<extra></extra>",
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=signal_line, mode="lines", name="シグナル",
        line=dict(color="red", width=1.5, dash="dash"),
        hovertemplate="%{x}<br>Signal %{y:.2f}<extra></extra>",
    ), row=4, col=1)
    fig.add_trace(go.Bar(
        x=dates, y=histogram, name="ヒストグラム",
        marker_color=hist_colors, showlegend=False,
        hovertemplate="%{x}<br>Hist %{y:.2f}<extra></extra>",
    ), row=4, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=4, col=1)

    fig.update_xaxes(rangeslider_visible=False)
    fig.update_yaxes(title_text="株価（円）", row=1, col=1)
    fig.update_yaxes(title_text="出来高", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
    fig.update_yaxes(title_text="MACD", row=4, col=1)
    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def _compute_step6_snapshot(series: TimeSeries | None) -> dict | None:
    """Step6 指標サマリー辞書を計算して返す。データ不足時は None。"""
    if series is None or not series.data or len(series.data) < 5:
        return None

    closes = [p.close for p in series.data]
    opens = [p.open for p in series.data]
    volumes = [p.volume for p in series.data]

    # ローソク足: 直近5日の陽線数
    bullish_count = sum(1 for c, o in zip(closes[-5:], opens[-5:]) if c >= o)
    trend = "上昇傾向" if bullish_count >= 3 else "下落傾向"
    candlestick_text = f"5日中{bullish_count}日が陽線（{trend}）"

    # MA25乖離率
    s = pd.Series(closes)
    ma25_val = s.rolling(window=25).mean().iloc[-1] if len(closes) >= 25 else None
    if ma25_val is not None and not math.isnan(ma25_val):
        dev = (closes[-1] - ma25_val) / ma25_val * 100
        direction = "上回っている" if dev >= 0 else "下回っている"
        ma_text = f"MA25を{abs(dev):.1f}%{direction}"
    else:
        ma_text = "データ不足（計算には25日分必要）"

    # 出来高: 5日平均 vs 20日平均
    if len(volumes) >= 20:
        avg5 = sum(volumes[-5:]) / 5
        avg20 = sum(volumes[-20:]) / 20
        ratio = avg5 / avg20 * 100 if avg20 > 0 else 100
        vol_trend = "増加傾向" if ratio >= 105 else ("減少傾向" if ratio <= 95 else "横ばい")
        volume_text = f"20日平均比{ratio:.0f}%（{vol_trend}）"
    else:
        volume_text = "データ不足（計算には20日分必要）"

    # RSI
    rsi_values = calc_rsi(closes)
    latest_rsi = next((v for v in reversed(rsi_values) if not math.isnan(v)), None)
    if latest_rsi is not None:
        status = "買われすぎ" if latest_rsi >= 70 else ("売られすぎ" if latest_rsi <= 30 else "中立")
        rsi_text = f"{latest_rsi:.0f}（{status}）"
    else:
        rsi_text = "データ不足"

    # MACD: 方向 + クロス検出（直近3日の符号変化）
    _, _, hist_vals = calc_macd(closes)
    valid_hist = [v for v in hist_vals if not math.isnan(v)]
    if valid_hist:
        recent3 = valid_hist[-3:]
        has_cross = len(set(v >= 0 for v in recent3)) > 1 if len(recent3) >= 2 else False
        if has_cross:
            macd_text = "クロス付近（直近3日以内に符号変化）"
        elif valid_hist[-1] >= 0:
            macd_text = "上向き"
        else:
            macd_text = "下向き"
    else:
        macd_text = "データ不足"

    return {
        "candlestick": candlestick_text,
        "ma": ma_text,
        "volume": volume_text,
        "rsi": rsi_text,
        "macd": macd_text,
    }


def _render_step6_snapshot(snapshot: dict | None) -> None:
    """Step6 指標サマリーを表示する。"""
    if snapshot is None:
        st.info("指標サマリーを生成するにはデータが不足しています。")
        return
    with st.container(border=True):
        st.markdown("**📋 指標サマリー（直近データ）**")
        st.write(f"🕯️ **ローソク足**: {snapshot['candlestick']}")
        st.write(f"📈 **移動平均線**: {snapshot['ma']}")
        st.write(f"📊 **出来高**: {snapshot['volume']}")
        st.write(f"🔵 **RSI**: {snapshot['rsi']}")
        st.write(f"📉 **MACD**: {snapshot['macd']}")


def _render_step6_case_study(
    snapshot: dict | None,
    symbol: str,
    company_name: str,
    explanation_service,
) -> None:
    """Step6 Part3: AIケーススタディ（入力欄 + フィードバック + Step7誘導）。"""
    st.markdown("### Part 3: あなたの判断を入力する（AIケーススタディ）")

    # 銘柄切替時にリセット（cs_guide_shown はセッション内維持のためリセットしない）
    if st.session_state.get("_cs_symbol") != symbol:
        st.session_state["_cs_symbol"] = symbol
        for k in ("cs_user_input", "cs_ai_feedback", "cs_feedback_done"):
            st.session_state.pop(k, None)

    st.write("上のチャートと指標サマリーを見て、あなたの考えを自由に入力してください。")
    st.caption("例：「上昇傾向なので少し様子を見てから買いたい」「RSIが高いので今は見送りたい」")

    # key を銘柄固有にすることで銘柄切替時に自動的に空のテキストエリアを表示する
    user_input = st.text_area(
        "あなたの考え",
        key=f"cs_input_{symbol}",
        height=100,
        label_visibility="collapsed",
        max_chars=500,
    )

    if st.button("AIにフィードバックをもらう", key="cs_btn_feedback", type="primary"):
        if not user_input or not user_input.strip():
            st.warning("考えを入力してからボタンを押してください。")
        elif snapshot is None:
            st.warning("指標データが取得できていないため、フィードバックを生成できません。")
        elif explanation_service is None:
            st.error("AIサービスが初期化されていません。")
        else:
            st.session_state["cs_user_input"] = user_input
            with st.spinner("AIがフィードバックを生成中..."):
                try:
                    feedback = explanation_service.get_case_study_feedback(
                        symbol=symbol,
                        company_name=company_name,
                        snapshot=snapshot,
                        user_input=user_input,
                    )
                    st.session_state["cs_ai_feedback"] = feedback
                    st.session_state["cs_feedback_done"] = True
                    st.rerun()
                except Exception:
                    st.error("フィードバックの生成に失敗しました。しばらく待ってから再試行してください。")

    feedback = st.session_state.get("cs_ai_feedback")
    if feedback:
        with st.container(border=True):
            st.markdown("#### 🤖 AIからのフィードバック")
            st.write(feedback)
            st.caption("※ このフィードバックは学習目的のものです。投資の推奨・売買の助言ではありません。")
        st.session_state["cs_guide_shown"] = True

    if st.session_state.get("cs_guide_shown"):
        st.info(
            "複数指標を使った分析ができました。次のステップへ\n\n"
            "実際に1株購入する準備はできていますか？"
            "ページ下部の「投資スタートガイド」で口座開設から最初の1株を買うまでの手順を確認できます。"
        )


def _render_guidance_card(tab_name: str, prerequisites: list[str]) -> None:
    """推奨案内カードを表示する。"""
    with st.container(border=True):
        st.markdown("📚 **学習の推奨順序について**")
        st.write(f"**{tab_name}** を学ぶ前に、以下を先に確認するとより深く理解できます：")
        for prereq in prerequisites:
            st.write(f"✓ {prereq}")


def render_indicators(quote: StockQuote) -> None:
    """主要指標（2×2グリッド）+ 用語解説 expander を表示する。"""
    st.subheader("主要指標")
    col1, col2 = st.columns(2)

    with col1:
        _render_indicator_card(
            "時価総額",
            f"¥{quote.market_cap / 1e8:,.1f}億円" if quote.market_cap else None,
        )
    with col2:
        _render_indicator_card(
            "PER（株価収益率）",
            f"{quote.pe_ratio:.1f}倍" if quote.pe_ratio else None,
            "PER",
        )

    col3, col4 = st.columns(2)
    with col3:
        _render_indicator_card(
            "PBR（株価純資産倍率）",
            f"{quote.pb_ratio:.2f}倍" if quote.pb_ratio else None,
            "PBR",
        )
    with col4:
        _render_indicator_card(
            "配当利回り",
            f"{quote.dividend_yield:.2f}%" if quote.dividend_yield else None,
            "配当利回り",
        )


def _render_indicator_card(label: str, value_str: str | None, glossary_key: str | None = None) -> None:
    """指標カードを1枚描画する。値がない場合は「取得できません」を表示。expander は常に表示。"""
    with st.container(border=True):
        display = value_str if value_str else "取得できません"
        st.metric(label, display)
        key = glossary_key or label
        with st.expander(f"▼ {key}とは？"):
            st.markdown(glossary.get_text(key))


def render_daily_word() -> None:
    """今日の学習用語を表示する（日付ベースのインデックスで選択）。"""
    st.divider()
    st.subheader("📚 今日の学習用語")

    try:
        with open(_LEARNING_WORDS_PATH, encoding="utf-8") as f:
            words: list[dict] = json.load(f)
    except Exception:
        st.info("学習用語を読み込めませんでした。")
        return

    if not words:
        return

    # Level順（0→5）にソートして推奨学習順を維持する（同Level内は元の順序を維持）
    words.sort(key=lambda w: w.get("level", 0))

    # APP_LAUNCH_DATE からの通算日数でインデックスを決定
    today = date.today()
    delta = (today - APP_LAUNCH_DATE).days
    if delta < 0:
        delta = 0
    idx = delta % len(words)
    word = words[idx]

    with st.container(border=True):
        st.markdown(f"**【{word.get('term', '')}】** *(Level {word.get('level', 0)})*")
        st.write(word.get("body", ""))


def render_news_area(symbol: str, profile, news_service) -> None:
    """関連ニュースエリアを表示する。銘柄切替時にキャッシュをリセットし自動取得する。"""
    if st.session_state.get("_news_symbol") != symbol:
        st.session_state["_news_symbol"] = symbol
        st.session_state.pop("news_items", None)
        st.session_state.pop("news_error", None)

    if "news_items" not in st.session_state and "news_error" not in st.session_state:
        with st.spinner("ニュースを取得中..."):
            try:
                items = news_service.get(symbol, profile.name)
                st.session_state["news_items"] = items
            except Exception as e:
                st.session_state["news_error"] = str(e)

    with st.container(border=True):
        company_name = profile.name if profile.name else symbol
        st.markdown(f"#### 📰 {company_name} 関連ニュース")

        if "news_error" in st.session_state:
            st.warning("ニュースを取得できませんでした。しばらく待ってから再試行してください。")
            if st.button("再試行", key="news_retry_btn"):
                st.session_state.pop("news_error", None)
                st.rerun()
        else:
            items = st.session_state.get("news_items", [])
            if not items:
                st.info("関連ニュースが見つかりませんでした。")
            else:
                for item in items:
                    st.markdown("---")
                    if item.link:
                        st.markdown(f"▼ [{item.title}]({_safe_url(item.link)})")
                    else:
                        st.markdown(f"▼ {item.title}")
                    if item.pub_date:
                        st.caption(f"{item.pub_date} | 出典: newsdata.io")
                    if item.description:
                        desc = item.description
                        st.write(desc[:200] + "..." if len(desc) > 200 else desc)

        st.caption("※ newsdata.io 無料枠（200 credits/日）| 最大12時間の遅延あり | ニュースは情報提供のみ。投資判断の根拠に使用しないこと")


def render_error(message: str) -> None:
    """エラーメッセージを表示する。"""
    st.error(message)


def render_investment_guide() -> None:
    """Step7: 投資スタートガイドを表示する（静的コンテンツ）。"""
    with st.container(border=True):
        st.markdown("### 🎯 Step7: 最初の1株を買ってみよう")
        st.write("ここまでで複数の指標を学びました。実際に1株買うまでの手順を説明します。")
        st.divider()

        st.markdown("#### 📋 STEP 1: 証券口座を開設する")
        with st.container(border=True):
            st.markdown("""
**口座開設先の例**: SBI証券・楽天証券・松井証券など主要証券会社のウェブサイトから申し込めます。
各社の手数料・サービス内容は各社公式サイトでご確認ください。

> ⚠️ 本ツールは特定の証券会社を推奨しません。複数社を比較して選んでください。

**口座開設の一般的な流れ**:
1. 証券会社のウェブサイトから「口座開設」を申し込む
2. 本人確認書類（マイナンバーカードまたは運転免許証）を提出する
3. 審査・登録完了（最短翌営業日〜数日）
4. 銀行から入金する
""")

        st.divider()

        st.markdown("#### 📋 STEP 2: 最初の銘柄を選ぶ")
        with st.container(border=True):
            st.markdown("""
- 自分がよく知っている企業から選ぶ（使ったことがある商品・サービスの会社）
- 1株の価格が手頃な銘柄から始める（最初は1〜3万円程度から）
- このツールで学んだ指標（ローソク足・MA・出来高・RSI・MACD）で確認してみる
""")

        st.divider()

        st.markdown("#### 📋 STEP 3: 注文を出す")
        with st.container(border=True):
            st.markdown("""
**■ 成行注文（なりゆき）**
「今すぐ買いたい」→ 今の市場価格で即時約定。価格は指定できないが確実に約定する。

**■ 指値注文（さしね）**
「◯円以下なら買いたい」→ 希望価格を指定。設定価格に達しないと約定しないことがある。

初めての場合は「成行注文で1株」が最もシンプルです。
""")

        st.warning("⚠️ 株式は元本保証ではありません。余裕資金で投資してください。投資判断はご自身の責任で行ってください。")
        st.caption("中長期の現物取引に慣れてきたら「デイトレード」という手法もありますが、リスクが高く高度な技術が必要なため、まずは中長期投資で経験を積むことをおすすめします。")


def render_footer(fetched_at: datetime | None = None) -> None:
    """フッターを表示する。"""
    ts = fetched_at.strftime("%Y-%m-%d %H:%M JST") if fetched_at else "—"
    st.caption(f"データ提供: Yahoo Finance (yfinance) | 取得時刻: {ts} | 本ツールは投資助言を行いません。")
