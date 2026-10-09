"""ASTRA Nebula — Local First AI Command Center.

Upgraded UI with glass/mica theme, upgraded OrbVisualizer,
and modular component structure.
"""

import math
import os
import sys
import threading
import time
from typing import Dict, List, Set, Optional

# Fix SSL cert path for httpx/ollama
try:
    import certifi
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
except ImportError:
    pass

# --- Modular UI components from astra_ui package ---
# (named astra_ui to avoid shadowing by this ui.py entry point)
try:
    from astra_ui.core.theme import STYLESHEET, COLORS, mode_stylesheet
    from astra_ui.widgets.orb import OrbVisualizer, CoreOrb
    from astra_ui.widgets.panels import Card, MetricCard, HealthRow
    from astra_ui.assets import load_assets
except ImportError:
    from core.theme import STYLESHEET, COLORS, mode_stylesheet
    from widgets.orb import OrbVisualizer, CoreOrb
    from widgets.panels import Card, MetricCard, HealthRow
    from assets import load_assets

from PyQt5.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    pyqtSignal,
    QSize,
)
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QKeySequence
from PyQt5.QtWidgets import QGraphicsOpacityEffect
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QShortcut,
    QStackedWidget,
    QStyle,
    QStyleFactory,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jarvis_runtime import DEFAULT_AGENT, DEFAULT_MODEL, DEFAULT_TOOLS, get_runtime
from branding import ASSISTANT_NAME, OWNER_NAME
from Brain.settings import SettingsStore
from Brain.orb_bridge import get_orb_bridge
from Brain.agent_loop import ReActAgent, AgentJournal
from co_brain import AstraVoiceLoop
from TextToSpeech.Fast_DF_TTS import speak


class AstraWindow(QMainWindow):
    status_changed = pyqtSignal(str, str)
    chat_result = pyqtSignal(str, str, object)
    models_ready = pyqtSignal(object, str)
    voice_finished = pyqtSignal(str, str)
    agent_event = pyqtSignal(object)
    transcript_changed = pyqtSignal(str, str)
    audio_level_changed = pyqtSignal(float)
    speech_activity_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._register_system_fonts()

        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.settings = SettingsStore()
        preferences = self.settings.load()
        runtime = get_runtime()
        runtime.set_memory_enabled(preferences.get("memory_enabled", True))
        memory_policy = preferences.get("memory_policy", "explicit")
        if memory_policy not in {"explicit", "ask", "do_not_save"}:
            memory_policy = "explicit"
        runtime.set_memory_policy(memory_policy)

        self.input_path = os.path.join(self.root_dir, "input.txt")
        self.log_path = os.path.join(self.root_dir, "log.txt")
        self.agent_started = False
        self.agent_ready = False
        self.voice_stop_event = None
        self.request_in_flight = False
        self.current_model = preferences.get("model") or DEFAULT_MODEL
        self.current_agent = preferences.get("agent", DEFAULT_AGENT)
        if self.current_agent not in {"native_react", "orchestrator", "simple", "agentic"}:
            self.current_agent = DEFAULT_AGENT
        self.enabled_tools = set(preferences.get("enabled_tools", DEFAULT_TOOLS)) & set(DEFAULT_TOOLS)
        self.auto_model = bool(preferences.get("auto_model", True))
        self.log_snapshot = self._read_log()

        self.setWindowTitle(f"{ASSISTANT_NAME} · Local Command Center")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 720)
        self.setStyleSheet(STYLESHEET)

        # Connect Orb Bridge for Three.js visualizer
        self._orb_bridge = get_orb_bridge()
        self._orb_bridge.subscribe(self._on_orb_event)

        # --- UI layout ---
        base = QWidget()
        base.setObjectName("Root")
        self.setCentralWidget(base)
        shell = QHBoxLayout(base)
        shell.setContentsMargins(14, 14, 14, 14)
        shell.setSpacing(12)

        self.page_stack = QStackedWidget()
        self.pages: List[QWidget] = []
        self.pages.append(self._build_workspace())
        self.pages.append(self._build_conversation_page())
        self.pages.append(self._build_agent_page())
        self.pages.append(self._build_voice_page())
        self.pages.append(self._build_tools_page())
        self.pages.append(self._build_memory_page())

        for page in self.pages:
            self.page_stack.addWidget(page)

        shell.addWidget(self._build_sidebar())
        shell.addWidget(self.page_stack, 1)

        # --- Signal connections ---
        self.status_changed.connect(self._set_status)
        self.chat_result.connect(self._finish_chat)
        self.models_ready.connect(self._set_models)
        self.voice_finished.connect(self._finish_voice)
        self.agent_event.connect(self._handle_agent_event)
        self.transcript_changed.connect(self._update_transcript_preview)
        self.audio_level_changed.connect(self._update_audio_level)
        self.speech_activity_changed.connect(self._update_speech_activity)

        self._event_subscription = get_runtime().event_bus.subscribe(self.agent_event.emit)
        get_runtime().set_agent_step_callback(self._on_agent_step)

        # Page transition effect
        self.page_effect = QGraphicsOpacityEffect(self.page_stack)
        self.page_stack.setGraphicsEffect(self.page_effect)
        self.page_animation = QPropertyAnimation(self.page_effect, b"opacity", self)
        self.page_animation.setDuration(260)
        self.page_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Log polling
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_log)
        self.timer.start(350)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self.send_message)

        threading.Thread(target=self._load_models, daemon=True).start()

    # ============================================================
    #  Font registration
    # ============================================================
    def _register_system_fonts(self):
        if os.name == "nt":
            fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
            for filename in ("segoeui.ttf", "segoeuib.ttf"):
                font_path = os.path.join(fonts_dir, filename)
                if os.path.isfile(font_path):
                    QFontDatabase.addApplicationFont(font_path)
        app = QApplication.instance()
        if app:
            font = QFont("Segoe UI", 10)
            app.setFont(font)

    # ============================================================
    #  Sidebar
    # ============================================================
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(8)

        # Brand
        brand = QHBoxLayout()
        mark = QLabel("◉")
        mark.setObjectName("BrandMark")
        name = QLabel(ASSISTANT_NAME)
        name.setObjectName("BrandName")
        brand.addWidget(mark)
        brand.addWidget(name)
        brand.addStretch()
        layout.addLayout(brand)

        sub = QLabel("LOCAL COMMAND CENTER")
        sub.setObjectName("Eyebrow")
        layout.addWidget(sub)
        layout.addSpacing(24)

        # Navigation
        self.nav_buttons: List[QPushButton] = []
        nav_items = [
            ("Command Center", "◆", 0),
            ("Conversations", "◐", 1),
            ("Agent Loop", "⎇", 2),
            ("Voice Interface", "🎤", 3),
            ("Tools & Skills", "⚙", 4),
            ("Memory", "💾", 5),
        ]

        for label, icon_text, index in nav_items:
            item = QPushButton(f"{icon_text}  {label}")
            item.setObjectName("NavActive" if index == 0 else "NavItem")
            item.setCheckable(True)
            item.setChecked(index == 0)
            item.clicked.connect(lambda _c=False, p=index: self._navigate(p))
            self.nav_buttons.append(item)
            layout.addWidget(item)

        layout.addStretch()

        # Voice status card
        voice = Card("Voice link", "Microphone", accent="teal")
        self.voice_status = QLabel("●  Standby")
        self.voice_status.setObjectName("StatusValue")
        voice.content.addWidget(self.voice_status)

        self.voice_hint = QLabel("Start the local voice agent to listen.")
        self.voice_hint.setObjectName("Muted")
        self.voice_hint.setWordWrap(True)
        voice.content.addWidget(self.voice_hint)
        layout.addWidget(voice)

        local = QLabel(f"LOCAL-FIRST CORE · {OWNER_NAME}\nOllama · OpenJarvis runtime")
        local.setObjectName("PrivacyNote")
        layout.addWidget(local)

        return sidebar

    # ============================================================
    #  Navigation
    # ============================================================
    def _navigate(self, page_index: int):
        self.page_stack.setCurrentIndex(page_index)
        for index, button in enumerate(self.nav_buttons):
            button.setChecked(index == page_index)
            button.setObjectName("NavActive" if index == page_index else "NavItem")
            button.style().unpolish(button)
            button.style().polish(button)

        title_map = {
            0: "Command Center",
            1: "Conversations",
            2: "Agent Loop",
            3: "Voice Interface",
            4: "Tools & Skills",
            5: "Memory",
        }
        self.page_title.setText(title_map.get(page_index, "Command Center"))

        self.page_animation.stop()
        self.page_animation.setStartValue(0.0)
        self.page_animation.setEndValue(1.0)
        self.page_animation.start()

        if page_index == 1:
            self._refresh_archive()

    # ============================================================
    #  Workspace / Command Center
    # ============================================================
    def _build_workspace(self):
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        title_box = QVBoxLayout()
        eyebrow = QLabel("PERSONAL AI · ON YOUR DEVICE")
        eyebrow.setObjectName("Eyebrow")
        self.page_title = QLabel("Command Center")
        self.page_title.setObjectName("PageTitle")
        title_box.addWidget(eyebrow)
        title_box.addWidget(self.page_title)
        top.addLayout(title_box)
        top.addStretch()

        self.top_status = QLabel("●  SYSTEM STANDBY")
        self.top_status.setObjectName("SystemBadge")
        top.addWidget(self.top_status)
        layout.addLayout(top)

        # Metrics row
        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.model_metric = self._metric("LOCAL MODEL", DEFAULT_MODEL, "Ollama runtime", accent="cyan")
        metrics.addWidget(self.model_metric)
        metrics.addWidget(self._metric("VOICE INPUT", "Vosk offline", "Local speech recognition", accent="teal"))
        metrics.addWidget(self._metric("VOICE OUTPUT", "Windows SAPI", "Offline voice fallback", accent="cyan"))
        self.inference_metric = self._metric("AGENT CORE", DEFAULT_AGENT, "OpenJarvis runtime", accent="violet")
        metrics.addWidget(self.inference_metric)
        layout.addLayout(metrics)

        # Controls row
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("MODEL"))
        self.model_selector = QComboBox()
        self.model_selector.addItem(DEFAULT_MODEL)
        self.model_selector.currentTextChanged.connect(self._model_changed)
        controls.addWidget(self.model_selector, 2)

        self.auto_model_checkbox = QCheckBox("Auto route")
        self.auto_model_checkbox.setChecked(self.auto_model)
        self.auto_model_checkbox.toggled.connect(self._auto_model_toggled)
        controls.addWidget(self.auto_model_checkbox)

        self.model_metric.value_label.setText("AUTO · fast / reasoning")
        self.model_metric.set_accent("cyan")

        controls.addWidget(QLabel("AGENT"))
        self.agent_selector = QComboBox()
        self.agent_selector.addItems(["native_react", "orchestrator", "simple", "agentic"])
        self.agent_selector.setCurrentText(self.current_agent)
        self.agent_selector.currentTextChanged.connect(self._agent_changed)
        controls.addWidget(self.agent_selector, 1)
        layout.addLayout(controls)

        # Main body
        body = QHBoxLayout()
        body.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(12)

        # Orb card (centerpiece)
        core_card = Card(f"{ASSISTANT_NAME} CORE", "Neural visualization", accent="cyan")
        self.orb = OrbVisualizer()  # Upgraded visualizer
        core_card.content.addWidget(self.orb, 1)

        self.state_label = QLabel("READY WHEN YOU ARE")
        self.state_label.setObjectName("CoreState")
        self.state_label.setAlignment(Qt.AlignCenter)
        core_card.content.addWidget(self.state_label)
        left.addWidget(core_card, 3)

        # Chat card
        chat_card = Card("Conversation", "Live session", accent="cyan")
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setObjectName("Transcript")
        self.transcript.setPlaceholderText(f"Start {ASSISTANT_NAME}, then speak or type a message.")
        chat_card.content.addWidget(self.transcript, 1)

        composer = QHBoxLayout()
        composer.setSpacing(8)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Message your local agent…")
        self.message_input.returnPressed.connect(self.send_message)
        composer.addWidget(self.message_input, 1)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.clicked.connect(self.send_message)
        composer.addWidget(self.send_button)

        self.mic_button = QPushButton("Start voice")
        self.mic_button.setObjectName("VoiceButton")
        self.mic_button.clicked.connect(self.toggle_voice)
        composer.addWidget(self.mic_button)

        chat_card.content.addLayout(composer)
        left.addWidget(chat_card, 2)
        body.addLayout(left, 7)

        # Right panel
        right = QVBoxLayout()
        right.setSpacing(12)

        runtime_card = Card("Runtime health", "Local systems", accent="teal")
        self.runtime_model = self._health_row(QStyle.SP_ComputerIcon, "Ollama", "Checking local models")
        self.runtime_stt = self._health_row(QStyle.SP_MediaVolume, "Speech recognition", "Vosk · local model")
        self.runtime_tts = self._health_row(QStyle.SP_MediaPlay, "Voice output", "Windows SAPI fallback")
        runtime_card.content.addWidget(self.runtime_model)
        runtime_card.content.addWidget(self.runtime_stt)
        runtime_card.content.addWidget(self.runtime_tts)
        right.addWidget(runtime_card)

        feed = Card("Activity feed", "Session events", accent="violet")
        self.activity = QLabel("Waiting for the agent to start.")
        self.activity.setObjectName("Muted")
        self.activity.setWordWrap(True)
        feed.content.addWidget(self.activity)
        right.addWidget(feed, 1)

        quick = Card("Quick prompts", f"Try {ASSISTANT_NAME}", accent="amber")
        for prompt in ("What can you do?", "Tell me about yourself", "Summarize the last response"):
            button = QPushButton(prompt)
            button.setObjectName("QuickButton")
            button.clicked.connect(lambda _c=False, text=prompt: self._use_prompt(text))
            quick.content.addWidget(button)
        right.addWidget(quick)

        body.addLayout(right, 3)
        layout.addLayout(body, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addWidget(QLabel("LOCAL AGENT  /  OLLAMA  /  VOICE"))
        footer.addStretch()
        self.footer_clock = QLabel("")
        footer.addWidget(self.footer_clock)
        layout.addLayout(footer)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(
            lambda: self.footer_clock.setText(
                time.strftime("%A, %d %B  ·  %H:%M:%S")
            )
        )
        self.clock_timer.start(1000)

        return workspace

    # ============================================================
    #  Metric / Health helpers
    # ============================================================
    def _metric(self, title: str, value: str, detail: str, accent: str = "cyan") -> MetricCard:
        card = MetricCard(title, value, detail, accent=accent)
        return card

    def _health_row(self, icon_enum, title: str, detail: str) -> HealthRow:
        return HealthRow(icon_enum, title, detail)

    # ============================================================
    #  Conversation page
    # ============================================================
    def _build_conversation_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 6, 8, 6)

        card = Card("Conversation archive", "Local session log", accent="cyan")
        self.archive_view = QPlainTextEdit()
        self.archive_view.setReadOnly(True)
        self.archive_view.setObjectName("Transcript")
        card.content.addWidget(self.archive_view, 1)

        refresh = QPushButton("Refresh session history")
        refresh.clicked.connect(self._refresh_archive)
        card.content.addWidget(refresh)
        layout.addWidget(card, 1)

        self._refresh_archive()
        return page

    # ============================================================
    #  Voice page
    # ============================================================
    def _build_voice_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 6, 8, 6)

        card = Card("Voice interface", "Speech services", accent="teal")
        self.voice_page_status = QLabel("Voice input is stopped.")
        self.voice_page_status.setObjectName("Muted")
        card.content.addWidget(self.voice_page_status)

        self.transcript_preview = QLabel("Your speech will appear here while ASTRA listens.")
        self.transcript_preview.setObjectName("BodyText")
        self.transcript_preview.setWordWrap(True)
        card.content.addWidget(self.transcript_preview)

        card.content.addWidget(QLabel("Microphone level"))
        self.microphone_level = QProgressBar()
        self.microphone_level.setRange(0, 100)
        self.microphone_level.setTextVisible(False)
        self.microphone_level.setFixedHeight(9)
        card.content.addWidget(self.microphone_level)

        start = QPushButton("Start voice listener")
        start.setObjectName("VoiceButton")
        start.clicked.connect(self.toggle_voice)
        card.content.addWidget(start)

        note = QLabel(
            "Voice recognition runs locally with Vosk. Voice output uses Windows SAPI; "
            "optional remote speech is disabled by default."
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        card.content.addWidget(note)
        card.content.addStretch(1)

        layout.addWidget(card, 1)
        return page

    # ============================================================
    #  Agent page
    # ============================================================
    def _build_agent_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 6, 8, 6)

        card = Card("ReAct agent loop", "Thought -> Action -> Observation", accent="violet")
        self.agent_step_view = QPlainTextEdit()
        self.agent_step_view.setReadOnly(True)
        self.agent_step_view.setObjectName("Transcript")
        self.agent_step_view.setPlaceholderText(
            "Run a goal with the 'agentic' agent mode to see the live step feed here."
        )
        card.content.addWidget(self.agent_step_view, 1)

        run_row = QHBoxLayout()
        run_row.setSpacing(8)
        self.agent_goal_input = QLineEdit()
        self.agent_goal_input.setPlaceholderText(
            "e.g. create a file called hello.py that prints 'Hello ASTRA' and run it"
        )
        self.agent_goal_input.returnPressed.connect(self.run_agent_goal)
        run_row.addWidget(self.agent_goal_input, 1)

        self.agent_run_button = QPushButton("Run agent")
        self.agent_run_button.setObjectName("PrimaryButton")
        self.agent_run_button.clicked.connect(self.run_agent_goal)
        run_row.addWidget(self.agent_run_button)

        self.agent_resume_button = QPushButton("Resume last")
        self.agent_resume_button.clicked.connect(self.resume_last_agent)
        run_row.addWidget(self.agent_resume_button)

        card.content.addLayout(run_row)

        runs_row = QHBoxLayout()
        runs_row.setSpacing(8)
        runs_row.addWidget(QLabel("Saved runs"))
        self.agent_runs = QListWidget()
        self.agent_runs.itemDoubleClicked.connect(self._resume_selected_run)
        runs_row.addWidget(self.agent_runs, 1)
        refresh_runs = QPushButton("Refresh")
        refresh_runs.clicked.connect(self._refresh_agent_runs)
        runs_row.addWidget(refresh_runs)
        card.content.addLayout(runs_row)

        layout.addWidget(card, 1)
        self._refresh_agent_runs()
        return page

    # ============================================================
    #  Tools page
    # ============================================================
    def _build_tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 6, 8, 6)

        card = Card("Agent capabilities", "OpenJarvis tools", accent="orange")
        self.tool_checkboxes: Dict[str, QCheckBox] = {}
        descriptions = {
            "calculator": "Evaluate arithmetic and numeric expressions.",
            "web_search": "Search the web for current information.",
            "think": "Use a reasoning scratchpad during multi-step tasks.",
        }

        for tool_name, description in descriptions.items():
            row = QHBoxLayout()
            row.setSpacing(8)
            checkbox = QCheckBox(tool_name.replace("_", " ").title())
            checkbox.setChecked(tool_name in self.enabled_tools)
            checkbox.toggled.connect(
                lambda enabled, name=tool_name: self._toggle_tool(name, enabled)
            )
            row.addWidget(checkbox)
            row.addStretch()
            detail = QLabel(description)
            detail.setObjectName("Muted")
            detail.setWordWrap(True)
            row.addWidget(detail)
            card.content.addLayout(row)
            self.tool_checkboxes[tool_name] = checkbox

        card.content.addStretch(1)
        layout.addWidget(card, 1)
        return page

    # ============================================================
    #  Memory page
    # ============================================================
    def _build_memory_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 6, 8, 6)

        card = Card("Persistent memory", "OpenJarvis persona memory", accent="magenta")
        settings = QHBoxLayout()
        settings.setSpacing(8)

        runtime = get_runtime()
        self.memory_enabled_control = QCheckBox("Memory enabled")
        self.memory_enabled_control.setChecked(runtime.memory_enabled)
        self.memory_enabled_control.toggled.connect(self._memory_enabled_changed)
        settings.addWidget(self.memory_enabled_control)

        settings.addSpacing(12)
        settings.addWidget(QLabel("Chat memory policy"))
        self.memory_policy_control = QComboBox()
        self.memory_policy_control.addItem("Save only when I ask", "explicit")
        self.memory_policy_control.addItem("Ask before saving", "ask")
        self.memory_policy_control.addItem("Do not save from chat", "do_not_save")
        self.memory_policy_control.setCurrentIndex(
            max(0, self.memory_policy_control.findData(runtime.memory_policy))
        )
        self.memory_policy_control.currentIndexChanged.connect(self._memory_policy_changed)
        settings.addWidget(self.memory_policy_control)
        settings.addStretch()

        card.content.addLayout(settings)

        self.memory_path_label = QLabel("Loading memory location…")
        self.memory_path_label.setObjectName("Muted")
        card.content.addWidget(self.memory_path_label)

        tabs = QTabWidget()
        profile_page = QWidget()
        profile_layout = QVBoxLayout(profile_page)
        self.memory_editor = QPlainTextEdit()
        self.memory_editor.setObjectName("Transcript")
        self.memory_editor.setPlaceholderText(
            f"Add durable facts and preferences for {ASSISTANT_NAME} to remember."
        )
        profile_layout.addWidget(self.memory_editor, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self._reload_memory)
        save_button = QPushButton("Save memory")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save_memory)
        actions.addWidget(reload_button)
        actions.addStretch()
        actions.addWidget(save_button)
        profile_layout.addLayout(actions)
        tabs.addTab(profile_page, "Profile & preferences")

        records_page = QWidget()
        records_layout = QVBoxLayout(records_page)
        self.memory_records = QListWidget()
        records_layout.addWidget(self.memory_records, 1)

        record_actions = QHBoxLayout()
        record_actions.setSpacing(8)
        refresh_records = QPushButton("Refresh")
        refresh_records.clicked.connect(self._refresh_memory_records)
        pin_record = QPushButton("Pin / unpin")
        pin_record.clicked.connect(self._toggle_memory_pin)
        delete_record = QPushButton("Delete selected")
        delete_record.clicked.connect(self._delete_memory_record)
        clear_records = QPushButton("Clear all records")
        clear_records.clicked.connect(self._clear_memory_records)
        record_actions.addWidget(refresh_records)
        record_actions.addWidget(pin_record)
        record_actions.addWidget(delete_record)
        record_actions.addStretch()
        record_actions.addWidget(clear_records)
        records_layout.addLayout(record_actions)
        tabs.addTab(records_page, "Episodic records")

        card.content.addWidget(tabs, 1)
        layout.addWidget(card, 1)

        self._refresh_memory_records()
        self._reload_memory()
        return page

    # ============================================================
    #  State handlers
    # ============================================================
    def _finish_voice(self, mode, message):
        """Clear voice lifecycle state without coupling it to chat errors."""
        self.agent_started = False
        self.agent_ready = False
        self.voice_stop_event = None
        self.mic_button.setDisabled(False)
        self.mic_button.setText("Start voice")
        self.voice_status.setText("●  Standby")
        self.top_status.setText("●  " + ("ERROR" if mode == "error" else "SYSTEM STANDBY"))
        if mode == "error":
            self.voice_page_status.setText(message)
        else:
            self.voice_page_status.setText("Voice input is stopped.")
        self.orb.reset()

    def _update_transcript_preview(self, preview, confirmed):
        text = preview or confirmed
        self.transcript_preview.setText(
            text or "Your speech will appear here while ASTRA listens."
        )

    def _update_audio_level(self, value):
        level = max(0.0, min(1.0, float(value)))
        self.microphone_level.setValue(round(level * 100))
        self.orb.set_audio_level(level)

    def _update_speech_activity(self, active):
        if not self.agent_started:
            return
        if active:
            self.orb.set_mode("listening")
            self.voice_status.setText("●  Listening")
            self.voice_page_status.setText("ASTRA is listening to your speech.")
        else:
            self.orb.set_mode("user_paused")
            self.voice_status.setText("●  Listening · pause")
            self.voice_page_status.setText("ASTRA is waiting for you to continue.")

    def _set_status(self, message, mode):
        self.state_label.setText(message.upper())
        self.activity.setText(message)
        self.orb.set_mode(mode)

        if mode == "listening":
            self.agent_ready = True
            self.voice_status.setText("●  Listening")
            self.voice_hint.setText("Say a request or use the message box below.")
            self.mic_button.setText("Stop voice")
            self.voice_page_status.setText("Voice agent is listening.")
            self.mic_button.setDisabled(False)
            self.runtime_stt.detail_label.setText("Listening for speech")
        elif mode == "booting" and self.agent_started:
            self.voice_status.setText("●  Starting")
            self.voice_hint.setText("Initializing local speech recognition.")
            self.mic_button.setText("Voice agent starting")
        elif self.agent_started:
            self.voice_status.setText("●  Active")
            self.mic_button.setText("Stop voice")
        else:
            self.voice_status.setText("●  Standby")
            self.mic_button.setText("Start voice")

        badge = "●  AGENT ACTIVE" if mode == "listening" else f"●  {mode.upper()}"
        self.top_status.setText(badge)

    # ============================================================
    #  Chat
    # ============================================================
    def send_message(self):
        message = self.message_input.text().strip()
        if not message or self.request_in_flight:
            return
        self.message_input.clear()
        self.transcript.appendPlainText(f"YOU  ·  {message}")
        self._append_log(f"\nYou : {message}\n")
        self.request_in_flight = True
        self.send_button.setDisabled(True)
        self._set_status("Request received · agent is thinking", "thinking")
        self.activity.setText(
            f"{self.current_agent} is processing the request with local tools."
        )

        requested_model = None if self.auto_model_checkbox.isChecked() else self.current_model
        threading.Thread(
            target=self._run_chat,
            args=(message, requested_model, self.current_agent, sorted(self.enabled_tools)),
            daemon=True,
        ).start()

    def _run_chat(self, message, model, agent, tools):
        try:
            result = get_runtime().ask_full(message, model=model, agent=agent, tools=tools)
            response = result.get("content", "")
        except Exception as exc:
            result = {"error": str(exc), "engine": "ollama", "model": model, "tool_results": []}
            response = f"OpenJarvis runtime error: {exc}"
        self.chat_result.emit(message, response, result)
        if response:
            speak(response)

    def _finish_chat(self, message, response, result):
        self.request_in_flight = False
        self.send_button.setDisabled(False)
        if response:
            self.transcript.appendPlainText(f"{ASSISTANT_NAME}  ·  {response}")

        log_lines = (
            f"{ASSISTANT_NAME.lower()} : {response}\n"
            f"runtime : {result.get('engine', 'ollama')} / {result.get('model', self.current_model)}\n"
        )
        tool_results = result.get("tool_results", [])
        for tool_result in tool_results:
            tool_name = tool_result.get("tool_name", "unknown")
            status = "ok" if tool_result.get("success") else "failed"
            log_lines += f"tool : {tool_name} / {status}\n"
            raw_result = tool_result.get("result", "")
            if isinstance(raw_result, dict):
                raw_result = raw_result.get("result", raw_result.get("target", ""))
            target = str(raw_result).replace("\n", " ")[:240]
            log_lines += f"action : {time.strftime('%Y-%m-%d %H:%M:%S')} | {tool_name} | {target} | {status}\n"

        self._append_log(log_lines)

        if result.get("error"):
            self._set_status("Agent request failed", "error")
            self.activity.setText(result["error"])
        else:
            self._set_status("Response ready · voice output active", "speaking")
            if result.get("model"):
                self.model_metric.value_label.setText(
                    f"AUTO · {result['model']}" if self.auto_model_checkbox.isChecked()
                    else result["model"]
                )
            if tool_results:
                tools_str = ", ".join(item.get("tool_name", "tool") for item in tool_results)
                self.activity.setText(f"Completed with {len(tool_results)} tool call(s): {tools_str}.")
            else:
                self.activity.setText(
                    f"{result.get('engine', 'ollama')} · {result.get('model', self.current_model)}"
                )
        self._refresh_archive()

    # ============================================================
    #  Agent
    # ============================================================
    def _handle_agent_event(self, event):
        state = event.state.value
        display = {
            "processing": "Request accepted",
            "thinking": "ASTRA is thinking",
            "tool_selection": "Selecting a tool",
            "executing": "Executing a tool",
            "observing": "Checking tool results",
            "responding": "Preparing response",
            "completed": "Task completed",
            "error": "Agent error",
        }.get(state, state.replace("_", " ").title())

        self._set_status(display, state)
        if event.detail:
            self.activity.setText(event.detail)

        # Forward to Orb Bridge
        try:
            get_orb_bridge().set_state(state)
        except Exception:
            pass

    def _on_orb_event(self, event):
        """Handle events from the Orb Bridge."""
        try:
            event_type = event.get("type")
            if event_type == "state":
                self.orb.set_mode(event.get("state", "idle"))
            elif event_type == "audio":
                self.orb.set_audio_level(event.get("level", 0.0))
            elif event_type == "pulse":
                self.orb.trigger_pulse()
            elif event_type == "tool":
                self.orb.set_tool_activity(event.get("tool", ""))
            elif event_type == "progress":
                self.orb.set_progress(event.get("value"))
        except Exception:
            pass

    def _on_agent_step(self, event):
        try:
            event_type = event.get("type")
            step = event.get("step", "")
            if event_type == "thinking":
                self._append_agent_step(f"[step {step}] thinking...\n")
            elif event_type == "step":
                self._append_agent_step(
                    f"[step {step}] thought: {event.get('thought')}\n"
                    f"  action: {event.get('action')} {event.get('action_input')}\n"
                )
            elif event_type == "observation":
                status = event.get("status", "ok")
                self._append_agent_step(
                    f"[step {step}] observation ({status}): {event.get('observation')}\n"
                )
            elif event_type == "finish":
                self._append_agent_step(f"\n=== finish: {event.get('summary')} ===\n")
            elif event_type == "error":
                self._append_agent_step(f"[step {step}] error: {event.get('error')}\n")
        except Exception:
            pass

    def _append_agent_step(self, text):
        self.agent_step_view.setPlainText(self.agent_step_view.toPlainText() + text)
        cursor = self.agent_step_view.textCursor()
        cursor.movePosition(cursor.End)
        self.agent_step_view.setTextCursor(cursor)

    def run_agent_goal(self):
        goal = self.agent_goal_input.text().strip()
        if not goal:
            return
        self.agent_goal_input.clear()
        self._append_agent_step(f"\n=== Goal: {goal} ===\n")
        self.agent_run_button.setDisabled(True)
        threading.Thread(target=self._run_agent_goal, args=(goal,), daemon=True).start()

    def _run_agent_goal(self, goal):
        try:
            agent = ReActAgent(on_step=self._on_agent_step)
            summary = agent.run(goal)
            self._append_agent_step(f"\n=== Summary: {summary} ===\n")
            self._refresh_agent_runs()
        except Exception as exc:
            self._append_agent_step(f"Agent error: {exc}")
        finally:
            self.agent_run_button.setDisabled(False)

    def _resume_agent_run(self, run_id):
        try:
            agent = ReActAgent(on_step=self._on_agent_step)
            agent.resume(run_id)
            self._refresh_agent_runs()
        except Exception as exc:
            self._append_agent_step(f"Resume error: {exc}")

    def _resume_selected_run(self, item):
        run_id = item.data(Qt.UserRole)
        if not run_id:
            return
        self._append_agent_step(f"\n=== Resuming run {run_id} ===\n")
        threading.Thread(
            target=self._resume_agent_run, args=(run_id,), daemon=True
        ).start()

    def resume_last_agent(self):
        try:
            journal = AgentJournal()
            runs = journal.list_runs(5)
            for run in runs:
                if run["status"] == "running":
                    self._append_agent_step(f"\n=== Resuming run {run['run_id']} ===\n")
                    threading.Thread(
                        target=self._resume_agent_run,
                        args=(run["run_id"],),
                        daemon=True,
                    ).start()
                    return
            self._append_agent_step("No interrupted runs to resume.")
        except Exception as exc:
            self._append_agent_step(f"Resume failed: {exc}")

    def _refresh_agent_runs(self):
        if not hasattr(self, "agent_runs"):
            return
        self.agent_runs.clear()
        try:
            journal = AgentJournal()
            for run in journal.list_runs(50):
                item = QListWidgetItem(
                    f"{run['run_id']} · {run['status']} · {run['goal'][:60]}"
                )
                item.setData(Qt.UserRole, run["run_id"])
                item.setData(Qt.UserRole + 1, bool(run.get("pinned")))
                self.agent_runs.addItem(item)
        except Exception as exc:
            self.activity.setText(f"Agent runs unavailable: {exc}")

    # ============================================================
    #  Voice lifecycle
    # ============================================================
    def start_agent(self):
        if self.agent_started:
            return
        self.agent_started = True
        self.voice_stop_event = threading.Event()
        self._set_status("Starting local voice services…", "booting")
        self.activity.setText("Loading speech recognition and local agent runtime.")
        self.mic_button.setText("Voice agent starting")
        self.mic_button.setDisabled(True)
        self.voice_page_status.setText("Starting the speech recognition bridge…")
        threading.Thread(target=self._run_agent, daemon=True).start()

    def toggle_voice(self):
        if self.agent_started:
            self.stop_agent()
        else:
            self.start_agent()

    def stop_agent(self):
        if self.voice_stop_event is not None:
            self.voice_stop_event.set()
            self.mic_button.setText("Stopping voice")
            self.mic_button.setDisabled(True)

    def _run_agent(self):
        last_mode = {"value": "booting"}
        last_message = {"value": "Starting local voice services…"}
        stop_event = self.voice_stop_event

        def report_status(message, mode):
            last_mode["value"] = mode
            last_message["value"] = message
            self.status_changed.emit(message, mode)

        def report_transcript(preview, confirmed):
            self.transcript_changed.emit(preview, confirmed)

        def report_audio_level(value):
            self.audio_level_changed.emit(value)

        def report_speech_activity(active):
            self.speech_activity_changed.emit(bool(active))

        try:
            os.chdir(self.root_dir)
            AstraVoiceLoop(
                status_callback=report_status,
                stop_event=stop_event,
                transcript_callback=report_transcript,
                audio_level_callback=report_audio_level,
                speech_activity_callback=report_speech_activity,
            )
            if last_mode["value"] != "error":
                report_status("Voice listener stopped", "idle")
        except Exception as exc:
            report_status(f"Startup error: {exc}", "error")
        finally:
            self.voice_finished.emit(last_mode["value"], last_message["value"])

    # ============================================================
    #  Memory helpers
    # ============================================================
    def _refresh_archive(self):
        if hasattr(self, "archive_view"):
            self.archive_view.setPlainText(self._read_log())
            cursor = self.archive_view.textCursor()
            cursor.movePosition(cursor.End)
            self.archive_view.setTextCursor(cursor)

    def _read_log(self):
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeError):
            return ""

    def _poll_log(self):
        current = self._read_log()
        # Log rotation: if current log is shorter than snapshot, reset snapshot
        if len(current) < len(self.log_snapshot):
            self.log_snapshot = ""
        # Only process new content
        if current.startswith(self.log_snapshot):
            added = current[len(self.log_snapshot):]
        else:
            # Log was truncated/rotated, only process new content from end
            added = current
        self.log_snapshot = current
        for line in added.splitlines():
            if line.startswith("You : "):
                text = line[6:].strip()
                if text:
                    self.transcript.appendPlainText(f"YOU  ·  {text}")
                    self._set_status("Request received · local model is thinking", "thinking")
            elif line.startswith((f"{ASSISTANT_NAME.lower()} : ", "jarvis : ")):
                text = line.split(":", 1)[1].strip()
                if text:
                    self.transcript.appendPlainText(f"{ASSISTANT_NAME}  ·  {text}")
                    self._set_status(f"Response ready · {ASSISTANT_NAME} is speaking", "speaking")
                    self.activity.setText("Completed a local inference and generated a voice response.")
            elif line.startswith("runtime : "):
                self.activity.setText(f"Runtime · {line[len('runtime : '):].strip()}")
            elif line.startswith("tool : "):
                self.activity.setText(f"Tool call · {line[len('tool : '):].strip()}")

    def _append_log(self, lines):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(lines)
            self.log_snapshot = self._read_log()
        except OSError as exc:
            self.activity.setText(f"Could not write session log: {exc}")

    def _use_prompt(self, prompt):
        self.message_input.setText(prompt)
        self.send_message()

    # ============================================================
    #  Settings handlers
    # ============================================================
    def _toggle_tool(self, tool_name, enabled):
        if enabled:
            self.enabled_tools.add(tool_name)
        else:
            self.enabled_tools.discard(tool_name)
        self.settings.update(enabled_tools=sorted(self.enabled_tools))

    def _model_changed(self, model):
        if model:
            self.current_model = model
            self.settings.update(model=model)
            self.model_metric.value_label.setText(
                "AUTO · fast / reasoning" if self.auto_model_checkbox.isChecked() else model
            )

    def _auto_model_toggled(self, enabled):
        self.auto_model = bool(enabled)
        self.settings.update(auto_model=self.auto_model)
        self.model_selector.setEnabled(not enabled)
        self.model_metric.value_label.setText(
            "AUTO · fast / reasoning" if enabled else self.current_model
        )

    def _agent_changed(self, agent):
        if agent:
            self.current_agent = agent
            self.settings.update(agent=agent)
            self.inference_metric.value_label.setText(agent)

    def _memory_enabled_changed(self, enabled):
        get_runtime().set_memory_enabled(enabled)
        self.settings.update(memory_enabled=bool(enabled))

    def _memory_policy_changed(self, _index):
        policy = self.memory_policy_control.currentData()
        get_runtime().set_memory_policy(policy)
        self.settings.update(memory_policy=policy)

    def _reload_memory(self):
        try:
            path, content = get_runtime().read_memory()
            self.memory_path_label.setText(str(path))
            self.memory_editor.setPlainText(content)
        except Exception as exc:
            self.memory_path_label.setText(f"Memory unavailable: {exc}")

    def _save_memory(self):
        try:
            path = get_runtime().write_memory(self.memory_editor.toPlainText())
            self.memory_path_label.setText(f"Saved · {path}")
            self.activity.setText("Persistent memory updated.")
        except Exception as exc:
            self.memory_path_label.setText(f"Could not save memory: {exc}")

    def _refresh_memory_records(self):
        if not hasattr(self, "memory_records"):
            return
        self.memory_records.clear()
        try:
            for memory in get_runtime().list_memories():
                pin = "★ " if memory.get("pinned") else ""
                row = QListWidgetItem(
                    f"{pin}[{memory['category']}] {memory['text']} · importance {memory['importance']}"
                )
                row.setData(Qt.UserRole, memory["id"])
                row.setData(Qt.UserRole + 1, bool(memory.get("pinned")))
                self.memory_records.addItem(row)
        except Exception as exc:
            self.activity.setText(f"Memory records unavailable: {exc}")

    def _toggle_memory_pin(self):
        item = self.memory_records.currentItem()
        if item is None:
            return
        pinned = not bool(item.data(Qt.UserRole + 1))
        if get_runtime().pin_memory(item.data(Qt.UserRole), pinned):
            self._refresh_memory_records()

    def _delete_memory_record(self):
        item = self.memory_records.currentItem()
        if item is not None and get_runtime().delete_memory(item.data(Qt.UserRole)):
            self._refresh_memory_records()

    def _clear_memory_records(self):
        answer = QMessageBox.question(
            self,
            "Clear episodic memory",
            "Delete all episodic and semantic records?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            get_runtime().clear_memories()
            self._refresh_memory_records()

    # ============================================================
    #  Model loading
    # ============================================================
    def _load_models(self):
        try:
            models = get_runtime().list_models()
            self.models_ready.emit(models, "")
            if models:
                warm_target = self.current_model if self.current_model in models else models[0]
                self.status_changed.emit(f"Loading {warm_target} into Ollama", "booting")
                warm_result = get_runtime().warm_model(warm_target)
                if warm_result is True:
                    self.status_changed.emit(f"{warm_target} is ready", "idle")
                    speak("Chào anh Dannz. ASTRA đã sẵn sàng. Anh có thể nhập tin nhắn hoặc bật trợ lý giọng nói.")
                else:
                    self.status_changed.emit(f"Model warm-up failed: {warm_result}", "error")
        except Exception as exc:
            self.models_ready.emit([], str(exc))

    def _set_models(self, models, error):
        if models:
            current = self.current_model
            self.model_selector.clear()
            self.model_selector.addItems(models)
            self.model_selector.setCurrentText(
                current if current in models else models[0]
            )
            self.runtime_model.detail_label.setText(f"{len(models)} local model(s) · online")
        else:
            self.runtime_model.detail_label.setText(error or "Ollama is not responding")

    # ============================================================
    #  Lifecycle
    # ============================================================
    def closeEvent(self, event):
        get_runtime().event_bus.unsubscribe(self._event_subscription)
        super().closeEvent(event)


def UI():
    app = QApplication([])
    app.setFont(QFont("Segoe UI", 10))
    load_assets(app)
    window = AstraWindow()
    window.showMaximized()
    app.exec_()


if __name__ == "__main__":
    UI()