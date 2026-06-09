from clients.claude_client import ClaudeClient
from models.stock_models import StockProfile, StockQuote


class AiExplanationService:
    def __init__(self, client: ClaudeClient) -> None:
        self._client = client

    def get(self, symbol: str, quote: StockQuote, profile: StockProfile) -> str:
        """Claude API を呼び出して初心者向け解説テキストを返す。"""
        prompt = _build_prompt(symbol, quote, profile)
        return self._client.generate(prompt)

    def get_case_study_feedback(
        self,
        symbol: str,
        company_name: str,
        snapshot: dict,
        user_input: str,
    ) -> str:
        """Step6 ケーススタディ用の教育的フィードバックを生成して返す。"""
        prompt = _build_case_study_prompt(symbol, company_name, snapshot, user_input[:500])
        return self._client.generate(prompt)

    def generate_raw(self, prompt: str) -> str:
        """任意のプロンプトをそのままClaudeに送り、レスポンステキストを返す。"""
        return self._client.generate(prompt)


def _build_case_study_prompt(
    symbol: str,
    company_name: str,
    snapshot: dict,
    user_input: str,
) -> str:
    snapshot_text = "\n".join([
        f"ローソク足: {snapshot.get('candlestick', '―')}",
        f"移動平均線: {snapshot.get('ma', '―')}",
        f"出来高: {snapshot.get('volume', '―')}",
        f"RSI: {snapshot.get('rsi', '―')}",
        f"MACD: {snapshot.get('macd', '―')}",
    ])
    return f"""あなたは投資学習の先生です。初心者の学習者が株式指標を見て判断を下す練習をしています。

【分析対象銘柄】
{company_name}（{symbol}）

【現在の指標サマリー（自動生成）】
{snapshot_text}

【学習者の判断・考え】
{user_input}

【あなたへの依頼】
学習者の考えを踏まえて、教育的なフィードバックを150〜250字で提供してください。

【フィードバックの方針】
・学習者の視点を認めてから補足する（否定から入らない）
・指標の読み方や複数指標を組み合わせる視点を伝える
・「いい視点です」「その点も考えてみましょう」などの対話的・肯定的トーンを使う
・「買うべき」「売るべき」「今がチャンス」などの売買判断・推奨表現は絶対に使わない
・断定的な将来予測はしない
・末尾に必ず「このフィードバックは学習目的であり、投資の助言ではありません。」を含める"""


def _build_prompt(symbol: str, quote: StockQuote, profile: StockProfile) -> str:
    per_str = f"{quote.pe_ratio:.1f}倍" if quote.pe_ratio else "取得できません"
    pbr_str = f"{quote.pb_ratio:.2f}倍" if quote.pb_ratio else "取得できません"
    div_str = f"{quote.dividend_yield:.2f}%" if quote.dividend_yield else "取得できません"
    sign = "+" if quote.change >= 0 else ""

    return f"""あなたは投資を始めたばかりの初心者向けに、株式情報をわかりやすく解説するアシスタントです。

以下の情報をもとに、200〜300字で解説してください。

【対象銘柄】
銘柄名: {profile.name}（{symbol}）
業種: {profile.sector or "不明"}
現在株価: ¥{quote.price:,.0f}
前日比: {sign}{quote.change:,.0f}円（{sign}{quote.change_percent:.2f}%）
PER: {per_str}
PBR: {pbr_str}
配当利回り: {div_str}

【解説の構成（この順序で書いてください）】
① 本日の株価の状況（前日比をもとに）
② PER・PBRの読み方（業種の特性も踏まえて）
③ 初心者が注意すべきポイント

【絶対に使わないこと】
- 「買い時」「売り時」「今すぐ買うべき」「〇〇円まで上がる」「下がる」などの投資判断表現
- 推奨・勧誘と受け取られる表現
- 断定的な将来予測

このツールは学習・情報提供のみを目的としています。"""
