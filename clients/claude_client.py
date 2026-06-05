import os

import anthropic


class ClaudeClient:
    """Anthropic Claude API クライアント。初回呼び出し時に初期化（遅延初期化）。"""

    def __init__(self) -> None:
        self._model: str = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
        self._client: anthropic.Anthropic | None = None

    def generate(self, prompt: str) -> str:
        """プロンプトを送信して生成テキストを返す。"""
        if self._client is None:
            self._client = anthropic.Anthropic()
        message = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
