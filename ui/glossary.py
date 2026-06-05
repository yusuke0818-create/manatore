# 目的：用語解説データの読み込み・取得
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（標準ライブラリのみ）

import json
from pathlib import Path

_GLOSSARY_PATH = Path(__file__).parent.parent / "data" / "glossary.json"

_data: dict = {}


def load() -> None:
    """起動時に1回呼び出す。"""
    global _data
    try:
        with open(_GLOSSARY_PATH, encoding="utf-8") as f:
            _data = json.load(f)
    except Exception:
        _data = {}


def get(term: str) -> dict:
    """用語の解説辞書を返す。存在しない場合は空辞書。"""
    return _data.get(term, {})


def get_text(term: str) -> str:
    """用語解説を1つのテキストとして返す。"""
    entry = _data.get(term)
    if not entry:
        return f"「{term}」の解説はありません。"

    lines = []
    if meaning := entry.get("meaning"):
        lines.append(f"**意味**: {meaning}")
    if why := entry.get("why"):
        lines.append(f"**なぜ見るのか**: {why}")
    if point := entry.get("beginner_point"):
        lines.append(f"**初心者ポイント**: {point}")
    return "\n\n".join(lines) if lines else f"「{term}」の解説はありません。"
