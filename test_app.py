"""Desktop integration checks with real Qt widgets and isolated settings."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt, QPoint
from PySide6.QtGui import QPalette, QWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from app import Window, STYLE, SAMPLE, KanaDialog, theme_colors
from kana import Options, convert


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings_path = str(Path(self.temp.name) / "settings.ini")
        self.w = Window(QSettings(self.settings_path, QSettings.Format.IniFormat))
        self.w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_live_preview_and_alphabet_buttons(self):
        self.w.source.setPlainText("Кана и кот")
        QTest.qWait(330)
        self.assertEqual(self.w.result.text, convert("Кана и кот").text)
        QTest.mouseClick(self.w.alphabet_buttons["katakana"], Qt.MouseButton.LeftButton)
        QTest.qWait(330)
        self.assertEqual(self.w.result.text, convert("Кана и кот", Options(alphabet="katakana")).text)
        self.assertEqual(self.w.output.toPlainText(), self.w.result.text)

    def test_copy_and_save_flush_pending_preview(self):
        self.w.source.setPlainText("Мама читает")
        self.w.copy_result()
        self.assertEqual(QApplication.clipboard().text(), convert("Мама читает").text)
        self.w.source.setPlainText("Новый текст")
        target = Path(self.temp.name) / "result.txt"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")):
            self.w.save_file()
        self.assertEqual(target.read_text(encoding="utf-8"), convert("Новый текст").text)

    def test_input_encodings_and_line_endings(self):
        for encoding in ["utf-8-sig", "cp1251", "utf-16"]:
            target = Path(self.temp.name) / "input.txt"
            target.write_bytes("Мама\r\nчитает".encode(encoding))
            with patch.object(QFileDialog, "getOpenFileName", return_value=(str(target), "")), patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                self.w.open_file()
            self.w.refresh()
            self.assertEqual(self.w.source.toPlainText(), "Мама\nчитает")

    def test_literal_markup_spaces_and_hint_data(self):
        self.w.source.setPlainText("Кот  <b>hello & world</b>\n\t🙂")
        self.w.refresh()
        self.assertEqual(self.w.output.toPlainText(), self.w.result.text)
        self.assertTrue(any("В исходном тексте: Ко" in r for r in self.w.output.readings.values()))
        self.w.highlight.setChecked(False)
        self.assertEqual(self.w.output.toPlainText(), self.w.result.text)

    def test_clear_is_undoable(self):
        self.w.source.setPlainText(SAMPLE)
        self.w.clear_text()
        self.assertEqual(self.w.source.toPlainText(), "")
        self.w.source.undo()
        self.assertEqual(self.w.source.toPlainText(), SAMPLE)

    def test_selection_and_persistence(self):
        dialog = KanaDialog(self.w.selected, self.w)
        dialog.set_selection({"ка", "кя"})
        self.w.set_selection(dialog.selection())
        self.w.alphabet_buttons["mixed"].setChecked(True)
        self.w.snowball.setChecked(True)
        self.w.density.setValue(42)
        self.w.source.setPlainText("ка кя ка кя")
        self.w.theme = "light"
        self.w.apply_theme()
        self.w.close()
        restored = Window(QSettings(self.settings_path, QSettings.Format.IniFormat))
        try:
            self.assertEqual(restored.selected, frozenset({"ка", "кя"}))
            self.assertEqual(restored.options().alphabet, "mixed")
            self.assertTrue(restored.options().snowball)
            self.assertEqual(restored.options().density, 42)
            self.assertEqual(restored.source.toPlainText(), "ка кя ка кя")
            self.assertEqual(restored.theme, "light")
        finally:
            restored.close()
            restored.deleteLater()
            dialog.deleteLater()

    def test_old_chi_selection_is_migrated_without_changing_draft(self):
        self.w.close()
        settings = QSettings(self.settings_path, QSettings.Format.IniFormat)
        settings.setValue("selected", ["ти", "тё", "ка"])
        settings.setValue("draft", "тихо чисто чоппер")
        settings.sync()
        restored = Window(settings)
        try:
            self.assertEqual(restored.selected, frozenset({"чи", "чо", "ка"}))
            self.assertEqual(restored.source.toPlainText(), "тихо чисто чоппер")
            self.assertEqual(restored.result.text, "тихо ちсто ちょппер")
            restored.close()
            self.assertEqual(set(settings.value("selected")), {"чи", "чо", "ка"})
        finally:
            restored.close()
            restored.deleteLater()

    def test_theme_switch_preserves_text_and_readability(self):
        self.w.source.setPlainText(SAMPLE)
        self.w.refresh()
        result = self.w.result.text
        for theme in ["light", "dark"]:
            QTest.mouseClick(self.w.title_bar.theme_button, Qt.MouseButton.LeftButton)
            self.assertEqual(self.w.theme, theme)
            self.assertEqual(self.w.source.toPlainText(), SAMPLE)
            self.assertEqual(self.w.output.toPlainText(), result)
            colors = theme_colors(theme)
            self.assertEqual(QApplication.palette().color(QPalette.ColorRole.Text).name(), colors["text"])
            self.assertEqual(self.w.settings.value("theme"), theme)

    def test_window_controls_and_double_click(self):
        self.assertTrue(self.w.windowFlags() & Qt.WindowType.FramelessWindowHint)
        QTest.mouseClick(self.w.title_bar.maximize_button, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.w.isMaximized())
        self.assertEqual(self.w.title_bar.maximize_button.toolTip(), "Восстановить размер")
        QTest.mouseDClick(self.w.title_bar, Qt.MouseButton.LeftButton, pos=QPoint(400, 20))
        self.app.processEvents()
        self.assertFalse(self.w.isMaximized())
        QTest.mouseClick(self.w.title_bar.minimize_button, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.w.isMinimized())
        self.w.showNormal()
        QTest.mouseClick(self.w.title_bar.close_button, Qt.MouseButton.LeftButton)
        self.assertFalse(self.w.isVisible())

    def test_drag_and_corner_resize_use_system_window_operations(self):
        with patch.object(QWindow, "startSystemMove", return_value=True) as move:
            QTest.mousePress(self.w.title_bar, Qt.MouseButton.LeftButton, pos=QPoint(400, 20))
            QTest.mouseRelease(self.w.title_bar, Qt.MouseButton.LeftButton, pos=QPoint(400, 20))
            move.assert_called_once()
        with patch.object(QWindow, "startSystemResize", return_value=True) as resize:
            QTest.mousePress(self.w.shell, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
            QTest.mouseRelease(self.w.shell, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
            resize.assert_called_once_with(Qt.Edge.TopEdge | Qt.Edge.LeftEdge)


if __name__ == "__main__":
    unittest.main()
