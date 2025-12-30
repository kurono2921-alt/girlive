"""
設定値モジュール
アプリケーション全体で使用する設定を一元管理
"""

import random
from pathlib import Path
from typing import Dict, List, Tuple

# =============================================================================
# パス設定
# =============================================================================

# プロジェクトのルートディレクトリ
BASE_DIR = Path(__file__).parent.parent

# 設定ファイルディレクトリ
CONFIG_DIR = BASE_DIR / "config"

# セッションファイル
SESSION_FILE = CONFIG_DIR / "session.json"

# アプリ設定ファイル
APP_SETTINGS_FILE = CONFIG_DIR / "app_settings.json"

# Google認証情報ファイル
GOOGLE_CREDENTIALS_FILE = CONFIG_DIR / "google_credentials.json"

# =============================================================================
# LINE URL設定
# =============================================================================

# LINE管理画面URL
LINE_MANAGER_URL = "https://manager.line.biz/"

# LINEログインURL（リダイレクト付き）
LINE_LOGIN_URL = (
    "https://account.line.biz/login?redirectUri="
    "https%3A%2F%2Faccount.line.biz%2Foauth2%2Fcallback%3F"
    "client_id%3D10%26code_challenge%3DoC9gWsWHhnh2rWpdcqQekSk2AoBeoEOAKZXdAy6qgXk%26"
    "code_challenge_method%3DS256%26redirect_uri%3Dhttps%253A%252F%252Fmanager.line.biz%252Fapi%252Foauth2%252FbizId%252Fcallback%26"
    "response_type%3Dcode%26state%3DaChi64NNfukeomNfi1i2Mz8nN23iJKZt"
)

# LINE Developers Console
LINE_DEVELOPERS_URL = "https://developers.line.biz/console"

# LINEアカウント作成URL
LINE_ENTRY_URL = "https://entry.line.biz/form/entry/unverified"

# =============================================================================
# ブラウザ設定
# =============================================================================

# 一般的なユーザーエージェント（Windows/Mac Chrome）
USER_AGENTS: List[str] = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Mac Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# 一般的な画面解像度
SCREEN_RESOLUTIONS: List[Tuple[int, int]] = [
    (1920, 1080),  # Full HD（最も一般的）
    (1366, 768),   # ノートPC
    (1536, 864),   # スケーリング適用
    (1440, 900),   # MacBook
    (2560, 1440),  # WQHD
]

# デフォルトビューポートサイズ
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# 言語設定
LANGUAGES: List[str] = ["ja-JP", "ja"]

# タイムゾーン
TIMEZONE = "Asia/Tokyo"

# ロケール
LOCALE = "ja-JP"

# =============================================================================
# 人間らしい操作の設定（ミリ秒）
# =============================================================================

# アクション間のランダム待機時間
ACTION_DELAY_MIN = 500  # 0.5秒
ACTION_DELAY_MAX = 1500  # 1.5秒

# タイピング時の1文字あたりのディレイ
TYPING_DELAY_MIN = 20   # 20ms
TYPING_DELAY_MAX = 100  # 100ms

# マウス移動のステップ数
MOUSE_MOVE_STEPS_MIN = 20
MOUSE_MOVE_STEPS_MAX = 40

# ベジェ曲線の制御点オフセット（ピクセル）
BEZIER_CONTROL_OFFSET = 50

# =============================================================================
# ブラウザ起動オプション
# =============================================================================

BROWSER_ARGS: List[str] = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-infobars',
    '--window-size=1920,1080',
    '--start-maximized',
]

# =============================================================================
# スプレッドシート設定
# =============================================================================

# 1回の処理で扱う最大アカウント数
MAX_ACCOUNTS = 100

# ヘッダー行数（スキップする行数）
HEADER_ROWS = 2

# 有効判定に使用する値
ENABLED_VALUES = ['TRUE', '1', 'はい', 'YES', '有効']

# =============================================================================
# アカウント作成設定
# =============================================================================

# 大業種（ウェブサービス）
CATEGORY_GROUP = '71'

# 小業種（ウェブサービス(エンターテインメント)）
CATEGORY = '595'

# =============================================================================
# ヘルパー関数
# =============================================================================

def get_random_user_agent() -> str:
    """ランダムなユーザーエージェントを取得"""
    return random.choice(USER_AGENTS)


def get_random_resolution() -> Tuple[int, int]:
    """ランダムな画面解像度を取得"""
    return random.choice(SCREEN_RESOLUTIONS)


def get_viewport_size() -> Dict[str, int]:
    """Playwright用のビューポートサイズを取得"""
    width, height = get_random_resolution()
    return {"width": width, "height": height}


def get_random_action_delay() -> float:
    """ランダムなアクション待機時間を取得（秒）"""
    return random.randint(ACTION_DELAY_MIN, ACTION_DELAY_MAX) / 1000


def get_random_typing_delay() -> float:
    """ランダムなタイピング待機時間を取得（秒）"""
    return random.randint(TYPING_DELAY_MIN, TYPING_DELAY_MAX) / 1000


def get_random_mouse_steps() -> int:
    """ランダムなマウス移動ステップ数を取得"""
    return random.randint(MOUSE_MOVE_STEPS_MIN, MOUSE_MOVE_STEPS_MAX)
