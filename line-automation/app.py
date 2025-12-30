"""
LINE自動化フロー - PySide6 フロントエンド
モダンでスタイリッシュなUIアプリケーション
"""

import sys
import threading
import asyncio
from typing import Optional, List
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTabWidget,
    QScrollArea, QFrame, QSpacerItem, QSizePolicy, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal, QObject, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QColor

from core.sheets_client import SheetsClient, get_column_options


class StyledComboBox(QComboBox):
    """矢印付きカスタムコンボボックス"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # リストビューを作成してチェックマークを無効化
        from PySide6.QtWidgets import QListView
        list_view = QListView()
        list_view.setStyleSheet("""
            QListView {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                color: #ffffff;
                outline: none;
                padding: 4px;
            }
            QListView::item {
                padding: 8px 16px;
                background-color: #1a1a1a;
                color: #ffffff;
                border: none;
            }
            QListView::item:hover {
                background-color: #2a2a2a;
            }
            QListView::item:selected {
                background-color: #00d4aa;
                color: #0f0f0f;
            }
        """)
        self.setView(list_view)
        
        self.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 12px 40px 12px 16px;
                color: #ffffff;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #00d4aa;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        # 矢印を描画
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("#a0a0a0"))
        painter.setFont(QFont("Arial", 12))
        
        # 右側に▼を描画
        rect = self.rect()
        arrow_rect = rect.adjusted(rect.width() - 35, 0, -10, 0)
        painter.drawText(arrow_rect, Qt.AlignVCenter | Qt.AlignCenter, "▼")


class CaptchaDialog(QDialog):
    """CAPTCHA認証待機ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("画像認証が必要です")
        self.setFixedSize(450, 280)
        self.setModal(True)
        
        # ダークテーマ
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # アイコン
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px; color: #ffffff;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # メッセージ
        message_label = QLabel("画像認証（CAPTCHA）が検出されました。\nブラウザで認証を完了してから、\n下のボタンをクリックしてください。")
        message_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        # 完了ボタン
        complete_button = QPushButton("認証完了")
        complete_button.setFixedSize(160, 48)
        complete_button.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                color: #0f0f0f;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #00f5c4;
            }
        """)
        complete_button.clicked.connect(self.accept)
        layout.addWidget(complete_button, alignment=Qt.AlignCenter)


class ToggleSwitch(QWidget):
    """カスタムトグルスイッチウィジェット"""
    toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._thumb_position = 4
        self.setFixedSize(52, 28)
        self.setCursor(Qt.PointingHandCursor)
        
        # アニメーション
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
    
    def get_thumb_position(self):
        return self._thumb_position
    
    def set_thumb_position(self, pos):
        self._thumb_position = pos
        self.update()
    
    thumb_position = Property(float, get_thumb_position, set_thumb_position)
    
    def isChecked(self):
        return self._checked
    
    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self._animate()
            self.toggled.emit(checked)
    
    def _animate(self):
        self._animation.stop()
        if self._checked:
            self._animation.setStartValue(self._thumb_position)
            self._animation.setEndValue(28)
        else:
            self._animation.setStartValue(self._thumb_position)
            self._animation.setEndValue(4)
        self._animation.start()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景
        if self._checked:
            bg_color = QColor("#00d4aa")
        else:
            bg_color = QColor("#3a3a3a")
        
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 52, 28, 14, 14)
        
        # サム（つまみ）
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(self._thumb_position), 4, 20, 20)
from core.settings_manager import SettingsManager, LineSettings, AppSettings


# スタイルシート（ダークテーマ）
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0f0f0f;
    color: #ffffff;
}

QTabWidget::pane {
    border: none;
    background-color: #0f0f0f;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #a0a0a0;
    padding: 14px 32px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 15px;
    font-weight: bold;
    min-width: 100px;
}

QTabBar::tab:selected {
    background-color: #00d4aa;
    color: #0f0f0f;
}

QTabBar::tab:hover:!selected {
    background-color: #242424;
}

QScrollArea {
    border: none;
    background-color: #0f0f0f;
}

QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #333333;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d4aa;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLineEdit {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 12px 16px;
    color: #ffffff;
    font-size: 14px;
}

QLineEdit:focus {
    border-color: #00d4aa;
}

QLineEdit::placeholder {
    color: #666666;
}

QComboBox {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 12px 16px;
    color: #ffffff;
    font-size: 14px;
    min-height: 20px;
}

QComboBox:focus {
    border-color: #00d4aa;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 35px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: none;
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    color: #ffffff;
    selection-background-color: #00d4aa;
    selection-color: #0f0f0f;
    outline: none;
}

QPushButton {
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#runButton {
    background-color: #00d4aa;
    color: #0f0f0f;
    font-size: 15px;
    font-weight: bold;
    min-width: 100px;
    border: 2px solid #00d4aa;
}

QPushButton#runButton:hover {
    background-color: #00f5c4;
    border-color: #00f5c4;
}

QPushButton#runButton:disabled {
    background-color: #1a1a1a;
    color: #666666;
    border-color: #333333;
}

QPushButton#pauseButton {
    background-color: #ff6b35;
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    min-width: 100px;
    border: 2px solid #ff6b35;
}

QPushButton#pauseButton:hover {
    background-color: #ff8c5a;
    border-color: #ff8c5a;
}

QPushButton#pauseButton:disabled {
    background-color: #1a1a1a;
    color: #666666;
    border-color: #333333;
}

QPushButton#saveButton {
    background-color: #242424;
    color: #ffffff;
    border: 1px solid #333333;
}

QPushButton#saveButton:hover {
    background-color: #333333;
}

QFrame#headlessFrame {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 8px;
}

QCheckBox {
    color: #ffffff;
    font-size: 14px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 40px;
    height: 22px;
    border-radius: 11px;
    background-color: #333333;
}

QCheckBox::indicator:checked {
    background-color: #00d4aa;
}
"""


class WorkerSignals(QObject):
    """ワーカースレッド用シグナル"""
    finished = Signal(list, str)
    sheet_names_loaded = Signal(object, object)  # (sheet_names, error)
    automation_finished = Signal()  # 自動化完了シグナル
    captcha_required = Signal()  # CAPTCHA検知シグナル
    captcha_resolved = Signal()  # CAPTCHA解決シグナル


class LineAutomationApp(QMainWindow):
    """LINE自動化アプリのメインウィンドウ"""
    
    def __init__(self):
        super().__init__()
        
        self.settings_manager = SettingsManager()
        self.sheets_client = SheetsClient()
        
        # シグナル用
        self.worker_signals = WorkerSignals()
        self.worker_signals.sheet_names_loaded.connect(self._on_sheet_names_loaded)
        self.worker_signals.automation_finished.connect(self._finish_automation)
        self.worker_signals.captcha_required.connect(self._on_captcha_required)
        
        # CAPTCHA待機用（スレッド間通信のためthreading.Eventを使用）
        self._captcha_event: Optional[threading.Event] = None
        
        # UI参照
        self.email_input: Optional[QLineEdit] = None
        self.password_input: Optional[QLineEdit] = None
        self.sheet_url_input: Optional[QLineEdit] = None
        self.sheet_name_combo: Optional[QComboBox] = None
        self.column_combos: dict = {}
        self.icon_path_input = None
        self.biz_manager_toggle = None
        self.biz_manager_input = None
        self.biz_manager_input_container = None
        self.headless_toggle = None
        
        self.run_button: Optional[QPushButton] = None
        self.pause_button: Optional[QPushButton] = None
        self.save_button: Optional[QPushButton] = None
        
        # 状態
        self.is_running = False
        self.is_paused = False
        self.automation_runner = None
        self.automation_thread = None
        self._pending_sheet_name = None  # 復元待ちのシート名
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """UIをセットアップ"""
        self.setWindowTitle("LINE自動化フロー")
        self.setMinimumSize(600, 700)
        self.resize(600, 900)
        self.setStyleSheet(DARK_STYLE)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        tab_widget.setFont(QFont("", 14))
        main_layout.addWidget(tab_widget)
        
        # 公式LINEタブ
        line_tab = self.create_line_tab()
        tab_widget.addTab(line_tab, "公式LINE")
        
        # プロラインタブ
        proline_tab = self.create_proline_tab()
        tab_widget.addTab(proline_tab, "プロライン")
    
    def create_section_header(self, title: str) -> QWidget:
        """セクションヘッダーを作成"""
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 24, 0, 12)
        layout.setSpacing(12)
        
        # アクセントバー
        accent = QFrame()
        accent.setFixedSize(4, 20)
        accent.setStyleSheet("background-color: #00d4aa; border-radius: 2px;")
        layout.addWidget(accent)
        
        # タイトル
        label = QLabel(title)
        label.setFont(QFont("", 16, QFont.Bold))
        label.setStyleSheet("color: #ffffff;")
        layout.addWidget(label)
        
        layout.addStretch()
        return frame
    
    def create_labeled_input(self, label_text: str, required: bool = False, 
                             password: bool = False, placeholder: str = "") -> tuple:
        """ラベル付き入力フィールドを作成"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(4)
        
        # ラベル
        label_layout = QHBoxLayout()
        label_layout.setSpacing(0)
        
        if required:
            req = QLabel("※")
            req.setStyleSheet("color: #ff4757; font-size: 14px;")
            label_layout.addWidget(req)
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        label_layout.addWidget(label)
        label_layout.addStretch()
        
        layout.addLayout(label_layout)
        
        # 入力フィールド
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        if password:
            input_field.setEchoMode(QLineEdit.Password)
        
        layout.addWidget(input_field)
        
        return container, input_field
    
    def create_labeled_combo(self, label_text: str, options: List[str], 
                             required: bool = False) -> tuple:
        """ラベル付きコンボボックスを作成"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(4)
        
        # ラベル
        label_layout = QHBoxLayout()
        label_layout.setSpacing(0)
        
        if required:
            req = QLabel("※")
            req.setStyleSheet("color: #ff4757; font-size: 14px;")
            label_layout.addWidget(req)
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        label_layout.addWidget(label)
        label_layout.addStretch()
        
        layout.addLayout(label_layout)
        
        # コンボボックス（カスタム）
        combo = StyledComboBox()
        combo.addItems(options)
        layout.addWidget(combo)
        
        return container, combo
    
    def create_line_tab(self) -> QWidget:
        """公式LINEタブを作成"""
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # コンテンツウィジェット
        content = QWidget()
        content.setStyleSheet("background-color: #0f0f0f;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        
        column_options = get_column_options()
        
        # ===== ログイン情報 =====
        layout.addWidget(self.create_section_header("ログイン情報"))
        
        email_container, self.email_input = self.create_labeled_input(
            "メールアドレス", required=True, placeholder="example@line.me"
        )
        layout.addWidget(email_container)
        
        password_container, self.password_input = self.create_labeled_input(
            "パスワード", required=True, password=True
        )
        layout.addWidget(password_container)
        
        # ===== シート情報 =====
        layout.addWidget(self.create_section_header("シート情報"))
        
        url_container, self.sheet_url_input = self.create_labeled_input(
            "連携先シートURL", required=True, 
            placeholder="https://docs.google.com/spreadsheets/d/..."
        )
        layout.addWidget(url_container)
        self.sheet_url_input.editingFinished.connect(self.on_sheet_url_change)
        
        sheet_container, self.sheet_name_combo = self.create_labeled_combo(
            "使用シート名", ["シートURLを入力してください"], required=True
        )
        self.sheet_name_combo.setEnabled(False)
        layout.addWidget(sheet_container)
        
        # ===== シートの列情報 =====
        layout.addWidget(self.create_section_header("シートの列情報"))
        
        column_configs = [
            ('enabled', '有効/無効の列', True),
            ('line_name', '公式LINE名の列', True),
            ('icon_image', 'アイコン画像の列', True),
            ('basic_id', 'ベーシックIDの列', False),
            ('access_token', 'アクセストークンの列', False),
            ('permission_link', '権限追加リンクの列', False),
            ('friend_link', '友達追加リンクの列', False),
            ('business_account', 'ビジネスアカウントの列', False),
        ]
        
        for key, label, required in column_configs:
            container, combo = self.create_labeled_combo(label, column_options, required)
            self.column_combos[key] = combo
            layout.addWidget(container)
        
        # ===== その他 =====
        layout.addWidget(self.create_section_header("その他"))
        
        # アイコン画像の保存先
        icon_path_frame = QFrame()
        icon_path_frame.setObjectName("headlessFrame")
        icon_path_layout = QVBoxLayout(icon_path_frame)
        icon_path_layout.setContentsMargins(16, 16, 16, 16)
        icon_path_layout.setSpacing(8)
        
        icon_path_label = QLabel("アイコン画像の保存先")
        icon_path_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        icon_path_layout.addWidget(icon_path_label)
        
        icon_path_row = QHBoxLayout()
        icon_path_row.setSpacing(8)
        
        self.icon_path_input = QLineEdit()
        self.icon_path_input.setPlaceholderText("フォルダを選択してください")
        self.icon_path_input.setReadOnly(True)
        icon_path_row.addWidget(self.icon_path_input)
        
        icon_path_button = QPushButton("選択")
        icon_path_button.setFixedWidth(80)
        icon_path_button.setStyleSheet("""
            QPushButton {
                background-color: #242424;
                color: #ffffff;
                font-size: 13px;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        icon_path_button.clicked.connect(self.on_select_icon_path)
        icon_path_row.addWidget(icon_path_button)
        
        icon_path_layout.addLayout(icon_path_row)
        layout.addWidget(icon_path_frame)
        
        spacer1 = QWidget()
        spacer1.setFixedHeight(12)
        layout.addWidget(spacer1)
        
        # ビジネスマネージャーの組織
        biz_manager_frame = QFrame()
        biz_manager_frame.setObjectName("headlessFrame")
        biz_manager_layout = QVBoxLayout(biz_manager_frame)
        biz_manager_layout.setContentsMargins(16, 16, 16, 16)
        biz_manager_layout.setSpacing(12)
        
        biz_toggle_row = QHBoxLayout()
        biz_label = QLabel("ビジネスマネージャーの組織")
        biz_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        biz_toggle_row.addWidget(biz_label)
        biz_toggle_row.addStretch()
        
        self.biz_manager_toggle = ToggleSwitch()
        self.biz_manager_toggle.toggled.connect(self.on_biz_manager_toggle)
        biz_toggle_row.addWidget(self.biz_manager_toggle)
        biz_manager_layout.addLayout(biz_toggle_row)
        
        self.biz_manager_input_container = QWidget()
        biz_input_layout = QVBoxLayout(self.biz_manager_input_container)
        biz_input_layout.setContentsMargins(0, 8, 0, 0)
        biz_input_layout.setSpacing(4)
        
        biz_input_label = QLabel("組織名を入力")
        biz_input_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        biz_input_layout.addWidget(biz_input_label)
        
        self.biz_manager_input = QLineEdit()
        self.biz_manager_input.setPlaceholderText("ビジネスマネージャーの組織名")
        biz_input_layout.addWidget(self.biz_manager_input)
        
        self.biz_manager_input_container.setVisible(False)
        biz_manager_layout.addWidget(self.biz_manager_input_container)
        
        layout.addWidget(biz_manager_frame)
        
        spacer2 = QWidget()
        spacer2.setFixedHeight(12)
        layout.addWidget(spacer2)
        
        # ヘッドレスモード
        headless_frame = QFrame()
        headless_frame.setObjectName("headlessFrame")
        headless_layout = QHBoxLayout(headless_frame)
        headless_layout.setContentsMargins(16, 16, 16, 16)
        
        headless_label = QLabel("ヘッドレスモード")
        headless_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        headless_layout.addWidget(headless_label)
        
        headless_layout.addStretch()
        
        self.headless_toggle = ToggleSwitch()
        self.headless_toggle.toggled.connect(lambda checked: None)
        headless_layout.addWidget(self.headless_toggle)
        
        layout.addWidget(headless_frame)
        
        # ===== ボタンエリア =====
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 32, 0, 40)
        button_layout.setSpacing(12)
        
        self.run_button = QPushButton("実行")
        self.run_button.setFixedHeight(48)
        self.run_button.setMinimumWidth(120)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #00d4aa;
                color: #0f0f0f;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #00f5c4;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.run_button.clicked.connect(self.on_run_click)
        button_layout.addWidget(self.run_button)
        
        self.pause_button = QPushButton("一時停止")
        self.pause_button.setFixedHeight(48)
        self.pause_button.setMinimumWidth(120)
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff8c5a;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.on_pause_click)
        button_layout.addWidget(self.pause_button)
        
        button_layout.addStretch()
        
        self.save_button = QPushButton("設定を保存")
        self.save_button.setFixedHeight(48)
        self.save_button.setMinimumWidth(120)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #242424;
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #555555;
            }
        """)
        self.save_button.clicked.connect(self.on_save_click)
        button_layout.addWidget(self.save_button)
        
        layout.addWidget(button_container)
        layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def create_proline_tab(self) -> QWidget:
        """プロラインタブを作成（開発中）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("🚧")
        icon.setFont(QFont("", 64))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        
        title = QLabel("開発中")
        title.setFont(QFont("", 24, QFont.Bold))
        title.setStyleSheet("color: #a0a0a0;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("この機能は現在開発中です")
        desc.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        return widget
    
    def on_sheet_url_change(self):
        """シートURL変更時"""
        print("[DEBUG] on_sheet_url_change が呼ばれました")
        url = self.sheet_url_input.text().strip()
        print(f"[DEBUG] URL: {url}")
        
        if not url:
            self.sheet_name_combo.clear()
            self.sheet_name_combo.addItem("シートURLを入力してください")
            self.sheet_name_combo.setEnabled(False)
            return
        
        self.sheet_name_combo.clear()
        self.sheet_name_combo.addItem("読み込み中...")
        self.sheet_name_combo.setEnabled(False)
        
        def fetch():
            print(f"[DEBUG] シート取得開始: {url}")
            try:
                sheet_names, error = self.sheets_client.get_sheet_names(url)
                print(f"[DEBUG] シート取得結果: names={sheet_names}, error={error}")
                # シグナルでメインスレッドに通知
                self.worker_signals.sheet_names_loaded.emit(sheet_names, error)
            except Exception as e:
                print(f"[DEBUG] シート取得エラー: {e}")
                self.worker_signals.sheet_names_loaded.emit([], str(e))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def _on_sheet_names_loaded(self, sheet_names, error):
        """シート名取得完了時のスロット（メインスレッド）"""
        print(f"[DEBUG] _on_sheet_names_loaded: names={len(sheet_names) if sheet_names else 0}, error={error}")
        
        self.sheet_name_combo.clear()
        
        if error:
            self.sheet_name_combo.addItem("エラー")
            self.sheet_name_combo.setEnabled(False)
            QMessageBox.warning(self, "エラー", str(error))
        else:
            self.sheet_name_combo.addItems(sheet_names)
            self.sheet_name_combo.setEnabled(True)
            
            # 保存されていたシート名があれば選択
            if self._pending_sheet_name:
                idx = self.sheet_name_combo.findText(self._pending_sheet_name)
                if idx >= 0:
                    self.sheet_name_combo.setCurrentIndex(idx)
                self._pending_sheet_name = None
    
    def on_run_click(self):
        """実行ボタン"""
        errors = self.validate()
        if errors:
            QMessageBox.warning(self, "入力エラー", "\n".join(errors))
            return
        
        # アイコン保存先の確認
        if not self.icon_path_input.text():
            QMessageBox.warning(self, "入力エラー", "アイコン画像の保存先を選択してください")
            return
        
        self.is_running = True
        self.run_button.setEnabled(False)
        self.run_button.setText("実行中...")
        self.pause_button.setEnabled(True)
        
        # 設定を保存
        self.on_save_click()
        
        # 別スレッドで自動化を実行
        def run_automation():
            from core.automation_runner import AutomationRunner, RunnerConfig
            
            config = RunnerConfig(
                email=self.email_input.text(),
                password=self.password_input.text(),
                sheet_url=self.sheet_url_input.text(),
                sheet_name=self.sheet_name_combo.currentText(),
                icon_save_path=self.icon_path_input.text(),
                headless=self.headless_toggle.isChecked(),
                biz_manager_enabled=self.biz_manager_toggle.isChecked(),
                biz_manager_name=self.biz_manager_input.text(),
                col_enabled=self.column_combos['enabled'].currentText(),
                col_line_name=self.column_combos['line_name'].currentText(),
                col_icon_image=self.column_combos['icon_image'].currentText(),
                col_basic_id=self.column_combos['basic_id'].currentText(),
                col_access_token=self.column_combos['access_token'].currentText(),
                col_permission_link=self.column_combos['permission_link'].currentText(),
                col_friend_link=self.column_combos['friend_link'].currentText(),
                col_business_account=self.column_combos['business_account'].currentText(),
            )
            
            # CAPTCHA待機用のイベントを作成（スレッド間通信）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._captcha_event = threading.Event()
            
            async def captcha_callback():
                """CAPTCHA検知時に呼ばれるコールバック"""
                # メインスレッドにシグナルを送信
                self.worker_signals.captcha_required.emit()
                # ユーザーがダイアログで「完了」を押すまで待機（ポーリング）
                while not self._captcha_event.is_set():
                    await asyncio.sleep(0.5)
                self._captcha_event.clear()
            
            self.automation_runner = AutomationRunner(
                config=config,
                on_status_update=self._log_status,
                on_progress_update=self._update_progress,
                on_captcha_required=captcha_callback
            )
            
            try:
                results = loop.run_until_complete(self.automation_runner.run())
                self._on_automation_complete(results)
            finally:
                loop.close()
        
        self.automation_thread = threading.Thread(target=run_automation, daemon=True)
        self.automation_thread.start()
    
    def _on_captcha_required(self):
        """CAPTCHAが必要なとき（メインスレッドで呼ばれる）"""
        dialog = CaptchaDialog(self)
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # ユーザーが「認証完了」を押した
            if self._captcha_event:
                self._captcha_event.set()
    
    def _log_status(self, message: str):
        """ステータスログ（スレッドセーフ）"""
        print(message)  # コンソールに出力
    
    def _update_progress(self, current: int, total: int):
        """進捗更新"""
        print(f"進捗: {current}/{total}")
    
    def _on_automation_complete(self, results):
        """自動化完了時のコールバック"""
        # シグナルでメインスレッドに通知
        self.worker_signals.automation_finished.emit()
    
    def _finish_automation(self):
        """自動化完了後のUI更新"""
        self.is_running = False
        self.run_button.setEnabled(True)
        self.run_button.setText("実行")
        self.pause_button.setEnabled(False)
        self.pause_button.setText("一時停止")
        QMessageBox.information(self, "完了", "処理が完了しました")
    
    def on_pause_click(self):
        """一時停止ボタン"""
        if not self.automation_runner:
            return
        
        if self.is_paused:
            self.is_paused = False
            self.pause_button.setText("一時停止")
            self.automation_runner.resume()
        else:
            self.is_paused = True
            self.pause_button.setText("再開")
            self.automation_runner.pause()
    
    def on_biz_manager_toggle(self, checked: bool):
        """ビジネスマネージャートグル切替"""
        self.biz_manager_input_container.setVisible(checked)
    
    def on_select_icon_path(self):
        """アイコン画像保存先フォルダを選択"""
        from PySide6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(
            self, 
            "アイコン画像の保存先を選択",
            self.icon_path_input.text() or ""
        )
        if folder:
            self.icon_path_input.setText(folder)
    
    def on_save_click(self):
        """設定保存ボタン"""
        settings = self.collect_settings()
        if self.settings_manager.save(AppSettings(line_settings=settings)):
            QMessageBox.information(self, "保存完了", "設定を保存しました")
        else:
            QMessageBox.warning(self, "エラー", "設定の保存に失敗しました")
    
    def validate(self) -> List[str]:
        """バリデーション"""
        errors = []
        if not self.email_input.text():
            errors.append("メールアドレスを入力してください")
        if not self.password_input.text():
            errors.append("パスワードを入力してください")
        if not self.sheet_url_input.text():
            errors.append("連携先シートURLを入力してください")
        sheet_val = self.sheet_name_combo.currentText()
        if sheet_val in ["シートURLを入力してください", "読み込み中...", "エラー", ""]:
            errors.append("使用シート名を選択してください")
        return errors
    
    def collect_settings(self) -> LineSettings:
        """設定収集"""
        return LineSettings(
            email=self.email_input.text(),
            password=self.password_input.text(),
            sheet_url=self.sheet_url_input.text(),
            sheet_name=self.sheet_name_combo.currentText(),
            col_enabled=self.column_combos['enabled'].currentText(),
            col_line_name=self.column_combos['line_name'].currentText(),
            col_icon_image=self.column_combos['icon_image'].currentText(),
            col_basic_id=self.column_combos['basic_id'].currentText(),
            col_access_token=self.column_combos['access_token'].currentText(),
            col_permission_link=self.column_combos['permission_link'].currentText(),
            col_friend_link=self.column_combos['friend_link'].currentText(),
            col_business_account=self.column_combos['business_account'].currentText(),
            icon_save_path=self.icon_path_input.text(),
            biz_manager_enabled=self.biz_manager_toggle.isChecked(),
            biz_manager_name=self.biz_manager_input.text(),
            headless_mode=self.headless_toggle.isChecked(),
        )
    
    def load_settings(self):
        """設定読み込み"""
        settings = self.settings_manager.load()
        line = settings.line_settings
        
        self.email_input.setText(line.email)
        self.password_input.setText(line.password)
        self.sheet_url_input.setText(line.sheet_url)
        
        # シート名を記憶してから読み込み
        if line.sheet_url:
            self._pending_sheet_name = line.sheet_name  # 後で選択するために記憶
            self.on_sheet_url_change()
        
        for key, combo in self.column_combos.items():
            value = getattr(line, f"col_{key}", "")
            if value:
                idx = combo.findText(value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        
        self.icon_path_input.setText(line.icon_save_path)
        
        self.biz_manager_toggle.setChecked(line.biz_manager_enabled)
        self.biz_manager_input.setText(line.biz_manager_name)
        self.biz_manager_input_container.setVisible(line.biz_manager_enabled)
        
        self.headless_toggle.setChecked(line.headless_mode)


def main():
    """アプリケーション起動"""
    app = QApplication(sys.argv)
    window = LineAutomationApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
