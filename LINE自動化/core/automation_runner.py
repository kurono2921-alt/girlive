"""
自動化実行モジュール
全体のフローを統合して実行
"""

import asyncio
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass

from .sheets_client import SheetsClient, AccountRow
from .image_downloader import ImageDownloader
from .line_automation import LineAutomation, AutomationResult


@dataclass
class RunnerConfig:
    """自動化実行設定"""
    email: str
    password: str
    sheet_url: str
    sheet_name: str
    icon_save_path: str
    headless: bool = False
    biz_manager_enabled: bool = False
    biz_manager_name: str = ""
    
    # 列設定
    col_enabled: str = ""
    col_line_name: str = ""
    col_icon_image: str = ""
    col_basic_id: str = ""
    col_access_token: str = ""
    col_permission_link: str = ""
    col_friend_link: str = ""
    col_business_account: str = ""


class AutomationRunner:
    """自動化実行クラス"""
    
    def __init__(
        self,
        config: RunnerConfig,
        on_status_update: Optional[Callable[[str], None]] = None,
        on_progress_update: Optional[Callable[[int, int], None]] = None,
        on_captcha_required: Optional[Callable[[], asyncio.Future]] = None
    ):
        """
        Args:
            config: 実行設定
            on_status_update: ステータス更新コールバック
            on_progress_update: 進捗更新コールバック (current, total)
            on_captcha_required: CAPTCHA検知時のコールバック
        """
        self.config = config
        self.on_status_update = on_status_update or (lambda x: print(x))
        self.on_progress_update = on_progress_update or (lambda c, t: None)
        self.on_captcha_required = on_captcha_required
        
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        
        self.sheets_client: Optional[SheetsClient] = None
        self.image_downloader: Optional[ImageDownloader] = None
        self.automation: Optional[LineAutomation] = None
        
        self.accounts: List[AccountRow] = []
        self.results: List[AutomationResult] = []
    
    def log(self, message: str):
        """ステータスログ"""
        self.on_status_update(message)
    
    def get_column_config(self) -> Dict[str, str]:
        """列設定を辞書で取得"""
        return {
            'col_enabled': self.config.col_enabled,
            'col_line_name': self.config.col_line_name,
            'col_icon_image': self.config.col_icon_image,
            'col_basic_id': self.config.col_basic_id,
            'col_access_token': self.config.col_access_token,
            'col_permission_link': self.config.col_permission_link,
            'col_friend_link': self.config.col_friend_link,
            'col_business_account': self.config.col_business_account,
        }
    
    async def run(self) -> List[AutomationResult]:
        """
        自動化を実行
        
        Returns:
            処理結果のリスト
        """
        self.is_running = True
        self.should_stop = False
        self.results = []
        
        try:
            # ===== 前処理フロー =====
            self.log("=" * 50)
            self.log("【前処理フロー】開始")
            self.log("=" * 50)
            
            # スプレッドシートに接続
            self.log("スプレッドシートに接続中...")
            self.sheets_client = SheetsClient()
            if not self.sheets_client.connect(self.config.sheet_url, self.config.sheet_name):
                self.log("✗ スプレッドシート接続失敗")
                return []
            self.log("✓ スプレッドシート接続成功")
            
            # 有効な行を取得
            self.log("有効なアカウントを取得中...")
            self.accounts = self.sheets_client.get_enabled_rows(self.get_column_config())
            self.log(f"✓ {len(self.accounts)}件のアカウントを検出")
            
            if not self.accounts:
                self.log("処理対象のアカウントがありません")
                return []
            
            # 画像をダウンロード
            self.log("アイコン画像をダウンロード中...")
            self.image_downloader = ImageDownloader(self.config.icon_save_path)
            download_results, row_to_image = self.image_downloader.download_all(self.accounts)
            
            success_count = sum(1 for r in download_results if r.success)
            self.log(f"✓ 画像ダウンロード完了: {success_count}/{len(download_results)}件")
            
            # ===== アカウント作成処理 =====
            self.log("")
            self.log("=" * 50)
            self.log("【アカウント作成処理】開始")
            self.log("=" * 50)
            
            # ブラウザ起動
            biz_manager_name = self.config.biz_manager_name if self.config.biz_manager_enabled else ""
            self.automation = LineAutomation(
                email=self.config.email,
                password=self.config.password,
                headless=self.config.headless,
                biz_manager_name=biz_manager_name,
                on_status_update=self.log,
                on_captcha_required=self.on_captcha_required
            )
            
            if not await self.automation.start():
                self.log("✗ ブラウザ起動失敗")
                return []
            
            # ログイン
            if not await self.automation.login():
                self.log("✗ ログイン失敗")
                await self.automation.stop()
                return []
            
            # 各アカウントを処理
            total = len(self.accounts)
            for idx, account in enumerate(self.accounts):
                # 停止チェック
                if self.should_stop:
                    self.log("処理が中断されました")
                    break
                
                # 一時停止チェック
                while self.is_paused:
                    await asyncio.sleep(1)
                    if self.should_stop:
                        break
                
                self.on_progress_update(idx + 1, total)
                self.log("")
                self.log(f"--- アカウント {idx + 1}/{total} ---")
                
                # 画像パスを取得
                image_path = row_to_image.get(account.row_number, "")
                
                # アカウント処理
                result = await self.automation.process_account(
                    account=account,
                    image_path=image_path,
                    sheet_reader=self.sheets_client,
                    column_config=self.get_column_config()
                )
                self.results.append(result)
                
                # 処理間の待機
                await asyncio.sleep(2)
            
            # 完了
            self.log("")
            self.log("=" * 50)
            self.log("【処理完了】")
            self.log("=" * 50)
            
            success_count = sum(1 for r in self.results if r.success)
            self.log(f"成功: {success_count}/{len(self.results)}件")
            
        except Exception as e:
            self.log(f"✗ 実行エラー: {e}")
        
        finally:
            # クリーンアップ
            if self.automation:
                await self.automation.stop()
            self.is_running = False
        
        return self.results
    
    def pause(self):
        """一時停止"""
        self.is_paused = True
        self.log("一時停止しました")
    
    def resume(self):
        """再開"""
        self.is_paused = False
        self.log("再開しました")
    
    def stop(self):
        """停止"""
        self.should_stop = True
        self.is_paused = False
        self.log("停止リクエストを受信しました")


def run_automation_sync(
    config: RunnerConfig,
    on_status_update: Optional[Callable[[str], None]] = None,
    on_progress_update: Optional[Callable[[int, int], None]] = None,
    on_captcha_required: Optional[Callable[[], asyncio.Future]] = None
) -> List[AutomationResult]:
    """
    自動化を同期的に実行（UIから呼び出し用）
    
    Args:
        config: 実行設定
        on_status_update: ステータス更新コールバック
        on_progress_update: 進捗更新コールバック
        on_captcha_required: CAPTCHA検知時のコールバック
        
    Returns:
        処理結果のリスト
    """
    runner = AutomationRunner(
        config=config,
        on_status_update=on_status_update,
        on_progress_update=on_progress_update,
        on_captcha_required=on_captcha_required
    )
    
    return asyncio.run(runner.run())
