"""
画像ダウンロードモジュール
Dropboxリンクから画像をダウンロードし、ローカルに保存
"""

import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests


@dataclass
class DownloadResult:
    """ダウンロード結果"""
    row_number: int  # スプレッドシートの行番号
    original_url: str  # 元のURL
    local_path: str  # ローカル保存パス
    success: bool  # 成功/失敗
    error_message: str = ""  # エラーメッセージ


class ImageDownloader:
    """Dropbox画像ダウンロードクラス"""
    
    def __init__(self, base_save_path: str):
        """
        Args:
            base_save_path: 基本保存先パス
        """
        self.base_save_path = Path(base_save_path)
        self.today_folder = self._create_today_folder()
        self.downloaded_urls: Dict[str, str] = {}  # URL -> ローカルパスのマッピング
        self.row_to_image: Dict[int, str] = {}  # 行番号 -> ローカルパスのマッピング
    
    def _create_today_folder(self) -> Path:
        """今日の日付フォルダを作成"""
        today = datetime.now().strftime("%Y-%m-%d")
        folder_path = self.base_save_path / today
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path
    
    def _convert_dropbox_url(self, url: str) -> str:
        """
        DropboxのURLを直接ダウンロード可能なURLに変換
        
        Args:
            url: 元のDropbox URL
            
        Returns:
            ダウンロード可能なURL
        """
        # dl=0 を dl=1 に変更してダウンロードリンクにする
        if 'dropbox.com' in url:
            # www.dropbox.com を dl.dropboxusercontent.com に変更
            url = url.replace('www.dropbox.com', 'dl.dropboxusercontent.com')
            url = url.replace('?dl=0', '?dl=1')
            # クエリパラメータを整理
            if '&dl=0' in url:
                url = url.replace('&dl=0', '&dl=1')
            elif 'dl=0' not in url and 'dl=1' not in url:
                if '?' in url:
                    url += '&dl=1'
                else:
                    url += '?dl=1'
        return url
    
    def _extract_filename_from_url(self, url: str) -> str:
        """URLからファイル名を抽出"""
        # URLからファイル名部分を取得
        match = re.search(r'/([^/]+\.(jpg|jpeg|png|gif|webp))', url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # ファイル名が取得できない場合はハッシュを使用
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"image_{url_hash}.jpg"
    
    def _normalize_url(self, url: str) -> str:
        """URLを正規化（重複チェック用）"""
        # クエリパラメータを除いた基本部分を取得
        base_url = re.sub(r'\?.*$', '', url)
        return base_url.lower()
    
    def download_image(self, url: str, row_number: int) -> DownloadResult:
        """
        画像をダウンロード
        
        Args:
            url: 画像URL（Dropboxリンク）
            row_number: スプレッドシートの行番号
            
        Returns:
            ダウンロード結果
        """
        if not url or url.strip() == "":
            return DownloadResult(
                row_number=row_number,
                original_url=url,
                local_path="",
                success=False,
                error_message="URLが空です"
            )
        
        # URLを正規化して重複チェック
        normalized_url = self._normalize_url(url)
        
        # 既にダウンロード済みの場合はスキップ
        if normalized_url in self.downloaded_urls:
            existing_path = self.downloaded_urls[normalized_url]
            self.row_to_image[row_number] = existing_path
            return DownloadResult(
                row_number=row_number,
                original_url=url,
                local_path=existing_path,
                success=True,
                error_message="既存ファイルを使用（重複URL）"
            )
        
        try:
            # ダウンロードURLに変換
            download_url = self._convert_dropbox_url(url)
            
            # ダウンロード実行
            response = requests.get(download_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # ファイル名を決定
            filename = self._extract_filename_from_url(url)
            # 連番を追加して一意にする
            base_name, ext = os.path.splitext(filename)
            save_filename = f"{len(self.downloaded_urls) + 1:03d}_{base_name}{ext}"
            save_path = self.today_folder / save_filename
            
            # ファイル保存
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            local_path = str(save_path)
            
            # マッピングを更新
            self.downloaded_urls[normalized_url] = local_path
            self.row_to_image[row_number] = local_path
            
            return DownloadResult(
                row_number=row_number,
                original_url=url,
                local_path=local_path,
                success=True
            )
            
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                row_number=row_number,
                original_url=url,
                local_path="",
                success=False,
                error_message=f"ダウンロードエラー: {str(e)}"
            )
        except Exception as e:
            return DownloadResult(
                row_number=row_number,
                original_url=url,
                local_path="",
                success=False,
                error_message=f"エラー: {str(e)}"
            )
    
    def download_all(self, accounts: List) -> Tuple[List[DownloadResult], Dict[int, str]]:
        """
        すべてのアカウントの画像をダウンロード
        
        Args:
            accounts: AccountRowのリスト
            
        Returns:
            (ダウンロード結果リスト, 行番号→画像パスのマッピング)
        """
        results = []
        
        for account in accounts:
            result = self.download_image(
                url=account.icon_image_url,
                row_number=account.row_number
            )
            results.append(result)
            
            if result.success:
                print(f"✓ 行{account.row_number}: {result.local_path}")
            else:
                print(f"✗ 行{account.row_number}: {result.error_message}")
        
        return results, self.row_to_image
    
    def get_image_path_for_row(self, row_number: int) -> Optional[str]:
        """
        指定行の画像パスを取得
        
        Args:
            row_number: 行番号
            
        Returns:
            画像のローカルパス（なければNone）
        """
        return self.row_to_image.get(row_number)

