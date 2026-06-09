# 目的：初心者コース Lesson 0-2 の教育コンテンツ表示
# 作成日：2026-06-08
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：streamlit

import streamlit as st

_LESSON1_HOOK_PROMPT = """銀行預金と株式投資の基本的な仕組みの違いを、初心者に100字以内でわかりやすく説明してください。
「なぜ多くの人が株式に注目するのか」という視点を含めてください。
以下の制約を守ってください：
・具体的な金額・利益額・利回りの数字は挙げない
・「過去の実績は将来の利益を保証しない」旨を必ず含める
・「買うべき」「儲かる」などの投資判断・推奨表現は使用しない
・このコメントは学習目的である旨を末尾に明記する"""

_LEVEL_NAMES = {
    0: "マナトレ入門",
    1: "株の基礎",
    2: "企業価値の見方",
}


def render_lesson_0() -> None:
    """Lesson 0: コースオリエンテーション。完了ボタンで current_level を 1 に更新。"""
    _render_lesson_header(0, "コースオリエンテーション", "")

    st.markdown("""
マナトレへようこそ！

このコースでは **10のLesson** を通じて、投資の基礎から実際の銘柄分析まで学びます。
""")

    with st.container(border=True):
        st.markdown("#### 🎯 ゴール")
        st.write("✅ 複数の指標を使って銘柄を分析できる")
        st.write("✅ 「なぜこの銘柄を選ぶか」を説明できる")
        st.write("✅ 最初の1株を買う準備が整う")

    with st.container(border=True):
        st.markdown("#### ⏱ 所要時間の目安")
        st.write("・1 Lesson：15〜30分")
        st.write("・全体：3〜5時間")

    st.info("📍 あなたは今 **Level 0 — マナトレ入門** にいます。")

    if st.button("次のLessonへ進む（Lesson 1: 株とは何か）", key="l0_next", type="primary"):
        _advance_level(1)


def render_lesson_1(explanation_service) -> None:
    """Lesson 1: 株とは何か。体験フック（AI解説）+ 教育テキスト + 理解チェック。"""
    _render_lesson_header(1, "株とは何か", "なぜ株を買うのか・何が起きるのかを知ります")

    # 体験フック
    with st.container(border=True):
        st.markdown("#### 💡 銀行預金と株式投資、何が違う？")

        hook_result = st.session_state.get("lesson1_hook_result")
        if hook_result is None:
            if st.button("AIに教えてもらう", key="l1_hook_btn"):
                with st.spinner("AIが解説しています..."):
                    try:
                        result = explanation_service.generate_raw(_LESSON1_HOOK_PROMPT)
                        st.session_state["lesson1_hook_result"] = result
                        st.rerun()
                    except Exception:
                        st.error("AI解説の取得に失敗しました。しばらく待ってから再試行してください。")
        else:
            st.write(hook_result)
            st.caption("※ AIによる解説です。学習目的のみ。")

    # 教育テキスト
    with st.container(border=True):
        st.markdown("#### 📖 株とは何か？")
        st.markdown("""
**■ 株 = 会社の「持ち分証書」**
株を買う = その会社の共同オーナーになる
例：トヨタの株主 = トヨタの「共同オーナー」

**■ 株で利益を得る2つの方法**
① **値上がり益（キャピタルゲイン）**
　買った値段より高く売れたときの利益
② **配当（インカムゲイン）**
　会社が利益の一部を株主に分配するもの

**■ リスクとは**
株は値下がりすることもある
会社が倒産すると株が無価値になるリスクもある
投資は「増える可能性」と「減る可能性」の両方がある

**■ 長期投資 vs 短期売買**
このコースは「長期投資」の基礎を学ぶ内容です
""")

    # 理解チェック
    st.divider()
    st.markdown("#### ✅ 理解チェック")

    check_state = st.session_state.get("lesson1_check_state")

    if check_state == "passed":
        st.success("✅ 正解！株で利益を得る2つの方法（値上がり益・配当）を理解しました。")
        if st.button("次のLessonへ進む（Lesson 2: 株価と時価総額）", key="l1_next", type="primary"):
            _advance_level(2)
        return

    if check_state == "failed":
        st.warning("❌ もう一度考えてみましょう。**ヒント**: 株の利益には「値上がり」と「配当」の2種類があります。利子は銀行預金の利益、家賃収入は不動産投資の利益です。")
        if st.button("もう一度", key="l1_retry"):
            del st.session_state["lesson1_check_state"]
            if "lesson1_quiz_answer" in st.session_state:
                del st.session_state["lesson1_quiz_answer"]
            st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. 株で利益を得る方法として正しいものを2つ選んでください**")
        st.multiselect(
            "正しいものを2つ選んでください",
            options=[
                "A: 値上がり益（キャピタルゲイン）",
                "B: 配当（インカムゲイン）",
                "C: 利子（インタレスト）",
                "D: 家賃収入",
            ],
            key="lesson1_quiz_answer",
            label_visibility="collapsed",
        )
        if st.button("回答する", key="l1_submit"):
            selected = st.session_state.get("lesson1_quiz_answer", [])
            if not selected:
                st.warning("選択してください。")
            elif set(selected) == {
                "A: 値上がり益（キャピタルゲイン）",
                "B: 配当（インカムゲイン）",
            }:
                st.session_state["lesson1_check_state"] = "passed"
                st.rerun()
            else:
                st.session_state["lesson1_check_state"] = "failed"
                st.rerun()


def render_lesson_2() -> None:
    """Lesson 2: 株価と時価総額。教育テキスト + 理解チェック。"""
    _render_lesson_header(2, "株価と時価総額", "会社の大きさを数字で理解します")

    with st.container(border=True):
        st.markdown("#### 📖 株価と時価総額")
        st.markdown("""
**■ 株価の決まり方**
需要と供給で決まる（買いたい人が多いと上がる）

**■ 時価総額とは**
時価総額 = 株価 × 発行済み株式数 = 会社の「値段」

**■ 「株価が安い ≠ 安い会社」の罠**
株価1000円の会社と株価5000円の会社、どちらが大きい？
→ 時価総額で比べないとわからない

**■ 日経平均・TOPIX**
市場全体の動きを示す指数
個別株とは別に参考として確認する
""")

    st.info("📊 **マナトレで確認しよう**: 銘柄を選択して、時価総額を見てみましょう")

    # 理解チェック
    st.divider()
    st.markdown("#### ✅ 理解チェック")

    check_state = st.session_state.get("lesson2_check_state")

    if check_state == "passed":
        st.success("✅ 正解！株価だけでは会社の大きさは判断できません。時価総額で比べることが大切です。")
        st.info("📊 銘柄を選んで時価総額を確認してください。確認できたら次へ進みます。")
        if st.button("次のLessonへ進む（Level 3: ファンダメンタル分析）", key="l2_next", type="primary"):
            _advance_level(3)
        return

    if check_state == "failed":
        st.warning("❌ もう一度考えてみましょう。**ヒント**: 株価は1株あたりの値段です。発行済み株式数が違うと、株価が安くても会社全体の大きさは大きい場合があります。")
        if st.button("もう一度", key="l2_retry"):
            del st.session_state["lesson2_check_state"]
            if "lesson2_quiz_radio" in st.session_state:
                del st.session_state["lesson2_quiz_radio"]
            st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. 株価1000円の会社と株価5000円の会社、どちらが大きい会社ですか？**")
        st.radio(
            "回答を選んでください",
            options=[
                "株価1000円の会社",
                "株価5000円の会社",
                "株価だけでは判断できない（時価総額で比べる必要がある）",
                "どちらでも同じ",
            ],
            key="lesson2_quiz_radio",
            label_visibility="collapsed",
            index=None,
        )
        if st.button("回答する", key="l2_submit"):
            selected = st.session_state.get("lesson2_quiz_radio")
            if selected is None:
                st.warning("選択してください。")
            elif selected == "株価だけでは判断できない（時価総額で比べる必要がある）":
                st.session_state["lesson2_check_state"] = "passed"
                st.rerun()
            else:
                st.session_state["lesson2_check_state"] = "failed"
                st.rerun()


def render_lesson_3() -> None:
    """Lesson 3: PER・PBR（ファンダメンタル分析）。教育テキスト + 理解チェック。"""
    _render_lesson_header(3, "PER・PBR（ファンダメンタル分析）", "会社の「割安・割高」を数字で判断します")

    with st.container(border=True):
        st.markdown("#### 📖 PERとは？（株価収益率）")
        st.markdown("""
**PER（P/E Ratio）= 株価 ÷ 1株あたり利益（EPS）**

「今の株価は1年間の利益の何倍か」を示す指標

**■ 読み方の目安**
- PER 15倍 = 15年分の利益で株価を買っている
- PER が低い → 割安候補（利益に対して株価が安い）
- PER が高い → 成長期待が高い（利益の何十倍も評価されている）

⚠️ 業種によって平均値が異なる（製造業は低め・IT/成長企業は高め）
⚠️ PER だけで投資判断をしないこと
""")

    with st.container(border=True):
        st.markdown("#### 📖 PBRとは？（株価純資産倍率）")
        st.markdown("""
**PBR（P/B Ratio）= 株価 ÷ 1株あたり純資産（BPS）**

「今の株価は会社の純資産の何倍か」を示す指標

**■ 読み方の目安**
- PBR 1倍 = 株価が純資産と同額（理論的な最低ライン）
- PBR 1倍未満 → 解散したほうが株主に価値がある状態（割安候補）
- PBR 2〜3倍 → ブランド・技術・将来性が評価されている

⚠️ 銀行・不動産などは PBR 1倍前後が多い（業種特性）
⚠️ 低PBR = 必ずしも良い会社ではない
""")

    with st.container(border=True):
        st.markdown("#### 📖 配当利回り")
        st.markdown("""
**配当利回り = 1年間の配当金 ÷ 株価 × 100（%）**

「株価に対して何%のリターンが配当で得られるか」を示す

**■ 読み方の目安**
- 2〜4%程度が一般的な高配当の目安（業種・時期により変動）
- 配当がない企業（成長企業）も多い

⚠️ 配当は企業の業績次第で減配・無配になることがある
""")

    st.info("📊 **マナトレで確認しよう**: Lesson 4以降で銘柄を選択したとき、「主要指標」のPER・PBR・配当利回りを一緒に確認してみましょう。")

    st.divider()
    st.markdown("#### ✅ 理解チェック")

    check_state = st.session_state.get("lesson3_check_state")

    if check_state == "passed":
        st.success("✅ 正解！PBRが1倍未満の銘柄は、理論的には解散価値より株価が低い「割安候補」と言われます。")
        if st.button("次のLessonへ進む（Level 4: ローソク足）", key="l3_next", type="primary"):
            _advance_level(4)
        return

    if check_state == "failed":
        st.warning("❌ もう一度考えてみましょう。**ヒント**: PBR = 株価 ÷ 純資産。1倍を下回ると「株価が純資産より安い」状態です。")
        if st.button("もう一度", key="l3_retry"):
            del st.session_state["lesson3_check_state"]
            if "lesson3_quiz_radio" in st.session_state:
                del st.session_state["lesson3_quiz_radio"]
            st.rerun()
        return

    with st.container(border=True):
        st.write("**Q. PBRが1倍未満の銘柄は一般的に何と言われますか？**")
        st.radio(
            "回答を選んでください",
            options=[
                "割安候補とされることが多い",
                "成長期待が高い銘柄とされる",
                "赤字の可能性が高い",
                "配当利回りが高い",
            ],
            key="lesson3_quiz_radio",
            label_visibility="collapsed",
            index=None,
        )
        if st.button("回答する", key="l3_submit"):
            selected = st.session_state.get("lesson3_quiz_radio")
            if selected is None:
                st.warning("選択してください。")
            elif selected == "割安候補とされることが多い":
                st.session_state["lesson3_check_state"] = "passed"
                st.rerun()
            else:
                st.session_state["lesson3_check_state"] = "failed"
                st.rerun()


def _render_lesson_header(lesson_num: int, title: str, framing: str) -> None:
    """Lesson共通ヘッダー（番号・タイトル・冒頭フレーミング）を表示する。"""
    st.markdown(f"## 📚 Lesson {lesson_num}: {title}")
    st.divider()
    if framing:
        st.markdown(f"**🎯 この授業では**: {framing}")


def _advance_level(next_level: int) -> None:
    """current_level を next_level に更新して st.rerun() を呼ぶ。"""
    st.session_state["current_level"] = next_level
    st.rerun()
