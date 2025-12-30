"""
設定管理モジュール
ユーザー設定をJSONファイルに保存・読み込み
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict, field

from config.settings import APP_SETTINGS_FILE


@dataclass
class LineSettings:
    """公式LINE タブの設定"""
    # ログイン情報
    email: str = ""
    password: str = ""
    
    # シート情報
    sheet_url: str = ""
    sheet_name: str = ""
    
    # 列情報（必須）
    col_enabled: str = ""        # 有効/無効の列
    col_line_name: str = ""      # 公式LINE名の列
    col_icon_image: str = ""     # アイコン画像の列
    
    # 列情報（任意）
    col_basic_id: str = ""       # ベーシックIDの列
    col_access_token: str = ""   # アクセストークンの列
    col_permission_link: str = "" # 権限追加リンクの列
    col_friend_link: str = ""    # 友達追加リンクの列
    col_business_account: str = "" # ビジネスアカウントの列
    
    # オプション
    icon_save_path: str = ""           # アイコン画像の保存先
    biz_manager_enabled: bool = False  # ビジネスマネージャーの組織を使用
    biz_manager_name: str = ""         # ビジネスマネージャーの組織名
    headless_mode: bool = False


@dataclass
class AppSettings:
    """アプリ全体の設定"""
    line_settings: LineSettings = field(default_factory=LineSettings)
    
    # 将来的な拡張用
    proline_settings: Dict[str, Any] = field(default_factory=dict)


class SettingsManager:
    """設定の保存・読み込みを管理"""
    
    def __init__(self, settings_file: Path = None):
        """
        Args:
            settings_file: 設定ファイルのパス
        """
        self.settings_file = settings_file or APP_SETTINGS_FILE
        self._settings: Optional[AppSettings] = None
    
    def load(self) -> AppSettings:
        """設定を読み込む"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # LineSettingsを復元
                line_data = data.get('line_settings', {})
                line_settings = LineSettings(**line_data)
                
                self._settings = AppSettings(
                    line_settings=line_settings,
                    proline_settings=data.get('proline_settings', {})
                )
            except Exception as e:
                print(f"設定の読み込みに失敗: {e}")
                self._settings = AppSettings()
        else:
            self._settings = AppSettings()
        
        return self._settings
    
    def save(self, settings: AppSettings) -> bool:
        """
        設定を保存
        
        Args:
            settings: 保存する設定
        
        Returns:
            成功したらTrue
        """
        try:
            # ディレクトリを作成
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # dataclassをdictに変換
            data = {
                'line_settings': asdict(settings.line_settings),
                'proline_settings': settings.proline_settings
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._settings = settings
            return True
            
        except Exception as e:
            print(f"設定の保存に失敗: {e}")
            return False
    
    @property
    def settings(self) -> AppSettings:
        """現在の設定を取得"""
        if self._settings is None:
            self.load()
        return self._settings
    
    def update_line_settings(self, **kwargs) -> bool:
        """
        LINE設定を部分更新
        
        Args:
            **kwargs: 更新するフィールドと値
        
        Returns:
            成功したらTrue
        """
        settings = self.settings
        
        for key, value in kwargs.items():
            if hasattr(settings.line_settings, key):
                setattr(settings.line_settings, key, value)
        
        return self.save(settings)
