# 目的：卒業試験のAIフィードバック生成
# 作成日：2026-06-08
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（ClaudeClientに依存）

from clients.claude_client import ClaudeClient


class GraduationService:
    def __init__(self, client: ClaudeClient) -> None:
        self._client = client

    def get_feedback(
        self,
        selected_symbol: str,
        selected_name: str,
        user_input: str,
        all_stocks_data: dict,
    ) -> str:
        """
        卒業試験のAIフィードバックを生成して返す。
        - selected_symbol: ユーザーが選んだ銘柄コード
        - selected_name: ユーザーが選んだ銘柄名
        - user_input: ユーザーの判断理由（自由記述）
        - all_stocks_data: 3銘柄全ての指標データ
        """
        prompt = _build_graduation_prompt(
            selected_symbol, selected_name, user_input[:500], all_stocks_data
        )
        return self._client.generate(prompt)


def _build_graduation_prompt(
    selected_symbol: str,
    selected_name: str,
    user_input: str,
    all_stocks_data: dict,
) -> str:
    """
    プロンプト設計方針:
    - 役割: 「投資学習の先生」
    - 出力長: 200〜300字
    - トーン: 対話的・肯定的（否定から入らない）
    - 評価軸（4項目。UIに表示した観点と一致させる）:
        1. PER・PBRなどファンダメンタル指標に触れているか
        2. RSIまたはMACDなどテクニカル指標に触れているか
        3. トレンドの方向（上向き・下向きなど）に触れているか
        4. 自分の言葉で根拠を説明しているか
    - 評価対象外: どの銘柄を選んだか（銘柄選択の優劣は評価しない）
    - 禁止表現: 「買うべき」「売るべき」「今がチャンス」「合格」「不合格」
    - 末尾必須: 「このフィードバックは学習目的であり、投資の助言ではありません」
    - GOAL宣言: フィードバック末尾に「あなたは卒業試験をクリアしました！」を必ず含める
    """
    stocks_lines = []
    for symbol, data in all_stocks_data.items():
        name = data.get("name", symbol)
        price = f"¥{data['price']:,.0f}" if data.get("price") is not None else "―"
        per = f"{data['pe_ratio']:.1f}倍" if data.get("pe_ratio") is not None else "―"
        pbr = f"{data['pb_ratio']:.2f}倍" if data.get("pb_ratio") is not None else "―"
        rsi = f"{data['rsi']:.0f}" if data.get("rsi") is not None else "―"
        macd = data.get("macd_direction", "―")
        stocks_lines.append(
            f"・{name}（{symbol}）: 株価={price}、PER={per}、PBR={pbr}、RSI={rsi}、MACD={macd}"
        )

    stocks_summary = "\n".join(stocks_lines)

    return f"""あなたは投資学習の先生です。
学習者が卒業試験として3銘柄から1つを選んで、その理由を自分の言葉で説明しました。
以下の評価観点でフィードバックを200〜300字で行ってください。

【分析対象の3銘柄データ】
{stocks_summary}

【学習者が選んだ銘柄】
{selected_name}（{selected_symbol}）

【学習者の判断理由】
{user_input}

【評価の観点（4項目）】
1. PER・PBRなどのファンダメンタル指標に触れているか
2. RSIまたはMACDなどのテクニカル指標に触れているか
3. トレンドの方向（上向き・下向きなど）に触れているか
4. 自分の言葉で選んだ理由を説明しているか

【フィードバックの方針】
・肯定的なトーンで始める（否定から入らない）
・評価軸ごとに具体的なコメントをする
・どの銘柄を選んだかは評価の対象にしない（銘柄選択の優劣は評価しない）
・「買うべき」「売るべき」「今がチャンス」「合格」「不合格」などの表現は使わない
・末尾に「このフィードバックは学習目的であり、投資の助言ではありません」を含める
・フィードバックの最後に「あなたは卒業試験をクリアしました！」を必ず含める"""
