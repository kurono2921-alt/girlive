"""
Google Sheets クライアントモジュール
スプレッドシートの操作（読み込み、書き込み、シート名取得）を行う
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
import gspread
from google.oauth2.service_account import Credentials

from config.settings import (
    GOOGLE_CREDENTIALS_FILE,
    MAX_ACCOUNTS,
    HEADER_ROWS,
    ENABLED_VALUES,
)


@dataclass
class AccountRow:
    """スプレッドシートの1行分のデータ"""
    row_number: int  # 行番号（1始まり）
    enabled: bool  # 有効/無効
    line_name: str  # 公式LINE名
    icon_image_url: str  # アイコン画像URL
    basic_id: str  # ベーシックID
    access_token: str  # アクセストークン
    permission_link: str  # 権限追加リンク
    friend_link: str  # 友達追加リンク
    business_account: str  # ビジネスアカウント


class SheetsClient:
    """Google Sheets APIクライアント"""
    
    SCOPES = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, credentials_path: Path = None):
        """
        Args:
            credentials_path: サービスアカウントキーのパス
        """
        self.credentials_path = credentials_path or GOOGLE_CREDENTIALS_FILE
        self._client: Optional[gspread.Client] = None
        
        # インスタンス変数としてスプレッドシート状態を保持（統合用）
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self.worksheet: Optional[gspread.Worksheet] = None
    
    def _get_client(self) -> gspread.Client:
        """認証済みクライアントを取得"""
        if self._client is None:
            creds = Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=self.SCOPES
            )
            self._client = gspread.authorize(creds)
        return self._client
    
    def extract_spreadsheet_id(self, url: str) -> Optional[str]:
        """
        スプレッドシートURLからIDを抽出
        
        Args:
            url: スプレッドシートのURL
        
        Returns:
            スプレッドシートID、抽出失敗時はNone
        """
        # パターン1: /d/SPREADSHEET_ID/
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        
        # パターン2: key=SPREADSHEET_ID
        match = re.search(r'key=([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        
        return None
    
    def get_sheet_names(self, url: str) -> Tuple[List[str], Optional[str]]:
        """
        スプレッドシートのシート名（タブ名）を取得
        
        Args:
            url: スプレッドシートのURL
        
        Returns:
            (シート名のリスト（50音順）, エラーメッセージ)
        """
        try:
            spreadsheet_id = self.extract_spreadsheet_id(url)
            if not spreadsheet_id:
                return [], "無効なスプレッドシートURLです"
            
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)
            
            # シート名を取得して50音順にソート
            sheet_names = [ws.title for ws in spreadsheet.worksheets()]
            sheet_names.sort(key=lambda x: x.lower())  # 大文字小文字無視でソート
            
            return sheet_names, None
            
        except gspread.exceptions.SpreadsheetNotFound:
            return [], "スプレッドシートが見つかりません。共有設定を確認してください。"
        except gspread.exceptions.APIError as e:
            return [], f"API エラー: {str(e)}"
        except Exception as e:
            import traceback
            print(f"[DEBUG] シート取得例外: {type(e).__name__}: {e}")
            traceback.print_exc()
            return [], f"エラー: {type(e).__name__}: {str(e)}"
    
    def validate_url(self, url: str) -> bool:
        """URLが有効なスプレッドシートURLかチェック"""
        return self.extract_spreadsheet_id(url) is not None

    # --- 以下、SheetReader から統合されたメソッド ---

    def connect(self, spreadsheet_url: str, sheet_name: str) -> bool:
        """
        スプレッドシートに接続
        
        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名
            
        Returns:
            接続成功かどうか
        """
        try:
            client = self._get_client()
            
            # URLからスプレッドシートIDを抽出
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            if not spreadsheet_id:
                raise ValueError("無効なスプレッドシートURLです")
            
            self.spreadsheet = client.open_by_key(spreadsheet_id)
            self.worksheet = self.spreadsheet.worksheet(sheet_name)
            
            return True
        except Exception as e:
            print(f"スプレッドシート接続エラー: {e}")
            return False

    def _col_letter_to_index(self, letter: str) -> int:
        """列文字をインデックスに変換（A=0, B=1, ..., AA=26, AB=27, ...）"""
        if not letter or letter == "-":
            return -1
        
        result = 0
        for char in letter.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1  # 0始まりに変換

    def _get_cell_value(self, row: List[str], col_idx: int) -> str:
        """セルの値を安全に取得"""
        if col_idx < 0 or col_idx >= len(row):
            return ""
        return row[col_idx].strip()

    def get_enabled_rows(self, column_config: Dict[str, str]) -> List[AccountRow]:
        """
        有効になっている行のデータを取得
        
        Args:
            column_config: 列設定（キー: フィールド名, 値: 列文字）
            
        Returns:
            有効な行のリスト（最大100件）
        """
        if not self.worksheet:
            raise ValueError("スプレッドシートに接続していません")
        
        # すべてのデータを取得
        all_values = self.worksheet.get_all_values()
        
        # ヘッダー行のチェック
        if len(all_values) < HEADER_ROWS + 1:
            return []
        
        # 列インデックスを計算
        col_indices = {
            'enabled': self._col_letter_to_index(column_config.get('col_enabled', '')),
            'line_name': self._col_letter_to_index(column_config.get('col_line_name', '')),
            'icon_image': self._col_letter_to_index(column_config.get('col_icon_image', '')),
            'basic_id': self._col_letter_to_index(column_config.get('col_basic_id', '')),
            'access_token': self._col_letter_to_index(column_config.get('col_access_token', '')),
            'permission_link': self._col_letter_to_index(column_config.get('col_permission_link', '')),
            'friend_link': self._col_letter_to_index(column_config.get('col_friend_link', '')),
            'business_account': self._col_letter_to_index(column_config.get('col_business_account', '')),
        }
        
        enabled_rows = []
        
        # ヘッダー行を除いてデータ行を処理（行番号はHEADER_ROWS+1から開始）
        for row_idx, row in enumerate(all_values[HEADER_ROWS:], start=HEADER_ROWS + 1):
            if len(enabled_rows) >= MAX_ACCOUNTS:
                break
            
            # 有効/無効チェック
            enabled_idx = col_indices['enabled']
            if enabled_idx < 0 or enabled_idx >= len(row):
                continue
            
            enabled_value = row[enabled_idx].strip().upper()
            if enabled_value not in ENABLED_VALUES:
                continue
            
            # データを抽出
            account = AccountRow(
                row_number=row_idx,
                enabled=True,
                line_name=self._get_cell_value(row, col_indices['line_name']),
                icon_image_url=self._get_cell_value(row, col_indices['icon_image']),
                basic_id=self._get_cell_value(row, col_indices['basic_id']),
                access_token=self._get_cell_value(row, col_indices['access_token']),
                permission_link=self._get_cell_value(row, col_indices['permission_link']),
                friend_link=self._get_cell_value(row, col_indices['friend_link']),
                business_account=self._get_cell_value(row, col_indices['business_account']),
            )
            
            enabled_rows.append(account)
        
        return enabled_rows

    def update_cell(self, row: int, col_letter: str, value: str) -> bool:
        """
        セルを更新
        
        Args:
            row: 行番号（1始まり）
            col_letter: 列文字（例: "A", "B", "AA"）
            value: 設定する値
            
        Returns:
            更新成功かどうか
        """
        if not self.worksheet:
            return False
        
        try:
            cell = f"{col_letter}{row}"
            self.worksheet.update_acell(cell, value)
            return True
        except Exception as e:
            print(f"セル更新エラー ({cell}): {e}")
            return False


def get_column_options() -> List[str]:
    """
    列選択用のオプションを生成（ブランク + A〜AZ）
    
    Returns:
        ["", "A", "B", ..., "Z", "AA", "AB", ..., "AZ"]
    """
    columns = ["-"]  # 先頭にブランク（ハイフンで表示）
    
    # A-Z
    for i in range(26):
        columns.append(chr(65 + i))
    
    # AA-AZ
    for i in range(26):
        columns.append("A" + chr(65 + i))
    
    return columns
