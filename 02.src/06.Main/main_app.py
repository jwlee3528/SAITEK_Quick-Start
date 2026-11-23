# -*- coding: utf-8 -*-
"""
Tektronix QuickStart Program - Main Integrated Window
Integrates the 7 Tek_Manuals folders into separate tabs/modules, global VISA connection bar,
Startup Remote Readiness Check dialog, and live OpenChoice Talker/Listener I/O Monitor dock.
"""

import os
import sys
from typing import Dict, Optional

# Ensure all 02.src subdirectories are on sys.path for both direct, root, and PyInstaller frozen execution
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    BUNDLE_DIR = BASE_DIR
    SRC_DIR = os.path.join(BASE_DIR, "02.src")
    for sub in ("01.Core", "02.Modules", "03.Drivers", "04.Utils", "05.Config", "06.Main"):
        p = os.path.join(SRC_DIR, sub)
        if p not in sys.path:
            sys.path.insert(0, p)


def resolve_app_Resource_path(*rel_parts: str) -> str:
    """Finds bundled read-only resources (like 01.docs/10. Tek_Manuals) in executable dir or _MEIPASS."""
    cand1 = os.path.join(BASE_DIR, *rel_parts)
    if os.path.exists(cand1):
        return cand1
    cand2 = os.path.join(BUNDLE_DIR, *rel_parts)
    if os.path.exists(cand2):
        return cand2
    # Check _internal folder in PyInstaller 6+ onedir builds
    cand3 = os.path.join(BASE_DIR, "_internal", *rel_parts)
    if os.path.exists(cand3):
        return cand3
    return cand1

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QFrame,
    QSplitter,
    QMessageBox,
    QStatusBar,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QResizeEvent, QShowEvent

from instrument_profiles import CATEGORY_PROFILES
from visa_manager import VisaConnectionManager
from category_panel import CategoryWorkspacePanel
from dialogs import StartupReadinessDialog, get_available_screen_geometry, fit_and_center_window


class TekQuickStartMainWindow(QMainWindow):
    def __init__(self, skip_startup_dialog: bool = False):
        super().__init__()
        self.visa_mgr = VisaConnectionManager()
        self.manuals_dir = resolve_app_Resource_path("01.docs", "10. Tek_Manuals")
        self.data_export_dir = os.path.join(BASE_DIR, "05.data", "02.Processed")
        os.makedirs(self.data_export_dir, exist_ok=True)
        self.category_panels: Dict[str, CategoryWorkspacePanel] = {}
        self._initial_splitter_sized: bool = False

        avail = get_available_screen_geometry(self)
        self.is_compact_screen = avail.height() <= 920 or avail.width() <= 1600

        self.setWindowTitle(
            f"Tektronix & Keithley QuickStart Program (화면 자동 최적화: {avail.width()}×{avail.height()})"
        )

        self._build_ui()
        self._apply_screen_adaptive_geometry()

        if not skip_startup_dialog:
            QTimer.singleShot(100, self.show_startup_readiness_dialog)
        else:
            self._connect_from_bar()

    def _apply_screen_adaptive_geometry(self):
        """Sizes and positions the main window automatically according to the display's usable resolution."""
        fit_and_center_window(
            self,
            target_w_ratio=0.95 if self.is_compact_screen else 0.90,
            target_h_ratio=0.94 if self.is_compact_screen else 0.90,
            min_w=960,
            min_h=600,
            max_w=2200,
            max_h=1320,
        )

    def show_adaptive(self):
        """Shows the window maximized on compact/scaled screens or fitted & centered on large monitors."""
        avail = get_available_screen_geometry(self)
        if avail.width() <= 1600 or avail.height() <= 920:
            self.showMaximized()
        else:
            self.show()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        margin = 4 if self.is_compact_screen else 8
        root_layout.setContentsMargins(margin, margin, margin, margin)
        root_layout.setSpacing(4 if self.is_compact_screen else 6)

        # =====================================================================
        # GLOBAL TOP CONNECTION & READINESS BAR
        # =====================================================================
        conn_bar = QFrame()
        conn_bar.setStyleSheet(
            "QFrame { background-color: #0b2545; color: white; border-radius: 6px; padding: 3px; }"
        )
        c_layout = QHBoxLayout(conn_bar)
        c_layout.setContentsMargins(8, 3, 8, 3)
        c_layout.setSpacing(6)

        title_lbl = QLabel("⚡ TEK QUICKSTART")
        title_lbl.setFont(QFont("Malgun Gothic", 10 if self.is_compact_screen else 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")
        c_layout.addWidget(title_lbl)

        lbl_r = QLabel("VISA 리소스:")
        lbl_r.setStyleSheet("color: #e2e8f0; font-weight: bold;")
        c_layout.addWidget(lbl_r)

        self.cmb_visa_resource = QComboBox()
        self.cmb_visa_resource.setEditable(True)
        self.cmb_visa_resource.setMinimumWidth(160)
        self.cmb_visa_resource.setMaximumWidth(400)
        self.cmb_visa_resource.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_visa_resource.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_visa_resource.setStyleSheet("background-color: white; color: #0f172a; padding: 2px 4px;")
        self.cmb_visa_resource.addItems(self.visa_mgr.scan_resources())
        c_layout.addWidget(self.cmb_visa_resource, 2)

        btn_pad = "4px 8px" if self.is_compact_screen else "5px 10px"
        btn_scan = QPushButton("🔄 검색")
        btn_scan.setToolTip("PC에 연결된 USB / LAN VISA 리소스를 다시 검색합니다")
        btn_scan.setStyleSheet(f"background-color: #1e3a8a; color: white; padding: {btn_pad}; font-weight: bold;")
        btn_scan.clicked.connect(self._scan_visa_resources)
        c_layout.addWidget(btn_scan)

        self.chk_sim_mode = QCheckBox("시뮬레이션 모드")
        self.chk_sim_mode.setToolTip("가상 장비 시뮬레이션(Virtual HW) 모드를 활성화합니다")
        self.chk_sim_mode.setChecked(True)
        self.chk_sim_mode.setStyleSheet("color: #f472b6; font-weight: bold;")
        c_layout.addWidget(self.chk_sim_mode)

        btn_conn = QPushButton("🔗 장비 연결")
        btn_conn.setToolTip("선택한 VISA 리소스 또는 시뮬레이션 세션에 연결합니다")
        btn_conn.setStyleSheet(f"background-color: #16a34a; color: white; padding: {btn_pad}; font-weight: bold;")
        btn_conn.clicked.connect(self._connect_from_bar)
        c_layout.addWidget(btn_conn)

        self.lbl_conn_status = QLabel("● 연결 대기")
        self.lbl_conn_status.setMinimumWidth(80)
        self.lbl_conn_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_conn_status.setStyleSheet("color: #fde047; font-weight: bold; padding-left: 4px;")
        c_layout.addWidget(self.lbl_conn_status, 2)

        btn_startup_chk = QPushButton("📋 사전 준비 점검표")
        btn_startup_chk.setToolTip("7개 장비군 리모트 사전 준비 점검표 및 통신 테스트 창을 다시 엽니다")
        btn_startup_chk.setStyleSheet(
            f"background-color: #0284c7; color: white; padding: {btn_pad}; font-weight: bold; border-radius: 4px;"
        )
        btn_startup_chk.clicked.connect(self.show_startup_readiness_dialog)
        c_layout.addWidget(btn_startup_chk)

        btn_fit_screen = QPushButton("🖥️ 화면 맞춤")
        btn_fit_screen.setToolTip("현재 모니터 해상도에 맞게 창 크기와 패널 비율을 자동으로 다시 최적화합니다")
        btn_fit_screen.setStyleSheet(
            f"background-color: #475569; color: white; padding: {btn_pad}; font-weight: bold; border-radius: 4px;"
        )
        btn_fit_screen.clicked.connect(self.optimize_layout_for_screen)
        c_layout.addWidget(btn_fit_screen)

        btn_emg_stop = QPushButton("🚨 긴급 정지 (ALL STOP)")
        btn_emg_stop.setToolTip("모든 장비의 측정 루프를 즉시 중단하고 출력을 안전하게 OFF 합니다")
        btn_emg_stop.setStyleSheet(
            f"background-color: #dc2626; color: white; padding: {btn_pad}; font-weight: bold; border-radius: 4px;"
        )
        btn_emg_stop.clicked.connect(self.emergency_stop_all)
        c_layout.addWidget(btn_emg_stop)

        root_layout.addWidget(conn_bar)

        # =====================================================================
        # VERTICAL SPLITTER:
        # Top: 7 Folder Tabs (01. AFGs ~ 07. Tek VISA)
        # Bottom: Interactive TekVISA Talker/Listener & Live Command Log Console
        # =====================================================================
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setChildrenCollapsible(False)
        self.v_splitter.setHandleWidth(6)

        self.category_tabs = QTabWidget()
        self.category_tabs.setUsesScrollButtons(True)
        tab_font_pt = 9 if self.is_compact_screen else 10
        tab_pad = "5px 10px" if self.is_compact_screen else "7px 14px"
        self.category_tabs.setFont(QFont("Malgun Gothic", tab_font_pt, QFont.Weight.Bold))
        self.category_tabs.setStyleSheet(
            f"QTabBar::tab {{ padding: {tab_pad}; margin-right: 2px; background: #e2e8f0; color: #334155; border-top-left-radius: 6px; border-top-right-radius: 6px; }}"
            "QTabBar::tab:selected { background: #1d4ed8; color: white; }"
        )

        for cat_id, profile in CATEGORY_PROFILES.items():
            panel = CategoryWorkspacePanel(
                profile=profile,
                visa_mgr=self.visa_mgr,
                manuals_base_dir=self.manuals_dir,
                data_export_dir=self.data_export_dir,
                parent=self,
            )
            panel.status_message_signal.connect(self._show_status_message)
            panel.io_updated_signal.connect(self._refresh_io_console)
            self.category_panels[cat_id] = panel
            self.category_tabs.addTab(panel, f"{profile.icon_text} {profile.folder_name}")

        self.category_tabs.currentChanged.connect(self._on_category_tab_changed)
        self.v_splitter.addWidget(self.category_tabs)

        # =====================================================================
        # BOTTOM CONSOLE: TekVISA OpenChoice Talker/Listener & Live SCPI/TSP Log
        # =====================================================================
        console_frame = QFrame()
        console_frame.setStyleSheet(
            "QFrame { background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; }"
        )
        con_layout = QVBoxLayout(console_frame)
        con_layout.setContentsMargins(6, 4, 6, 4)
        con_layout.setSpacing(3)

        cmd_bar = QHBoxLayout()
        cmd_bar.setSpacing(5)
        lbl_tl = QLabel("💬 TekVISA Talker/Listener 명령 전송 & 통신 로그:")
        lbl_tl.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        cmd_bar.addWidget(lbl_tl)

        self.txt_direct_cmd = QLineEdit("*IDN?")
        self.txt_direct_cmd.setPlaceholderText("SCPI 또는 TSP 명령어 입력 (예: *IDN?, :MEAS:VOLT?, print(smua.measure.v()))")
        self.txt_direct_cmd.setMinimumWidth(140)
        cmd_bar.addWidget(self.txt_direct_cmd, 1)

        btn_write = QPushButton("📤 Write")
        btn_write.clicked.connect(self._direct_write)
        cmd_bar.addWidget(btn_write)

        btn_query = QPushButton("🔄 Query (송수신)")
        btn_query.setStyleSheet("background-color: #0f766e; color: white; font-weight: bold; padding: 3px 8px;")
        btn_query.clicked.connect(self._direct_query)
        cmd_bar.addWidget(btn_query)

        btn_read = QPushButton("📥 Read")
        btn_read.clicked.connect(self._direct_read)
        cmd_bar.addWidget(btn_read)

        btn_clear_log = QPushButton("🧹 로그 지우기")
        btn_clear_log.clicked.connect(self._clear_io_console)
        cmd_bar.addWidget(btn_clear_log)

        self.btn_toggle_log = QPushButton("🔽 로그 표 접기")
        self.btn_toggle_log.setCheckable(True)
        self.btn_toggle_log.setChecked(True)
        self.btn_toggle_log.toggled.connect(self._on_toggle_io_table)
        cmd_bar.addWidget(self.btn_toggle_log)

        con_layout.addLayout(cmd_bar)

        self._last_io_count: int = 0
        self.io_table = QTableWidget(0, 5)
        self.io_table.setHorizontalHeaderLabels(["시각 (Time)", "구분 (Dir)", "리소스 (Resource)", "전송 명령 (Command)", "수신 응답 (Response & Latency)"])
        h_io = self.io_table.horizontalHeader()
        if h_io is not None:
            h_io.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            h_io.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            h_io.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            h_io.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            h_io.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            self.io_table.setColumnWidth(0, 100)
            self.io_table.setColumnWidth(1, 75)
            self.io_table.setColumnWidth(2, 260)
        v_io = self.io_table.verticalHeader()
        if v_io is not None:
            v_io.setVisible(False)
            v_io.setDefaultSectionSize(22)
        self.io_table.setMinimumHeight(60)
        con_layout.addWidget(self.io_table)

        self.v_splitter.addWidget(console_frame)
        self.v_splitter.setStretchFactor(0, 5)
        self.v_splitter.setStretchFactor(1, 1)
        root_layout.addWidget(self.v_splitter, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._show_status_message("Tektronix QuickStart 준비 완료. 상단에서 장비 폴더 탭(01. AFGs ~ 07. Tek VISA)을 선택하세요.")

    def minimumSizeHint(self) -> QSize:
        return QSize(800, 520)

    def optimize_layout_for_screen(self):
        """Re-applies screen-adaptive geometry and recalculates all splitter proportions."""
        avail = get_available_screen_geometry(self)
        if not self.isMaximized():
            self._apply_screen_adaptive_geometry()
        self._sync_main_splitters()
        for panel in self.category_panels.values():
            panel.sync_splitter_proportions()
        self._show_status_message(
            f"현재 모니터 작업 영역 해상도({avail.width()}×{avail.height()})에 맞춰 화면 레이아웃이 최적화되었습니다."
        )

    def _sync_main_splitters(self):
        h = self.v_splitter.height() or self.height()
        if h > 250:
            if not self.btn_toggle_log.isChecked():
                self.v_splitter.setSizes([max(400, h - 42), 42])
            else:
                bot = max(100, int(h * (0.18 if self.is_compact_screen else 0.22)))
                self.v_splitter.setSizes([max(320, h - bot), bot])

    def _on_toggle_io_table(self, checked: bool):
        self.io_table.setVisible(checked)
        self.btn_toggle_log.setText("🔽 로그 표 접기" if checked else "🔼 로그 표 펼치기")
        self._sync_main_splitters()

    def showEvent(self, a0: Optional[QShowEvent]):
        super().showEvent(a0)
        if not self._initial_splitter_sized:
            self._initial_splitter_sized = True
            QTimer.singleShot(0, self.optimize_layout_for_screen)

    def resizeEvent(self, a0: Optional[QResizeEvent]):
        super().resizeEvent(a0)
        if not self._initial_splitter_sized and self.height() > 300:
            self._initial_splitter_sized = True
            self._sync_main_splitters()

    def show_startup_readiness_dialog(self):
        cur_w = self.category_tabs.currentWidget()
        cur_panel: Optional[CategoryWorkspacePanel] = cur_w if isinstance(cur_w, CategoryWorkspacePanel) else None
        init_cat = cur_panel.profile.folder_id if cur_panel is not None else "01_AFG"
        init_mod = cur_panel.get_current_model().model_id if cur_panel is not None else ""

        dlg = StartupReadinessDialog(
            self.visa_mgr,
            CATEGORY_PROFILES,
            initial_category_id=init_cat,
            initial_model_id=init_mod,
            manuals_base_dir=self.manuals_dir,
            parent=self,
        )
        if dlg.exec() == StartupReadinessDialog.DialogCode.Accepted:
            if dlg.selected_resource:
                self.cmb_visa_resource.setCurrentText(dlg.selected_resource)
            self.chk_sim_mode.setChecked(dlg.use_simulation)

            # Switch to the selected category tab and model automatically
            target_cat = dlg.selected_category_id
            target_mod = dlg.selected_model_id
            if target_cat in self.category_panels:
                target_panel = self.category_panels[target_cat]
                idx_tab = self.category_tabs.indexOf(target_panel)
                if idx_tab >= 0:
                    self.category_tabs.setCurrentIndex(idx_tab)
                idx_m = target_panel.cmb_model.findData(target_mod)
                if idx_m >= 0:
                    target_panel.cmb_model.setCurrentIndex(idx_m)
                target_panel.apply_checked_map(dlg.get_checked_map())

            self._connect_from_bar()

    def _scan_visa_resources(self):
        cur = self.cmb_visa_resource.currentText()
        self.cmb_visa_resource.clear()
        res_list = self.visa_mgr.scan_resources()
        self.cmb_visa_resource.addItems(res_list)
        if cur:
            self.cmb_visa_resource.setCurrentText(cur)
        self._show_status_message(f"VISA 리소스 검색 완료: {len(res_list)}개 리소스 발견")

    def _connect_from_bar(self):
        res = self.cmb_visa_resource.currentText().strip()
        sim = self.chk_sim_mode.isChecked() or res.startswith("SIM::")
        cur_w = self.category_tabs.currentWidget()
        cur_panel: Optional[CategoryWorkspacePanel] = cur_w if isinstance(cur_w, CategoryWorkspacePanel) else None
        cat_id = cur_panel.profile.folder_id if cur_panel is not None else "01_AFG"
        mod_id = cur_panel.get_current_model().model_id if cur_panel is not None else "AFG31000"

        ok, msg = self.visa_mgr.connect(res, simulation=sim, category_id=cat_id, model_id=mod_id)
        short_msg = msg if len(msg) <= 44 else (msg[:42] + "...")
        self.lbl_conn_status.setToolTip(msg)
        if ok:
            self.lbl_conn_status.setText(f"✅ {short_msg}")
            self.lbl_conn_status.setStyleSheet("color: #4ade80; font-weight: bold; padding-left: 4px;")
        else:
            self.lbl_conn_status.setText(f"❌ {short_msg}")
            self.lbl_conn_status.setStyleSheet("color: #f87171; font-weight: bold; padding-left: 4px;")
        self._refresh_io_console()

    def _on_category_tab_changed(self, idx: int):
        w = self.category_tabs.widget(idx)
        if isinstance(w, CategoryWorkspacePanel):
            model = w.get_current_model()
            self.visa_mgr.set_category_model(w.profile.folder_id, model.model_id)
            self._show_status_message(f"[{w.profile.title_ko}] 모듈로 전환되었습니다. (현재 모델: {model.display_name})")

    def emergency_stop_all(self):
        for panel in self.category_panels.values():
            if panel.state in (panel.STATE_RUNNING, panel.STATE_PAUSED):
                panel.on_stop_clicked()
        self._show_status_message("🚨 모든 장비의 측정 루프가 중단되었으며 출력이 안전하게 OFF 되었습니다.")

    def _direct_write(self):
        cmd = self.txt_direct_cmd.text().strip()
        if not cmd:
            return
        try:
            self.visa_mgr.write(cmd)
            self._refresh_io_console()
        except Exception as e:
            QMessageBox.critical(self, "Write 오류", str(e))

    def _direct_query(self):
        cmd = self.txt_direct_cmd.text().strip()
        if not cmd:
            return
        try:
            resp, dt = self.visa_mgr.query(cmd)
            self._refresh_io_console()
            self._show_status_message(f"Query 응답 ({dt:.1f} ms): {resp}")
        except Exception as e:
            QMessageBox.critical(self, "Query 오류", str(e))

    def _direct_read(self):
        try:
            resp, dt = self.visa_mgr.read()
            self._refresh_io_console()
            self._show_status_message(f"Read 응답 ({dt:.1f} ms): {resp}")
        except Exception as e:
            QMessageBox.critical(self, "Read 오류", str(e))

    def _clear_io_console(self):
        self.visa_mgr.transcript.clear()
        self._last_io_count = 0
        self.io_table.setRowCount(0)

    def _refresh_io_console(self):
        total = self.visa_mgr.total_logged_count
        entries = self.visa_mgr.transcript
        if not entries:
            self._last_io_count = 0
            self.io_table.setRowCount(0)
            return

        new_cnt = total - self._last_io_count
        if new_cnt <= 0:
            return

        max_rows = 80
        self.io_table.setUpdatesEnabled(False)
        try:
            # Fast incremental append when only a few entries were added
            if 0 < new_cnt <= 20 and self.io_table.rowCount() > 0:
                to_add = entries[-new_cnt:]
                for e in to_add:
                    if self.io_table.rowCount() >= max_rows:
                        self.io_table.removeRow(0)
                    r = self.io_table.rowCount()
                    self.io_table.insertRow(r)
                    self._set_io_row(r, e)
            else:
                tail = entries[-max_rows:]
                self.io_table.setRowCount(len(tail))
                for r, e in enumerate(tail):
                    self._set_io_row(r, e)
            self._last_io_count = total
        finally:
            self.io_table.setUpdatesEnabled(True)
        self.io_table.scrollToBottom()

    def _set_io_row(self, r: int, e) -> None:
        self.io_table.setItem(r, 0, QTableWidgetItem(e.timestamp))
        dir_item = QTableWidgetItem(e.direction)
        if e.direction == "ERROR":
            dir_item.setForeground(QColor("#dc2626"))
        elif e.direction == "QUERY":
            dir_item.setForeground(QColor("#0284c7"))
        elif e.direction == "WRITE":
            dir_item.setForeground(QColor("#16a34a"))
        self.io_table.setItem(r, 1, dir_item)
        self.io_table.setItem(r, 2, QTableWidgetItem(e.resource))
        self.io_table.setItem(r, 3, QTableWidgetItem(e.command))
        self.io_table.setItem(r, 4, QTableWidgetItem(f"{e.response} ({e.latency_ms} ms)"))

    def _show_status_message(self, msg: str):
        self.status_bar.showMessage(msg)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    avail = get_available_screen_geometry()
    base_font_pt = 8 if (avail.height() <= 800 or avail.width() <= 1366) else 9
    app.setFont(QFont("Malgun Gothic", base_font_pt))
    is_self_test = "--self-test" in sys.argv
    skip_startup = ("--no-startup-dialog" in sys.argv) or is_self_test
    win = TekQuickStartMainWindow(skip_startup_dialog=skip_startup)
    win.show_adaptive()
    if is_self_test:
        if len(win.category_panels) != len(CATEGORY_PROFILES):
            sys.exit(2)
        QTimer.singleShot(350, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
