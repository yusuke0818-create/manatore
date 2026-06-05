from clients.claude_client import ClaudeClient
from models.stock_models import StockProfile, StockQuote


class AiExplanationService:
    def __init__(self, client: ClaudeClient) -> None:
        self._client = client

    def get(self, symbol: str, quote: StockQuote, profile: StockProfile) -> str:
        """Claude API を呼び出して初心者向け解説テキストを返す。"""
        prompt = _build_prompt(symbol, quote, profile)
        return self._client.generate(prompt)


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
