# -*- coding: utf-8 -*-
"""
SAITEK Tektronix Quick Start SW - Category Workspace Panel
Implements the 4 core user requirements per manual folder:
1. Folder-specific instrument model selection & manual reference
2. Explicit separation of [Required Input Parameters] vs [Measurable Items] with pre-start user confirmation
3. Measurement Start (▶) / Pause & Resume (⏸) / Complete Stop (⏹) / Real-Time Graph (pyqtgraph) / Excel Export (.xlsx)
4. Remote Readiness Checklist & Live Instrument Status Verification (*IDN?, *LANG?, login?, remote?, Error Queue)
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional, Set
import numpy as np

# Ensure sibling 02.src subdirectories are on sys.path for standalone execution & IDE analysis
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _SRC_DIR = os.path.join(_BASE_DIR, "02.src")
    for _sub in ("01.Core", "02.Modules", "03.Drivers", "04.Utils", "05.Config", "06.Main"):
        _p = os.path.join(_SRC_DIR, _sub)
        if _p not in sys.path:
            sys.path.insert(0, _p)

from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QDoubleSpinBox,
    QSpinBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QScrollArea,
    QFrame,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QSizePolicy,
)
from PyQt6.QtWidgets import QInputDialog, QMenu
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QSize, QPoint
from PyQt6.QtGui import QFont, QDesktopServices, QResizeEvent, QShowEvent, QCloseEvent

import pyqtgraph as pg

from instrument_profiles import CategoryProfile, ModelProfile, InputParameterSpec
from instrument_drivers import create_driver_for_category, BaseCategoryDriver, MeasurementResult, OscilloscopeDriver
from excel_exporter import export_session_to_excel
from dialogs import PreStartConfirmDialog, ChecklistStepCard, get_available_screen_geometry, fit_and_center_window
from run_history import (
    RunRecord,
    RunHistoryStore,
    RunHistoryTab,
    GraphCursorBar,
    draw_run,
    clear_data_items,
)


class DetachablePaneDialog(QDialog):
    """
    Floating top-level window that hosts either the Real-Time Graph or the Measured Data Table
    so the user can move it to another monitor or maximize it on a large screen.
    Closing the window automatically docks the widget back into the main workspace splitter.
    """

    def __init__(self, title: str, dock_callback, parent: Any = None):
        super().__init__(parent)
        self._dock_callback = dock_callback
        self._is_redocking = False
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        fit_and_center_window(self, target_w_ratio=0.78, target_h_ratio=0.78, min_w=760, min_h=480, max_w=2200, max_h=1350)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 8)
        self.main_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        lbl_info = QLabel(f"🗗 <b>{title}</b> &nbsp;<span style='color:#64748b; font-size:8.5pt;'>(이 창을 다른 모니터로 이동하거나 최대화하여 크게 볼 수 있습니다. 창을 닫으면 원래 화면으로 복귀합니다.)</span>")
        lbl_info.setWordWrap(True)
        top_bar.addWidget(lbl_info, 1)

        self.btn_redock = QPushButton("↙ 원래 화면으로 복귀 (Dock)")
        self.btn_redock.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 5px 12px; border-radius: 4px;"
        )
        self.btn_redock.clicked.connect(self.close)
        top_bar.addWidget(self.btn_redock)
        self.main_layout.addLayout(top_bar)

        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(4)
        self.main_layout.addWidget(self.body_container, 1)

    def closeEvent(self, a0: Optional[QCloseEvent]):
        if not self._is_redocking:
            self._is_redocking = True
            self._dock_callback()
        super().closeEvent(a0)


class CategoryWorkspacePanel(QWidget):
    status_message_signal = pyqtSignal(str, arguments=["msg"])
    io_updated_signal = pyqtSignal(arguments=[])

    STATE_IDLE = "IDLE"
    STATE_RUNNING = "RUNNING"
    STATE_PAUSED = "PAUSED"
    STATE_STOPPED = "STOPPED"

    def __init__(
        self,
        profile: CategoryProfile,
        visa_mgr,
        manuals_base_dir: str,
        data_export_dir: str,
        parent: Any = None,
    ):
        super().__init__(parent)
        self.profile = profile
        self.visa_mgr = visa_mgr
        self.manuals_base_dir = manuals_base_dir
        self.data_export_dir = data_export_dir

        self.state = self.STATE_IDLE
        self.driver: Optional[BaseCategoryDriver] = None
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._on_measurement_tick)
        self._last_tick_start: float = 0.0

        # Widget registries
        self.checklist_widgets: Dict[str, QCheckBox] = {}
        self.checklist_cards: Dict[str, ChecklistStepCard] = {}
        self.input_widgets: Dict[str, QWidget] = {}
        self.measurable_widgets: Dict[str, QCheckBox] = {}
        self.live_value_labels: Dict[str, QLabel] = {}

        # Run history (KickStart-style): every measurement is kept as a RunRecord
        self.history_store = RunHistoryStore()
        self.live_run: RunRecord = self._make_scratch_run()
        self.column_aliases: Dict[str, str] = {}
        self.hidden_columns: Set[str] = set()
        self._table_headers: List[str] = []
        self._initial_splitters_applied: bool = False
        self.graph_float_dialog: Optional[DetachablePaneDialog] = None
        self.table_float_dialog: Optional[DetachablePaneDialog] = None

        self._build_ui()
        self._on_model_changed(0)

    # ---- live run data (backed by the current RunRecord) ----------------------
    @property
    def measured_rows(self) -> List[Dict[str, Any]]:
        return self.live_run.rows

    @property
    def time_history(self) -> List[float]:
        return self.live_run.time_history

    @property
    def xy_x_history(self) -> List[float]:
        return self.live_run.xy_x_history

    @property
    def series_history(self) -> Dict[str, List[float]]:
        return self.live_run.series_history

    @property
    def last_waveform_x(self) -> Optional[np.ndarray]:
        return self.live_run.waveform_x

    @last_waveform_x.setter
    def last_waveform_x(self, value: Optional[np.ndarray]) -> None:
        self.live_run.waveform_x = value

    @property
    def last_waveform_y(self) -> Optional[np.ndarray]:
        return self.live_run.waveform_y

    @last_waveform_y.setter
    def last_waveform_y(self, value: Optional[np.ndarray]) -> None:
        self.live_run.waveform_y = value

    @property
    def last_wfm_x_label(self) -> str:
        return self.live_run.wfm_x_label

    @last_wfm_x_label.setter
    def last_wfm_x_label(self, value: str) -> None:
        self.live_run.wfm_x_label = value

    @property
    def last_wfm_y_label(self) -> str:
        return self.live_run.wfm_y_label

    @last_wfm_y_label.setter
    def last_wfm_y_label(self, value: str) -> None:
        self.live_run.wfm_y_label = value

    def _make_scratch_run(self) -> RunRecord:
        """An unregistered, empty run used as the 'current screen' before/after a measurement."""
        return RunRecord(run_id=0, folder_id=self.profile.folder_id, category_title=self.profile.title_ko)

    def _build_ui(self):
        avail = get_available_screen_geometry(self)
        self.is_compact_screen = avail.height() <= 920 or avail.width() <= 1550
        margin = 4 if self.is_compact_screen else 8
        spacing = 4 if self.is_compact_screen else 8

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(spacing)

        # =====================================================================
        # TOP BAR: Model Selector, Manual PDF Link & Requirement 4 Remote Check
        # =====================================================================
        top_frame = QFrame()
        top_frame.setStyleSheet(
            "QFrame { background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; }"
        )
        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(8, 5 if self.is_compact_screen else 8, 8, 5 if self.is_compact_screen else 8)
        top_layout.setSpacing(4 if self.is_compact_screen else 6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        lbl_cat = QLabel(f"{self.profile.icon_text}  {self.profile.title_ko}")
        lbl_cat.setFont(QFont("Malgun Gothic", 10 if self.is_compact_screen else 11, QFont.Weight.Bold))
        lbl_cat.setStyleSheet("color: #0f172a; border: none;")
        lbl_cat.setMinimumWidth(120)
        lbl_cat.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        row1.addWidget(lbl_cat)

        row1.addSpacing(4)
        lbl_mod = QLabel("모델:")
        lbl_mod.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        lbl_mod.setStyleSheet("border: none;")
        row1.addWidget(lbl_mod)

        self.cmb_model = QComboBox()
        self.cmb_model.setMinimumWidth(140)
        self.cmb_model.setMaximumWidth(420)
        self.cmb_model.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        for m in self.profile.models:
            self.cmb_model.addItem(f"{m.display_name} [{m.protocol}]", m.model_id)
        self.cmb_model.currentIndexChanged.connect(self._on_model_changed)
        row1.addWidget(self.cmb_model, 1)

        btn_pad = "4px 8px" if self.is_compact_screen else "5px 10px"
        self.btn_open_manual = QPushButton("📖 PDF 매뉴얼")
        self.btn_open_manual.setToolTip("현재 선택된 장비 모델의 공식 프로그래머/레퍼런스 PDF 매뉴얼을 엽니다.")
        self.btn_open_manual.setStyleSheet(
            f"background-color: #334155; color: white; font-weight: bold; padding: {btn_pad}; border-radius: 4px;"
        )
        self.btn_open_manual.clicked.connect(self._open_current_manual_pdf)
        row1.addWidget(self.btn_open_manual)

        self.btn_verify_status = QPushButton("🔍 상태 확인 (*IDN?)")
        self.btn_verify_status.setToolTip("장비 리모트 상태(*IDN?, *LANG?, login?, remote?, Error Queue)를 즉시 진단합니다.")
        self.btn_verify_status.setStyleSheet(
            f"background-color: #0284c7; color: white; font-weight: bold; padding: {btn_pad}; border-radius: 4px;"
        )
        self.btn_verify_status.clicked.connect(self._run_live_status_check)
        row1.addWidget(self.btn_verify_status)

        self.btn_toggle_chk = QPushButton("☑ 체크리스트 접기 ▲")
        self.btn_toggle_chk.setCheckable(True)
        self.btn_toggle_chk.setChecked(True)
        self.btn_toggle_chk.setStyleSheet(
            f"background-color: #e0f2fe; color: #0369a1; font-weight: bold; padding: {btn_pad}; border: 1px solid #7dd3fc; border-radius: 4px;"
        )
        self.btn_toggle_chk.toggled.connect(self._on_toggle_checklist)
        row1.addWidget(self.btn_toggle_chk)

        top_layout.addLayout(row1)

        # Model specification & remote notes bar
        self.lbl_model_specs = QLabel("")
        self.lbl_model_specs.setStyleSheet(
            f"color: #334155; font-size: {'8.5pt' if self.is_compact_screen else '9pt'}; border: none;"
        )
        self.lbl_model_specs.setWordWrap(True)
        self.lbl_model_specs.setMinimumWidth(100)
        self.lbl_model_specs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        top_layout.addWidget(self.lbl_model_specs)

        # Requirement 4: Remote Readiness Checklist Group inside a compact scroll area
        self.chk_group = QGroupBox("요구사항 4: 초보자용 단계별 리모트 준비 사항 점검표 (각 항목별 [📘 가이드] 및 [🔍 개별 상태 확인] 가능)")
        self.chk_group.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        self.chk_group.setStyleSheet("QGroupBox { color: #0369a1; }")
        chk_outer_layout = QVBoxLayout(self.chk_group)
        chk_outer_layout.setContentsMargins(6, 4, 6, 4)
        chk_outer_layout.setSpacing(4)

        chk_scroll = QScrollArea()
        chk_scroll.setWidgetResizable(True)
        chk_scroll.setFrameShape(QFrame.Shape.NoFrame)
        chk_scroll.setMaximumHeight(115 if self.is_compact_screen else 155)
        chk_container = QWidget()
        chk_grid = QGridLayout(chk_container)
        chk_grid.setContentsMargins(2, 2, 2, 2)
        chk_grid.setSpacing(6)

        cols = 1 if avail.width() < 1400 else 2
        for idx, item in enumerate(self.profile.checklist):
            card = ChecklistStepCard(
                item_spec=item,
                verify_callback=self._verify_single_checklist_item,
                compact=True,
                parent=chk_container,
            )
            self.checklist_cards[item.id] = card
            self.checklist_widgets[item.id] = card.checkbox
            chk_grid.addWidget(card, idx // cols, idx % cols)

        chk_scroll.setWidget(chk_container)
        chk_outer_layout.addWidget(chk_scroll)
        top_layout.addWidget(self.chk_group)

        # On very low vertical resolution (e.g. <= 780px logical height), auto-collapse checklist by default
        if avail.height() <= 780:
            self.btn_toggle_chk.setChecked(False)

        main_layout.addWidget(top_frame)

        # =====================================================================
        # MIDDLE SPLITTER:
        # Left: [1. Required Input Parameters]
        # Center: [2. Measurable Items & Live Readouts]
        # Right: [3. Real-Time Graph & Data Table]
        # =====================================================================
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)

        grp_font_size = 9 if self.is_compact_screen else 10

        # --- LEFT PANE: Required Input Parameters (입력이 필요한 사항) ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(200)
        left_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        grp_inputs = QGroupBox("1. 입력이 필요한 사항 (Required Input Parameters)")
        grp_inputs.setFont(QFont("Malgun Gothic", grp_font_size, QFont.Weight.Bold))
        grp_inputs.setStyleSheet(
            "QGroupBox { border: 2px solid #2563eb; border-radius: 6px; margin-top: 8px; padding-top: 8px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #1d4ed8; }"
        )
        in_vbox = QVBoxLayout(grp_inputs)
        in_vbox.setContentsMargins(6, 6, 6, 6)
        in_vbox.setSpacing(4)

        scroll_in = QScrollArea()
        scroll_in.setWidgetResizable(True)
        scroll_in.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_in.setFrameShape(QFrame.Shape.NoFrame)
        in_content = QWidget()
        in_content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        in_form_layout = QVBoxLayout(in_content)
        in_form_layout.setContentsMargins(2, 2, 4, 2)
        in_form_layout.setSpacing(6)

        # Group input parameters by 'group' attribute
        grouped_specs: Dict[str, List[InputParameterSpec]] = {}
        for spec in self.profile.input_parameters:
            grouped_specs.setdefault(spec.group, []).append(spec)

        for grp_title, specs in grouped_specs.items():
            sub_grp = QGroupBox(grp_title)
            sub_grp.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
            sub_grp.setStyleSheet("QGroupBox { border: 1px solid #cbd5e1; border-radius: 4px; margin-top: 6px; }")
            grid = QGridLayout(sub_grp)
            grid.setContentsMargins(6, 8, 6, 6)
            grid.setSpacing(5)
            grid.setColumnStretch(0, 5)
            grid.setColumnStretch(1, 6)
            for r_idx, spec in enumerate(specs):
                lbl = QLabel(spec.label + (f" ({spec.unit})" if spec.unit else ""))
                lbl.setFont(QFont("Malgun Gothic", 8 if self.is_compact_screen else 9))
                lbl.setWordWrap(True)
                lbl.setMinimumWidth(60)
                lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                lbl.setToolTip(spec.tooltip)
                w = self._create_input_widget(spec)
                w.setToolTip(spec.tooltip)
                self.input_widgets[spec.key] = w
                grid.addWidget(lbl, r_idx, 0)
                grid.addWidget(w, r_idx, 1)
            in_form_layout.addWidget(sub_grp)

        in_form_layout.addStretch()
        scroll_in.setWidget(in_content)
        in_vbox.addWidget(scroll_in)

        btn_reset_in = QPushButton("↺ 입력값 매뉴얼 기본값(Default) 초기화")
        btn_reset_in.clicked.connect(self._reset_inputs_to_default)
        in_vbox.addWidget(btn_reset_in)

        left_layout.addWidget(grp_inputs)
        self.main_splitter.addWidget(left_widget)

        # --- CENTER PANE: Measurable Items (측정이 가능한 부분) ---
        center_widget = QWidget()
        center_widget.setMinimumWidth(210)
        center_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        grp_meas = QGroupBox("2. 측정이 가능한 부분 (Measurable Items & Live Readouts)")
        grp_meas.setFont(QFont("Malgun Gothic", grp_font_size, QFont.Weight.Bold))
        grp_meas.setStyleSheet(
            "QGroupBox { border: 2px solid #059669; border-radius: 6px; margin-top: 8px; padding-top: 8px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #047857; }"
        )
        meas_vbox = QVBoxLayout(grp_meas)
        meas_vbox.setContentsMargins(6, 6, 6, 6)
        meas_vbox.setSpacing(4)

        sel_btn_row = QHBoxLayout()
        btn_all_m = QPushButton("☑ 전체 측정 선택")
        btn_all_m.clicked.connect(lambda: [cb.setChecked(True) for cb in self.measurable_widgets.values()])
        btn_none_m = QPushButton("☐ 전체 해제")
        btn_none_m.clicked.connect(lambda: [cb.setChecked(False) for cb in self.measurable_widgets.values()])
        sel_btn_row.addWidget(btn_all_m)
        sel_btn_row.addWidget(btn_none_m)
        sel_btn_row.addStretch()
        meas_vbox.addLayout(sel_btn_row)

        scroll_m = QScrollArea()
        scroll_m.setWidgetResizable(True)
        scroll_m.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_m.setFrameShape(QFrame.Shape.NoFrame)
        m_content = QWidget()
        m_content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        m_vbox_inner = QVBoxLayout(m_content)
        m_vbox_inner.setContentsMargins(2, 2, 4, 2)
        m_vbox_inner.setSpacing(6)

        for m_spec in self.profile.measurable_items:
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 5px; padding: 3px; }"
            )
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(5, 3, 5, 3)
            c_layout.setSpacing(2)

            top_r = QHBoxLayout()
            cb = QCheckBox(f"{m_spec.label}")
            cb.setChecked(m_spec.default_checked)
            cb.setFont(QFont("Malgun Gothic", 8 if self.is_compact_screen else 9, QFont.Weight.Bold))
            cb.setMinimumWidth(60)
            cb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            cb.setToolTip(f"{m_spec.description}\n명령어: {m_spec.scpi_or_tsp_hint}")
            self.measurable_widgets[m_spec.key] = cb
            top_r.addWidget(cb, 1)

            val_lbl = QLabel("--- " + m_spec.unit)
            val_lbl.setFont(QFont("Consolas", 10 if self.is_compact_screen else 11, QFont.Weight.Bold))
            val_lbl.setStyleSheet("color: #0f766e; background-color: #f0fdf4; padding: 2px 6px; border-radius: 4px;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.live_value_labels[m_spec.key] = val_lbl
            top_r.addWidget(val_lbl)
            c_layout.addLayout(top_r)

            cmd_lbl = QLabel(f"SCPI/TSP: {m_spec.scpi_or_tsp_hint}  |  {m_spec.description}")
            cmd_lbl.setStyleSheet("color: #64748b; font-size: 8pt; border: none;")
            cmd_lbl.setWordWrap(True)
            cmd_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            c_layout.addWidget(cmd_lbl)

            m_vbox_inner.addWidget(card)

        # Remote notes from manual for selected model (placed inside scroll area so it never clips measurable items)
        self.grp_notes = QGroupBox("📌 선택된 장비 매뉴얼 리모트 주의사항")
        self.grp_notes.setFont(QFont("Malgun Gothic", 8 if self.is_compact_screen else 9, QFont.Weight.Bold))
        notes_l = QVBoxLayout(self.grp_notes)
        notes_l.setContentsMargins(6, 6, 6, 6)
        self.lbl_remote_notes = QLabel("")
        self.lbl_remote_notes.setWordWrap(True)
        self.lbl_remote_notes.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_remote_notes.setStyleSheet("color: #334155; font-size: 8.5pt;")
        notes_l.addWidget(self.lbl_remote_notes)
        m_vbox_inner.addWidget(self.grp_notes)

        m_vbox_inner.addStretch()
        scroll_m.setWidget(m_content)
        meas_vbox.addWidget(scroll_m)

        center_layout.addWidget(grp_meas)
        self.main_splitter.addWidget(center_widget)

        # --- RIGHT PANE: Requirement 3 (Controls, Real-Time Graph, Data Table, Excel Export) ---
        right_widget = QWidget()
        right_widget.setMinimumWidth(280)
        right_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grp_ctrl = QGroupBox("3. 측정 제어 / 실시간 그래프 표현 / 데이터 저장 (Excel)")
        grp_ctrl.setFont(QFont("Malgun Gothic", grp_font_size, QFont.Weight.Bold))
        grp_ctrl.setStyleSheet(
            "QGroupBox { border: 2px solid #7c3aed; border-radius: 6px; margin-top: 8px; padding-top: 8px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #6d28d9; }"
        )
        r_vbox = QVBoxLayout(grp_ctrl)
        r_vbox.setContentsMargins(6, 6, 6, 6)
        r_vbox.setSpacing(5)

        # Control Bar: Start / Pause / Stop / Clear / Excel Save (compact responsive buttons)
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(4)
        ctrl_font = QFont("Malgun Gothic", 9 if self.is_compact_screen else 10, QFont.Weight.Bold)
        ctrl_pad = "6px 10px" if self.is_compact_screen else "7px 12px"

        self.btn_start = QPushButton("▶ 측정 시작")
        self.btn_start.setToolTip("입력 파라미터와 측정 항목을 확인한 후 측정을 시작합니다 (Start)")
        self.btn_start.setFont(ctrl_font)
        self.btn_start.setStyleSheet(
            f"QPushButton {{ background-color: #16a34a; color: white; padding: {ctrl_pad}; border-radius: 5px; }}"
            "QPushButton:disabled { background-color: #94a3b8; }"
        )
        self.btn_start.clicked.connect(self.on_start_clicked)
        ctrl_bar.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸ 일시정지")
        self.btn_pause.setToolTip("측정을 일시정지하거나 재개합니다 (Pause / Resume)")
        self.btn_pause.setFont(ctrl_font)
        self.btn_pause.setStyleSheet(
            f"QPushButton {{ background-color: #d97706; color: white; padding: {ctrl_pad}; border-radius: 5px; }}"
            "QPushButton:disabled { background-color: #94a3b8; }"
        )
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.on_pause_clicked)
        ctrl_bar.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ 완전 정지 (OFF)")
        self.btn_stop.setToolTip("측정 루프를 완전히 정지하고 장비 출력을 안전하게 OFF 합니다 (Complete Stop)")
        self.btn_stop.setFont(ctrl_font)
        self.btn_stop.setStyleSheet(
            f"QPushButton {{ background-color: #dc2626; color: white; padding: {ctrl_pad}; border-radius: 5px; }}"
            "QPushButton:disabled { background-color: #94a3b8; }"
        )
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        ctrl_bar.addWidget(self.btn_stop)

        self.btn_clear = QPushButton("🗑 초기화")
        self.btn_clear.setToolTip("누적된 그래프 및 테이블 측정 데이터를 초기화합니다")
        self.btn_clear.setStyleSheet(f"padding: {ctrl_pad};")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        ctrl_bar.addWidget(self.btn_clear)

        self.btn_excel = QPushButton("💾 Excel 저장 (.xlsx)")
        self.btn_excel.setToolTip("측정 데이터, 통계, 설정값 및 파형을 Excel (.xlsx) 파일로 저장합니다")
        self.btn_excel.setFont(ctrl_font)
        self.btn_excel.setStyleSheet(
            f"background-color: #0f766e; color: white; padding: {ctrl_pad}; border-radius: 5px;"
        )
        self.btn_excel.clicked.connect(self.on_export_excel_clicked)
        ctrl_bar.addWidget(self.btn_excel)

        r_vbox.addLayout(ctrl_bar)

        # Status badge & Graph mode selector
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.lbl_state_badge = QLabel("● 상태: 대기 중 (IDLE)")
        self.lbl_state_badge.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        self.lbl_state_badge.setStyleSheet(
            "background-color: #e2e8f0; color: #334155; padding: 3px 8px; border-radius: 4px;"
        )
        status_row.addWidget(self.lbl_state_badge)

        self.lbl_sample_count = QLabel("누적 샘플: 0 pts")
        self.lbl_sample_count.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        status_row.addWidget(self.lbl_sample_count)

        self.btn_export_opts = QPushButton("📤 내보내기 옵션")
        self.btn_export_opts.setToolTip(
            "표(Excel/CSV)와 그래프(PNG)를 선택하여 현재/선택/전체 Run을 내보냅니다.\n"
            "※ 자동 내보내기는 [📜 실행 이력] 탭에서 설정합니다."
        )
        self.btn_export_opts.setStyleSheet("padding: 2px 8px; font-size: 8.5pt;")
        self.btn_export_opts.clicked.connect(self.on_export_options_clicked)
        status_row.addWidget(self.btn_export_opts)

        status_row.addStretch()
        status_row.addWidget(QLabel("그래프 모드:"))
        self.cmb_graph_mode = QComboBox()
        self.cmb_graph_mode.setMinimumWidth(140)
        self.cmb_graph_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_graph_mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_graph_mode.addItems(self.profile.graph_modes)
        self.cmb_graph_mode.currentIndexChanged.connect(self._refresh_plots)
        status_row.addWidget(self.cmb_graph_mode, 1)

        self.btn_detach_graph = QPushButton("🗗 그래프 새 창 분리")
        self.btn_detach_graph.setToolTip("실시간 측정 그래프를 별도 창으로 분리하여 다른 모니터나 전체 화면으로 크게 봅니다.")
        self.btn_detach_graph.setStyleSheet(
            "background-color: #eff6ff; color: #1d4ed8; border: 1px solid #93c5fd; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        self.btn_detach_graph.clicked.connect(self.toggle_detach_graph)
        status_row.addWidget(self.btn_detach_graph)

        self.btn_detach_table = QPushButton("🗗 데이터 표 새 창 분리")
        self.btn_detach_table.setToolTip("하단 측정 데이터 테이블을 별도 창으로 분리하여 다른 모니터나 큰 창으로 넓게 봅니다.")
        self.btn_detach_table.setStyleSheet(
            "background-color: #f0fdf4; color: #15803d; border: 1px solid #86efac; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        self.btn_detach_table.clicked.connect(self.toggle_detach_table)
        status_row.addWidget(self.btn_detach_table)

        r_vbox.addLayout(status_row)

        # PyQtGraph Dual Plot Area + Data Table inside a resizable Vertical Splitter
        pg.setConfigOptions(antialias=True)
        self.plot_tabs = QTabWidget()

        plot_container = QWidget()
        p_layout = QVBoxLayout(plot_container)
        p_layout.setContentsMargins(2, 2, 2, 2)

        self.plot_table_splitter = QSplitter(Qt.Orientation.Vertical)
        self.plot_table_splitter.setChildrenCollapsible(False)

        # Slot 0: Graph wrapper (holds cursor_bar + primary_plot or detached placeholder)
        self.graph_slot_widget = QWidget()
        self.graph_slot_layout = QVBoxLayout(self.graph_slot_widget)
        self.graph_slot_layout.setContentsMargins(0, 0, 0, 0)
        self.graph_slot_layout.setSpacing(2)

        self.graph_inner_panel = QWidget()
        g_inner_lay = QVBoxLayout(self.graph_inner_panel)
        g_inner_lay.setContentsMargins(0, 0, 0, 0)
        g_inner_lay.setSpacing(2)

        self.primary_plot = pg.PlotWidget()
        self.primary_plot.setMinimumHeight(130)
        self.primary_plot.setBackground("#0f172a")
        self.primary_plot.showGrid(x=True, y=True, alpha=0.3)
        self.primary_plot.addLegend(offset=(10, 10))
        self.cursor_bar = GraphCursorBar(self.primary_plot)
        btn_inline_pop_g = QPushButton("🗗 그래프 크게 보기 (새 창)")
        btn_inline_pop_g.setToolTip("실시간 그래프를 별도 창으로 분리하거나 원래 화면으로 복귀합니다.")
        btn_inline_pop_g.setStyleSheet(
            "background-color: #dbeafe; color: #1e40af; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        btn_inline_pop_g.clicked.connect(self.toggle_detach_graph)
        self.cursor_bar.layout().itemAt(0).layout().addWidget(btn_inline_pop_g)  # type: ignore[union-attr]

        g_inner_lay.addWidget(self.cursor_bar)
        g_inner_lay.addWidget(self.primary_plot, 1)
        self.graph_slot_layout.addWidget(self.graph_inner_panel)

        self.lbl_graph_detached = QLabel("🗗 실시간 측정 그래프가 별도 창으로 분리되어 표시 중입니다.\n(원래 위치로 되돌리려면 상단 [↙ 그래프 복귀] 버튼을 누르거나 분리된 창을 닫으세요.)")
        self.lbl_graph_detached.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_graph_detached.setStyleSheet(
            "background-color: #f8fafc; color: #475569; border: 1px dashed #94a3b8; border-radius: 6px; padding: 12px; font-size: 9pt;"
        )
        self.lbl_graph_detached.setVisible(False)
        self.graph_slot_layout.addWidget(self.lbl_graph_detached)
        self.plot_table_splitter.addWidget(self.graph_slot_widget)

        # Slot 1: Data Table wrapper (holds data_table or detached placeholder)
        self.table_slot_widget = QWidget()
        self.table_slot_layout = QVBoxLayout(self.table_slot_widget)
        self.table_slot_layout.setContentsMargins(0, 0, 0, 0)
        self.table_slot_layout.setSpacing(2)

        self.table_inner_panel = QWidget()
        t_inner_lay = QVBoxLayout(self.table_inner_panel)
        t_inner_lay.setContentsMargins(0, 0, 0, 0)
        t_inner_lay.setSpacing(2)

        self.data_table = QTableWidget(0, 5)
        self.data_table.setMinimumHeight(80)
        self.data_table.setAlternatingRowColors(True)
        v_dt = self.data_table.verticalHeader()
        if v_dt is not None:
            v_dt.setDefaultSectionSize(22)
        h_dt = self.data_table.horizontalHeader()
        if h_dt is not None:
            h_dt.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            h_dt.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            h_dt.customContextMenuRequested.connect(self._on_header_menu)
            h_dt.setToolTip("컬럼 머리글을 우클릭하면 이름 변경 / 숨기기가 가능합니다.")
        t_inner_lay.addWidget(self.data_table, 1)
        self.table_slot_layout.addWidget(self.table_inner_panel)

        self.lbl_table_detached = QLabel("🗗 측정 데이터 테이블이 별도 창으로 분리되어 표시 중입니다.\n(원래 위치로 되돌리려면 상단 [↙ 데이터 표 복귀] 버튼을 누르거나 분리된 창을 닫으세요.)")
        self.lbl_table_detached.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_table_detached.setStyleSheet(
            "background-color: #f8fafc; color: #475569; border: 1px dashed #94a3b8; border-radius: 6px; padding: 12px; font-size: 9pt;"
        )
        self.lbl_table_detached.setVisible(False)
        self.table_slot_layout.addWidget(self.lbl_table_detached)
        self.plot_table_splitter.addWidget(self.table_slot_widget)

        self.plot_table_splitter.setStretchFactor(0, 3)
        self.plot_table_splitter.setStretchFactor(1, 2)
        p_layout.addWidget(self.plot_table_splitter)

        self.plot_tabs.addTab(plot_container, "📊 실시간 측정 그래프 & 데이터 테이블")

        self.history_tab = RunHistoryTab(
            store=self.history_store,
            title_prefix=self.profile.title_ko,
            default_export_dir=os.path.join(self.data_export_dir, "AutoExport"),
            parent=self,
        )
        self.history_tab.row_transform = self._export_rows_for
        self.history_tab.status_message_signal.connect(self.status_message_signal.emit)
        self.plot_tabs.addTab(self.history_tab, "📜 실행 이력 (Run History) · 비교 · 자동내보내기")
        self.plot_tabs.currentChanged.connect(self._on_plot_tab_changed)
        r_vbox.addWidget(self.plot_tabs, 1)

        right_layout.addWidget(grp_ctrl)
        self.main_splitter.addWidget(right_widget)

        self.main_splitter.setStretchFactor(0, 25)
        self.main_splitter.setStretchFactor(1, 27)
        self.main_splitter.setStretchFactor(2, 48)
        main_layout.addWidget(self.main_splitter, 1)

    def minimumSizeHint(self) -> QSize:
        return QSize(720, 420)

    def _on_toggle_checklist(self, checked: bool):
        self.chk_group.setVisible(checked)
        self.btn_toggle_chk.setText(
            "☑ 체크리스트 접기 ▲" if checked else "☑ 체크리스트 펼치기 ▼"
        )

    # =========================================================================
    # DETACHABLE GRAPH & DATA TABLE WINDOWS (Pop-Out / Redock)
    # =========================================================================
    def toggle_detach_graph(self):
        if self.graph_float_dialog is not None:
            self._redock_graph()
        else:
            self._detach_graph()

    def _detach_graph(self):
        if self.graph_float_dialog is not None:
            self.graph_float_dialog.raise_()
            self.graph_float_dialog.activateWindow()
            return
        dlg = DetachablePaneDialog(
            title=f"{self.profile.title_ko} - 실시간 측정 그래프 (분리된 창)",
            dock_callback=self._redock_graph,
            parent=self.window(),
        )
        self.graph_slot_layout.removeWidget(self.graph_inner_panel)
        dlg.body_layout.addWidget(self.graph_inner_panel)
        self.graph_inner_panel.show()
        self.lbl_graph_detached.setVisible(True)
        self.graph_float_dialog = dlg
        self.btn_detach_graph.setText("↙ 그래프 복귀")
        self.btn_detach_graph.setStyleSheet(
            "background-color: #dbeafe; color: #1e3a8a; border: 1px solid #3b82f6; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        dlg.show()
        self._update_plot_table_splitter_sizes()
        self.status_message_signal.emit(f"[{self.profile.title_ko}] 실시간 그래프를 별도 창으로 분리했습니다.")

    def _redock_graph(self):
        dlg = self.graph_float_dialog
        self.graph_float_dialog = None
        if dlg is not None:
            dlg._is_redocking = True
            dlg.body_layout.removeWidget(self.graph_inner_panel)
            dlg.close()
        self.lbl_graph_detached.setVisible(False)
        self.graph_slot_layout.insertWidget(0, self.graph_inner_panel)
        self.graph_inner_panel.show()
        self.btn_detach_graph.setText("🗗 그래프 새 창 분리")
        self.btn_detach_graph.setStyleSheet(
            "background-color: #eff6ff; color: #1d4ed8; border: 1px solid #93c5fd; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        self._update_plot_table_splitter_sizes()
        self.status_message_signal.emit(f"[{self.profile.title_ko}] 실시간 그래프가 메인 화면으로 복귀했습니다.")

    def toggle_detach_table(self):
        if self.table_float_dialog is not None:
            self._redock_table()
        else:
            self._detach_table()

    def _detach_table(self):
        if self.table_float_dialog is not None:
            self.table_float_dialog.raise_()
            self.table_float_dialog.activateWindow()
            return
        dlg = DetachablePaneDialog(
            title=f"{self.profile.title_ko} - 실시간 측정 데이터 테이블 (분리된 창)",
            dock_callback=self._redock_table,
            parent=self.window(),
        )
        self.table_slot_layout.removeWidget(self.table_inner_panel)
        dlg.body_layout.addWidget(self.table_inner_panel)
        self.table_inner_panel.show()
        self.lbl_table_detached.setVisible(True)
        self.table_float_dialog = dlg
        self.btn_detach_table.setText("↙ 데이터 표 복귀")
        self.btn_detach_table.setStyleSheet(
            "background-color: #dcfce7; color: #14532d; border: 1px solid #22c55e; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        dlg.show()
        self._update_plot_table_splitter_sizes()
        self.status_message_signal.emit(f"[{self.profile.title_ko}] 측정 데이터 테이블을 별도 창으로 분리했습니다.")

    def _redock_table(self):
        dlg = self.table_float_dialog
        self.table_float_dialog = None
        if dlg is not None:
            dlg._is_redocking = True
            dlg.body_layout.removeWidget(self.table_inner_panel)
            dlg.close()
        self.lbl_table_detached.setVisible(False)
        self.table_slot_layout.insertWidget(0, self.table_inner_panel)
        self.table_inner_panel.show()
        self.btn_detach_table.setText("🗗 데이터 표 새 창 분리")
        self.btn_detach_table.setStyleSheet(
            "background-color: #f0fdf4; color: #15803d; border: 1px solid #86efac; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 8.5pt;"
        )
        self._update_plot_table_splitter_sizes()
        self.status_message_signal.emit(f"[{self.profile.title_ko}] 측정 데이터 테이블이 메인 화면으로 복귀했습니다.")

    def _update_plot_table_splitter_sizes(self):
        ph = self.plot_table_splitter.height()
        if ph <= 120:
            return
        g_det = self.graph_float_dialog is not None
        t_det = self.table_float_dialog is not None
        if g_det and not t_det:
            self.plot_table_splitter.setSizes([56, max(100, ph - 56)])
        elif t_det and not g_det:
            self.plot_table_splitter.setSizes([max(100, ph - 56), 56])
        else:
            self.plot_table_splitter.setSizes([int(ph * 0.65), int(ph * 0.35)])

    def sync_splitter_proportions(self):
        w = self.main_splitter.width() or self.width()
        if w > 300:
            self.main_splitter.setSizes([int(w * 0.25), int(w * 0.27), int(w * 0.48)])
        self._update_plot_table_splitter_sizes()

    def showEvent(self, a0: Optional[QShowEvent]):
        super().showEvent(a0)
        if not self._initial_splitters_applied:
            self._initial_splitters_applied = True
            QTimer.singleShot(0, self.sync_splitter_proportions)

    def resizeEvent(self, a0: Optional[QResizeEvent]):
        super().resizeEvent(a0)
        if not self._initial_splitters_applied and self.width() > 400 and self.height() > 250:
            self._initial_splitters_applied = True
            self.sync_splitter_proportions()

    def _create_input_widget(self, spec: InputParameterSpec) -> QWidget:
        if spec.param_type == "multi_choice":
            box = QWidget()
            h_lay = QHBoxLayout(box)
            h_lay.setContentsMargins(0, 0, 0, 0)
            h_lay.setSpacing(6)
            default_tokens = [t.strip().upper() for t in str(spec.default).split(",") if t.strip()]
            cbs: List[QCheckBox] = []
            for ch_name in spec.choices:
                cb = QCheckBox(ch_name)
                cb.setFont(QFont("Malgun Gothic", 8 if self.is_compact_screen else 9, QFont.Weight.Bold))
                cb.setChecked(ch_name.upper() in default_tokens)
                h_lay.addWidget(cb)
                cbs.append(cb)
            h_lay.addStretch()
            box._multi_checkboxes = cbs  # type: ignore[attr-defined]
            return box
        elif spec.param_type == "choice":
            cmb = QComboBox()
            cmb.setMinimumWidth(90)
            cmb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cmb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cmb.addItems(spec.choices)
            if str(spec.default) in spec.choices:
                cmb.setCurrentText(str(spec.default))
            return cmb
        elif spec.param_type == "float":
            sp = QDoubleSpinBox()
            sp.setMinimumWidth(90)
            sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            sp.setDecimals(6 if (spec.min_val is not None and spec.min_val < 0.001) else 3)
            sp.setMinimum(spec.min_val if spec.min_val is not None else -1e9)
            sp.setMaximum(spec.max_val if spec.max_val is not None else 1e9)
            def_f = float(spec.default)
            if spec.key == "poll_interval_s":
                sp.setSingleStep(0.05)
                sp.valueChanged.connect(self._on_poll_interval_spin_changed)
            elif spec.key == "nplc":
                sp.setSingleStep(0.1)
            elif 0 < abs(def_f) < 1.0:
                sp.setSingleStep(0.05)
            sp.setValue(def_f)
            return sp
        elif spec.param_type == "int":
            sp = QSpinBox()
            sp.setMinimumWidth(90)
            sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            sp.setMinimum(int(spec.min_val) if spec.min_val is not None else -1000000)
            sp.setMaximum(int(spec.max_val) if spec.max_val is not None else 10000000)
            sp.setValue(int(spec.default))
            return sp
        elif spec.param_type == "bool":
            cb = QCheckBox("활성화 (Enable)")
            cb.setChecked(bool(spec.default))
            return cb
        else:
            le = QLineEdit(str(spec.default))
            le.setMinimumWidth(90)
            le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return le

    def _reset_inputs_to_default(self):
        for spec in self.profile.input_parameters:
            w = self.input_widgets.get(spec.key)
            if w is None:
                continue
            if hasattr(w, "_multi_checkboxes"):
                default_tokens = [t.strip().upper() for t in str(spec.default).split(",") if t.strip()]
                for cb in getattr(w, "_multi_checkboxes"):
                    cb.setChecked(cb.text().upper() in default_tokens and cb.isEnabled())
            elif isinstance(w, QComboBox):
                w.setCurrentText(str(spec.default))
            elif isinstance(w, QDoubleSpinBox):
                w.setValue(float(spec.default))
            elif isinstance(w, QSpinBox):
                w.setValue(int(spec.default))
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(spec.default))
            elif isinstance(w, QLineEdit):
                w.setText(str(spec.default))
        self.status_message_signal.emit(f"[{self.profile.title_ko}] 입력 파라미터가 매뉴얼 기본값으로 초기화되었습니다.")

    def get_current_model(self) -> ModelProfile:
        idx = max(0, self.cmb_model.currentIndex())
        return self.profile.models[idx]

    def _on_model_changed(self, idx: int):
        model = self.get_current_model()
        self.lbl_model_specs.setText(
            f"• <b>지원 인터페이스:</b> {', '.join(model.interfaces)} &nbsp;|&nbsp; "
            f"• <b>최대 채널:</b> {model.max_channels}CH &nbsp;|&nbsp; "
            f"• <b>주요 사양:</b> {model.specs_summary} &nbsp;|&nbsp; "
            f"• <b>매뉴얼:</b> <code>{model.manual_file}</code>"
        )
        notes_html = "<ul style='margin: 0; padding-left: 16px;'>" + "".join(
            f"<li>{n}</li>" for n in model.remote_notes
        ) + "</ul>"
        self.lbl_remote_notes.setText(notes_html)
        self.visa_mgr.set_category_model(self.profile.folder_id, model.model_id)
        # Enable/disable multi-channel checkboxes based on model.max_channels (e.g., 2CH vs 4CH scopes)
        ch_w = self.input_widgets.get("channel")
        if ch_w is not None and hasattr(ch_w, "_multi_checkboxes"):
            cbs: List[QCheckBox] = getattr(ch_w, "_multi_checkboxes")
            for i_cb, cb in enumerate(cbs):
                allowed = (i_cb + 1) <= model.max_channels
                cb.setEnabled(allowed)
                if not allowed and cb.isChecked():
                    cb.setChecked(False)
            if not any(cb.isChecked() for cb in cbs if cb.isEnabled()) and cbs:
                cbs[0].setChecked(True)

    def _open_current_manual_pdf(self):
        model = self.get_current_model()
        pdf_path = os.path.normpath(os.path.join(self.manuals_base_dir, model.manual_file))
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        else:
            QMessageBox.warning(self, "매뉴얼 파일 확인", f"매뉴얼 경로를 찾을 수 없습니다:\n{pdf_path}")

    def _verify_single_checklist_item(self, item_spec):
        model = self.get_current_model()
        self.visa_mgr.set_category_model(self.profile.folder_id, model.model_id)
        cmd = getattr(item_spec, "verify_cmd", "*IDN?")
        try:
            resp, dt = self.visa_mgr.query(cmd)
            self.io_updated_signal.emit()
            self.status_message_signal.emit(f"[{item_spec.title}] 확인 완료: {cmd} → {resp} ({dt:.1f} ms)")
            return True, resp, dt
        except Exception as e:
            self.io_updated_signal.emit()
            return False, str(e), 0.0

    def apply_checked_map(self, checked_map: Dict[str, bool]):
        for cid, is_chk in checked_map.items():
            if cid in self.checklist_widgets:
                self.checklist_widgets[cid].setChecked(is_chk)

    def _run_live_status_check(self):
        model = self.get_current_model()
        self.visa_mgr.set_category_model(self.profile.folder_id, model.model_id)
        pwd = ""
        if "auth_password" in self.input_widgets and isinstance(self.input_widgets["auth_password"], QLineEdit):
            pwd = self.input_widgets["auth_password"].text().strip()
        report = self.visa_mgr.verify_instrument_status(protocol=model.protocol, password=pwd)
        for card in self.checklist_cards.values():
            card.run_single_verification()
        self.io_updated_signal.emit()

        lines = [f"<b>[{model.display_name}] 전체 항목 리모트 상태 진단 완료</b><hr>"]
        for k, v in report.items():
            lines.append(f"• <b>{k}:</b> {v}")
        QMessageBox.information(self, "장비 리모트 상태 확인 (*IDN? & 항목별 점검)", "<br>".join(lines))

    def collect_inputs(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for spec in self.profile.input_parameters:
            w = self.input_widgets.get(spec.key)
            if w is not None and hasattr(w, "_multi_checkboxes"):
                checked_list = [cb.text() for cb in getattr(w, "_multi_checkboxes") if cb.isChecked() and cb.isEnabled()]
                if not checked_list:
                    cbs = getattr(w, "_multi_checkboxes")
                    if cbs:
                        cbs[0].setChecked(True)
                        checked_list = [cbs[0].text()]
                result[spec.key] = ", ".join(checked_list)
            elif isinstance(w, QComboBox):
                result[spec.key] = w.currentText()
            elif isinstance(w, QDoubleSpinBox):
                result[spec.key] = float(w.value())
            elif isinstance(w, QSpinBox):
                result[spec.key] = int(w.value())
            elif isinstance(w, QCheckBox):
                result[spec.key] = bool(w.isChecked())
            elif isinstance(w, QLineEdit):
                result[spec.key] = w.text()
        return result

    def collect_selected_measurables(self) -> List[str]:
        return [k for k, cb in self.measurable_widgets.items() if cb.isChecked()]

    # =========================================================================
    # REQUIREMENT 2 & 3: Start (with Pre-Start Confirmation), Pause/Resume, Stop
    # =========================================================================
    def on_start_clicked(self):
        selected_meas = self.collect_selected_measurables()
        if not selected_meas:
            QMessageBox.warning(self, "측정 항목 선택 필요", "최소 1개 이상의 [측정 가능 항목]을 체크해 주세요.")
            return

        inputs = self.collect_inputs()
        model = self.get_current_model()

        # Gather checklist status
        unchecked = [
            item.title
            for item in self.profile.checklist
            if not self.checklist_widgets[item.id].isChecked()
        ]

        # Build human-readable summaries for PreStartConfirmDialog (Requirement 2)
        input_summary = []
        for spec in self.profile.input_parameters:
            val = inputs.get(spec.key)
            val_str = f"{val} {spec.unit}".strip() if spec.unit else str(val)
            input_summary.append({"label": spec.label, "value": val_str})

        meas_summary = []
        for m_spec in self.profile.measurable_items:
            if m_spec.key in selected_meas:
                meas_summary.append(
                    {"label": m_spec.label, "unit": m_spec.unit, "cmd": m_spec.scpi_or_tsp_hint}
                )

        dlg = PreStartConfirmDialog(
            category_title=self.profile.title_ko,
            model_name=model.display_name,
            resource_addr=self.visa_mgr.active_resource or "SIM::VIRTUAL_INSTRUMENT",
            is_simulation=self.visa_mgr.is_simulation,
            has_power_output=self.profile.has_power_output,
            unchecked_items=unchecked,
            input_summary=input_summary,
            selected_meas_summary=meas_summary,
            parent=self,
        )
        if dlg.exec() != PreStartConfirmDialog.DialogCode.Accepted:
            return

        # Setup table columns for current measurement session
        self.clear_session_data()
        scope_channels = (
            OscilloscopeDriver.parse_selected_channels(inputs.get("channel", "CH1"))
            if self.profile.folder_id == "04_OSCILLOSCOPE"
            else []
        )
        if len(scope_channels) > 1:
            meas_cols = [
                f"[{ch}] {m.label}"
                for m in self.profile.measurable_items
                if m.key in selected_meas
                for ch in scope_channels
            ]
        else:
            meas_cols = [
                m.label for m in self.profile.measurable_items if m.key in selected_meas
            ]
        headers = ["Step", "Timestamp", "Elapsed (s)"] + meas_cols
        self._apply_table_headers(headers)

        # Initialize driver and start acquisition timer
        self.driver = create_driver_for_category(self.visa_mgr, self.profile.folder_id, model.model_id)
        self.begin_new_run(model, inputs, selected_meas)
        try:
            self.driver.configure_and_start(inputs, selected_meas)
            self.io_updated_signal.emit()
        except Exception as e:
            self.history_store.remove([self.live_run.run_id])
            self.live_run = self._make_scratch_run()
            self.history_tab.refresh_list()
            QMessageBox.critical(self, "장비 초기화 오류", f"명령 전송 중 오류가 발생했습니다:\n{e}")
            return

        poll_s = float(inputs.get("poll_interval_s", 0.5))
        self._target_poll_ms = max(15, int(poll_s * 1000))
        self._set_state(self.STATE_RUNNING)
        self._on_measurement_tick()

    def _on_poll_interval_spin_changed(self, new_val: float):
        """Updates the acquisition timer immediately when the user changes poll_interval_s while running."""
        target_ms = max(15, int(float(new_val) * 1000))
        self._target_poll_ms = target_ms
        if self.timer.isActive() and self.timer.interval() > target_ms:
            self.timer.start(max(1, target_ms))

    # =========================================================================
    # RUN HISTORY / COLUMN CUSTOMISATION / EXPORT OPTIONS
    # =========================================================================
    def begin_new_run(self, model: ModelProfile, inputs: Dict[str, Any], selected_meas: List[str]) -> RunRecord:
        """Registers a new RunRecord in the history and makes it the live (current) run."""
        try:
            idn_str, _ = self.visa_mgr.query("*IDN?")
        except Exception:
            idn_str = "N/A"
        chk_status = [
            {"title": item.title, "checked": self.checklist_widgets[item.id].isChecked()}
            for item in self.profile.checklist
        ]
        meas_labels = {
            m.key: f"{m.label} [{m.unit}]"
            for m in self.profile.measurable_items
            if m.key in selected_meas
        }
        run = self.history_store.new_run(
            folder_id=self.profile.folder_id,
            category_title=self.profile.title_ko,
            model_id=model.model_id,
            model_name=model.display_name,
            manual_file=model.manual_file,
            resource=self.visa_mgr.active_resource or "SIMULATION",
            is_simulation=self.visa_mgr.is_simulation,
            idn=str(idn_str),
            checklist_status=chk_status,
            inputs=dict(inputs),
            meas_labels=meas_labels,
            mode_idx=self.cmb_graph_mode.currentIndex(),
        )
        run.status = "RUNNING"
        self.live_run = run
        self.history_tab.refresh_list(select_ids=[run.run_id], redraw=False)
        return run

    def _finalize_run(self, status: str) -> None:
        run = self.live_run
        if run.run_id <= 0 or run.ended:
            return
        run.status = status
        run.ended = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history_tab.auto_export(run)
        self.history_tab.refresh_list()

    def _on_clear_clicked(self):
        if self.state in (self.STATE_RUNNING, self.STATE_PAUSED):
            QMessageBox.warning(self, "초기화 불가", "측정 중에는 화면을 초기화할 수 없습니다. 먼저 [⏹ 완전 정지]를 눌러 주세요.")
            return
        self.clear_session_data()

    def _on_plot_tab_changed(self, index: int):
        if self.plot_tabs.widget(index) is self.history_tab:
            self.history_tab.refresh_list()

    def _apply_table_headers(self, headers: List[str]):
        self._table_headers = list(headers)
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels([self.column_aliases.get(h, h) for h in headers])
        for i, h in enumerate(headers):
            self.data_table.setColumnHidden(i, h in self.hidden_columns)

    def _on_header_menu(self, pos: QPoint):
        hdr = self.data_table.horizontalHeader()
        if hdr is None:
            return
        col = hdr.logicalIndexAt(pos)
        menu = QMenu(self)
        if 0 <= col < len(self._table_headers):
            orig = self._table_headers[col]
            act_rename = menu.addAction(f"✏ '{self.column_aliases.get(orig, orig)}' 컬럼 이름 변경")
            act_hide = menu.addAction("🙈 이 컬럼 숨기기")
        else:
            orig = ""
            act_rename = None
            act_hide = None
        act_show = menu.addAction("👁 숨긴 컬럼 모두 표시")
        act_reset = menu.addAction("↺ 컬럼 이름/숨김 초기화")
        chosen = menu.exec(hdr.mapToGlobal(pos))
        if chosen is None:
            return
        if act_rename is not None and chosen is act_rename:
            new_name, ok = QInputDialog.getText(
                self, "컬럼 이름 변경", f"'{orig}' 컬럼의 새 이름 (표와 내보내기 파일에 반영됩니다):",
                text=self.column_aliases.get(orig, orig),
            )
            if ok and new_name.strip():
                self.column_aliases[orig] = new_name.strip()
        elif act_hide is not None and chosen is act_hide:
            self.hidden_columns.add(orig)
        elif chosen is act_show:
            self.hidden_columns.clear()
        elif chosen is act_reset:
            self.hidden_columns.clear()
            self.column_aliases.clear()
        self._apply_table_headers(self._table_headers)

    def _export_rows_for(self, run: RunRecord) -> List[Dict[str, Any]]:
        """Applies the user's column rename / hide settings to a run's table rows."""
        out: List[Dict[str, Any]] = []
        for r in run.rows:
            out.append(
                {
                    self.column_aliases.get(k, k): v
                    for k, v in r.items()
                    if k not in self.hidden_columns
                }
            )
        return out

    def on_export_options_clicked(self):
        self.history_tab.open_export_dialog(self.live_run, preferred="current")

    def on_pause_clicked(self):
        if self.state == self.STATE_RUNNING:
            self.timer.stop()
            if self.driver:
                self.driver.pause_measurement(self.collect_inputs())
            self._set_state(self.STATE_PAUSED)
            self.live_run.status = "PAUSED"
            self.history_tab.refresh_list()
            self.io_updated_signal.emit()
        elif self.state == self.STATE_PAUSED:
            inputs = self.collect_inputs()
            if self.driver:
                self.driver.resume_measurement(inputs)
            poll_s = float(inputs.get("poll_interval_s", 0.5))
            self.timer.start(max(50, int(poll_s * 1000)))
            self._set_state(self.STATE_RUNNING)
            self.live_run.status = "RUNNING"
            self.history_tab.refresh_list()
            self.io_updated_signal.emit()

    def on_stop_clicked(self):
        self.timer.stop()
        if self.driver:
            try:
                self.driver.stop_and_safe_shutdown(self.collect_inputs())
            except Exception:
                pass
        self._set_state(self.STATE_STOPPED)
        self._finalize_run("STOPPED")
        self.io_updated_signal.emit()

    def _set_state(self, new_state: str):
        self.state = new_state
        if new_state == self.STATE_RUNNING:
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("⏸ 일시정지")
            self.btn_stop.setEnabled(True)
            self.lbl_state_badge.setText("● 상태: 측정 및 동작 중 (RUNNING)")
            self.lbl_state_badge.setStyleSheet(
                "background-color: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 4px; font-weight: bold;"
            )
            self.status_message_signal.emit(f"[{self.profile.title_ko}] 측정이 시작되었습니다.")
        elif new_state == self.STATE_PAUSED:
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("▶ 측정 재개")
            self.btn_stop.setEnabled(True)
            self.lbl_state_badge.setText("● 상태: 일시정지됨 (PAUSED)")
            self.lbl_state_badge.setStyleSheet(
                "background-color: #fef3c7; color: #92400e; padding: 3px 8px; border-radius: 4px; font-weight: bold;"
            )
            self.status_message_signal.emit(f"[{self.profile.title_ko}] 측정이 일시정지되었습니다.")
        elif new_state == self.STATE_STOPPED:
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_pause.setText("⏸ 일시정지")
            self.btn_stop.setEnabled(False)
            self.lbl_state_badge.setText("● 상태: 완전 정지 / 안전 출력 차단 (STOPPED)")
            self.lbl_state_badge.setStyleSheet(
                "background-color: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-weight: bold;"
            )
            self.status_message_signal.emit(f"[{self.profile.title_ko}] 측정이 완전 정지되었으며 출력이 안전하게 OFF 되었습니다.")
        else:
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.lbl_state_badge.setText("● 상태: 대기 중 (IDLE)")
            self.lbl_state_badge.setStyleSheet(
                "background-color: #e2e8f0; color: #334155; padding: 4px 10px; border-radius: 4px;"
            )

    def _on_measurement_tick(self):
        if self.driver is None or self.state != self.STATE_RUNNING:
            return
        t_tick_start = time.perf_counter()
        self._last_tick_start = t_tick_start
        inputs = self.collect_inputs()
        target_ms = max(15, int(float(inputs.get("poll_interval_s", 0.5)) * 1000))
        self._target_poll_ms = target_ms
        selected_meas = self.collect_selected_measurables()
        try:
            res: MeasurementResult = self.driver.acquire_step(inputs, selected_meas)
            self.io_updated_signal.emit()
        except Exception as e:
            self.on_stop_clicked()
            QMessageBox.critical(self, "측정 루프 오류", f"데이터 획득 중 오류가 발생하여 정지합니다:\n{e}")
            return

        # Update live scalar labels
        for m_spec in self.profile.measurable_items:
            if m_spec.key in res.scalars:
                v = res.scalars[m_spec.key]
                self.live_value_labels[m_spec.key].setText(f"{v} {m_spec.unit}".strip())

        # Record history row
        row_dict: Dict[str, Any] = {
            "Step": res.step_index,
            "Timestamp": res.timestamp_str,
            "Elapsed (s)": res.elapsed_s,
        }
        scope_channels = (
            OscilloscopeDriver.parse_selected_channels(inputs.get("channel", "CH1"))
            if self.profile.folder_id == "04_OSCILLOSCOPE"
            else []
        )
        if len(scope_channels) > 1:
            for m_spec in self.profile.measurable_items:
                if m_spec.key in selected_meas:
                    for ch in scope_channels:
                        row_dict[f"[{ch}] {m_spec.label}"] = res.scalars.get(
                            f"{m_spec.key}_{ch}", res.scalars.get(m_spec.key, "")
                        )
        else:
            for m_spec in self.profile.measurable_items:
                if m_spec.key in selected_meas:
                    row_dict[m_spec.label] = res.scalars.get(m_spec.key, "")
        self.measured_rows.append(row_dict)
        self.lbl_sample_count.setText(f"누적 샘플: {len(self.measured_rows)} pts")

        # Refresh table headers dynamically if user toggled additional channels mid-run
        cur_keys = list(row_dict.keys())
        if cur_keys != self._table_headers:
            self._apply_table_headers(cur_keys)

        # Append row to GUI table
        self.data_table.setUpdatesEnabled(False)
        try:
            r_pos = self.data_table.rowCount()
            self.data_table.insertRow(r_pos)
            for c_idx, col_key in enumerate(cur_keys):
                item = QTableWidgetItem(str(row_dict[col_key]))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.data_table.setItem(r_pos, c_idx, item)
        finally:
            self.data_table.setUpdatesEnabled(True)
        self.data_table.scrollToBottom()

        # Store time-series & waveform history
        self.time_history.append(res.elapsed_s)
        if res.primary_plot_x is not None:
            self.xy_x_history.append(res.primary_plot_x)
        for s_name, s_val in res.primary_plot_y.items():
            self.series_history.setdefault(s_name, []).append(float(s_val))

        if res.waveform_x is not None and (res.waveform_y is not None or bool(res.waveform_multi_y)):
            self.last_waveform_x = res.waveform_x
            self.last_waveform_y = res.waveform_y
            self.live_run.waveform_multi_y = dict(res.waveform_multi_y)
            self.last_wfm_x_label = res.waveform_x_label
            self.last_wfm_y_label = res.waveform_y_label

        self._refresh_plots()

        if res.is_completed_sweep:
            self.on_stop_clicked()
            self.status_message_signal.emit(f"[{self.profile.title_ko}] 지정된 스윕({res.step_index} 포인트) 측정이 완료되어 자동 정지되었습니다.")
            return

        if self.state == self.STATE_RUNNING:
            elapsed_work_ms = int((time.perf_counter() - t_tick_start) * 1000.0)
            wait_ms = max(5, target_ms - elapsed_work_ms)
            self.timer.start(wait_ms)

    def _refresh_plots(self):
        clear_data_items(self.primary_plot)
        draw_run(
            self.primary_plot,
            self.live_run,
            self.cmb_graph_mode.currentIndex(),
            title_prefix=self.profile.title_ko,
            mode_text=self.cmb_graph_mode.currentText(),
        )
        cursor_bar = getattr(self, "cursor_bar", None)
        if cursor_bar is not None:
            cursor_bar.refresh()

    def clear_session_data(self):
        """Clears the current screen. Finished runs stay available in the Run History tab."""
        self.live_run = self._make_scratch_run()
        self.data_table.setRowCount(0)
        clear_data_items(self.primary_plot)
        self.cursor_bar.refresh()
        self.lbl_sample_count.setText("누적 샘플: 0 pts")
        for m_spec in self.profile.measurable_items:
            self.live_value_labels[m_spec.key].setText(f"--- {m_spec.unit}".strip())
    def on_export_excel_clicked(self):
        if not self.measured_rows and self.last_waveform_x is None:
            QMessageBox.warning(
                self,
                "저장할 데이터 없음",
                "아직 측정된 데이터가 없습니다. 먼저 [▶ 측정 시작]을 눌러 데이터를 수집해 주세요.",
            )
            return

        model = self.get_current_model()
        ts_file = time.strftime("%Y%m%d_%H%M%S")
        default_name = f"SAITEK Tektronix Quick Start SW_{self.profile.folder_id}_{model.model_id}_{ts_file}.xlsx"
        default_path = os.path.join(self.data_export_dir, default_name)
        os.makedirs(self.data_export_dir, exist_ok=True)

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "측정 데이터 Excel (.xlsx) 저장",
            default_path,
            "Excel Files (*.xlsx)",
        )
        if not filepath:
            return

        chk_status = [
            {"title": item.title, "checked": self.checklist_widgets[item.id].isChecked()}
            for item in self.profile.checklist
        ]
        selected_meas = self.collect_selected_measurables()
        meas_labels = {
            m.key: f"{m.label} [{m.unit}]"
            for m in self.profile.measurable_items
            if m.key in selected_meas
        }
        idn_str, _ = self.visa_mgr.query("*IDN?")

        try:
            saved_path = export_session_to_excel(
                filepath=filepath,
                category_title=self.profile.title_ko,
                model_name=model.display_name,
                manual_file=model.manual_file,
                resource_addr=self.visa_mgr.active_resource or "SIMULATION",
                is_simulation=self.visa_mgr.is_simulation,
                idn_string=idn_str,
                checklist_status=chk_status,
                input_params=self.collect_inputs(),
                selected_meas_labels=meas_labels,
                measured_rows=self._export_rows_for(self.live_run),
                last_waveform_x=self.last_waveform_x,
                last_waveform_y=self.last_waveform_y,
                waveform_x_label=self.last_wfm_x_label,
                waveform_y_label=self.last_wfm_y_label,
                last_waveform_multi_y=self.live_run.waveform_multi_y,
            )
            self.status_message_signal.emit(f"Excel 저장 완료: {saved_path}")
            QMessageBox.information(
                self,
                "Excel 데이터 저장 완료",
                f"측정 데이터가 4개 시트(Summary/Checklist, Input Config, Measured Data+통계, Waveform Trace)를 포함한 Excel 파일로 저장되었습니다:\n\n{saved_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Excel 저장 실패", f"파일 저장 중 오류가 발생했습니다:\n{e}")
