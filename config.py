# 目的：アプリ全体の設定・定数管理
# 作成日：2026-06-03
# 対象OS：Windows / Mac / Linux
# 依存ライブラリ：なし（標準ライブラリのみ）

from datetime import date

# 学習用語の基準日。この日が「day 0」= Level0の最初の用語が表示される
APP_LAUNCH_DATE: date = date(2026, 6, 10)

PRESET_SYMBOLS: list[dict] = [
    {"code": "7203", "label": "トヨタ 7203"},
    {"code": "8306", "label": "三菱UFJ 8306"},
    {"code": "7974", "label": "任天堂 7974"},
    {"code": "9432", "label": "NTT 9432"},
    {"code": "6758", "label": "ソニー 6758"},
]

CHART_PERIODS: list[dict] = [
    {"label": "1ヶ月", "outputsize": 30},
    {"label": "3ヶ月", "outputsize": 90},
    {"label": "6ヶ月", "outputsize": 180},
    {"label": "1年", "outputsize": 365},
]
CHART_DEFAULT_PERIOD: str = "3ヶ月"

# APIキャッシュTTL（秒）
CACHE_TTL: int = 300

GRADUATION_STOCKS: list[dict] = [
    {"code": "7203", "name": "トヨタ自動車"},
    {"code": "8306", "name": "三菱UFJフィナンシャル・グループ"},
    {"code": "9432", "name": "日本電信電話（NTT）"},
    {"code": "7974", "name": "任天堂"},
    {"code": "6758", "name": "ソニーグループ"},
    {"code": "9434", "name": "ソフトバンク"},
]
