"""
セッション管理モジュール
ログイン状態（Cookie/LocalStorage）を保存・復元
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import SESSION_FILE


class SessionManager:
    """セッション管理クラス"""
    
    def __init__(self, session_file: Path = None):
        """
        Args:
            session_file: セッションファイルのパス
        """
        self.session_file = session_file or SESSION_FILE
    
    def save_session(self, cookies: list, storage_state: Dict[str, Any] = None) -> bool:
        """
        セッションを保存
        
        Args:
            cookies: Cookieリスト
            storage_state: ストレージ状態（localStorage等）
            
        Returns:
            保存成功かどうか
        """
        try:
            session_data = {
                "cookies": cookies,
                "storage_state": storage_state or {}
            }
            
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ セッション保存: {self.session_file}")
            return True
            
        except Exception as e:
            print(f"✗ セッション保存エラー: {e}")
            return False
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        セッションを読み込み
        
        Returns:
            セッションデータ（なければNone）
        """
        try:
            if not self.session_file.exists():
                return None
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            print(f"✓ セッション読み込み: {self.session_file}")
            return session_data
            
        except Exception as e:
            print(f"✗ セッション読み込みエラー: {e}")
            return None
    
    def has_session(self) -> bool:
        """保存されたセッションがあるか"""
        return self.session_file.exists()
    
    def clear_session(self) -> bool:
        """セッションを削除"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                print("✓ セッション削除")
            return True
        except Exception as e:
            print(f"✗ セッション削除エラー: {e}")
            return False
