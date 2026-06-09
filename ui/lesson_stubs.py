# 目的：Lesson 3-9 のスタブ表示（Phase E 暫定）
# 作成日：2026-06-08
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit

import streamlit as st


_LESSON_STUBS: dict = {
    4: {
        "title": "ローソク足",
        "goal": "チャートを開いたときに1本1本のローソク足の意味が読める",
        "guide": "チャートの「ローソク足（Step0）」タブを確認してください。",
        "next_level": 5,
        "quiz": {
            "question": "ローソク足1本でわかるものはどれですか？",
            "options": [
                "始値・高値・安値・終値",
                "翌日の株価予測",
                "会社の利益額",
                "株主の人数",
            ],
            "answer_index": 0,
            "hint": "ローソク足は1期間の価格変動を4つの数値（OHLC）で表します。",
        },
    },
    5: {
        "title": "移動平均線と出来高",
        "goal": "「今はトレンドの中にいるか」「動きに信頼性があるか」を判断できる",
        "guide": "チャートの「移動平均線（Step2）」と「出来高（Step3）」タブを確認してください。",
        "next_level": 6,
        "quiz": {
            "question": "株価が移動平均線を大きく上回っているとき、一般的にどんな状態と言われますか？",
            "options": [
                "上昇トレンドの可能性がある",
                "下降トレンドが確定している",
                "出来高が必ず増える",
                "株価は必ず元に戻る",
            ],
            "answer_index": 0,
            "hint": "移動平均線は「過去N日間の平均値」。上回る＝平均より強い動きが続いていることを示します。",
        },
    },
    7: {
        "title": "複合指標・総合分析",
        "goal": "複数の指標を同時に使って判断の根拠を説明できる",
        "guide": "チャートの「複数指標（Step6）」タブでAIケーススタディを試してください。",
        "next_level": 8,
        "quiz": {
            "question": "複数の指標を組み合わせて判断する主な理由はどれですか？",
            "options": [
                "判断の信頼性を高めるため",
                "計算が簡単になるため",
                "絶対的な正解が出るため",
                "他の投資家の意図がわかるため",
            ],
            "answer_index": 0,
            "hint": "1つの指標だけでは誤シグナルが出ることがある。複数で確認するとシグナルの精度が上がります。",
        },
    },
}


def render_lesson_stub(lesson_num: int) -> None:
    """
    Lesson 4・5・7 のスタブ表示。概念理解クイズで next_level に進む。
    ⚠️ Level 3 は lesson_beginner.render_lesson_3() を呼ぶこと（Phase F フル実装済み）。
    ⚠️ Level 6 は render_lesson_6_stub() を呼ぶこと（2段階進行のため辞書対象外）。

    クイズ進行管理:
      - session_state["lesson_{N}_quiz_done"]: bool（クイズ正解フラグ）
      - lesson_{N}_quiz_done == False:
          スタブ + クイズ（4択ラジオ + 「回答する」ボタン）を表示
          正解 → lesson_{N}_quiz_done = True → 「次のLessonへ進む」ボタン表示
          不正解 → ヒント表示 + ラジオリセット
      - lesson_{N}_quiz_done == True:
          ✅ クイズ正解済みを表示 + 「次のLessonへ進む」ボタン常時表示
    """
    stub = _LESSON_STUBS[lesson_num]

    st.markdown(f"## 📚 Lesson {lesson_num}: {stub['title']}")
    st.divider()

    with st.container(border=True):
        st.markdown(f"**🎯 このLessonの目標**: {stub['goal']}")
        st.info(f"📊 **マナトレで確認する**: {stub['guide']}")
        st.caption("（詳細な学習コンテンツは今後のアップデートで追加予定です）")

    st.divider()
    st.markdown("#### ✅ 理解チェック")

    quiz = stub["quiz"]
    quiz_done = st.session_state.get(f"lesson_{lesson_num}_quiz_done", False)
    check_state = st.session_state.get(f"lesson_{lesson_num}_check_state")

    if quiz_done or check_state == "passed":
        st.success("✅ クイズ正解済みです！")
        if st.button(
            f"次のLessonへ進む（Level {stub['next_level']}）",
            key=f"l{lesson_num}_next",
            type="primary",
        ):
            st.session_state["current_level"] = stub["next_level"]
            st.rerun()
        return

    if check_state == "failed":
        st.warning(f"❌ もう一度考えてみましょう。**ヒント**: {quiz['hint']}")
        if st.button("もう一度", key=f"l{lesson_num}_retry"):
            del st.session_state[f"lesson_{lesson_num}_check_state"]
            radio_key = f"lesson_{lesson_num}_quiz_radio"
            if radio_key in st.session_state:
                del st.session_state[radio_key]
            st.rerun()
        return

    with st.container(border=True):
        st.write(f"**Q. {quiz['question']}**")
        st.radio(
            "選択してください",
            options=quiz["options"],
            key=f"lesson_{lesson_num}_quiz_radio",
            label_visibility="collapsed",
            index=None,
        )
        if st.button("回答する", key=f"l{lesson_num}_submit"):
            selected = st.session_state.get(f"lesson_{lesson_num}_quiz_radio")
            if selected is None:
                st.warning("選択してください。")
            elif selected == quiz["options"][quiz["answer_index"]]:
                st.session_state[f"lesson_{lesson_num}_quiz_done"] = True
                st.session_state[f"lesson_{lesson_num}_check_state"] = "passed"
                st.rerun()
            else:
                st.session_state[f"lesson_{lesson_num}_check_state"] = "failed"
                st.rerun()


def render_lesson_6_stub() -> None:
    """
    Level 6: RSI + MACD の2段階スタブ。両方完了して初めて Level 7 へ進む。

    進行管理:
      - session_state["lesson_6_rsi_done"]: bool（RSI確認完了フラグ）
      - session_state["lesson_6_macd_done"]: bool（MACD確認完了フラグ）

    表示ロジック:
      1. lesson_6_rsi_done == False:
           RSI確認スタブを表示
           「RSIを確認しました」ボタン → lesson_6_rsi_done = True → st.rerun()
      2. lesson_6_rsi_done == True かつ lesson_6_macd_done == False:
           ✅ RSI確認済み を表示
           MACD確認スタブを表示
           「MACDを確認しました」ボタン → lesson_6_macd_done = True → st.rerun()
      3. lesson_6_rsi_done == True かつ lesson_6_macd_done == True:
           ✅ RSI確認済み / ✅ MACD確認済み を表示
           「Level 7（総合分析）へ進む」ボタン → current_level = 7 → st.rerun()
    """
    st.markdown("## 📚 Lesson 6+7: モメンタム分析（RSI・MACD）")
    st.divider()

    rsi_done = st.session_state.get("lesson_6_rsi_done", False)
    macd_done = st.session_state.get("lesson_6_macd_done", False)

    if rsi_done:
        st.success("✅ RSI確認済み")
    if macd_done:
        st.success("✅ MACD確認済み")

    if rsi_done and macd_done:
        if st.button("Level 7（総合分析）へ進む", key="l6_to_l7", type="primary"):
            st.session_state["current_level"] = 7
            st.rerun()
        return

    if not rsi_done:
        with st.container(border=True):
            st.markdown("**🎯 Step 1: RSI を確認する**")
            st.markdown("**目標**: 「買われすぎ・売られすぎ」の感覚をつかめる")
            st.info("📊 チャートの「RSI（Step4）」タブを確認してください。RSIが70以上・30以下のときの状態を確認しましょう。")
            st.caption("（詳細な学習コンテンツは今後のアップデートで追加予定です）")
        if st.button("RSIを確認しました", key="l6_rsi_done_btn", type="primary"):
            st.session_state["lesson_6_rsi_done"] = True
            st.rerun()
        return

    # rsi_done == True かつ macd_done == False
    with st.container(border=True):
        st.markdown("**🎯 Step 2: MACD を確認する**")
        st.markdown("**目標**: 「トレンドの転換点」を示すゴールデンクロス・デッドクロスの見方がわかる")
        st.info("📊 チャートの「MACD（Step5）」タブを確認してください。MACDラインとシグナルラインの交差点を確認しましょう。")
        st.caption("（詳細な学習コンテンツは今後のアップデートで追加予定です）")
    if st.button("MACDを確認しました", key="l6_macd_done_btn", type="primary"):
        st.session_state["lesson_6_macd_done"] = True
        st.rerun()


def render_lesson_8_stub() -> bool:
    """
    Level 8: 購入準備（Lesson 9）のスタブ表示。
    current_level は変更しない（Level 8 のまま卒業試験を表示する）。

    戻り値:
      True  — 購入準備未完了。呼び出し元は後続処理（卒業試験）を実行しないこと。
      False — 購入準備完了済み。呼び出し元は卒業試験を続けて表示すること。

    進行管理:
      - session_state["lesson_9_done"]: bool
      - lesson_9_done == False:
          購入準備スタブを表示
          「確認しました → 卒業試験へ進む」ボタン → lesson_9_done = True → st.rerun()
          True を返す → main.py が render_daily_word() を呼んで return する
      - lesson_9_done == True:
          ✅ 購入準備確認済みを折りたたみ表示
          False を返す → main.py が卒業試験・render_daily_word() を続けて呼ぶ
    """
    lesson_9_done = st.session_state.get("lesson_9_done", False)

    if lesson_9_done:
        with st.expander("✅ Lesson 9: 購入準備 — 確認済み"):
            st.write("購入準備（口座開設・注文方法の確認）を完了しました。")
        return False

    # 購入準備スタブを表示
    st.markdown("## 📚 Lesson 9: 購入準備")
    st.divider()

    with st.container(border=True):
        st.markdown("**🎯 目標**: 口座開設から最初の注文まで自分でできる")
        st.info(
            "📊 Step7「投資スタートガイド」（ページ下部）で口座開設・注文方法を確認してください。\n"
            "（Phase D で実装予定）"
        )
        st.caption("（詳細な学習コンテンツは今後のアップデートで追加予定です）")

    if st.button("確認しました → 卒業試験へ進む", key="l8_confirm_btn", type="primary"):
        st.session_state["lesson_9_done"] = True
        st.rerun()

    return True
