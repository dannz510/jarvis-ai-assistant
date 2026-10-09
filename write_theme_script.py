from pathlib import Path

theme_path = Path(r"D:\ASTRA\jarvis-ai-assistant\ui\core\theme.py")

colors = {
    "bg_deep": "#05070f",
    "bg_base": "#07111d",
    "bg_elevated": "#0a1624",
    "bg_glass": "rgba(10, 22, 36, 0.72)",
    "bg_glass_hover": "rgba(14, 32, 52, 0.88)",
    "border_subtle": "rgba(70, 130, 160, 0.18)",
    "border_glass": "rgba(95, 235, 255, 0.22)",
    "border_glow": "rgba(95, 235, 255, 0.45)",
    "border_strong": "rgba(95, 235, 255, 0.65)",
    "text_primary": "#e8f7ff",
    "text_secondary": "#9dc3da",
    "text_tertiary": "#6f93b3",
    "text_muted": "#4a6b85",
    "cyan": "#4df4ff",
    "cyan_soft": "#7afffb",
    "cyan_deep": "#00b4cc",
    "teal": "#3df5d9",
    "violet": "#9d7bff",
    "magenta": "#ff4dff",
    "amber": "#f5b63b",
    "orange": "#ff9a4d",
    "red": "#ff6b66",
    "green": "#6ef2ab",
}

mode_colors = {
    "idle": "#29d3f1",
    "listening": "#4cf4de",
    "user_paused": "#6f93b3",
    "processing": "#4bc0ff",
    "thinking": "#5cadff",
    "tool_selection": "#f1c26e",
    "executing": "#ffaa5e",
    "observing": "#68dcff",
    "responding": "#5de8de",
    "speaking": "#69efff",
    "success": "#6df2ab",
    "error": "#ff7571",
    "interrupted": "#ffd183",
    "waiting_for_clarification": "#f5c36e",
    "booting": "#63cdff",
}

color_str = 'COLORS = {\n'
for k, v in colors.items():
    color_str += f'    "{k}": "{v}",\n'
color_str += '}\n'

mode_str = '\nMODE_COLORS = {\n'
for k, v in mode_colors.items():
    mode_str += f'    "{k}": "{v}",\n'
mode_str += '}\n'

qss = r'''STYLESHEET = """
QMainWindow, QWidget#Root {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #05070f, stop:0.55 #07111d, stop:1 #080b14);
    color: #e8f7ff;
}

QFrame#Sidebar,
QFrame#Card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(12, 26, 40, 0.85), stop:1 rgba(8, 18, 28, 0.72));
    border: 1px solid rgba(95, 235, 255, 0.16);
    border-radius: 12px;
}

QFrame#Card:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(14, 32, 52, 0.92), stop:1 rgba(10, 22, 36, 0.82));
    border: 1px solid rgba(95, 235, 255, 0.32);
}

QFrame#Card[accent="cyan"] { border-color: rgba(95, 235, 255, 0.55); }
QFrame#Card[accent="teal"] { border-color: rgba(61, 245, 217, 0.55); }
QFrame#Card[accent="amber"] { border-color: rgba(245, 182, 59, 0.55); }
QFrame#Card[accent="violet"] { border-color: rgba(157, 123, 255, 0.55); }
QFrame#Card[accent="orange"] { border-color: rgba(255, 154, 77, 0.55); }
QFrame#Card[accent="magenta"] { border-color: rgba(255, 77, 255, 0.55); }
QFrame#Card[accent="green"] { border-color: rgba(110, 242, 171, 0.55); }
QFrame#Card[accent="red"] { border-color: rgba(255, 107, 102, 0.55); }

QFrame#Sidebar {
    background: #091522;
    border: 1px solid rgba(95, 235, 255, 0.10);
}

QLabel { color: #e8f7ff; }
QLabel#BrandMark { color: #4df4ff; font-size: 26px; font-family: "Exo 2", "Outfit", "Segoe UI"; font-weight: 700; }
QLabel#BrandName { color: #ecf8ff; font-size: 20px; font-weight: 700; font-family: "Exo 2", "Outfit", "Segoe UI"; }
QLabel#Eyebrow { color: #f5b63b; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; font-family: "Oxanium", "Outfit", "Segoe UI"; text-transform: uppercase; }
QLabel#PageTitle { color: #f0f8ff; font-size: 28px; font-weight: 600; font-family: "Exo 2", "Outfit", "Segoe UI"; }
QLabel#CardTitle { color: #e7f4fb; font-size: 15px; font-weight: 600; font-family: "Outfit", "Segoe UI"; }
QLabel#MetricValue { color: #f0f8ff; font-size: 18px; font-weight: 600; font-family: "Exo 2", "Outfit", "Segoe UI"; }
QLabel#StatusValue, QLabel#CoreState { color: #3df5d9; font-size: 10px; font-weight: 700; letter-spacing: 0.6px; font-family: "Oxanium", "Outfit", "Segoe UI"; text-transform: uppercase; }
QLabel#SystemBadge { color: #3df5d9; background: rgba(11, 40, 44, 0.9); border: 1px solid rgba(28, 85, 85, 0.9); border-radius: 12px; padding: 9px 13px; font-size: 10px; font-weight: 700; font-family: "Oxanium", "Outfit", "Segoe UI"; }
QLabel#HealthGlyph { color: #4df4ff; font-size: 20px; min-width: 28px; }
QLabel#PrivacyNote { color: #6f93b3; font-size: 10px; padding: 12px 2px; }
QLabel#Muted { color: #9dc3da; font-size: 11px; }
QLabel#BodyText { color: #e8f7ff; font-size: 12px; font-family: "Inter", "Segoe UI"; }

QPushButton#NavActive {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(20, 60, 80, 0.95), stop:1 rgba(10, 30, 48, 0.65));
    border: 1px solid rgba(95, 235, 255, 0.45);
    border-radius: 10px;
    color: #7afffb;
    text-align: left;
    padding: 11px 10px;
    font-size: 12px;
    font-weight: 600;
    font-family: "Outfit", "Segoe UI";
}
QPushButton#NavItem {
    color: #9dc3da;
    text-align: left;
    padding: 11px 10px;
    font-size: 12px;
    font-family: "Outfit", "Segoe UI";
    border-color: transparent;
    background: transparent;
    border-radius: 10px;
}
QPushButton#NavItem:hover {
    color: #e8f7ff;
    background: rgba(13, 32, 48, 0.6);
    border: 1px solid rgba(95, 235, 255, 0.22);
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(16, 38, 57, 0.96), stop:1 rgba(10, 26, 41, 0.92));
    color: #c9deea;
    border: 1px solid rgba(95, 235, 255, 0.18);
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 12px;
    font-family: "Outfit", "Segoe UI";
    font-weight: 500;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(21, 54, 75, 0.98), stop:1 rgba(13, 32, 48, 0.96));
    border-color: rgba(95, 235, 255, 0.4);
}
QPushButton:pressed {
    background: rgba(8, 20, 33, 0.98);
    border-color: rgba(95, 235, 255, 0.6);
}
QPushButton:disabled {
    color: #4a6b85;
    background: rgba(8, 16, 26, 0.8);
    border-color: rgba(70, 130, 160, 0.12);
}
QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0f9fc5, stop:1 #0a7fa3);
    color: white;
    border: 0;
    font-weight: 600;
    padding-left: 20px;
    padding-right: 20px;
}
QPushButton#PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #14b8e0, stop:1 #0d94bd);
}
QPushButton#VoiceButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(6, 61, 75, 0.98), stop:1 rgba(5, 44, 56, 0.96));
    color: #7ef2ee;
    border-color: rgba(17, 122, 136, 0.9);
    font-weight: 600;
}
QPushButton#VoiceButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(8, 78, 95, 0.99), stop:1 rgba(6, 56, 70, 0.98));
    border-color: rgba(61, 245, 217, 0.6);
}
QPushButton#QuickButton {
    text-align: left;
    background: rgba(10, 26, 41, 0.92);
    padding: 10px 12px;
    border-color: rgba(95, 235, 255, 0.12);
    font-family: "Outfit", "Segoe UI";
}
QPushButton#QuickButton:hover {
    background: rgba(14, 32, 52, 0.96);
    border-color: rgba(95, 235, 255, 0.35);
    color: #e8f7ff;
}

QLineEdit, QComboBox {
    background: rgba(8, 20, 33, 0.96);
    color: #e7f4fb;
    border: 1px solid rgba(95, 235, 255, 0.22);
    border-radius: 8px;
    padding: 9px 11px;
    selection-background-color: #137b97;
    font-family: "Outfit", "Segoe UI";
    font-size: 12px;
}
QLineEdit:focus, QComboBox:focus {
    border-color: rgba(95, 235, 255, 0.6);
}
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #9dc3da;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: rgba(11, 25, 40, 0.98);
    color: #e7f4fb;
    selection-background-color: #137b97;
    border: 1px solid rgba(95, 235, 255, 0.18);
    outline: none;
}
QComboBox QAbstractItemView::item { padding: 8px 12px; }
QComboBox QAbstractItemView::item:hover { background: rgba(13, 32, 48, 0.6); }

QCheckBox { color: #e8f7ff; spacing: 9px; font-family: "Outfit", "Segoe UI"; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(95, 235, 255, 0.35); background: rgba(8, 20, 33, 0.96); }
QCheckBox::indicator:checked { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3df5d9, stop:1 #4df4ff); border-color: #3df5d9; }

QPlainTextEdit#Transcript {
    background: rgba(8, 20, 33, 0.92);
    color: #d6e8f5;
    border: 1px solid rgba(95, 235, 255, 0.16);
    border-radius: 10px;
    padding: 10px;
    font-size: 12px;
    font-family: "JetBrains Mono", "Consolas", "Monospace";
}

QTabWidget::pane { border: 1px solid rgba(95, 235, 255, 0.16); background: rgba(11, 25, 40, 0.92); border-radius: 10px; margin-top: -1px; }
QTabBar::tab { background: rgba(10, 26, 41, 0.92); color: #9dc3da; padding: 8px 16px; border: 1px solid rgba(95, 235, 255, 0.16); border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; font-family: "Outfit", "Segoe UI"; font-size: 11px; font-weight: 500; min-width: 80px; }
QTabBar::tab:selected { background: rgba(11, 25, 40, 0.98); color: #3df5d9; font-weight: 600; border-color: rgba(95, 235, 255, 0.35); }
QTabBar::tab:hover:!selected { background: rgba(13, 32, 48, 0.96); color: #e8f7ff; }

QProgressBar { background: rgba(8, 20, 33, 0.96); border: 1px solid rgba(95, 235, 255, 0.16); border-radius: 6px; text-align: center; color: #e8f7ff; font-family: "Oxanium", "Outfit"; font-size: 9px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3df5d9, stop:0.5 #4df4ff, stop:1 #9d7bff); border-radius: 6px; }

QListWidget { background: rgba(8, 20, 33, 0.96); border: 1px solid rgba(95, 235, 255, 0.16); border-radius: 8px; outline: none; font-family: "Outfit", "Segoe UI"; }
QListWidget::item { padding: 8px 12px; border-bottom: 1px solid rgba(24, 53, 74, 0.4); }
QListWidget::item:last { border-bottom: none; }
QListWidget::item:hover { background: rgba(13, 32, 48, 0.6); }
QListWidget::item:selected { background: rgba(16, 45, 64, 0.9); color: #3df5d9; border-left: 2px solid #3df5d9; }

QScrollBar:vertical { width: 6px; background: transparent; margin: 0; }
QScrollBar::handle:vertical { background: rgba(95, 235, 255, 0.28); border-radius: 3px; min-height: 24px; margin: 2px 1px; }
QScrollBar::handle:vertical:hover { background: rgba(95, 235, 255, 0.55); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal { height: 6px; background: transparent; margin: 0; }
QScrollBar::handle:horizontal { background: rgba(95, 235, 255, 0.28); border-radius: 3px; min-width: 24px; margin: 1px 2px; }
QScrollBar::handle:horizontal:hover { background: rgba(95, 235, 255, 0.55); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QToolTip { background: rgba(8, 16, 26, 0.98); color: #e8f7ff; border: 1px solid rgba(95, 235, 255, 0.35); border-radius: 8px; padding: 6px 10px; font-family: "Outfit", "Segoe UI"; font-size: 11px; }

QMessageBox { background: rgba(10, 22, 36, 0.95); color: #e8f7ff; }
QMessageBox QLabel { color: #e8f7ff; }
QMessageBox QPushButton { min-width: 80px; }

QSplitter::handle { background: rgba(95, 235, 255, 0.12); width: 1px; height: 1px; }
QSplitter::handle:hover { background: rgba(95, 235, 255, 0.35); }
"""'''

content = color_str + mode_str + '\n' + qss + '\n'

theme_path.write_text(content, encoding='utf-8')
print('Theme file written:', theme_path)
print('Lines:', len(content.splitlines()))
