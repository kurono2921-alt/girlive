"""
LINE公式アカウント自動化モジュール
アカウント作成、アイコン変更、API有効化、権限追加、友達追加リンク取得
"""

import asyncio
import re
from typing import Optional, Dict, Callable
from dataclasses import dataclass

from config.settings import (
    LINE_LOGIN_URL,
    LINE_MANAGER_URL,
    LINE_DEVELOPERS_URL,
    LINE_ENTRY_URL,
    CATEGORY_GROUP,
    CATEGORY,
)
from .stealth_browser import StealthBrowser
from .sheets_client import AccountRow
from .session_manager import SessionManager


@dataclass
class AutomationResult:
    """自動化処理の結果"""
    row_number: int
    success: bool
    basic_id: str = ""
    permission_link: str = ""
    friend_link: str = ""
    access_token: str = ""
    error_message: str = ""


class LineAutomation:
    """LINE公式アカウント自動化クラス"""
    
    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = False,
        biz_manager_name: str = "",
        on_status_update: Optional[Callable[[str], None]] = None,
        on_captcha_required: Optional[Callable[[], asyncio.Future]] = None
    ):
        """
        Args:
            email: ログインメールアドレス
            password: ログインパスワード
            headless: ヘッドレスモードで実行するか
            biz_manager_name: ビジネスマネージャーの組織名（設定されている場合）
            on_status_update: ステータス更新コールバック
            on_captcha_required: CAPTCHA検知時のコールバック（Futureを返す）
        """
        self.email = email
        self.password = password
        self.biz_manager_name = biz_manager_name
        self.browser = StealthBrowser(headless=headless)
        self.on_status_update = on_status_update or (lambda x: print(x))
        self.on_captcha_required = on_captcha_required
        self.session_manager = SessionManager()
        self.is_logged_in = False
        self.current_basic_id = ""
    
    def log(self, message: str):
        """ステータスログ"""
        self.on_status_update(message)
    
    async def start(self) -> bool:
        """ブラウザを起動"""
        self.log("ブラウザを起動中...")
        return await self.browser.launch()
    
    async def stop(self):
        """ブラウザを終了"""
        self.log("ブラウザを終了中...")
        await self.browser.close()
    
    async def login(self) -> bool:
        """
        LINEビジネスアカウントにログイン
        保存されたセッションがあれば復元を試みる
        
        Returns:
            ログイン成功かどうか
        """
        # 保存されたセッションを試行
        if await self._try_restore_session():
            return True
        
        # セッションがない/無効な場合は通常ログイン
        return await self._login_with_credentials()
    
    async def _try_restore_session(self) -> bool:
        """
        保存されたセッションでログインを試みる
        
        Returns:
            セッション復元成功かどうか
        """
        if not self.session_manager.has_session():
            self.log("保存されたセッションがありません。通常ログインを行います。")
            return False
        
        self.log("保存されたセッションを復元中...")
        
        try:
            session_data = self.session_manager.load_session()
            if not session_data:
                return False
            
            # Cookieを設定してから管理画面にアクセス
            cookies = session_data.get("cookies", [])
            if cookies:
                await self.browser.context.add_cookies(cookies)
            
            # 管理画面に直接アクセス
            self.log("管理画面にアクセス中...")
            await self.browser.navigate(LINE_MANAGER_URL)
            await asyncio.sleep(3)
            
            current_url = await self.browser.get_current_url()
            
            # ログイン画面にリダイレクトされていないか確認
            if 'manager.line.biz' in current_url and 'login' not in current_url:
                self.is_logged_in = True
                self.log("✓ セッション復元成功")
                return True
            else:
                self.log("セッションが無効です。再ログインが必要です。")
                self.session_manager.clear_session()
                return False
                
        except Exception as e:
            self.log(f"セッション復元エラー: {e}")
            return False
    
    async def _save_session(self):
        """現在のセッションを保存"""
        try:
            cookies = await self.browser.context.cookies()
            self.session_manager.save_session(cookies)
            self.log("✓ セッションを保存しました（次回から自動ログイン）")
        except Exception as e:
            self.log(f"セッション保存エラー: {e}")
    
    async def _detect_captcha(self) -> bool:
        """
        CAPTCHAの存在を検知（実際に表示されているもののみ）
        
        Returns:
            CAPTCHAが表示されているかどうか
        """
        try:
            # reCAPTCHAのiframeを検出（表示されているもののみ）
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[title*="reCAPTCHA"]',
                '.g-recaptcha',
                '#recaptcha',
                'div[data-sitekey]',
            ]
            
            for selector in captcha_selectors:
                element = await self.browser.page.query_selector(selector)
                if element:
                    # 要素が実際に表示されているかチェック
                    is_visible = await element.is_visible()
                    if is_visible:
                        # さらにサイズをチェック（0x0は非表示扱い）
                        box = await element.bounding_box()
                        if box and box['width'] > 10 and box['height'] > 10:
                            self.log(f"🔍 CAPTCHA検出（表示中）: {selector}")
                            return True
            
            return False
        except Exception as e:
            self.log(f"CAPTCHA検出エラー: {e}")
            return False
    
    async def _wait_for_captcha_completion(self):
        """
        ユーザーがCAPTCHAを解くまで待機
        """
        self.log("⚠️ 画像認証（CAPTCHA）が検出されました")
        self.log("手動で認証を完了してください...")
        
        if self.on_captcha_required:
            # コールバックでUIに通知し、完了を待つ
            try:
                await self.on_captcha_required()
                self.log("✓ 認証完了確認")
            except Exception as e:
                self.log(f"CAPTCHA待機エラー: {e}")
        else:
            # コールバックがない場合は一定時間待機
            self.log("60秒以内に認証を完了してください...")
            await asyncio.sleep(60)
    
    async def _login_with_credentials(self) -> bool:
        """
        メールアドレスとパスワードでログイン
        
        Returns:
            ログイン成功かどうか
        """
        self.log("ログインページに移動中...")
        await self.browser.navigate(LINE_LOGIN_URL)
        
        try:
            # ページ読み込み待機
            await asyncio.sleep(2)
            
            # ビジネスアカウントボタンをクリック
            self.log("ビジネスアカウントボタンをクリック...")
            await self.browser.human_click('toly-button[data-email-login-button="true"]')
            await asyncio.sleep(2)
            await self.browser.wait_for_load()
            
            # メールアドレス入力
            self.log("メールアドレスを入力中...")
            await self.browser.human_type('input[type="email"]', self.email)
            await asyncio.sleep(1)
            
            # パスワード入力
            self.log("パスワードを入力中...")
            await self.browser.human_type('input[type="password"]', self.password)
            await asyncio.sleep(1)
            
            # ログイン実行（Enterキーで送信）
            self.log("ログイン実行中...")
            await self.browser.page.keyboard.press('Enter')
            
            # ログイン処理の完了を待機
            self.log("ログイン処理を待機中...")
            await asyncio.sleep(3)
            
            # CAPTCHA検知
            if await self._detect_captcha():
                await self._wait_for_captcha_completion()
                await asyncio.sleep(2)
            
            # ページ遷移を待つ
            try:
                await self.browser.page.wait_for_url("**/manager.line.biz/**", timeout=10000)
                self.is_logged_in = True
                self.log("✓ ログイン成功")
                
                # セッションを保存
                await self._save_session()
                
                return True
            except Exception:
                # URLが変わらない場合、現在のURLを確認
                current_url = await self.browser.get_current_url()
                self.log(f"現在のURL: {current_url}")
                
                # 再度CAPTCHA確認
                if await self._detect_captcha():
                    self.log("CAPTCHAがまだ表示されています。再度認証してください。")
                    await self._wait_for_captcha_completion()
                    await asyncio.sleep(2)
                    current_url = await self.browser.get_current_url()
                
                if 'manager.line.biz' in current_url:
                    self.is_logged_in = True
                    self.log("✓ ログイン成功")
                    
                    # セッションを保存
                    await self._save_session()
                    
                    return True
                else:
                    self.log("✗ ログイン失敗 - 管理画面に遷移できませんでした")
                    return False
                
        except Exception as e:
            self.log(f"✗ ログインエラー: {e}")
            return False
    
    async def create_account(self, account: AccountRow, image_path: str) -> AutomationResult:
        """
        アカウントを作成
        
        Args:
            account: アカウント情報
            image_path: アイコン画像のパス
            
        Returns:
            処理結果
        """
        result = AutomationResult(row_number=account.row_number, success=False)
        
        try:
            # ===== アカウント作成処理 =====
            self.log(f"[行{account.row_number}] アカウント作成開始: {account.line_name}")
            
            # 管理画面トップに戻る（2件目以降のために確実に遷移）
            self.log("管理画面トップへ移動...")
            await self.browser.navigate(LINE_MANAGER_URL)
            await asyncio.sleep(2)
            
            # 作成ボタンをクリック（別タブが開く）
            self.log("作成ボタンをクリック...")
            await self.browser.human_click(f'a[href="{LINE_ENTRY_URL}"]')
            
            # 新しいタブに切り替え
            self.log("新しいタブに移動...")
            await self.browser.switch_to_new_tab()
            await self.browser.wait_for_load()
            
            # アカウント名を入力
            self.log("アカウント名を入力...")
            await self.browser.human_type('input[name="bot.name"]', account.line_name)
            
            # 大業種を選択（設定値から取得）
            self.log("大業種を選択...")
            await self.browser.select_option('select[name="category_group"]', CATEGORY_GROUP)
            await self.browser.random_wait()
            
            # 小業種を選択（設定値から取得）
            self.log("小業種を選択...")
            await self.browser.select_option('select[name="category"]', CATEGORY)
            
            # チェックボックスにチェック（ラベルをクリック）
            self.log("利用目的をチェック...")
            await self.browser.human_click('label:has-text("お問い合わせに対応したい")')
            await self.browser.random_wait()
            
            # メッセージ配信用を選択（ラベルをクリック）
            self.log("メイン用途を選択...")
            await self.browser.human_click('label:has-text("メッセージ配信用")')
            
            # ビジネスマネージャーの組織を設定（設定されている場合）
            if self.biz_manager_name:
                await self._select_business_manager()
            
            # 確認ボタンをクリック
            self.log("確認ボタンをクリック...")
            try:
                await self.browser.page.click('button:has-text("確認")', timeout=10000)
            except Exception:
                # フォールバック: type=submitで探す
                await self.browser.page.click('button[type="submit"]', timeout=5000)
            await asyncio.sleep(3)
            
            # 完了ボタンをクリック
            self.log("完了ボタンをクリック...")
            try:
                # data-entrytypeで探す
                await self.browser.page.click('button[data-entrytype="unverified"]', timeout=10000)
            except Exception:
                try:
                    await self.browser.page.click('button:has-text("完了")', timeout=5000)
                except Exception:
                    # 最終フォールバック
                    await self.browser.page.click('button.btn-primary:has-text("完了")', force=True, timeout=5000)
            
            # ページ遷移を待つ
            self.log("ページ遷移を待機中...")
            await asyncio.sleep(3)
            
            # CAPTCHA検知（完了ボタン後）
            if await self._detect_captcha():
                await self._wait_for_captcha_completion()
                await asyncio.sleep(2)
            
            # 「あとで認証を行う」をクリック
            self.log("認証スキップ...")
            
            # リンクが表示されるまで待機してからクリック
            try:
                auth_link = await self.browser.page.wait_for_selector(
                    'a:has-text("あとで認証を行う")',
                    state='visible',
                    timeout=10000
                )
                await auth_link.click(force=True)
            except Exception as e:
                self.log(f"認証スキップリンクが見つかりません: {e}")
                # 既に管理画面にいる可能性をチェック
                current_url = await self.browser.get_current_url()
                if 'manager.line.biz/account' in current_url:
                    self.log("既に管理画面に遷移済み")
                else:
                    raise
            
            await asyncio.sleep(2)
            
            # 同意ボタンをクリック（2回）
            self.log("利用規約に同意...")
            if await self.browser.check_element_exists('#modalAgreementAgree'):
                await self.browser.human_click('#modalAgreementAgree')
                await self.browser.wait_for_load()
            
            if await self.browser.check_element_exists('#modalAgreementAgree'):
                await self.browser.human_click('#modalAgreementAgree')
                await self.browser.wait_for_load()
            
            # ポップアップを「閉じる」ボタンで閉じてからリロード
            self.log("ポップアップを閉じてリロード中...")
            await self._close_modal_popups()
            
            await self.browser.page.reload()
            await self.browser.wait_for_load()
            await asyncio.sleep(2)
            
            # ベーシックIDを取得
            current_url = await self.browser.get_current_url()
            basic_id = self._extract_basic_id(current_url)
            result.basic_id = basic_id
            self.current_basic_id = basic_id
            self.log(f"✓ アカウント作成完了: {basic_id}")
            
            # ===== アイコン変更処理 =====
            if image_path:
                await self._change_icon(basic_id, image_path)
            
            # ===== メッセージAPI有効化処理 =====
            await self._enable_messaging_api(basic_id)
            
            # ===== 権限追加処理 =====
            permission_link = await self._add_permission(basic_id)
            result.permission_link = permission_link
            
            # ===== 友達追加リンク取得 =====
            friend_link = await self._get_friend_link(basic_id)
            result.friend_link = friend_link
            
            # ===== アクセストークン取得 =====
            access_token = await self._get_access_token(account.line_name)
            result.access_token = access_token
            
            result.success = True
            self.log(f"✓ [行{account.row_number}] 全処理完了")
            
        except Exception as e:
            result.error_message = str(e)
            self.log(f"✗ [行{account.row_number}] エラー: {e}")
        
        return result
    
    async def _select_business_manager(self):
        """ビジネスマネージャーの組織を選択または作成"""
        self.log("ビジネスマネージャーの組織を設定...")
        
        # ラジオボタンを選択（ラベルをクリック）
        await self.browser.human_click('label:has-text("ビジネスマネージャーの組織を選択")')
        await self.browser.random_wait()
        await asyncio.sleep(1)
        
        # 「組織を選択」ボタンをクリック
        await self.browser.human_click('button:has-text("組織を選択")')
        await self.browser.random_wait()
        await asyncio.sleep(1)
        
        # 組織名を入力
        await self.browser.human_type('input[placeholder="組織名を入力"]', self.biz_manager_name)
        await self.browser.random_wait()
        await asyncio.sleep(2)  # 検索結果が表示されるまで待機
        
        # 検索結果から選択を試みる
        select_button_found = False
        try:
            # モーダル内の「選択」ボタンを探す
            modal_selector = '.modal.show button.btn-outline-primary:has-text("選択")'
            select_button = await self.browser.page.query_selector(modal_selector)
            
            if select_button:
                await self.browser.page.click(modal_selector, force=True, timeout=5000)
                select_button_found = True
                self.log(f"✓ 既存の組織を選択: {self.biz_manager_name}")
            else:
                # フォールバック: 直接「選択」テキストを探す
                select_button = await self.browser.page.query_selector('.modal.show button:has-text("選択")')
                if select_button:
                    await select_button.click(force=True)
                    select_button_found = True
                    self.log(f"✓ 既存の組織を選択: {self.biz_manager_name}")
        except Exception as e:
            self.log(f"組織選択ボタンが見つかりません: {e}")
        
        # 選択ボタンが見つからなかった場合 → 組織を新規作成
        if not select_button_found:
            self.log(f"組織が見つかりません。新規作成します: {self.biz_manager_name}")
            
            # モーダルを閉じる（ESCキーまたは閉じるボタン）
            try:
                close_btn = await self.browser.page.query_selector('.modal.show button.close, .modal.show button:has-text("閉じる")')
                if close_btn:
                    await close_btn.click(force=True)
                else:
                    await self.browser.page.keyboard.press('Escape')
            except Exception:
                await self.browser.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 「ビジネスマネージャーの組織を作成」ラジオボタンを選択
            await self.browser.human_click('label:has-text("ビジネスマネージャーの組織を作成")')
            await self.browser.random_wait()
            await asyncio.sleep(1)
            
            # 組織名入力欄に入力（「組織を作成」選択後に表示される入力欄）
            # セレクタ: div.d-flex.mt-2 内の input.form-control
            create_input_selector = 'div.d-flex.mt-2 input.form-control'
            try:
                await self.browser.human_type(create_input_selector, self.biz_manager_name)
                self.log(f"✓ 新規組織名を入力: {self.biz_manager_name}")
            except Exception as e:
                # フォールバック: input[value="new"] の兄弟要素から探す
                self.log(f"入力欄セレクタ失敗、フォールバック試行: {e}")
                fallback_selector = 'input.form-control[aria-required="false"]'
                await self.browser.human_type(fallback_selector, self.biz_manager_name)
        
        await self.browser.random_wait()
    
    async def _change_icon(self, basic_id: str, image_path: str):
        """アイコンを変更"""
        self.log("アイコン変更処理を開始...")
        
        try:
            # 編集ボタンをクリック（別タブが開く）
            await self.browser.human_click(f'a[href="https://page.line.biz/account/{basic_id}"]')
            await self.browser.switch_to_new_tab()
            await self.browser.wait_for_load()
            await asyncio.sleep(2)
            
            # カメラアイコンをクリック
            await self.browser.human_click('i.la-camera')
            await self.browser.random_wait()
            
            # ファイルアップロード（filechooserイベントを使用してダイアログを回避）
            self.log("画像をアップロード中...")
            
            # filechooserイベントをリッスンしながら「アップロード」をクリック
            async with self.browser.page.expect_file_chooser() as fc_info:
                await self.browser.human_click('a:has-text("アップロード")')
            
            file_chooser = await fc_info.value
            await file_chooser.set_files(image_path)
            
            self.log("画像アップロード完了、クロップ画面を待機...")
            await asyncio.sleep(3)
            
            # クロップ範囲を調整
            await self._adjust_crop()
            
            # OKボタンをクリック
            await self.browser.human_click('button[data-automation="confirmation-modal-confirm"]:has-text("OK")')
            await self.browser.random_wait()
            await asyncio.sleep(2)
            
            # 公開ボタンをクリック（data-automation属性を使用）
            await self.browser.page.click('button[data-automation="confirmation-modal-confirm"]:has-text("公開")', force=True, timeout=10000)
            await self.browser.wait_for_load()
            
            # タブを閉じる
            await self.browser.close_current_tab()
            
            self.log("✓ アイコン変更完了")
            
        except Exception as e:
            self.log(f"⚠ アイコン変更エラー: {e}")
    
    async def _adjust_crop(self):
        """クロップ範囲を調整（最大範囲に）"""
        self.log("クロップ範囲を調整中...")
        
        try:
            # クロッパーの面を左上にドラッグ
            face_element = await self.browser.page.wait_for_selector('.cropper-face', timeout=5000)
            if face_element:
                box = await face_element.bounding_box()
                if box:
                    # 左上隅にドラッグ
                    await self.browser.drag_element('.cropper-face', int(box['x']), int(box['y']))
            
            # 右下のハンドルを右下にドラッグ
            se_handle = await self.browser.page.query_selector('.cropper-point.point-se')
            if se_handle:
                box = await se_handle.bounding_box()
                if box:
                    # クロッパーコンテナの範囲を取得
                    container = await self.browser.page.query_selector('.cropper-container')
                    if container:
                        container_box = await container.bounding_box()
                        if container_box:
                            target_x = container_box['x'] + container_box['width'] - 10
                            target_y = container_box['y'] + container_box['height'] - 10
                            await self.browser.drag_element('.cropper-point.point-se', int(target_x), int(target_y))
            
        except Exception as e:
            self.log(f"⚠ クロップ調整スキップ: {e}")
    
    async def _enable_messaging_api(self, basic_id: str):
        """メッセージAPIを有効化"""
        self.log("メッセージAPI有効化処理...")
        
        try:
            # Messaging API設定ページに移動
            url = f"{LINE_MANAGER_URL}account/{basic_id}/setting/messaging-api"
            await self.browser.navigate(url)
            await asyncio.sleep(2)
            
            # 「Messaging APIを利用する」ボタンをクリック
            await self.browser.human_click('button:has-text("Messaging APIを利用する")')
            await self.browser.random_wait()
            await asyncio.sleep(2)
            
            # プロバイダーを選択または入力
            if self.biz_manager_name:
                # まず選択肢に組織名があるか確認
                provider_label_selector = f'label.custom-control-label:has-text("{self.biz_manager_name}")'
                provider_label = await self.browser.page.query_selector(provider_label_selector)
                
                if provider_label:
                    # 選択肢がある場合はクリックして選択
                    self.log(f"プロバイダーを選択: {self.biz_manager_name}")
                    await provider_label.click(force=True)
                    await self.browser.random_wait()
                else:
                    # 選択肢がない場合は入力フォームに入力
                    self.log(f"プロバイダー名を入力: {self.biz_manager_name}")
                    provider_input = await self.browser.page.query_selector('input[name="providerName"]')
                    if provider_input:
                        await provider_input.fill('')  # クリア
                        await self.browser.human_type('input[name="providerName"]', self.biz_manager_name)
                        await self.browser.random_wait()
            
            await asyncio.sleep(1)
            
            # 同意するボタンをクリック
            await self.browser.human_click('button:has-text("同意する")')
            await self.browser.random_wait()
            await asyncio.sleep(2)
            
            # OKボタンを2回クリック
            for _ in range(2):
                if await self.browser.check_element_exists('button:has-text("OK")'):
                    await self.browser.human_click('button:has-text("OK")')
                    await self.browser.random_wait()
                    await asyncio.sleep(1)
            
            self.log("✓ メッセージAPI有効化完了")
            
        except Exception as e:
            self.log(f"⚠ メッセージAPI有効化エラー: {e}")
    
    async def _add_permission(self, basic_id: str) -> str:
        """権限追加リンクを取得"""
        self.log("権限追加処理...")
        permission_link = ""
        
        try:
            # 権限設定ページに移動
            url = f"{LINE_MANAGER_URL}account/{basic_id}/setting/user"
            await self.browser.navigate(url)
            
            # メンバーを追加ボタンをクリック
            await self.browser.human_click('button:has-text("メンバーを追加")')
            await self.browser.random_wait()
            
            # 管理者を選択
            await self.browser.select_option('#formPermissonType', 'ADMIN')
            await self.browser.random_wait()
            
            # URLを発行ボタンをクリック
            await self.browser.human_click('button:has-text("URLを発行")')
            await self.browser.random_wait(2000, 3000)
            
            # 発行されたリンクを取得
            input_element = await self.browser.page.wait_for_selector('input[readonly]')
            permission_link = await input_element.input_value()
            
            # 閉じるボタンをクリック
            await self.browser.human_click('button:has-text("閉じる")')
            await self.browser.random_wait()
            
            self.log(f"✓ 権限追加リンク取得: {permission_link[:50]}...")
            
        except Exception as e:
            self.log(f"⚠ 権限追加エラー: {e}")
        
        return permission_link
    
    async def _get_friend_link(self, basic_id: str) -> str:
        """友達追加リンクを取得"""
        self.log("友達追加リンク取得...")
        friend_link = ""
        
        try:
            # 友達追加URL設定ページに移動
            url = f"{LINE_MANAGER_URL}account/{basic_id}/gainfriends/add-friend-url"
            await self.browser.navigate(url)
            
            # コピーボタンをクリック
            await self.browser.human_click('button:has-text("コピー")')
            await self.browser.random_wait()
            
            # クリップボードから取得する代わりに、表示されているURLを取得
            # 通常、入力欄かテキスト要素に表示されている
            url_element = await self.browser.page.query_selector('input[readonly], .friend-url')
            if url_element:
                friend_link = await url_element.input_value() or await url_element.text_content() or ""
            
            self.log(f"✓ 友達追加リンク取得: {friend_link}")
            
        except Exception as e:
            self.log(f"⚠ 友達追加リンク取得エラー: {e}")
        
        return friend_link
    
    async def _get_access_token(self, line_name: str) -> str:
        """LINE Developers Consoleでアクセストークンを取得"""
        self.log("アクセストークン取得処理...")
        access_token = ""
        
        try:
            # ① LINE Developers Consoleにアクセス
            self.log("LINE Developers Consoleにアクセス...")
            await self.browser.navigate(LINE_DEVELOPERS_URL)
            await self.browser.wait_for_load()
            await asyncio.sleep(3)
            
            # ② ビジネスマネージャーの組織名をクリック
            if self.biz_manager_name:
                self.log(f"組織を選択: {self.biz_manager_name}")
                org_selector = f'.dc-provider-name:has-text("{self.biz_manager_name}")'
                await self.browser.page.click(org_selector, timeout=10000)
                await self.browser.wait_for_load()
                await asyncio.sleep(2)
            
            # ③ 公式LINE名のメニューをクリック
            self.log(f"チャンネルを選択: {line_name}")
            channel_selector = f'h3.title:has-text("{line_name}")'
            try:
                await self.browser.page.click(channel_selector, timeout=10000)
            except Exception:
                # フォールバック: section全体をクリック
                await self.browser.page.click(f'section:has-text("{line_name}")', timeout=5000)
            await self.browser.wait_for_load()
            await asyncio.sleep(2)
            
            # ④ Messaging API設定タブをクリック（日本語/英語両対応）
            self.log("Messaging API設定タブをクリック...")
            await asyncio.sleep(3)  # ページ読み込み待機
            
            # タブナビゲーション内のボタンをクリック
            clicked = False
            
            # 日本語: "Messaging API設定"
            try:
                tab_jp = await self.browser.page.query_selector('nav ul li button:has-text("Messaging API設定")')
                if tab_jp:
                    await tab_jp.click(force=True)
                    clicked = True
                    self.log("Messaging API設定タブをクリック（日本語）")
            except Exception:
                pass
            
            # 英語: "Messaging API"（設定なし）
            if not clicked:
                try:
                    tab_en = await self.browser.page.query_selector('nav ul li button:has-text("Messaging API")')
                    if tab_en:
                        await tab_en.click(force=True)
                        clicked = True
                        self.log("Messaging APIタブをクリック（英語）")
                except Exception:
                    pass
            
            # フォールバック
            if not clicked:
                try:
                    await self.browser.page.click('.kv-tabs button:has-text("Messaging")', force=True, timeout=5000)
                except Exception:
                    await self.browser.page.click('text="Messaging API"', force=True, timeout=5000)
            
            await self.browser.wait_for_load()
            await asyncio.sleep(2)
            
            # ⑤ アクセストークン発行ボタンをクリック（日本語: 発行 / 英語: Issue）
            self.log("アクセストークンを発行...")
            try:
                # 日本語「発行」
                issue_btn_jp = await self.browser.page.query_selector('button:has-text("発行")')
                if issue_btn_jp:
                    await issue_btn_jp.click()
                    self.log("発行ボタンをクリック（日本語）")
                else:
                    # 英語「Issue」
                    await self.browser.page.click('button:has-text("Issue")', timeout=10000)
                    self.log("Issueボタンをクリック（英語）")
            except Exception:
                await self.browser.page.click('button.kv-button:has-text("Issue")', timeout=10000)
            await asyncio.sleep(2)
            
            # ⑥ アクセストークンを取得
            self.log("アクセストークンを取得...")
            await asyncio.sleep(3)
            
            # 戦略1: HTML全体からトークンらしい文字列を正規表現で探す
            try:
                # ページ内の怪しい要素をすべて取得
                elements = await self.browser.page.query_selector_all('div, span, code, p')
                
                for el in elements:
                    text = await el.text_content()
                    if not text:
                        continue
                        
                    text = text.strip()
                    # Reissueなどのボタンテキストが混入している場合を除去
                    if text.endswith("Reissue"):
                        text = text[:-7].strip()
                    elif text.endswith("再発行"):
                        text = text[:-3].strip()
                    
                    # トークンの特徴: 100文字以上、英数字と記号のみ、スペースなし
                    # 末尾が=で終わることを確認
                    if len(text) > 100 and " " not in text and re.match(r'^[a-zA-Z0-9+/=]+$', text):
                        access_token = text
                        self.log(f"✓ アクセストークン発見 (テキスト解析): {access_token[:30]}...")
                        break
                
                # 戦略2: もし上記で見つからなければ、特定のクラスを再度トライ
                if not access_token:
                    # div.copyableのcontent属性
                    el = await self.browser.page.query_selector('div.copyable')
                    if el:
                        access_token = await el.get_attribute('content')
            
            except Exception as e:
                self.log(f"トークン探索エラー: {e}")

            if access_token:
                access_token = access_token.strip()
                self.log(f"✓ アクセストークン確定: {access_token[:20]}...")
            else:
                self.log("⚠ アクセストークンの取得に失敗しました")
                # デバッグ用：ページテキストの一部を保存（解析用）
                content = await self.browser.page.content()
                with open("debug_token_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                self.log("デバッグ用HTMLを保存しました: debug_token_page.html")
            
        except Exception as e:
            self.log(f"⚠ アクセストークン取得エラー: {e}")
        
        return access_token
    
    async def _close_modal_popups(self):
        """モーダルポップアップを閉じる（「閉じる」ボタン優先）"""
        for _ in range(5):
            await asyncio.sleep(0.5)
            
            # モーダルが表示されているか確認
            modal = await self.browser.page.query_selector('.modal-content, .modal.show')
            if not modal:
                break
            
            # 1. 「閉じる」ボタンを優先してクリック
            try:
                close_btn = await self.browser.page.query_selector('button.btn-secondary:has-text("閉じる")')
                if close_btn:
                    await close_btn.click(force=True)
                    self.log("閉じるボタンでポップアップを閉じました")
                    await asyncio.sleep(0.5)
                    continue
            except Exception:
                pass
            
            # 2. 汎用の閉じるボタン
            try:
                close_btn2 = await self.browser.page.query_selector('button:has-text("閉じる")')
                if close_btn2:
                    await close_btn2.click(force=True)
                    self.log("閉じるボタンでポップアップを閉じました")
                    await asyncio.sleep(0.5)
                    continue
            except Exception:
                pass
            
            # 3. ESCキーで閉じる（フォールバック）
            await self.browser.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
    
    def _extract_basic_id(self, url: str) -> str:
        """URLからベーシックIDを抽出"""
        match = re.search(r'(@[a-zA-Z0-9]+)', url)
        return match.group(1) if match else ""
    
    async def process_account(
        self,
        account: AccountRow,
        image_path: str,
        sheet_reader,  # SheetReader インスタンス
        column_config: Dict[str, str]
    ) -> AutomationResult:
        """
        1つのアカウントを処理し、結果をスプレッドシートに書き戻す
        
        Args:
            account: アカウント情報
            image_path: アイコン画像のパス
            sheet_reader: シート読み取りインスタンス
            column_config: 列設定
            
        Returns:
            処理結果
        """
        result = await self.create_account(account, image_path)
        
        # スプレッドシートに結果を書き戻す
        if result.success:
            # ベーシックID
            if result.basic_id and column_config.get('col_basic_id', '-') != '-':
                sheet_reader.update_cell(
                    account.row_number,
                    column_config['col_basic_id'],
                    result.basic_id
                )
            
            # 権限追加リンク
            if result.permission_link and column_config.get('col_permission_link', '-') != '-':
                sheet_reader.update_cell(
                    account.row_number,
                    column_config['col_permission_link'],
                    result.permission_link
                )
            
            # 友達追加リンク
            if result.friend_link and column_config.get('col_friend_link', '-') != '-':
                sheet_reader.update_cell(
                    account.row_number,
                    column_config['col_friend_link'],
                    result.friend_link
                )
            
            # アクセストークン
            if result.access_token and column_config.get('col_access_token', '-') != '-':
                sheet_reader.update_cell(
                    account.row_number,
                    column_config['col_access_token'],
                    result.access_token
                )
            
            # ビジネスアカウント（ログイン用メールアドレス）
            if column_config.get('col_business_account', '-') != '-':
                sheet_reader.update_cell(
                    account.row_number,
                    column_config['col_business_account'],
                    self.email
                )
        
        # 不要なタブを閉じる（現在のタブ以外）
        await self.browser.close_other_tabs()
        
        return result
