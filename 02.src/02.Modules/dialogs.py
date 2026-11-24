# -*- coding: utf-8 -*-
"""
Tektronix QuickStart Program - Dialogs for Requirement 4 (Beginner-Friendly Interactive Startup Remote Readiness)
and Requirement 2 (Pre-Start Input & Measurement Confirmation Modal).
"""

import os
import sys
from typing import Dict, Any, List, Optional

# Ensure sibling 02.src subdirectories are on sys.path
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
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QFrame,
    QScrollArea,
    QWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl, QRect
from PyQt6.QtGui import QFont, QPixmap, QDesktopServices


def get_available_screen_geometry(widget: Optional[QWidget] = None) -> QRect:
    """Returns the usable screen geometry (excluding Windows taskbar) for the current monitor."""
    screen = None
    if widget is not None:
        win_handle = widget.windowHandle()
        if win_handle is not None:
            screen = win_handle.screen()
        if screen is None:
            screen = widget.screen()
    if screen is None and QApplication.instance() is not None:
        screen = QApplication.primaryScreen()
    if screen is not None:
        return screen.availableGeometry()
    return QRect(0, 0, 1920, 1040)


def fit_and_center_window(
    window: QWidget,
    target_w_ratio: float = 0.88,
    target_h_ratio: float = 0.88,
    min_w: int = 720,
    min_h: int = 500,
    max_w: int = 1920,
    max_h: int = 1200,
):
    """Resizes and centers a window or dialog so it never overflows the user's screen."""
    avail = get_available_screen_geometry(window)
    w = min(max_w, max(min_w, int(avail.width() * target_w_ratio)))
    h = min(max_h, max(min_h, int(avail.height() * target_h_ratio)))
    w = min(w, avail.width() - 16)
    h = min(h, avail.height() - 36)
    window.resize(w, h)
    x = avail.x() + max(0, (avail.width() - w) // 2)
    y = avail.y() + max(0, (avail.height() - h) // 2)
    window.move(x, y)


class ChecklistStepCard(QFrame):
    """
    Beginner-friendly step-by-step interactive card for a single ChecklistItem.
    Displays:
    - Checkbox with clear step title
    - Description & collapsible/visible step-by-step Beginner Guide (how_to_steps)
    - Individual [🔍 이 항목 즉시 확인] button that queries the instrument and updates a status badge!
    """

    def __init__(self, item_spec, verify_callback, compact: bool = False, parent: Any = None):
        super().__init__(parent)
        self.item_spec = item_spec
        self.verify_callback = verify_callback
        self.compact = compact
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            "ChecklistStepCard { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        # Top row: Checkbox + Individual Verify Button + Guide Popup Button
        top_row = QHBoxLayout()
        self.checkbox = QCheckBox(self.item_spec.title)
        self.checkbox.setChecked(self.item_spec.checked_by_default)
        self.checkbox.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        self.checkbox.setStyleSheet("color: #0f172a;")
        top_row.addWidget(self.checkbox, 1)

        if self.compact and getattr(self.item_spec, "how_to_steps", None):
            btn_guide = QPushButton("📘 초보자 연결 가이드 보기")
            btn_guide.setStyleSheet(
                "background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; "
                "padding: 3px 8px; border-radius: 4px; font-size: 8.5pt; font-weight: bold;"
            )
            btn_guide.clicked.connect(self._show_guide_popup)
            top_row.addWidget(btn_guide)

        self.btn_verify = QPushButton(getattr(self.item_spec, "verify_label", "🔍 상태 확인"))
        self.btn_verify.setStyleSheet(
            "background-color: #0284c7; color: white; padding: 4px 10px; border-radius: 4px; font-size: 8.5pt; font-weight: bold;"
        )
        self.btn_verify.clicked.connect(self.run_single_verification)
        top_row.addWidget(self.btn_verify)

        layout.addLayout(top_row)

        # Description label
        desc_lbl = QLabel(f"💡 {self.item_spec.description}")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #475569; font-size: 8.5pt; padding-left: 18px;")
        layout.addWidget(desc_lbl)

        # Beginner step-by-step instructions (shown directly in Startup Wizard, or via popup in compact workspace)
        steps = getattr(self.item_spec, "how_to_steps", [])
        if steps and not self.compact:
            guide_box = QFrame()
            guide_box.setStyleSheet(
                "QFrame { background-color: #f8fafc; border-left: 3px solid #3b82f6; border-radius: 3px; padding: 6px; margin-left: 18px; }"
            )
            g_layout = QVBoxLayout(guide_box)
            g_layout.setContentsMargins(6, 4, 6, 4)
            g_layout.setSpacing(3)
            hdr_g = QLabel("📘 [초보자 따라하기 가이드 - 장비/PC 조작 순서]")
            hdr_g.setStyleSheet("color: #1d4ed8; font-weight: bold; font-size: 8.5pt; border: none;")
            g_layout.addWidget(hdr_g)
            for s in steps:
                s_lbl = QLabel(s)
                s_lbl.setWordWrap(True)
                s_lbl.setStyleSheet("color: #1e293b; font-size: 8.5pt; border: none;")
                g_layout.addWidget(s_lbl)
            layout.addWidget(guide_box)

        # Verification result badge row
        res_row = QHBoxLayout()
        res_row.setContentsMargins(18, 0, 0, 0)
        cmd_hint = getattr(self.item_spec, "verify_cmd", "*IDN?")
        exp_hint = getattr(self.item_spec, "expected_hint", "")
        self.lbl_verify_result = QLabel(f"⏳ 미확인 (명령어: {cmd_hint} | 기대 결과: {exp_hint})")
        self.lbl_verify_result.setWordWrap(True)
        self.lbl_verify_result.setStyleSheet(
            "background-color: #f1f5f9; color: #64748b; border-radius: 4px; padding: 3px 8px; font-size: 8.5pt;"
        )
        res_row.addWidget(self.lbl_verify_result, 1)
        layout.addLayout(res_row)

    def run_single_verification(self) -> bool:
        ok, resp_text, dt_ms = self.verify_callback(self.item_spec)
        if ok:
            self.checkbox.setChecked(True)
            self.lbl_verify_result.setText(
                f"✅ 확인 완료 ({dt_ms:.1f} ms) | 명령: {self.item_spec.verify_cmd} → 응답: {resp_text}"
            )
            self.lbl_verify_result.setStyleSheet(
                "background-color: #dcfce7; color: #166534; border: 1px solid #86efac; "
                "border-radius: 4px; padding: 3px 8px; font-size: 8.5pt; font-weight: bold;"
            )
            self.setStyleSheet(
                "ChecklistStepCard { background-color: #f0fdf4; border: 1px solid #4ade80; border-radius: 6px; }"
            )
            return True
        else:
            self.lbl_verify_result.setText(
                f"❌ 확인 실패 | 명령: {self.item_spec.verify_cmd} → 오류: {resp_text}"
            )
            self.lbl_verify_result.setStyleSheet(
                "background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; "
                "border-radius: 4px; padding: 3px 8px; font-size: 8.5pt; font-weight: bold;"
            )
            self.setStyleSheet(
                "ChecklistStepCard { background-color: #fef2f2; border: 1px solid #f87171; border-radius: 6px; }"
            )
            return False

    def _show_guide_popup(self):
        steps = getattr(self.item_spec, "how_to_steps", [])
        html = (
            f"<h3>{self.item_spec.title}</h3>"
            f"<p><b>설명:</b> {self.item_spec.description}</p><hr>"
            f"<h4>📘 초보자 따라하기 순서:</h4>"
            + "<br>".join(f"<p style='margin:4px 0;'>{s}</p>" for s in steps)
            + f"<hr><p><b>검증 명령어:</b> <code>{self.item_spec.verify_cmd}</code><br>"
            f"<b>기대 결과:</b> {self.item_spec.expected_hint}</p>"
        )
        QMessageBox.information(self, "초보자 장비 연결 및 설정 가이드", html)


class StartupReadinessDialog(QDialog):
    """
    Requirement 4 (Upgraded for Complete Beginners):
    1. Allows user to select their exact Instrument Folder (01~07) and Model first.
    2. Displays beginner-friendly physical cable connection & front-panel menu guides for that model.
    3. Provides per-item [🔍 이 항목 즉시 확인] buttons that query the device and auto-check each step.
    """

    def __init__(
        self,
        visa_mgr,
        category_profiles: Dict[str, Any],
        initial_category_id: str = "01_AFG",
        initial_model_id: str = "",
        manuals_base_dir: str = "",
        parent: Any = None,
    ):
        super().__init__(parent)
        self.visa_mgr = visa_mgr
        self.category_profiles = category_profiles
        self.selected_category_id = initial_category_id if initial_category_id in category_profiles else "01_AFG"
        self.selected_model_id = initial_model_id
        self.manuals_base_dir = manuals_base_dir or os.path.join(_BASE_DIR, "01.docs", "10. Tek_Manuals")
        self.selected_resource = ""
        self.use_simulation = True
        self.step_cards: List[ChecklistStepCard] = []

        self.setWindowTitle("Tektronix QuickStart - 초보자용 장비 연결 마법사 & 사전 준비 점검표")
        self._build_ui()
        fit_and_center_window(self, target_w_ratio=0.86, target_h_ratio=0.88, min_w=820, min_h=560, max_w=1280, max_h=920)
        self._run_auto_scan()
        self._populate_models_for_category()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header banner
        banner = QFrame()
        banner.setStyleSheet(
            "background-color: #0b2545; color: white; border-radius: 8px; padding: 10px;"
        )
        b_layout = QVBoxLayout(banner)
        b_top = QHBoxLayout()
        b_top.setSpacing(10)
        logo_cand = os.path.join(_BASE_DIR, "로고 이미지.png")
        if os.path.exists(logo_cand):
            lbl_dlg_logo = QLabel()
            lbl_dlg_logo.setStyleSheet(
                "background-color: #ffffff; border: 1px solid #7dd3fc; border-radius: 4px; padding: 2px 6px;"
            )
            pix = QPixmap(logo_cand)
            if not pix.isNull():
                lbl_dlg_logo.setPixmap(pix.scaledToHeight(28, Qt.TransformationMode.SmoothTransformation))
                b_top.addWidget(lbl_dlg_logo)

        title = QLabel("🧭 장비-PC 연결 가이드 및 항목별 사전 준비 점검 마법사")
        title.setFont(QFont("Malgun Gothic", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        b_top.addWidget(title, 1)
        b_layout.addLayout(b_top)

        sub = QLabel(
            "장비를 처음 다루는 분도 아래 [STEP 1 장비 선택] → [STEP 2 케이블/리소스 연결] → [STEP 3 항목별 따라하기 및 개별 확인] 순서대로 누르면 즉시 측정 준비가 완료됩니다."
        )
        sub.setStyleSheet("color: #c9d6ea; font-size: 9.5pt;")
        b_layout.addWidget(sub)
        layout.addWidget(banner)

        # =====================================================================
        # STEP 1: Select Instrument Category & Model
        # =====================================================================
        grp_step1 = QGroupBox("STEP 1. 연결할 장비 종류(폴더)와 세부 모델을 선택하세요")
        grp_step1.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        grp_step1.setStyleSheet("QGroupBox { color: #1d4ed8; }")
        s1_layout = QVBoxLayout(grp_step1)

        row_sel = QHBoxLayout()
        row_sel.addWidget(QLabel(f"① 장비 분류 ({len(self.category_profiles)}개 폴더):"))
        self.cmb_category = QComboBox()
        self.cmb_category.setMinimumWidth(280)
        for cat_id, prof in self.category_profiles.items():
            self.cmb_category.addItem(f"{prof.icon_text} {prof.title_ko}", cat_id)
        idx_cat = self.cmb_category.findData(self.selected_category_id)
        if idx_cat >= 0:
            self.cmb_category.setCurrentIndex(idx_cat)
        self.cmb_category.currentIndexChanged.connect(self._on_category_changed)
        row_sel.addWidget(self.cmb_category)

        row_sel.addSpacing(15)
        row_sel.addWidget(QLabel("② 세부 장비 모델:"))
        self.cmb_model = QComboBox()
        self.cmb_model.setMinimumWidth(360)
        self.cmb_model.currentIndexChanged.connect(self._on_model_changed)
        row_sel.addWidget(self.cmb_model, 1)

        btn_open_pdf = QPushButton("📖 선택 모델 PDF 매뉴얼 열기")
        btn_open_pdf.setStyleSheet(
            "background-color: #334155; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px;"
        )
        btn_open_pdf.clicked.connect(self._open_selected_manual)
        row_sel.addWidget(btn_open_pdf)
        s1_layout.addLayout(row_sel)

        self.lbl_model_guide = QLabel("")
        self.lbl_model_guide.setWordWrap(True)
        self.lbl_model_guide.setStyleSheet(
            "background-color: #eff6ff; color: #1e3a8a; border: 1px solid #bfdbfe; border-radius: 5px; padding: 8px; font-size: 9pt; font-weight: normal;"
        )
        s1_layout.addWidget(self.lbl_model_guide)
        layout.addWidget(grp_step1)

        # =====================================================================
        # STEP 2: VISA Resource Selection & Connection Test
        # =====================================================================
        grp_step2 = QGroupBox("STEP 2. PC와 장비 통신 포트(USB / LAN / 가상 시뮬레이션)를 선택하고 연결을 확인하세요")
        grp_step2.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        grp_step2.setStyleSheet("QGroupBox { color: #047857; }")
        s2_layout = QVBoxLayout(grp_step2)

        h_res = QHBoxLayout()
        self.lbl_backend = QLabel(f"• VISA 엔진: {self.visa_mgr.backend_info}")
        self.lbl_backend.setStyleSheet("color: #0f766e; font-weight: bold;")
        h_res.addWidget(self.lbl_backend)
        h_res.addSpacing(15)

        h_res.addWidget(QLabel("통신 포트(리소스):"))
        self.cmb_resources = QComboBox()
        self.cmb_resources.setEditable(True)
        self.cmb_resources.setMinimumWidth(380)
        h_res.addWidget(self.cmb_resources, 1)

        btn_scan = QPushButton("🔄 포트 다시 찾기")
        btn_scan.clicked.connect(self._run_auto_scan)
        h_res.addWidget(btn_scan)

        btn_ping = QPushButton("📡 STEP 2: 장비 연결 및 *IDN? 응답 확인")
        btn_ping.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;"
        )
        btn_ping.clicked.connect(self._test_selected_resource)
        h_res.addWidget(btn_ping)
        s2_layout.addLayout(h_res)

        self.chk_sim = QCheckBox(
            "가상 장비 시뮬레이션 모드(Virtual Hardware) 사용 — 실제 장비가 없어도 모든 연결 확인과 측정을 연습할 수 있습니다."
        )
        self.chk_sim.setChecked(True)
        self.chk_sim.setStyleSheet("color: #b5179e; font-weight: bold;")
        s2_layout.addWidget(self.chk_sim)

        self.lbl_test_result = QLabel(
            "상태: 아직 연결 확인 전입니다. 우측 상단의 [📡 STEP 2: 장비 연결 및 *IDN? 응답 확인] 버튼을 눌러주세요."
        )
        self.lbl_test_result.setStyleSheet(
            "background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; padding: 6px; font-weight: normal;"
        )
        s2_layout.addWidget(self.lbl_test_result)
        layout.addWidget(grp_step2)

        # =====================================================================
        # STEP 3: Per-Item Beginner Guide & Individual Verification Cards
        # =====================================================================
        self.grp_step3 = QGroupBox("STEP 3. 선택한 장비의 단계별 연결/설정 점검표 (각 항목의 [🔍 확인] 버튼을 하나씩 눌러보세요)")
        self.grp_step3.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        self.grp_step3.setStyleSheet("QGroupBox { color: #7c3aed; }")
        s3_layout = QVBoxLayout(self.grp_step3)

        top_s3_bar = QHBoxLayout()
        self.lbl_progress = QLabel("점검 진행률: 0 / 0 완료")
        self.lbl_progress.setStyleSheet("color: #6d28d9; font-weight: bold; font-size: 9.5pt;")
        top_s3_bar.addWidget(self.lbl_progress)
        top_s3_bar.addStretch()

        btn_verify_all = QPushButton("⚡ 모든 항목 한 번에 자동 점검 & 체크하기")
        btn_verify_all.setStyleSheet(
            "background-color: #7c3aed; color: white; font-weight: bold; padding: 5px 14px; border-radius: 4px;"
        )
        btn_verify_all.clicked.connect(self.verify_all_steps)
        top_s3_bar.addWidget(btn_verify_all)
        s3_layout.addLayout(top_s3_bar)

        self.scroll_steps = QScrollArea()
        self.scroll_steps.setWidgetResizable(True)
        self.steps_container = QWidget()
        self.steps_vbox = QVBoxLayout(self.steps_container)
        self.steps_vbox.setSpacing(8)
        self.scroll_steps.setWidget(self.steps_container)
        s3_layout.addWidget(self.scroll_steps, 1)

        layout.addWidget(self.grp_step3, 1)

        # =====================================================================
        # Bottom Action Row
        # =====================================================================
        btn_row = QHBoxLayout()
        btn_check_all = QPushButton("☑ 수동으로 전체 체크")
        btn_check_all.clicked.connect(self._check_all_manually)
        btn_row.addWidget(btn_check_all)

        lbl_dlg_support = QLabel(
            "📞 <b>기술 문의 : 사이텍(주)</b> &nbsp;|&nbsp; "
            "<b>E-mail :</b> ssaitek@ssaitek.com &nbsp;|&nbsp; "
            "<b>Tel :</b> 041-698-4242"
        )
        lbl_dlg_support.setStyleSheet(
            "background-color: #f0f9ff; color: #0f172a; border: 1px solid #bae6fd; "
            "border-radius: 5px; padding: 5px 10px; font-size: 9pt;"
        )
        btn_row.addWidget(lbl_dlg_support)
        btn_row.addStretch()

        self.btn_start = QPushButton("🚀 선택한 장비 화면으로 이동하여 측정 시작하기")
        self.btn_start.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        self.btn_start.setStyleSheet(
            "background-color: #005b96; color: white; padding: 10px 24px; border-radius: 6px;"
        )
        self.btn_start.clicked.connect(self._on_accept)
        btn_row.addWidget(self.btn_start)
        layout.addLayout(btn_row)

    def _on_category_changed(self, _idx: int):
        cat_id = self.cmb_category.currentData()
        if cat_id:
            self.selected_category_id = cat_id
            self._populate_models_for_category()

    def _populate_models_for_category(self):
        prof = self.category_profiles[self.selected_category_id]
        self.cmb_model.blockSignals(True)
        self.cmb_model.clear()
        for m in prof.models:
            self.cmb_model.addItem(f"{m.display_name} [{m.protocol}]", m.model_id)
        if self.selected_model_id:
            idx_m = self.cmb_model.findData(self.selected_model_id)
            if idx_m >= 0:
                self.cmb_model.setCurrentIndex(idx_m)
        self.cmb_model.blockSignals(False)
        self._on_model_changed(self.cmb_model.currentIndex())

    def _on_model_changed(self, _idx: int):
        prof = self.category_profiles[self.selected_category_id]
        m_idx = max(0, self.cmb_model.currentIndex())
        model = prof.models[m_idx]
        self.selected_model_id = model.model_id
        self.visa_mgr.set_category_model(self.selected_category_id, self.selected_model_id)

        notes_str = "<br>".join(f"  • {n}" for n in model.remote_notes)
        self.lbl_model_guide.setText(
            f"<b>📌 [{model.display_name}] 초보자 연결 요약</b> &nbsp;|&nbsp; "
            f"<b>지원 연결:</b> {', '.join(model.interfaces)} &nbsp;|&nbsp; <b>채널 수:</b> {model.max_channels}채널<br>"
            f"<b>주요 특징:</b> {model.specs_summary}<br>"
            f"<b>매뉴얼 핵심 연결 안내:</b><br>{notes_str}"
        )
        self._rebuild_step_cards()

    def _rebuild_step_cards(self):
        # Clear existing cards
        while self.steps_vbox.count():
            child = self.steps_vbox.takeAt(0)
            if child is not None:
                w = child.widget()
                if w is not None:
                    w.deleteLater()
        self.step_cards.clear()

        prof = self.category_profiles[self.selected_category_id]
        self.grp_step3.setTitle(
            f"STEP 3. [{prof.title_ko}] 초보자용 단계별 연결 점검표 (총 {len(prof.checklist)}단계)"
        )

        for item_spec in prof.checklist:
            card = ChecklistStepCard(
                item_spec=item_spec,
                verify_callback=self._verify_single_item,
                compact=False,
                parent=self.steps_container,
            )
            card.checkbox.toggled.connect(self._update_progress_label)
            self.step_cards.append(card)
            self.steps_vbox.addWidget(card)

        self.steps_vbox.addStretch()
        self._update_progress_label()

    def _verify_single_item(self, item_spec):
        # Ensure VISA session is connected first
        res = self.cmb_resources.currentText().strip()
        sim = self.chk_sim.isChecked() or res.startswith("SIM::")
        if not self.visa_mgr.active_resource:
            ok, msg = self.visa_mgr.connect(
                res,
                simulation=sim,
                category_id=self.selected_category_id,
                model_id=self.selected_model_id,
            )
            if not ok:
                return False, msg, 0.0
        else:
            self.visa_mgr.set_category_model(self.selected_category_id, self.selected_model_id)

        cmd = getattr(item_spec, "verify_cmd", "*IDN?")
        try:
            resp, dt = self.visa_mgr.query(cmd)
            self._update_progress_label()
            return True, resp, dt
        except Exception as e:
            return False, str(e), 0.0

    def verify_all_steps(self):
        self._test_selected_resource()
        for card in self.step_cards:
            card.run_single_verification()
        self._update_progress_label()

    def _check_all_manually(self):
        for card in self.step_cards:
            card.checkbox.setChecked(True)
        self._update_progress_label()

    def _update_progress_label(self):
        total = len(self.step_cards)
        checked = sum(1 for c in self.step_cards if c.checkbox.isChecked())
        self.lbl_progress.setText(f"점검 진행률: {checked} / {total} 단계 확인 완료")
        if checked == total and total > 0:
            self.lbl_progress.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 10pt;")
        else:
            self.lbl_progress.setStyleSheet("color: #d97706; font-weight: bold; font-size: 9.5pt;")

    def _open_selected_manual(self):
        prof = self.category_profiles[self.selected_category_id]
        m_idx = max(0, self.cmb_model.currentIndex())
        model = prof.models[m_idx]
        pdf_path = os.path.normpath(os.path.join(self.manuals_base_dir, model.manual_file))
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        else:
            QMessageBox.warning(self, "매뉴얼 파일 확인", f"매뉴얼 경로를 찾을 수 없습니다:\n{pdf_path}")

    def _run_auto_scan(self):
        self.cmb_resources.clear()
        res_list = self.visa_mgr.scan_resources()
        self.cmb_resources.addItems(res_list)

    def _test_selected_resource(self):
        res = self.cmb_resources.currentText().strip()
        sim = self.chk_sim.isChecked() or res.startswith("SIM::")
        ok, msg = self.visa_mgr.connect(
            res,
            simulation=sim,
            category_id=self.selected_category_id,
            model_id=self.selected_model_id,
        )
        if ok:
            idn, dt = self.visa_mgr.query("*IDN?")
            self.lbl_test_result.setText(f"✅ 연결 성공 ({dt:.1f} ms) | *IDN? 응답: {idn}")
            self.lbl_test_result.setStyleSheet(
                "background-color: #dcfce7; color: #166534; border: 1px solid #86efac; border-radius: 4px; padding: 6px; font-weight: bold;"
            )
        else:
            self.lbl_test_result.setText(f"❌ {msg}")
            self.lbl_test_result.setStyleSheet(
                "background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; border-radius: 4px; padding: 6px; font-weight: bold;"
            )

    def get_checked_map(self) -> Dict[str, bool]:
        return {card.item_spec.id: card.checkbox.isChecked() for card in self.step_cards}

    def _on_accept(self):
        self.selected_resource = self.cmb_resources.currentText().strip()
        self.use_simulation = self.chk_sim.isChecked() or self.selected_resource.startswith("SIM::")
        self.accept()


class PreStartConfirmDialog(QDialog):
    """
    Requirement 2 & 4: 각 장비별 측정이 가능한 부분과 입력이 필요한 사항을 분리해서
    측정 및 동작 전에 사용자에게 요청(최종 확인 및 승인)하는 모달 다이얼로그
    """

    def __init__(
        self,
        category_title: str,
        model_name: str,
        resource_addr: str,
        is_simulation: bool,
        has_power_output: bool,
        unchecked_items: List[str],
        input_summary: List[Dict[str, str]],
        selected_meas_summary: List[Dict[str, str]],
        parent: Any = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"[동작 및 측정 전 사용자 확인] {category_title}")
        self._build_ui(
            category_title,
            model_name,
            resource_addr,
            is_simulation,
            has_power_output,
            unchecked_items,
            input_summary,
            selected_meas_summary,
        )
        fit_and_center_window(self, target_w_ratio=0.72, target_h_ratio=0.75, min_w=680, min_h=480, max_w=980, max_h=760)

    def _build_ui(
        self,
        category_title: str,
        model_name: str,
        resource_addr: str,
        is_simulation: bool,
        has_power_output: bool,
        unchecked_items: List[str],
        input_summary: List[Dict[str, str]],
        selected_meas_summary: List[Dict[str, str]],
    ):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        hdr = QLabel(f"⚡ [{category_title}] 측정 및 장비 동작 전 설정 확인 요청")
        hdr.setFont(QFont("Malgun Gothic", 12, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #0b2545;")
        layout.addWidget(hdr)

        info_lbl = QLabel(
            f"• 대상 모델: <b>{model_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"• 통신 리소스: <b>{resource_addr}</b> ({'시뮬레이션 모드' if is_simulation else '실제 장비 제어'})"
        )
        layout.addWidget(info_lbl)

        # Unchecked checklist warning if any
        if unchecked_items:
            warn_box = QFrame()
            warn_box.setStyleSheet(
                "background-color: #fff7ed; border: 1px solid #fdba74; border-radius: 6px; padding: 8px;"
            )
            w_layout = QVBoxLayout(warn_box)
            w_title = QLabel(f"⚠️ 아직 체크되지 않은 리모트 준비 사항이 {len(unchecked_items)}건 있습니다:")
            w_title.setStyleSheet("color: #c2410c; font-weight: bold;")
            w_layout.addWidget(w_title)
            for u in unchecked_items:
                l_u = QLabel(f"  - {u}")
                l_u.setStyleSheet("color: #9a3412;")
                w_layout.addWidget(l_u)
            layout.addWidget(warn_box)

        # Split tables: 1) Required Inputs vs 2) Measurable Items
        h_tables = QHBoxLayout()

        # Left Table: Required Input Parameters
        grp_in = QGroupBox(f"1. 사용자 입력 파라미터 확인 ({len(input_summary)}개 항목)")
        grp_in.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        in_layout = QVBoxLayout(grp_in)
        tbl_in = QTableWidget(len(input_summary), 2)
        tbl_in.setHorizontalHeaderLabels(["입력 항목 (Input Parameter)", "설정값 (Configured Value)"])
        h_in = tbl_in.horizontalHeader()
        if h_in is not None:
            h_in.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            h_in.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        v_in = tbl_in.verticalHeader()
        if v_in is not None:
            v_in.setVisible(False)
        for r, item in enumerate(input_summary):
            tbl_in.setItem(r, 0, QTableWidgetItem(item["label"]))
            val_item = QTableWidgetItem(item["value"])
            val_item.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
            tbl_in.setItem(r, 1, val_item)
        in_layout.addWidget(tbl_in)
        h_tables.addWidget(grp_in, 1)

        # Right Table: Selected Measurable Items
        grp_meas = QGroupBox(f"2. 측정 대상 항목 확인 ({len(selected_meas_summary)}개 항목)")
        grp_meas.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        m_layout = QVBoxLayout(grp_meas)
        tbl_m = QTableWidget(len(selected_meas_summary), 2)
        tbl_m.setHorizontalHeaderLabels(["측정 항목 (Measurable Item)", "단위 / 명령어"])
        h_m = tbl_m.horizontalHeader()
        if h_m is not None:
            h_m.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            h_m.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        v_m = tbl_m.verticalHeader()
        if v_m is not None:
            v_m.setVisible(False)
        for r, item in enumerate(selected_meas_summary):
            tbl_m.setItem(r, 0, QTableWidgetItem(item["label"]))
            tbl_m.setItem(r, 1, QTableWidgetItem(f"{item['unit']} ({item['cmd']})"))
        m_layout.addWidget(tbl_m)
        h_tables.addWidget(grp_meas, 1)

        layout.addLayout(h_tables, 1)

        # Safety confirmation checkbox for active output instruments
        self.chk_safety = QCheckBox(
            "위 입력 설정값과 측정 항목을 모두 확인하였으며, 장비에 명령을 전송하고 동작(Output ON / 측정 시작)하는 것에 동의합니다."
        )
        self.chk_safety.setChecked(True)
        self.chk_safety.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        if has_power_output:
            self.chk_safety.setStyleSheet("color: #b91c1c; padding: 4px;")
        layout.addWidget(self.chk_safety)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("취소 (설정 수정)")
        btn_cancel.setStyleSheet("padding: 8px 16px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_ok = QPushButton("▶ 확인 및 측정 시작 (Start Measurement)")
        self.btn_ok.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        self.btn_ok.setStyleSheet(
            "background-color: #16a34a; color: white; padding: 8px 20px; border-radius: 5px;"
        )
        self.btn_ok.clicked.connect(self.accept)
        self.chk_safety.toggled.connect(self.btn_ok.setEnabled)
        btn_row.addWidget(self.btn_ok)

        layout.addLayout(btn_row)
