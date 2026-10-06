"""Kana Studio — a local Windows desktop application, written independently."""
import html
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSettings, QEvent, QSize, QRectF
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QTextCursor, QPen, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QToolButton,
    QHBoxLayout, QVBoxLayout, QGridLayout, QPlainTextEdit, QTextBrowser, QSplitter,
    QButtonGroup, QCheckBox, QSlider, QFileDialog, QMessageBox, QDialog,
    QScrollArea, QTabWidget, QDialogButtonBox, QToolTip,
)
from kana import KANA, GROUP_NAMES, BASE_READINGS, READING_MIGRATIONS, Options, Result, convert
from version import VERSION

APP_NAME = "Kana Studio"
SAMPLE = (
    "Утром Маша открыла окно. На столе стояла чашка чая, а рядом лежала книга.\n\n"
    "Сегодня она решила никуда не спешить. Можно читать, слушать музыку и смотреть, "
    "как солнечные лучи тихо скользят по стене.\n\n"
    "За окном шумели деревья. Маленькая птица села на ветку, покачалась и полетела дальше. "
    "Маша улыбнулась: иногда для хорошего дня достаточно чашки чая и новой истории."
)

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #263439; }
QMainWindow, QWidget#workspace { background: #f5f6f3; }
QFrame#sidebar { background: #173c3a; border: none; }
QFrame#sidebar QLabel { color: #c0d6d0; }
QLabel#brand { color: white; font-size: 21px; font-weight: 700; }
QLabel#brandKana { color: #dcf7b4; font-size: 33px; font-family: 'Yu Gothic'; font-weight: 700; }
QLabel#sidebarTitle { color: #8bad9f; font-size: 11px; font-weight: 700; }
QLabel#sidebarNote { color: #b5cec5; font-size: 12px; }
QLabel#pageTitle { font-size: 29px; font-weight: 700; color: #183c39; }
QLabel#muted { color: #72807b; }
QLabel#eyebrow { color: #688379; font-size: 11px; font-weight: 700; }
QLabel#sectionTitle { font-weight: 600; font-size: 14px; color: #263e37; }
QLabel#panelTitle { font-size: 15px; font-weight: 600; }
QLabel#statValue { font-size: 23px; color: #235b49; font-weight: 600; }
QLabel#pill { background: #e4eee4; border-radius: 12px; padding: 5px 11px; color: #356450; font-size: 11px; }
QFrame#card { background: white; border: 1px solid #dfe6df; border-radius: 14px; }
QFrame#innerCard { background: #f0f5ed; border: none; border-radius: 12px; }
QFrame#sidebarCard { background: #234b45; border-radius: 12px; }
QPushButton, QToolButton { background: #ffffff; border: 1px solid #d9e2da; border-radius: 8px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover, QToolButton:hover { background: #edf3e9; border-color: #91b2a0; }
QPushButton:pressed { background: #dae9d9; }
QPushButton:disabled { color: #9ca8a0; background: #f1f3ef; border-color: #e6ebe4; }
QPushButton#primary { background: #285d47; color: white; border: 1px solid #285d47; }
QPushButton#primary:hover { background: #1c4936; }
QPushButton#primary:disabled { background: #b0c5b7; border-color: #b0c5b7; }
QPushButton#segment { background: #f2f5ef; border: 1px solid transparent; color: #64756a; padding: 9px 18px; }
QPushButton#segment:checked { background: #285d47; color: white; border-color: #285d47; }
QPushButton#sidebarButton { color: #d4e5dd; background: transparent; border: none; text-align: left; padding: 11px 13px; }
QPushButton#sidebarButton:hover { background: #2b5149; }
QPushButton#sidebarButton:checked { color: #e5facb; background: #31584a; }
QPushButton#link { background: transparent; color: #416f51; border: none; padding: 5px 8px; }
QCheckBox { spacing: 8px; color: #43574b; padding: 3px 0px; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #aabcb0; border-radius: 5px; background: white; }
QCheckBox::indicator:checked { background: #397352; border: 1px solid #397352; image: none; }
QCheckBox::indicator:indeterminate { background: #afc5a9; }
QSlider::groove:horizontal { height: 5px; border-radius: 2px; background: #e1e8de; }
QSlider::sub-page:horizontal { background: #54825e; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; background: #285d47; border: 3px solid white; border-radius: 9px; }
QPlainTextEdit, QTextBrowser { background: transparent; border: none; selection-background-color: #d7eacb; selection-color: #20352a; padding: 8px; }
QSplitter::handle { background: transparent; width: 14px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 8px; background: transparent; margin: 3px; }
QScrollBar::handle:vertical { background: #c6d3c5; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QDialog { background: #f5f6f3; }
QWidget#kanaTable { background: white; }
QWidget#kanaTable QCheckBox { font-family: 'Segoe UI'; font-size: 16px; }
QTabWidget::pane { background: white; border: 1px solid #dfe6df; border-radius: 8px; }
QTabBar::tab { padding: 10px 18px; background: #edf2e9; margin-right: 3px; }
QTabBar::tab:selected { background: white; color: #24573e; }
QStatusBar { background: #f5f6f3; color: #637868; border-top: 1px solid #e3e8df; }
QToolTip { background: #173c3a; color: white; padding: 8px; border: none; }
"""
CHECK_PATH = (Path(__file__).resolve().parent / "assets" / "check.svg").as_posix()
STYLE += f'QCheckBox::indicator:checked {{ image: url("{CHECK_PATH}"); }}'

CHROME_STYLE = """
QWidget#shell { background: #e1e8e2; }
QFrame#titleBar { background: #f5f6f3; border-bottom: 1px solid #dfe6df; }
QLabel#windowTitle { color: #263e37; font-size: 14px; font-weight: 600; }
QToolButton#windowControl, QToolButton#windowClose { background: transparent; border: none; border-radius: 6px; padding: 0; }
QToolButton#windowControl:hover { background: #e0e9df; }
QToolButton#windowClose:hover { background: #c94350; color: white; }
QPushButton#themeSwitch { background: transparent; border: none; padding: 6px 12px; color: #516b5b; font-weight: 400; }
QPushButton#themeSwitch:hover { background: #e0e9df; }
QLabel#toast { background: #285d47; color: white; border: 1px solid #528666; border-radius: 8px; padding: 10px 18px; }
QMessageBox { background: #f5f6f3; }
"""

DARK_STYLE = """
QWidget { color: #e1e9e4; }
QMainWindow, QWidget#workspace, QDialog, QMessageBox { background: #151d1c; }
QWidget#shell { background: #35423c; }
QFrame#titleBar { background: #192421; border-bottom-color: #33423a; }
QLabel#windowTitle { color: #e1e9e4; }
QFrame#sidebar { background: #102a26; }
QFrame#sidebar QLabel { color: #b3cec1; }
QLabel#brandKana { color: #dcf7b4; }
QLabel#pageTitle { color: #e6eee7; }
QLabel#muted { color: #a2b3a9; }
QLabel#eyebrow { color: #9cbaa7; }
QLabel#sectionTitle, QLabel#panelTitle { color: #dbe8dd; }
QLabel#statValue { color: #b0dba5; }
QLabel#pill { background: #2d4233; color: #bcdeb0; }
QFrame#card { background: #1d2925; border-color: #33443a; }
QPushButton, QToolButton { background: #26372e; color: #dfebe0; border-color: #415649; }
QPushButton:hover, QToolButton:hover { background: #344b3a; border-color: #739471; }
QPushButton:pressed { background: #3b5541; }
QPushButton:disabled { background: #202d26; color: #718779; border-color: #34443a; }
QPushButton#primary { background: #a5cc91; color: #172b1c; border-color: #a5cc91; }
QPushButton#primary:hover { background: #bbdda9; }
QPushButton#primary:disabled { background: #344739; color: #809783; border-color: #344739; }
QPushButton#segment { background: #25332c; color: #b4c4b8; border-color: transparent; }
QPushButton#segment:checked { background: #a5cc91; color: #172b1c; border-color: #a5cc91; }
QPushButton#sidebarButton { background: transparent; color: #bbd1c4; border: none; }
QPushButton#sidebarButton:hover { background: #224235; }
QPushButton#sidebarButton:checked { background: #2b4c39; color: #dcf7b4; }
QPushButton#link { background: transparent; border: none; color: #b3d5a4; }
QPushButton#link:hover { background: #2b4031; }
QCheckBox { color: #cfddd1; }
QCheckBox::indicator { background: #17221c; border-color: #728976; }
QCheckBox::indicator:checked { background: #54825e; border-color: #85a781; }
QCheckBox::indicator:indeterminate { background: #405a40; border-color: #85a781; }
QSlider::groove:horizontal { background: #3a4b3c; }
QSlider::sub-page:horizontal { background: #a0c58d; }
QSlider::handle:horizontal { background: #bbdda9; border-color: #1d2925; }
QPlainTextEdit, QTextBrowser { color: #e1e9e4; selection-background-color: #456749; selection-color: #ffffff; }
QScrollBar::handle:vertical { background: #4c6350; }
QWidget#kanaTable { background: #1d2925; }
QTabWidget::pane { background: #1d2925; border-color: #33443a; }
QTabBar::tab { background: #25362b; color: #afc5b0; }
QTabBar::tab:selected { background: #1d2925; color: #c7e0ba; }
QToolTip { background: #344b3a; color: #f0f7ec; border: 1px solid #678360; }
QToolButton#windowControl, QToolButton#windowClose { background: transparent; color: #d8e6d9; border: none; }
QToolButton#windowControl:hover { background: #33483b; }
QToolButton#windowClose:hover { background: #c94350; color: white; }
QPushButton#themeSwitch { background: transparent; border: none; color: #b8cfb8; }
QPushButton#themeSwitch:hover { background: #33483b; }
QLabel#toast { background: #a5cc91; color: #172b1c; border-color: #a5cc91; }
"""

CORNER_STYLE = """
QMainWindow, QWidget#shell { background: transparent; }
QFrame#titleBar { border-top-left-radius: 10px; border-top-right-radius: 10px; }
QFrame#sidebar { border-bottom-left-radius: 10px; }
QWidget#workspace { border-bottom-right-radius: 10px; }
QWidget#shell[maximized="true"] QFrame#titleBar { border-top-left-radius: 0; border-top-right-radius: 0; }
QWidget#shell[maximized="true"] QFrame#sidebar { border-bottom-left-radius: 0; }
QWidget#shell[maximized="true"] QWidget#workspace { border-bottom-right-radius: 0; }
"""


def theme_colors(theme):
    return ({"text": "#e1e9e4", "muted": "#a2b3a9", "kana": "#c4e6af", "highlight": "#334b32", "heading": "#c4e6af", "background": "#151d1c", "base": "#1d2925"}
            if theme == "dark" else
            {"text": "#34433b", "muted": "#72807b", "kana": "#327049", "highlight": "#e7f1df", "heading": "#285d47", "background": "#f5f6f3", "base": "#ffffff"})


def theme_icon(button, symbol):
    """Keep the label size and enlarge only the original theme glyph by 5%."""
    pixmap = QPixmap(54, 54)
    pixmap.setDevicePixelRatio(3)
    pixmap.fill(Qt.GlobalColor.transparent)
    font = QFont(button.font())
    points = font.pointSizeF()
    if points <= 0: points = font.pixelSize() * 72 / button.logicalDpiY()
    font.setPointSizeF(points * 1.05)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setFont(font)
    painter.setPen(button.palette().color(QPalette.ColorRole.ButtonText))
    painter.drawText(QRectF(0, 0, 18, 18), Qt.AlignmentFlag.AlignCenter, symbol)
    painter.end()
    return QIcon(pixmap)


class WindowControl(QToolButton):
    def __init__(self, kind, callback, parent):
        super().__init__(parent)
        self.kind = kind
        self.setObjectName("windowClose" if kind == "close" else "windowControl")
        self.setFixedSize(44, 34)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip({"minimize": "Свернуть", "maximize": "Развернуть", "close": "Закрыть"}[kind])
        self.setAccessibleName(self.toolTip())
        self.clicked.connect(callback)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("white") if self.kind == "close" and self.underMouse() else self.palette().color(QPalette.ColorRole.ButtonText)
        painter.setPen(QPen(color, 1.3))
        x, y = self.width() // 2 - 5, self.height() // 2 - 5
        if self.kind == "minimize":
            painter.drawLine(x, y + 6, x + 10, y + 6)
        elif self.kind == "close":
            painter.drawLine(x, y, x + 10, y + 10)
            painter.drawLine(x + 10, y, x, y + 10)
        elif self.window().isMaximized():
            painter.drawRect(x + 3, y, 8, 8)
            painter.fillRect(x, y + 3, 8, 8, self.palette().color(QPalette.ColorRole.Window))
            painter.drawRect(x, y + 3, 8, 8)
        else:
            painter.drawRect(x, y, 10, 10)


class TitleBar(QFrame):
    def __init__(self, window):
        super().__init__(window)
        self.setObjectName("titleBar")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 5, 0)
        layout.setSpacing(3)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(23, 23))
        title = label(APP_NAME, "windowTitle")
        for w in [icon, title]:
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(w)
        layout.addStretch()
        self.theme_button = button("", window.toggle_theme, "themeSwitch")
        layout.addWidget(self.theme_button)
        layout.addSpacing(12)
        self.minimize_button = WindowControl("minimize", window.showMinimized, self)
        self.maximize_button = WindowControl("maximize", window.toggle_maximized, self)
        self.close_button = WindowControl("close", window.close, self)
        for w in [self.minimize_button, self.maximize_button, self.close_button]: layout.addWidget(w)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class WindowShell(QWidget):
    """A small exposed border delegates resizing to the Windows window manager."""
    def __init__(self, window):
        super().__init__(window)
        self.setObjectName("shell")
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = theme_colors(self.window().theme)
        painter.setBrush(QColor(colors["background"]))
        painter.setPen(QPen(QColor("#35423c" if self.window().theme == "dark" else "#dfe6df"), 1))
        radius = 0 if self.window().isMaximized() else 16
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

    def edges_at(self, position):
        edges = Qt.Edge(0)
        if self.window().isMaximized(): return edges
        if position.x() < 6: edges |= Qt.Edge.LeftEdge
        elif position.x() >= self.width() - 6: edges |= Qt.Edge.RightEdge
        if position.y() < 6: edges |= Qt.Edge.TopEdge
        elif position.y() >= self.height() - 6: edges |= Qt.Edge.BottomEdge
        return edges

    def mouseMoveEvent(self, event):
        edges = self.edges_at(event.position())
        if edges in [Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.Edge.RightEdge | Qt.Edge.BottomEdge]:
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edges in [Qt.Edge.RightEdge | Qt.Edge.TopEdge, Qt.Edge.LeftEdge | Qt.Edge.BottomEdge]:
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge): cursor = Qt.CursorShape.SizeHorCursor
        elif edges: cursor = Qt.CursorShape.SizeVerCursor
        else: cursor = Qt.CursorShape.ArrowCursor
        self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        edges = self.edges_at(event.position())
        if event.button() == Qt.MouseButton.LeftButton and edges and self.window().windowHandle():
            self.window().windowHandle().startSystemResize(edges)
            event.accept()
        else:
            super().mousePressEvent(event)


def label(text, name=None, wrap=False):
    w = QLabel(text)
    if name: w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text, callback=None, name=None):
    w = QPushButton(text)
    if name: w.setObjectName(name)
    if callback: w.clicked.connect(callback)
    return w


def card(name="card"):
    w = QFrame()
    w.setObjectName(name)
    return w


def app_icon():
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#173c3a"))
    painter.drawRoundedRect(8, 8, 240, 240, 58, 58)
    painter.setPen(QColor("#dcf7b4"))
    painter.setFont(QFont("Yu Gothic", 122, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "あ")
    painter.end()
    return QIcon(pixmap)


class KanaBrowser(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.setOpenLinks(False)
        self.setMouseTracking(True)
        self.readings = {}
        self.highlighted.connect(lambda url: self.show_reading(url.toString()))
        self.anchorClicked.connect(lambda url: self.show_reading(url.toString()))

    def show_reading(self, anchor):
        if anchor in self.readings:
            QToolTip.showText(QCursor.pos(), self.readings[anchor], self)
        else:
            QToolTip.hideText()


class KanaDialog(QDialog):
    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор слогов · Kana Studio")
        self.resize(740, 650)
        self.setMinimumSize(590, 420)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.addWidget(label("Выбери знаки для чтения", "pageTitle"))
        root.addWidget(label("Отмеченные слоги будут заменяться в твоём тексте. Оба знака показаны для сравнения.", "muted", True))
        tools = QHBoxLayout()
        tools.addWidget(button("Базовые 46", lambda: self.set_selection(BASE_READINGS)))
        tools.addWidget(button("Все знаки", lambda: self.set_selection({k.reading for k in KANA})))
        tools.addWidget(button("Снять выбор", lambda: self.set_selection(set())))
        tools.addStretch()
        self.count = label("", "pill")
        tools.addWidget(self.count)
        root.addLayout(tools)
        tabs = QTabWidget()
        self.boxes = {}
        for title, groups in [("Базовые", set(GROUP_NAMES) - {"voiced", "contracted"}), ("Звонкие", {"voiced"}), ("Сочетания", {"contracted"})]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            container = QWidget()
            container.setObjectName("kanaTable")
            layout = QVBoxLayout(container)
            layout.setContentsMargins(18, 12, 18, 12)
            for group, group_name in GROUP_NAMES.items():
                if group not in groups: continue
                layout.addWidget(label(group_name, "sectionTitle"))
                grid = QGridLayout()
                for i, k in enumerate(k for k in KANA if k.group == group):
                    checkbox = QCheckBox(f"{k.hiragana}  {k.katakana}   {k.reading}")
                    checkbox.setFont(QFont("Yu Gothic", 12))
                    checkbox.setMinimumHeight(34)
                    checkbox.setChecked(k.reading in selected)
                    checkbox.setToolTip("Также: " + ", ".join(k.aliases) if k.aliases else k.reading)
                    checkbox.toggled.connect(self.update_count)
                    self.boxes[k.reading] = checkbox
                    grid.addWidget(checkbox, i // 5, i % 5)
                layout.addLayout(grid)
                layout.addSpacing(9)
            layout.addStretch()
            scroll.setWidget(container)
            tabs.addTab(scroll, title)
        root.addWidget(tabs, 1)
        root.addWidget(label("Чтение приблизительное. ち / チ — «чи»; ちゃ / チャ — «ча». Варианты си/ши и ху/фу поддерживаются.", "muted", True))
        actions = QDialogButtonBox()
        actions.addButton("Отмена", QDialogButtonBox.ButtonRole.RejectRole)
        apply = actions.addButton("Применить", QDialogButtonBox.ButtonRole.AcceptRole)
        apply.setObjectName("primary")
        actions.accepted.connect(self.accept)
        actions.rejected.connect(self.reject)
        root.addWidget(actions)
        self.update_count()

    def selection(self):
        return frozenset(key for key, w in self.boxes.items() if w.isChecked())

    def set_selection(self, selected):
        for key, w in self.boxes.items(): w.setChecked(key in selected)

    def update_count(self):
        self.count.setText(f"Выбрано: {len(self.selection())}")


class Window(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("KanaStudio", "KanaStudio")
        self.theme = self.settings.value("theme", "dark")
        if self.theme not in {"dark", "light"}: self.theme = "dark"
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Kana Studio — Кананизация")
        self.setWindowIcon(app_icon())
        self.resize(1320, 890)
        self.setMinimumSize(1080, 740)
        saved = self.settings.value("selected", list(BASE_READINGS))
        if isinstance(saved, str): saved = [saved]
        saved = [READING_MIGRATIONS.get(k, k) for k in saved]
        self.selected = frozenset(k for k in saved if k in {x.reading for x in KANA})
        self.result = Result("", (), 0, 0, 0)
        self.busy = False
        self.text_size = int(self.settings.value("text_size", 18))
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh)
        self.shell = WindowShell(self)
        self.shell.setProperty("maximized", False)
        self.shell_layout = QVBoxLayout(self.shell)
        self.shell_layout.setContentsMargins(6, 6, 6, 6)
        self.shell_layout.setSpacing(0)
        self.title_bar = TitleBar(self)
        self.shell_layout.addWidget(self.title_bar)
        content = QWidget()
        content.setCursor(Qt.CursorShape.ArrowCursor)
        outer = QHBoxLayout(content)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.build_sidebar())
        outer.addWidget(self.build_workspace(), 1)
        self.shell_layout.addWidget(content, 1)
        self.setCentralWidget(self.shell)
        self.toast = label("", "toast")
        self.toast.setParent(self)
        self.toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.toast.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast.hide)
        self.create_shortcuts()
        self.load_settings()
        self.sync_groups()
        self.apply_theme()
        self.refresh()

    def build_sidebar(self):
        side = card("sidebar")
        side.setFixedWidth(206)
        root = QVBoxLayout(side)
        root.setContentsMargins(21, 27, 21, 22)
        root.setSpacing(8)
        root.addWidget(label("あ", "brandKana"))
        root.addSpacing(28)
        active = button("  Чтение с каной", name="sidebarButton")
        active.setCheckable(True)
        active.setChecked(True)
        root.addWidget(active)
        root.addWidget(button("  Таблица знаков", self.choose_kana, "sidebarButton"))
        root.addWidget(button("  Как это работает", self.show_help, "sidebarButton"))
        root.addStretch()
        return side

    def build_workspace(self):
        work = QWidget()
        work.setObjectName("workspace")
        root = QVBoxLayout(work)
        root.setContentsMargins(28, 25, 28, 19)
        root.setSpacing(16)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(5)
        heading.addWidget(label("Кананизация", "pageTitle"))
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(button("Как начать  ?", self.show_help))
        root.addLayout(header)

        settings_card = card()
        layout = QVBoxLayout(settings_card)
        layout.setContentsMargins(19, 16, 19, 15)
        layout.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(label("НАСТРОЙКИ", "eyebrow"))
        top.addStretch()
        self.selected_label = label("", "pill")
        top.addWidget(self.selected_label)
        layout.addLayout(top)
        controls = QHBoxLayout()
        controls.setSpacing(6)
        self.alphabets = QButtonGroup(self)
        self.alphabet_buttons = {}
        for i, (key, title) in enumerate([("hiragana", "あ  Хирагана"), ("katakana", "ア  Катакана"), ("mixed", "あ / ア  Обе азбуки")]):
            b = button(title, name="segment")
            b.setCheckable(True)
            b.setProperty("alphabet", key)
            self.alphabets.addButton(b, i)
            self.alphabet_buttons[key] = b
            controls.addWidget(b)
        self.alphabet_buttons["hiragana"].setChecked(True)
        self.alphabets.buttonClicked.connect(self.schedule_refresh)
        controls.addStretch()
        controls.addWidget(label("Количество замен", "muted"))
        self.density = QSlider(Qt.Orientation.Horizontal)
        self.density.setRange(0, 100)
        self.density.setValue(100)
        self.density.setFixedWidth(112)
        self.density.setAccessibleName("Количество замен в процентах")
        self.density.valueChanged.connect(self.schedule_refresh)
        controls.addWidget(self.density)
        self.density_label = label("100 %", "sectionTitle")
        self.density_label.setFixedWidth(52)
        controls.addWidget(self.density_label)
        layout.addLayout(controls)
        groups_line = QHBoxLayout()
        groups_line.addWidget(label("Слоги для замены", "sectionTitle"))
        groups_line.addStretch()
        groups_line.addWidget(button("Базовые", lambda: self.set_selection(BASE_READINGS), "link"))
        groups_line.addWidget(button("Все", lambda: self.set_selection({k.reading for k in KANA}), "link"))
        groups_line.addWidget(button("Выбрать отдельно →", self.choose_kana, "link"))
        layout.addLayout(groups_line)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(2)
        self.groups = {}
        for i, (key, title) in enumerate(GROUP_NAMES.items()):
            cb = QCheckBox(title)
            cb.setTristate(True)
            cb.setToolTip("Включить или выключить всю группу. Отдельные знаки: «Выбрать отдельно».")
            cb.clicked.connect(lambda checked, group=key: self.toggle_group(group))
            self.groups[key] = cb
            grid.addWidget(cb, i // 3, i % 3)
        layout.addLayout(grid)
        advanced = QHBoxLayout()
        self.snowball = QCheckBox("Снежный ком")
        self.snowball.setToolTip("В начале текста замен мало; к концу они появляются всё чаще. Лучше работает на длинном тексте.")
        self.replace_e = QCheckBox("Заменять «е» как «э»")
        self.replace_e.setToolTip("Дополнительно заменяет е, ке, се и другие варианты с е. Это приблизительное учебное чтение.")
        self.wide_spaces = QCheckBox("Широкие пробелы")
        self.wide_spaces.setToolTip("Заменяет обычные пробелы на японские полноширинные пробелы.")
        for cb in [self.snowball, self.replace_e, self.wide_spaces]:
            cb.toggled.connect(self.schedule_refresh)
            advanced.addWidget(cb)
        advanced.addStretch()
        layout.addLayout(advanced)
        root.addWidget(settings_card)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        source_panel = card()
        source_layout = QVBoxLayout(source_panel)
        source_layout.setContentsMargins(17, 15, 17, 12)
        source_header = QHBoxLayout()
        source_header.addWidget(label("ИСХОДНЫЙ ТЕКСТ", "eyebrow"))
        source_header.addStretch()
        source_header.addWidget(button("Открыть TXT", self.open_file))
        source_layout.addLayout(source_header)
        self.source = QPlainTextEdit()
        self.source.setPlaceholderText("Вставь сюда любой текст на русском…\n\nМожно взять рассказ, заметку или несколько предложений.\nРезультат появится справа автоматически.")
        self.source.setAccessibleName("Исходный русский текст")
        self.source.textChanged.connect(self.schedule_refresh)
        source_layout.addWidget(self.source, 1)
        source_footer = QHBoxLayout()
        self.source_count = label("0 символов", "muted")
        source_footer.addWidget(self.source_count)
        source_footer.addStretch()
        source_footer.addWidget(button("Пример", self.load_example, "link"))
        source_footer.addWidget(button("Очистить", self.clear_text, "link"))
        source_layout.addLayout(source_footer)
        result_panel = card()
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(17, 15, 17, 12)
        result_header = QHBoxLayout()
        result_header.addWidget(label("РЕЗУЛЬТАТ", "eyebrow"))
        result_header.addStretch()
        self.highlight = QCheckBox("Выделять знаки")
        self.highlight.setChecked(True)
        self.highlight.toggled.connect(self.render_result)
        result_header.addWidget(self.highlight)
        result_layout.addLayout(result_header)
        self.output = KanaBrowser()
        self.output.setToolTip("Наведи на японский знак, чтобы увидеть чтение")
        self.output.setAccessibleName("Преобразованный текст с каной")
        result_layout.addWidget(self.output, 1)
        output_footer = QHBoxLayout()
        self.output_note = label("", "muted")
        self.output_note.hide()
        output_footer.addWidget(self.output_note)
        output_footer.addStretch()
        output_footer.addWidget(button("−", lambda: self.adjust_font(-1), "link"))
        output_footer.addWidget(button("+", lambda: self.adjust_font(1), "link"))
        result_layout.addLayout(output_footer)
        self.splitter.addWidget(source_panel)
        self.splitter.addWidget(result_panel)
        self.splitter.setSizes([480, 500])
        root.addWidget(self.splitter, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(23)
        self.stat_replacements = label("0", "statValue")
        self.stat_unique = label("0", "statValue")
        for value, caption in [(self.stat_replacements, "замен в тексте"), (self.stat_unique, "разных знаков")]:
            stat = QHBoxLayout()
            stat.setSpacing(8)
            stat.addWidget(value)
            stat.addWidget(label(caption, "muted"))
            bottom.addLayout(stat)
        bottom.addStretch()
        self.copy_button = button("Копировать", self.copy_result)
        self.save_button = button("Сохранить TXT", self.save_file, "primary")
        bottom.addWidget(self.copy_button)
        bottom.addWidget(self.save_button)
        root.addLayout(bottom)
        return work

    def apply_theme(self):
        colors = theme_colors(self.theme)
        palette = QPalette()
        for role, color in [(QPalette.ColorRole.Window, colors["background"]),
                            (QPalette.ColorRole.Base, colors["base"]),
                            (QPalette.ColorRole.AlternateBase, colors["background"]),
                            (QPalette.ColorRole.Button, colors["base"]),
                            (QPalette.ColorRole.WindowText, colors["text"]),
                            (QPalette.ColorRole.Text, colors["text"]),
                            (QPalette.ColorRole.ButtonText, colors["text"]),
                            (QPalette.ColorRole.PlaceholderText, colors["muted"]),
                            (QPalette.ColorRole.ToolTipBase, colors["base"]),
                            (QPalette.ColorRole.ToolTipText, colors["text"]),
                            (QPalette.ColorRole.Highlight, colors["highlight"]),
                            (QPalette.ColorRole.HighlightedText, colors["text"]),
                            (QPalette.ColorRole.Link, colors["kana"])]:
            palette.setColor(role, QColor(color))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors["muted"]))
        app = QApplication.instance()
        app.setPalette(palette)
        app.setStyleSheet(STYLE + CHROME_STYLE + (DARK_STYLE if self.theme == "dark" else "") + CORNER_STYLE)
        self.title_bar.theme_button.setText("Светлая" if self.theme == "dark" else "Тёмная")
        self.title_bar.theme_button.setIconSize(QSize(18, 18))
        self.title_bar.theme_button.setIcon(theme_icon(self.title_bar.theme_button, "☀" if self.theme == "dark" else "☾"))
        self.title_bar.theme_button.setToolTip("Переключить на светлую тему" if self.theme == "dark" else "Переключить на тёмную тему")
        self.title_bar.theme_button.setAccessibleName(self.title_bar.theme_button.toolTip())
        self.shell.update()
        self.render_result()

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.setValue("theme", self.theme)
        self.apply_theme()

    def toggle_maximized(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "title_bar"):
            maximized = self.isMaximized()
            self.shell.setProperty("maximized", maximized)
            for widget in [self.shell, *self.shell.findChildren(QWidget)]:
                if widget.objectName() in {"shell", "titleBar", "sidebar", "workspace"}:
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                    widget.update()
            self.shell_layout.setContentsMargins(*([0] * 4 if maximized else [6] * 4))
            self.title_bar.maximize_button.setToolTip("Восстановить размер" if maximized else "Развернуть")
            self.title_bar.maximize_button.setAccessibleName(self.title_bar.maximize_button.toolTip())
            self.title_bar.maximize_button.update()

    def notify(self, text):
        self.toast.setText(text)
        self.toast.adjustSize()
        self.position_toast()
        self.toast.show()
        self.toast.raise_()
        self.toast_timer.start(3000)

    def position_toast(self):
        self.toast.move(max(10, self.width() - self.toast.width() - 35), max(10, self.height() - self.toast.height() - 75))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast"): self.position_toast()

    def create_shortcuts(self):
        for shortcut, handler in [(QKeySequence.StandardKey.Open, self.open_file),
                                  (QKeySequence.StandardKey.Save, self.save_file),
                                  ("Ctrl+Return", self.refresh), ("F1", self.show_help)]:
            action = QAction(self)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)
            self.addAction(action)

    def load_settings(self):
        self.busy = True
        key = self.settings.value("alphabet", "hiragana")
        self.alphabet_buttons.get(key, self.alphabet_buttons["hiragana"]).setChecked(True)
        self.density.setValue(int(self.settings.value("density", 100)))
        for key, widget in [("snowball", self.snowball), ("replace_e", self.replace_e), ("wide_spaces", self.wide_spaces), ("highlight", self.highlight)]:
            widget.setChecked(self.settings.value(key, key == "highlight", type=bool))
        text = self.settings.value("draft", "")
        self.source.setPlainText(text)
        geometry = self.settings.value("geometry")
        if geometry: self.restoreGeometry(geometry)
        self.busy = False
        self.adjust_font(0)

    def options(self):
        checked = self.alphabets.checkedButton()
        return Options(checked.property("alphabet"), self.selected, self.density.value(),
                       self.snowball.isChecked(), self.replace_e.isChecked(), self.wide_spaces.isChecked())

    def schedule_refresh(self, *_):
        if self.busy: return
        self.density_label.setText(f"{self.density.value()} %")
        self.timer.start()

    def refresh(self):
        self.timer.stop()
        text = self.source.toPlainText()
        self.source_count.setText(f"{len(text):,} символов".replace(",", " "))
        self.result = convert(text, self.options())
        self.stat_replacements.setText(str(self.result.replacements))
        self.stat_unique.setText(str(self.result.unique))
        self.copy_button.setEnabled(bool(self.result.text))
        self.save_button.setEnabled(bool(self.result.text))
        self.density_label.setText(f"{self.density.value()} %")
        self.render_result()

    def render_result(self, *_):
        if not hasattr(self, "output"): return
        colors = theme_colors(self.theme)
        scroll = self.output.verticalScrollBar().value()
        if len(self.result.text) > 120_000:
            self.output.readings = {}
            self.output.setPlainText(self.result.text)
            self.output.setStyleSheet(f"font-family: 'Segoe UI'; font-size: {self.text_size}px;")
            self.output.verticalScrollBar().setValue(scroll)
            self.output_note.setText("Большой текст: подсветка и подсказки отключены")
            self.output_note.show()
            return
        parts, readings = [], {}
        for index, segment in enumerate(self.result.segments):
            content = html.escape(segment.text).replace("\n", "<br>")
            if segment.reading:
                key = f"kana:{index}"
                readings[key] = f"{segment.text}  →  {segment.reading}\nВ исходном тексте: {segment.original}"
                color = colors["kana"] if self.highlight.isChecked() else colors["text"]
                background = f'background-color: {colors["highlight"]};' if self.highlight.isChecked() else ""
                parts.append(f'<a href="{key}" style="font-family:Yu Gothic UI;color:{color};text-decoration:none;{background}">{content}</a>')
            else:
                parts.append(content)
        self.output.readings = readings
        if not self.result.text:
            body = f'<span style="color:{colors["muted"]}">Добавь текст слева или нажми «Пример».</span>'
        else:
            body = "".join(parts)
        self.output.setHtml(f'<html><body style="font-family:Segoe UI; font-size:{self.text_size}px; color:{colors["text"]}; white-space:pre-wrap;">{body}</body></html>')
        self.output.verticalScrollBar().setValue(scroll)
        if self.source.toPlainText() and not self.selected:
            self.output_note.setText("Выбери хотя бы один слог в настройках")
        elif self.source.toPlainText() and not self.result.possible:
            self.output_note.setText("В тексте нет выбранных слогов")
        else:
            self.output_note.clear()
        self.output_note.setVisible(bool(self.output_note.text()))

    def adjust_font(self, delta):
        self.text_size = min(28, max(14, self.text_size + delta))
        self.source.setStyleSheet(f"font-family: 'Segoe UI'; font-size: {self.text_size}px;")
        self.render_result()

    def sync_groups(self):
        for group, cb in self.groups.items():
            members = {k.reading for k in KANA if k.group == group}
            chosen = members & self.selected
            state = Qt.CheckState.Checked if chosen == members else Qt.CheckState.PartiallyChecked if chosen else Qt.CheckState.Unchecked
            cb.blockSignals(True)
            cb.setCheckState(state)
            cb.blockSignals(False)
        self.selected_label.setText(f"{len(self.selected)} слогов выбрано")

    def toggle_group(self, group):
        members = {k.reading for k in KANA if k.group == group}
        chosen = self.selected & members
        # A partial selection becomes complete on the next click.
        self.set_selection(self.selected - members if chosen == members else self.selected | members)

    def set_selection(self, selected):
        self.selected = frozenset(selected)
        self.sync_groups()
        self.schedule_refresh()

    def choose_kana(self):
        dialog = KanaDialog(self.selected, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_selection(dialog.selection())

    def confirm_replace(self):
        if not self.source.toPlainText().strip(): return True
        return QMessageBox.question(self, "Заменить текст?", "Текущий текст будет заменён. Продолжить?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def load_example(self):
        if self.confirm_replace(): self.source.setPlainText(SAMPLE)

    def clear_text(self):
        cursor = self.source.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()
        self.source.setTextCursor(cursor)
        self.source.setFocus()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть русский текст", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path: return
        try:
            if Path(path).stat().st_size > 2_000_000:
                QMessageBox.information(self, "Большой файл", "Выбери текст до 2 МБ, чтобы предпросмотр работал плавно.")
                return
            raw = Path(path).read_bytes()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                    text = raw.decode("utf-16")
                else:
                    text = raw.decode("cp1251")
            if "\x00" in text:
                raise ValueError("Это не текстовый файл. Сохрани документ как TXT.")
            if not self.confirm_replace(): return
            self.source.setPlainText(text.replace("\r\n", "\n").replace("\r", "\n"))
            self.notify(f"Открыт файл: {Path(path).name}")
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, "Не удалось открыть файл", str(error))

    def save_file(self):
        self.refresh()
        if not self.result.text: return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить текст с каной", "Текст с каной.txt", "Текст UTF-8 (*.txt)")
        if not path: return
        if not Path(path).suffix: path += ".txt"
        try:
            Path(path).write_text(self.result.text, encoding="utf-8")
            self.notify(f"Сохранено: {Path(path).name}")
        except OSError as error:
            QMessageBox.warning(self, "Не удалось сохранить файл", str(error))

    def copy_result(self):
        self.refresh()
        if self.result.text:
            QApplication.clipboard().setText(self.result.text)
            self.notify("Текст скопирован")

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Как пользоваться Kana Studio")
        dialog.resize(690, 610)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 23, 25, 23)
        layout.addWidget(label("Знакомый текст, новые знаки", "pageTitle"))
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        help_html = '''<style>body{font-family:Segoe UI;color:#34433b;font-size:14px}h3{color:#285d47}a{color:#285d47}</style>
        <h3>1. Добавь текст</h3><p>Вставь русский текст слева, открой TXT или нажми «Пример». Результат обновляется автоматически.</p>
        <h3>2. Выбери, что учить</h3><p>Укажи хирагану, катакану или обе азбуки. Включай группы слогов или выбирай отдельные знаки в таблице. Длинные сочетания заменяются раньше коротких.</p>
        <h3>3. Читай в своём темпе</h3><p>Ползунок уменьшает количество замен. «Снежный ком» делает замены редкими в начале и частыми к концу текста. В смешанном режиме азбуки чередуются.</p>
        <h3>4. Пользуйся подсказками</h3><p>Наведи курсор на знак: увидишь его чтение и исходный слог. Текст справа можно выделять и копировать. Кнопки − и + меняют размер текста.</p>
        <p><b>Дополнительно:</b> «е» можно приблизительно читать как «э»; широкие пробелы помогают визуально выровнять кану. Результат сохраняется в TXT UTF-8.</p>
        <p><b>Клавиши:</b> Ctrl+O — открыть; Ctrl+S — сохранить; Ctrl+Enter — обновить; F1 — справка. Ctrl+Z в левом поле отменяет правку или очистку.</p>
        <p>Настройки и черновик автоматически сохраняются локально. Если текст больше 200 000 символов, черновик при закрытии не сохраняется.</p>
        <hr><p>Это учебная замена слогов, а не перевод и не точная запись японского произношения. Русские подсказки приблизительны; を обычно произносится «о».</p>
        <p>Kana Studio · Copyright (C) 2026 GodRayine. Код распространяется по GNU GPL v3 или более поздней версии, без гарантий. <a href="https://github.com/GodRayine/KanaStudio">Исходники и лицензии</a>.</p>
        <p>Независимая реализация по описанию метода <a href="https://www.japlang.ru/soft/index.html">«Кананизации» на japlang.ru</a>. Идея метода — Илья Виноградов; автор исходной программы — Алексей Сергеев. Исходный код и материалы оригинала в приложение не включены.</p>'''
        colors = theme_colors(self.theme)
        browser.setHtml(help_html.replace("#34433b", colors["text"]).replace("#285d47", colors["heading"]))
        layout.addWidget(browser, 1)
        layout.addWidget(button("Всё понятно", dialog.accept, "primary"), alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def closeEvent(self, event):
        options = self.options()
        self.settings.setValue("selected", sorted(self.selected))
        self.settings.setValue("alphabet", options.alphabet)
        self.settings.setValue("density", options.density)
        for name in ["snowball", "replace_e", "wide_spaces"]:
            self.settings.setValue(name, getattr(options, name))
        self.settings.setValue("highlight", self.highlight.isChecked())
        self.settings.setValue("text_size", self.text_size)
        self.settings.setValue("theme", self.theme)
        text = self.source.toPlainText()
        self.settings.setValue("draft", text if len(text) <= 200_000 else "")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.sync()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("KanaStudio")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(app_icon())
    if "--smoke-test" in sys.argv:
        # Exercise the packaged application without touching the user's settings.
        import json
        index = sys.argv.index("--smoke-test")
        directory = Path(sys.argv[index + 1]).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        settings = QSettings(str(directory / "smoke.ini"), QSettings.Format.IniFormat)
        window = Window(settings)
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.resize(1320, 890)
        window.source.setPlainText(SAMPLE)
        window.refresh()
        window.show()
        app.processEvents()
        for theme in ["dark", "light"]:
            window.theme = theme
            window.apply_theme()
            app.processEvents()
            window.grab().save(str(directory / ("preview.png" if theme == "dark" else "preview-light.png")))
            assert window.output.toPlainText() == window.result.text
        window.theme = "dark"
        window.apply_theme()
        window.title_bar.maximize_button.click()
        app.processEvents()
        maximized = window.isMaximized()
        window.title_bar.maximize_button.click()
        app.processEvents()
        restored = not window.isMaximized()
        (directory / "output.txt").write_text(window.result.text, encoding="utf-8")
        success = window.output.toPlainText() == window.result.text and window.result.replacements > 0
        report = {"ok": success, "replacements": window.result.replacements, "unique": window.result.unique,
                  "frozen": bool(getattr(sys, "frozen", False)), "check_icon": Path(CHECK_PATH).is_file(),
                  "version": VERSION, "themes": ["dark", "light"], "window_controls": maximized and restored}
        (directory / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        window.close()
        return 0 if success and report["check_icon"] and report["window_controls"] else 1
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
