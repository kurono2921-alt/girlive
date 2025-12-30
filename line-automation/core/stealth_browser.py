"""
隠蔽型ブラウザモジュール
Playwrightを使用したボット検知回避ブラウザ
"""

import asyncio
import random
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

from config.settings import (
    BROWSER_ARGS,
    DEFAULT_VIEWPORT,
    LOCALE,
    TIMEZONE,
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
    TYPING_DELAY_MIN,
    TYPING_DELAY_MAX,
    BEZIER_CONTROL_OFFSET,
    get_random_user_agent,
    get_random_mouse_steps,
)


class StealthBrowser:
    """隠蔽型ブラウザクラス"""
    
    def __init__(self, headless: bool = False):
        """
        Args:
            headless: ヘッドレスモードで実行するか
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.pages: List[Page] = []
    
    async def launch(self) -> bool:
        """
        ブラウザを起動
        
        Returns:
            起動成功かどうか
        """
        try:
            self.playwright = await async_playwright().start()
            
            # ブラウザ起動オプション
            launch_options = {
                'headless': self.headless,
                'args': BROWSER_ARGS,
            }
            
            # Chromeを優先して使用
            try:
                self.browser = await self.playwright.chromium.launch(
                    channel='chrome',  # 実際のGoogle Chromeを使用
                    **launch_options
                )
            except Exception:
                # Chromeがない場合はChromiumを使用
                self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # コンテキスト作成（設定値を使用）
            self.context = await self.browser.new_context(
                viewport=DEFAULT_VIEWPORT,
                user_agent=get_random_user_agent(),
                locale=LOCALE,
                timezone_id=TIMEZONE,
            )
            
            # 新しいページを作成
            self.page = await self.context.new_page()
            self.pages.append(self.page)
            
            # ステルスモードを適用
            stealth = Stealth()
            await stealth.apply_stealth_async(self.page)
            
            # navigator.webdriverを偽装
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Chromeの自動化検出を回避
                window.chrome = {
                    runtime: {}
                };
                
                // 権限の偽装
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            return True
            
        except Exception as e:
            print(f"ブラウザ起動エラー: {e}")
            return False
    
    async def close(self):
        """ブラウザを閉じる"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def random_wait(self, min_ms: int = None, max_ms: int = None):
        """
        ランダムな待機時間
        
        Args:
            min_ms: 最小待機時間（ミリ秒）
            max_ms: 最大待機時間（ミリ秒）
        """
        min_ms = min_ms or ACTION_DELAY_MIN
        max_ms = max_ms or ACTION_DELAY_MAX
        wait_time = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(wait_time)
    
    async def wait_for_load(self):
        """ページ読み込み完了を待機"""
        await self.page.wait_for_load_state('networkidle')
        await self.random_wait(500, 1000)
    
    async def human_type(self, selector: str, text: str):
        """
        人間らしいタイピング
        
        Args:
            selector: 入力要素のセレクタ
            text: 入力するテキスト
        """
        element = await self.page.wait_for_selector(selector)
        await element.click()
        await self.random_wait(200, 500)
        
        # 1文字ずつ入力
        for char in text:
            await self.page.keyboard.type(char)
            delay = random.randint(TYPING_DELAY_MIN, TYPING_DELAY_MAX)
            await asyncio.sleep(delay / 1000)
    
    async def bezier_move_to(self, x: int, y: int):
        """
        ベジェ曲線を使った人間らしいマウス移動
        
        Args:
            x: 目標X座標
            y: 目標Y座標
        """
        # 現在のマウス位置を取得（デフォルトは画面中央付近）
        start_x = random.randint(400, 600)
        start_y = random.randint(300, 500)
        
        # 制御点をランダムに生成
        offset = BEZIER_CONTROL_OFFSET
        ctrl1_x = start_x + (x - start_x) * 0.3 + random.randint(-offset, offset)
        ctrl1_y = start_y + (y - start_y) * 0.3 + random.randint(-offset, offset)
        ctrl2_x = start_x + (x - start_x) * 0.7 + random.randint(-offset, offset)
        ctrl2_y = start_y + (y - start_y) * 0.7 + random.randint(-offset, offset)
        
        # ベジェ曲線に沿って移動
        steps = get_random_mouse_steps()
        for i in range(steps + 1):
            t = i / steps
            
            # 3次ベジェ曲線の計算
            px = (1-t)**3 * start_x + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * x
            py = (1-t)**3 * start_y + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * y
            
            await self.page.mouse.move(px, py)
            await asyncio.sleep(random.randint(5, 15) / 1000)
    
    async def human_click(self, selector: str, wait_after: bool = True):
        """
        人間らしいクリック
        
        Args:
            selector: クリック要素のセレクタ
            wait_after: クリック後に待機するか
        """
        element = await self.page.wait_for_selector(selector, state='visible')
        
        # 要素の位置を取得
        box = await element.bounding_box()
        if box:
            # 要素の中心にランダムなオフセットを加えた位置をクリック
            x = box['x'] + box['width'] / 2 + random.randint(-5, 5)
            y = box['y'] + box['height'] / 2 + random.randint(-5, 5)
            
            # ベジェ曲線で移動
            await self.bezier_move_to(int(x), int(y))
            await self.random_wait(100, 300)
        
        await element.click()
        
        if wait_after:
            await self.random_wait()
    
    async def select_option(self, selector: str, value: str):
        """
        プルダウンから選択
        
        Args:
            selector: セレクト要素のセレクタ
            value: 選択する値
        """
        await self.page.wait_for_selector(selector)
        await self.random_wait(300, 600)
        await self.page.select_option(selector, value=value)
        await self.random_wait()
    
    async def navigate(self, url: str):
        """
        ページに移動
        
        Args:
            url: 移動先URL
        """
        await self.page.goto(url)
        await self.wait_for_load()
        await self.random_wait()
    
    async def switch_to_new_tab(self) -> Optional[Page]:
        """
        新しく開いたタブに切り替え
        
        Returns:
            新しいページ（なければNone）
        """
        # タブが開くのを少し待つ
        for _ in range(10):  # 最大5秒待機
            await asyncio.sleep(0.5)
            pages = self.context.pages
            if len(pages) > 0:
                latest_page = pages[-1]
                # 現在のページと異なる、かつまだ管理リストにない（または最新のページ）場合に切り替え
                if latest_page != self.page:
                    await latest_page.wait_for_load_state()
                    self.page = latest_page
                    
                    # 管理リストを更新
                    self.pages = pages
                    
                    # ステルスモードを適用
                    stealth = Stealth()
                    await stealth.apply_stealth_async(self.page)
                    
                    return self.page
        
        return None
    
    async def close_current_tab(self):
        """現在のタブを閉じる"""
        if len(self.pages) > 1:
            current_page = self.page
            self.pages.remove(current_page)
            await current_page.close()
            
            # 前のタブに戻る
            self.page = self.pages[-1]
            await self.random_wait()
    
    async def get_current_url(self) -> str:
        """現在のURLを取得"""
        return self.page.url
    
    async def get_text_content(self, selector: str) -> str:
        """
        要素のテキストを取得
        
        Args:
            selector: セレクタ
            
        Returns:
            テキスト内容
        """
        element = await self.page.wait_for_selector(selector)
        return await element.text_content() or ""
    
    async def get_input_value(self, selector: str) -> str:
        """
        入力要素の値を取得
        
        Args:
            selector: セレクタ
            
        Returns:
            入力値
        """
        element = await self.page.wait_for_selector(selector)
        return await element.input_value() or ""
    
    async def check_element_exists(self, selector: str, timeout: int = 5000) -> bool:
        """
        要素が存在するかチェック
        
        Args:
            selector: セレクタ
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            存在するかどうか
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def drag_element(self, selector: str, target_x: int, target_y: int):
        """
        要素をドラッグ
        
        Args:
            selector: ドラッグする要素のセレクタ
            target_x: 移動先X座標
            target_y: 移動先Y座標
        """
        element = await self.page.wait_for_selector(selector)
        box = await element.bounding_box()
        
        if box:
            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2
            
            await self.page.mouse.move(start_x, start_y)
            await self.random_wait(100, 200)
            await self.page.mouse.down()
            await self.random_wait(100, 200)
            
            # 段階的に移動
            steps = 10
            for i in range(1, steps + 1):
                px = start_x + (target_x - start_x) * i / steps
                py = start_y + (target_y - start_y) * i / steps
                await self.page.mouse.move(px, py)
                await asyncio.sleep(random.randint(10, 30) / 1000)
            
            await self.random_wait(100, 200)
            await self.page.mouse.up()
    
    async def close_other_tabs(self):
        """
        現在のアクティブなタブ以外をすべて閉じる
        """
        if not self.context:
            return
            
        pages = self.context.pages
        current_page = self.page
        
        for p in pages:
            if p != current_page and not p.is_closed():
                try:
                    await p.close()
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
        
        # 管理リストを更新（閉じられていないページのみ残す）
        self.pages = [p for p in self.context.pages if not p.is_closed()]

    async def upload_file(self, selector: str, file_path: str):
        """
        ファイルをアップロード
        
        Args:
            selector: ファイル入力要素のセレクタ
            file_path: アップロードするファイルのパス
        """
        # ファイル選択ダイアログをバイパスして直接ファイルを設定
        file_input = await self.page.wait_for_selector(selector)
        await file_input.set_input_files(file_path)
        await self.random_wait()
