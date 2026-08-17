"""
PDAWindow — the frameless, always-on-top widget itself.

Display modes:
  - "full"  — the panel with clock, stat bars, network readout
  - "pill"  — a condensed single-line strip

Themes: amber / green / red / blue — see ui/theme.py.

Lock state controls whether the window can be dragged.

Note on the full<->pill switch: we deliberately use plain
QWidget.setVisible() instead of QStackedLayout. QStackedLayout sizes
itself to the LARGEST page by default, so the pill view was inheriting
the full view's height. A QVBoxLayout, by contrast, excludes hidden
widgets from its size calculation entirely — so swapping visibility on
two widgets directly in the same layout is what actually makes
adjustSize() shrink the window in pill mode.
"""

import os
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QAction

from system_stats import SystemStats
from network_stats import NetworkStats
from theme import THEME_ORDER, build_stylesheet


class PDAWindow(QWidget):
    def __init__(self):
        super().__init__()

        self._drag_pos: QPoint | None = None
        self._net = NetworkStats()
        self._locked = True
        self._mode = "full"
        self._theme_index = 0

        self._setup_window_flags()
        self._build_ui()
        self._start_timers()
        self._apply_theme()
        self._apply_mode()
        self._update_lock_button()
        self._setup_tray_icon()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen_geo = self.screen().availableGeometry()
        self.move(screen_geo.right() - 240 - 24, screen_geo.top() + 24)

    def _build_ui(self):
        self.setObjectName("PDAPanel")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(4)
        self._outer_layout = outer

        # --- header row: title, theme, mode, lock, close ---
        header_row = QHBoxLayout()
        header_row.setSpacing(4)
        self.header_label = QLabel("PDA // STATUS")
        self.header_label.setObjectName("HeaderLabel")
        header_row.addWidget(self.header_label)
        header_row.addStretch()

        self.theme_btn = self._make_icon_button("◐", "Cycle color theme")
        self.theme_btn.clicked.connect(self._cycle_theme)
        header_row.addWidget(self.theme_btn)

        self.mode_btn = self._make_icon_button("▭", "Toggle compact/full view")
        self.mode_btn.clicked.connect(self._toggle_mode)
        header_row.addWidget(self.mode_btn)

        self.lock_btn = self._make_icon_button("", "")
        self.lock_btn.clicked.connect(self._toggle_lock)
        header_row.addWidget(self.lock_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.clicked.connect(self.hide)  # tray keeps it alive
        self.close_btn.setToolTip("Hide (right-click tray icon to quit)")
        header_row.addWidget(self.close_btn)

        outer.addLayout(header_row)

        # --- both views live directly in the same layout; we toggle
        #     visibility rather than using a QStackedLayout (see note
        #     in the module docstring for why) ---
        self.full_view = self._build_full_view()
        outer.addWidget(self.full_view)

        self.pill_view = self._build_pill_view()
        outer.addWidget(self.pill_view)

    def _make_icon_button(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("IconButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(26, 26)  # set in code, not just QSS — see main.py note
        if tooltip:
            btn.setToolTip(tooltip)
        return btn

    def _build_full_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setObjectName("ClockLabel")
        layout.addWidget(self.clock_label)

        self.date_label = QLabel("")
        self.date_label.setObjectName("DateLabel")
        layout.addWidget(self.date_label)

        sys_section = QLabel("SYSTEM")
        sys_section.setObjectName("SectionLabel")
        layout.addWidget(sys_section)

        self.cpu_bar = self._make_stat_row(layout, "CPU")
        self.ram_bar = self._make_stat_row(layout, "RAM")
        self.disk_bar = self._make_stat_row(layout, "DISK")

        net_section = QLabel("NETWORK")
        net_section.setObjectName("SectionLabel")
        layout.addWidget(net_section)

        self.net_label = QLabel("↑ 0.0 KB/s   ↓ 0.0 KB/s")
        self.net_label.setObjectName("StatLabel")
        layout.addWidget(self.net_label)

        return view

    def _build_pill_view(self) -> QWidget:
        view = QWidget()
        layout = QHBoxLayout(view)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(10)

        self.pill_clock_label = QLabel("00:00:00")
        self.pill_clock_label.setObjectName("PillLabel")
        layout.addWidget(self.pill_clock_label)

        self.pill_cpu_label = QLabel("CPU --%")
        self.pill_cpu_label.setObjectName("PillLabel")
        layout.addWidget(self.pill_cpu_label)

        self.pill_ram_label = QLabel("RAM --%")
        self.pill_ram_label.setObjectName("PillLabel")
        layout.addWidget(self.pill_ram_label)

        self.pill_net_label = QLabel("↑0.0 ↓0.0")
        self.pill_net_label.setObjectName("PillLabel")
        layout.addWidget(self.pill_net_label)

        return view

    def _make_stat_row(self, layout: QVBoxLayout, name: str) -> QProgressBar:
        row = QHBoxLayout()
        label = QLabel(name)
        label.setObjectName("StatLabel")
        label.setFixedWidth(36)
        row.addWidget(label)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(True)
        row.addWidget(bar)

        layout.addLayout(row)
        return bar

    def _start_timers(self):
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(2000)
        self._update_stats()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _cycle_theme(self):
        self._theme_index = (self._theme_index + 1) % len(THEME_ORDER)
        self._apply_theme()

    def _apply_theme(self):
        theme_name = THEME_ORDER[self._theme_index]
        self.setStyleSheet(build_stylesheet(theme_name))

    # ------------------------------------------------------------------
    # Mode (full <-> pill)
    # ------------------------------------------------------------------

    def _toggle_mode(self):
        self._mode = "pill" if self._mode == "full" else "full"
        self._apply_mode()

    def _apply_mode(self):
        is_full = self._mode == "full"

        self.full_view.setVisible(is_full)
        self.pill_view.setVisible(not is_full)
        self.header_label.setVisible(is_full)
        self.setProperty("mode", self._mode)

        if is_full:
            self._outer_layout.setContentsMargins(14, 10, 14, 10)
            self.setFixedWidth(240)
        else:
            self._outer_layout.setContentsMargins(14, 6, 10, 6)
            self.setFixedWidth(340)

        self.style().unpolish(self)
        self.style().polish(self)

        # Hidden widgets are excluded from QVBoxLayout's size calc,
        # so this now actually shrinks/grows the window correctly.
        self.adjustSize()

        # Pill mode is wider than full mode. If the panel is parked
        # near a screen edge, growing it can push it partly or fully
        # off-screen — and since it's often locked, you'd have no way
        # to drag it back. Keep it fully on-screen after every resize.
        self._clamp_to_screen()

    def _clamp_to_screen(self):
        """Nudges the window back on-screen if any edge has gone
        past the available screen geometry."""
        screen_geo = self.screen().availableGeometry()
        geo = self.frameGeometry()

        x = geo.x()
        y = geo.y()

        if geo.right() > screen_geo.right():
            x = screen_geo.right() - geo.width()
        if geo.left() < screen_geo.left():
            x = screen_geo.left()
        if geo.bottom() > screen_geo.bottom():
            y = screen_geo.bottom() - geo.height()
        if geo.top() < screen_geo.top():
            y = screen_geo.top()

        if (x, y) != (geo.x(), geo.y()):
            self.move(x, y)

    # ------------------------------------------------------------------
    # Lock (draggable <-> fixed)
    # ------------------------------------------------------------------

    def _toggle_lock(self):
        self._locked = not self._locked
        self._update_lock_button()

    def _update_lock_button(self):
        self.lock_btn.setText("🔒" if self._locked else "🔓")
        self.lock_btn.setToolTip(
            "Locked — click to unlock and drag" if self._locked
            else "Unlocked — click to lock in place"
        )

    # ------------------------------------------------------------------
    # System tray (keeps the app running when the panel is hidden,
    # gives you a real quit action, and a way to reopen it)
    # ------------------------------------------------------------------

    def _setup_tray_icon(self):
        icon = self._make_tray_pixmap()
        self.tray = QSystemTrayIcon(QIcon(icon), self)
        self.tray.setToolTip("PDA Widget")

        menu = QMenu()

        show_action = QAction("Show / Hide", self)
        show_action.triggered.connect(self._toggle_visibility)
        menu.addAction(show_action)

        lock_action = QAction("Toggle Lock", self)
        lock_action.triggered.connect(self._toggle_lock)
        menu.addAction(lock_action)

        reset_pos_action = QAction("Reset Position", self)
        reset_pos_action.triggered.connect(self._reset_position)
        menu.addAction(reset_pos_action)

        theme_action = QAction("Cycle Theme", self)
        theme_action.triggered.connect(self._cycle_theme)
        menu.addAction(theme_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _make_tray_pixmap(self) -> QPixmap:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#0c0e0a"))
        return pixmap

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _toggle_visibility(self):
        self.setVisible(not self.isVisible())

    def _reset_position(self):
        screen_geo = self.screen().availableGeometry()
        self.move(screen_geo.right() - self.width() - 24, screen_geo.top() + 24)
        if not self.isVisible():
            self.show()

    def _quit(self):
        self.tray.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    # ------------------------------------------------------------------
    # Update handlers
    # ------------------------------------------------------------------

    def _update_clock(self):
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        self.clock_label.setText(time_str)
        self.date_label.setText(now.strftime("%a %d %b %Y").upper())
        self.pill_clock_label.setText(time_str)

    def _update_stats(self):
        cpu = int(SystemStats.cpu_percent())
        ram = int(SystemStats.ram_percent())
        disk = int(SystemStats.disk_percent())

        self.cpu_bar.setValue(cpu)
        self.ram_bar.setValue(ram)
        self.disk_bar.setValue(disk)
        self.pill_cpu_label.setText(f"CPU {cpu:>2}%")
        self.pill_ram_label.setText(f"RAM {ram:>2}%")

        up_kbps, down_kbps = self._net.sample()
        self.net_label.setText(f"↑ {up_kbps:6.1f} KB/s   ↓ {down_kbps:6.1f} KB/s")
        self.pill_net_label.setText(f"↑{up_kbps:.1f} ↓{down_kbps:.1f}")

    # ------------------------------------------------------------------
    # Dragging
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self._locked:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._locked or self._drag_pos is None:
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            self._clamp_to_screen()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None