# 目的：Streamlit 画面コンポーネント群
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit, plotly, pandas

import json
import math
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as psp
import streamlit as st

from config import APP_LAUNCH_DATE, CHART_DEFAULT_PERIOD, CHART_PERIODS, PRESET_SYMBOLS
from models.stock_models import StockProfile, StockQuote, TimeSeries
from ui import glossary

_DISCLAIMER_PATH = Path(__file__).parent.parent / "data" / "disclaimer.txt"
_LEARNING_WORDS_PATH = Path(__file__).parent.parent / "data" / "learning_words.json"


def render_disclaimer_banner() -> None:
    """免責バナーを常時表示する。"""
    try:
        text = _DISCLAIMER_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        text = "⚠️ このツールは学習・情報提供を目的としています。投資助言・売買の推奨は一切行いません。"
    st.warning(text)


def render_stock_selector() -> str | None:
    """プリセットボタン + 手入力で銘柄コードを返す。未選択時は None。"""
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


def render_chart_tabs(series: TimeSeries | None, period_label: str) -> str:
    """チャートエリア（期間ボタン＋5タブ）を表示する。選択中の期間ラベルを返す。"""
    st.subheader("📊 チャート")

    # 期間切り替えボタン
    period_labels = [p["label"] for p in CHART_PERIODS]
    cols = st.columns(len(period_labels))
    selected = period_label
    for i, label in enumerate(period_labels):
        btn_type = "primary" if label == period_label else "secondary"
        if cols[i].button(label, key=f"period_{label}", type=btn_type):
            selected = label

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["株価推移", "移動平均線", "出来高", "RSI", "MACD"])

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

    return selected


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


def _calc_macd(closes: list[float]) -> tuple[list[float], list[float], list[float]]:
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


def _render_macd_chart(series: TimeSeries | None) -> None:
    """MACDチャート（株価推移＋MACD/シグナル/ヒストグラムの2段サブプロット）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]
    macd, signal, histogram = _calc_macd(closes)

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


def _calc_rsi(closes: list[float], period: int = 14) -> list[float]:
    """Wilder法でRSI(14)を計算して返す。期間不足の先頭はNaNのまま。"""
    s = pd.Series(closes)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.tolist()


def _render_rsi_chart(series: TimeSeries | None) -> None:
    """RSIチャート（株価推移＋RSI(14)の2段サブプロット）を表示する。"""
    if series is None or not series.data:
        st.info("チャートデータを取得できませんでした。")
        return

    dates = [p.date for p in series.data]
    closes = [p.close for p in series.data]
    rsi = _calc_rsi(closes)

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
        else:
            items = st.session_state.get("news_items", [])
            if not items:
                st.info("関連ニュースが見つかりませんでした。")
            else:
                for item in items:
                    st.markdown("---")
                    if item.link:
                        st.markdown(f"▼ [{item.title}]({item.link})")
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


def render_footer(fetched_at: datetime | None = None) -> None:
    """フッターを表示する。"""
    ts = fetched_at.strftime("%Y-%m-%d %H:%M JST") if fetched_at else "—"
    st.caption(f"データ提供: Yahoo Finance (yfinance) | 取得時刻: {ts} | 本ツールは投資助言を行いません。")
