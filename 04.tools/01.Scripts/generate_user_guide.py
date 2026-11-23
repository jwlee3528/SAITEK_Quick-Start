# -*- coding: utf-8 -*-
r"""
Tektronix & Keithley Multi-Category QuickStart Program
Beginner-Friendly GUI User Guide Generator (PPTX + PDF + Annotated GUI Screenshots)

Captures real live GUI screenshots from the PyQt6 application, adds numbered
visual callout badges (1, 2, 3...) and highlight boxes, and generates:
1. 01.docs\06.development_guides\TekQuickStart_Beginner_User_Guide.pptx (PowerPoint)
2. 01.docs\06.development_guides\TekQuickStart_Beginner_User_Guide.pdf  (PDF Manual)
3. Copies of both in 06.Release\ for easy distribution alongside TekQuickStart_Setup.exe
"""

import os
import sys
import shutil
from typing import List, Tuple, Dict, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(BASE_DIR, "02.src")
for _sub in ("01.Core", "02.Modules", "03.Drivers", "04.Utils", "05.Config", "06.Main"):
    _p = os.path.join(SRC_DIR, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRectF, QMarginsF
from PyQt6.QtGui import (
    QFont,
    QPdfWriter,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QImage,
    QPageSize,
    QPageLayout,
)

from pptx import Presentation
from pptx.util import Emu, Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from instrument_profiles import CATEGORY_PROFILES
from visa_manager import VisaConnectionManager
from instrument_drivers import create_driver_for_category
from dialogs import StartupReadinessDialog, PreStartConfirmDialog
from main_app import TekQuickStartMainWindow


GUIDE_DIR = os.path.join(BASE_DIR, "01.docs", "06.development_guides")
SCREENSHOT_DIR = os.path.join(GUIDE_DIR, "screenshots")
RELEASE_DIR = os.path.join(BASE_DIR, "06.Release")

PPTX_PATH = os.path.join(GUIDE_DIR, "TekQuickStart_Beginner_User_Guide.pptx")
PDF_PATH = os.path.join(GUIDE_DIR, "TekQuickStart_Beginner_User_Guide.pdf")


def get_pil_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        r"C:\Windows\Fonts\malgunbd.ttf" if bold else r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ]
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def grab_widget_png(widget: QWidget, out_path: str) -> str:
    """Renders a QWidget to a crisp PNG file."""
    QApplication.processEvents()
    pixmap = widget.grab()
    pixmap.save(out_path, "PNG")
    return out_path


def annotate_image_ratio(
    src_png: str,
    boxes_and_badges: List[Tuple[int, Tuple[float, float, float, float], str]],
    badge_color: Tuple[int, int, int] = (220, 38, 38),
) -> str:
    """
    Draws highlighted bounding boxes and numbered callout badges using normalized (0.0~1.0) coordinates
    so that DPI scaling never shifts the boxes.
    """
    img = Image.open(src_png).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_lbl = get_pil_font(max(13, int(h * 0.019)), bold=True)

    for num, (rx1, ry1, rx2, ry2), label in boxes_and_badges:
        x1 = max(3, min(w - 6, int(rx1 * w)))
        y1 = max(3, min(h - 6, int(ry1 * h)))
        x2 = max(x1 + 16, min(w - 3, int(rx2 * w)))
        y2 = max(y1 + 16, min(h - 3, int(ry2 * h)))

        draw.rectangle([x1, y1, x2, y2], fill=(239, 68, 68, 18), outline=(220, 38, 38, 245), width=3)

        bbox = draw.textbbox((0, 0), f" [{num}] {label} ", font=font_lbl)
        tw = bbox[2] - bbox[0] + 12
        th = bbox[3] - bbox[1] + 10

        bx = min(max(4, x1), max(4, w - tw - 4))
        by = y1 - th - 2 if y1 >= (th + 6) else y1 + 3

        draw.rounded_rectangle(
            [bx, by, min(w - 3, bx + tw), by + th],
            radius=5,
            fill=(badge_color[0], badge_color[1], badge_color[2], 245),
            outline=(255, 255, 255, 255),
            width=2,
        )
        draw.text((bx + 6, by + 2), f"[{num}] {label}", fill=(255, 255, 255, 255), font=font_lbl)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(src_png, "PNG")
    return src_png


def create_beginner_guide_popup_image(item_spec: Any, model_name: str, out_path: str) -> str:
    """Renders a high-res visual capture of the [📘 초보자 연결 가이드 보기] popup dialog."""
    w, h = 980, 580
    img = Image.new("RGB", (w, h), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    f_title = get_pil_font(19, bold=True)
    f_sec = get_pil_font(15, bold=True)
    f_body = get_pil_font(13, bold=False)
    f_bold = get_pil_font(13, bold=True)

    # Window Title Bar
    draw.rectangle([0, 0, w, 38], fill=(11, 37, 69))
    draw.text((16, 8), "★ 초보자 장비 연결 및 설정 가이드 팝업 ([초보자 연결 가이드 보기] 클릭 시 표시)", fill=(255, 255, 255), font=f_sec)

    # Top item header box
    draw.rounded_rectangle([18, 52, w - 18, 138], radius=8, fill=(239, 246, 255), outline=(59, 130, 246), width=2)
    draw.text((32, 62), f"▶ {item_spec.title}", fill=(29, 78, 216), font=f_title)
    draw.text((32, 96), f"• 대상 모델: {model_name}\n• 핵심 설명: {item_spec.description}", fill=(30, 58, 138), font=f_body)

    # Step-by-step instructions box
    draw.rounded_rectangle([18, 152, w - 18, 435], radius=8, fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    draw.rectangle([18, 152, 26, 435], fill=(2, 132, 199))
    draw.text((38, 164), "▶ 초보자 따라하기 순서 (장비 케이블 연결 및 전면 패널 메뉴 조작법):", fill=(3, 105, 161), font=f_sec)

    cy = 198
    steps = getattr(item_spec, "how_to_steps", [])
    for s in steps:
        # Wrap long lines neatly
        line_chunks = [s[i:i + 74] for i in range(0, len(s), 74)]
        for c_idx, chunk in enumerate(line_chunks):
            prefix = "   " if c_idx > 0 else ""
            draw.text((42, cy), prefix + chunk, fill=(15, 23, 42), font=f_body)
            cy += 24
        cy += 8

    # Bottom verification command & expected result box
    draw.rounded_rectangle([18, 448, w - 18, 525], radius=8, fill=(220, 252, 231), outline=(74, 222, 128), width=2)
    draw.text(
        (34, 458),
        f"▶ 자동 검증 명령어 (Verify Command):  {item_spec.verify_cmd}",
        fill=(22, 101, 52),
        font=f_bold,
    )
    draw.text(
        (34, 486),
        f"✔ 정상 연결 시 기대 응답 (Expected Result):  {item_spec.expected_hint}",
        fill=(22, 101, 52),
        font=f_body,
    )

    # OK Button
    draw.rounded_rectangle([w - 150, 534, w - 18, 570], radius=6, fill=(2, 132, 199))
    draw.text((w - 114, 543), "확인 (OK)", fill=(255, 255, 255), font=f_bold)

    img.save(out_path, "PNG")
    annotate_image_ratio(
        out_path,
        [
            (1, (0.018, 0.09, 0.982, 0.24), "점검 단계 제목 및 왜 이 설정이 필요한지 초보자 눈높이 설명"),
            (2, (0.018, 0.265, 0.982, 0.75), "1단계 ~ 4단계 따라하기 순서 (케이블 포트 위치 & 장비 버튼 조작 순서)"),
            (3, (0.018, 0.775, 0.982, 0.905), "[단계별 확인] 버튼 클릭 시 전송되는 검증 명령어와 정상 응답 기준"),
        ],
    )
    return out_path


def create_installer_preview_image(out_path: str) -> str:
    """Renders a high-res visual mockup of the TekQuickStart_Setup.exe GUI Wizard with annotations."""
    w, h = 960, 620
    img = Image.new("RGB", (w, h), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    f_title = get_pil_font(20, bold=True)
    f_sub = get_pil_font(13, bold=False)
    f_sec = get_pil_font(15, bold=True)
    f_mono = get_pil_font(14, bold=False)
    f_btn = get_pil_font(15, bold=True)

    # Window title bar
    draw.rectangle([0, 0, w, 36], fill=(30, 41, 59))
    draw.text((14, 7), "Tektronix & Keithley QuickStart Program v1.2 - 통합 설치 마법사 (TekQuickStart_Setup.exe)", fill=(248, 250, 252), font=f_sub)

    # Top Header Banner
    draw.rounded_rectangle([20, 50, w - 20, 140], radius=8, fill=(30, 41, 59), outline=(56, 189, 248), width=2)
    draw.text((36, 62), "⚡ Tektronix & Keithley QuickStart Program 통합 설치 마법사", fill=(56, 189, 248), font=f_title)
    draw.text(
        (36, 94),
        "다른 PC에 Python이나 별도 패키지가 전혀 설치되어 있지 않아도 실행에 필요한 모든 런타임 파일,\n"
        "8개 장비 폴더별 30종 PDF 매뉴얼, 가상 시뮬레이터 및 실행 파일(TekQuickStart.exe)을 한 번에 설치합니다.",
        fill=(203, 213, 225),
        font=f_sub,
    )

    # Included Components Box
    draw.rounded_rectangle([20, 155, w - 20, 285], radius=8, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
    draw.text((34, 163), "📦 설치 포함 구성 요소 (Included Components)", fill=(56, 189, 248), font=f_sec)
    draw.text(
        (38, 192),
        "• 실행 파일 (TekQuickStart.exe) + 내장 Python / PyQt6 / PyQtGraph / NumPy / OpenPyXL / PyVISA-py 엔진\n"
        "• 8대 계측기 폴더별 모듈 (01.AFGs / 02.DC Power / 03.MP5000 / 04.Scopes / 05.RSA / 06.SMUs / 07.Tek VISA / 08.DMM)\n"
        "• 초보자용 단계별 장비 연결 점검 마법사 + 30종 공식 프로그래머 매뉴얼 PDF 원본 (01.docs/10. Tek_Manuals)\n"
        "• 물리 엔진 기반 가상 장비 시뮬레이터 ([VIRTUAL] 모드) + Run History 비교 + Excel/CSV/PNG 자동 리포트 출력기",
        fill=(226, 232, 240),
        font=f_sub,
    )

    # Directory Selection Box
    draw.rounded_rectangle([20, 300, w - 20, 385], radius=8, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
    draw.text((34, 308), "📁 설치 폴더 선택 (Installation Directory)", fill=(56, 189, 248), font=f_sec)
    draw.rounded_rectangle([36, 338, w - 180, 372], radius=4, fill=(30, 41, 59), outline=(100, 116, 139), width=1)
    draw.text((48, 346), r"C:\TekQuickStart", fill=(248, 250, 252), font=f_mono)
    draw.rounded_rectangle([w - 168, 338, w - 36, 372], radius=4, fill=(51, 65, 85))
    draw.text((w - 152, 346), "폴더 찾아보기...", fill=(248, 250, 252), font=f_sub)

    # Shortcut Options Box
    draw.rounded_rectangle([20, 400, w - 20, 505], radius=8, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
    draw.text((34, 408), "⚙️ 바로가기 및 실행 옵션 (Shortcut & Launch Options)", fill=(56, 189, 248), font=f_sec)
    draw.text((42, 436), "☑ 바탕화면에 [Tektronix QuickStart] 실행 바로가기 아이콘 생성 (권장)", fill=(226, 232, 240), font=f_sub)
    draw.text((42, 458), "☑ Windows 시작 메뉴에 [Tektronix QuickStart] 프로그램 등록", fill=(226, 232, 240), font=f_sub)
    draw.text((42, 480), "☑ 설치 완료 후 Tektronix QuickStart 프로그램 즉시 실행 (TekQuickStart.exe)", fill=(226, 232, 240), font=f_sub)

    # Progress & Bottom Buttons
    draw.text((24, 518), "✅ 설치 준비 완료: [프로그램 설치 시작] 버튼을 클릭하면 모든 파일이 자동 설치됩니다.", fill=(167, 243, 208), font=f_sub)
    draw.rounded_rectangle([20, 542, w - 20, 560], radius=4, fill=(30, 41, 59), outline=(51, 65, 85))
    draw.rounded_rectangle([22, 544, 620, 558], radius=3, fill=(2, 132, 199))

    draw.rounded_rectangle([20, 570, 190, 608], radius=6, fill=(51, 65, 85))
    draw.text((44, 580), "닫기 / 취소 (Cancel)", fill=(226, 232, 240), font=f_sub)

    draw.rounded_rectangle([w - 310, 570, w - 20, 608], radius=6, fill=(2, 132, 199))
    draw.text((w - 288, 579), "🚀 프로그램 설치 시작 (Install Now)", fill=(255, 255, 255), font=f_btn)

    img.save(out_path, "PNG")
    annotate_image_ratio(
        out_path,
        [
            (1, (0.02, 0.48, 0.98, 0.62), "설치할 폴더 경로 확인 (기본값 C:\\TekQuickStart)"),
            (2, (0.02, 0.645, 0.98, 0.815), "바탕화면 바로가기 & 설치 후 즉시 실행 체크"),
            (3, (0.675, 0.915, 0.98, 0.985), "[프로그램 설치 시작] 클릭 -> 원클릭 설치 완료"),
        ],
    )
    return out_path


def create_excel_report_preview_image(out_path: str) -> str:
    """Renders a visual guide of the 4-Sheet Excel (.xlsx) Report structure."""
    w, h = 1100, 620
    img = Image.new("RGB", (w, h), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    f_title = get_pil_font(20, bold=True)
    f_sec = get_pil_font(15, bold=True)
    f_body = get_pil_font(13, bold=False)
    f_bold = get_pil_font(13, bold=True)

    # Excel Green Banner
    draw.rectangle([0, 0, w, 54], fill=(21, 128, 61))
    draw.text((20, 14), "📊 Tektronix QuickStart - 자동 생성 4-시트 Excel (.xlsx) 측정 리포트 구성도", fill=(255, 255, 255), font=f_title)

    cards = [
        (
            "시트 1: 1_Summary_Checklist (측정 요약 및 사전 점검 기록)",
            (20, 74, 535, 320),
            (30, 58, 138),
            [
                "• 측정 리포트 생성 시각 / 장비 폴더 분류 / 선택 장비 모델명",
                "• 참조한 PDF 프로그래머 매뉴얼 파일명",
                "• 연결된 VISA 리소스 주소 및 동작 모드 (실제 장비 / 가상 시뮬레이션)",
                "• 장비 식별 정보 (*IDN? 응답 문자열) 및 총 기록 데이터 포인트 수",
                "• [사전 준비 점검표] 각 항목별 사용자 확인 완료 여부 자동 기록",
            ],
        ),
        (
            "시트 2: 2_Input_Configuration (입력 파라미터 & 선택 측정 항목)",
            (565, 74, 1080, 320),
            (3, 105, 161),
            [
                "• 측정 시작 전 사용자가 설정한 모든 [사용자 입력 필수 파라미터] 값",
                "  (예: 출력 주파수 1000 Hz, 진폭 2.5 Vpp, 목표 전압 5.0 V, 전류 제한 1.0 A 등)",
                "• 사용자가 체크한 [측정 가능 항목 (Measurable Items)] 활성화 목록",
                "• 재현성 검증: 동일한 조건으로 재측정할 때 설정값을 그대로 참조 가능",
            ],
        ),
        (
            "시트 3: 3_Measured_Data (시계열 측정 데이터 + 자동 통계 요약)",
            (20, 340, 535, 595),
            (21, 128, 61),
            [
                "• 측정 시각(Timestamp) 및 경과 시간(Elapsed_s)별 모든 측정 데이터 기록",
                "• 데이터 하단에 4대 핵심 통계치 자동 계산 및 하이라이트 표시:",
                "  1) 평균 (Mean)    2) 최댓값 (Max)",
                "  3) 최솟값 (Min)   4) 표준편차 (StdDev)",
                "• 별도 수식 입력 없이 보고서 및 품질 성적서에 즉시 활용 가능",
            ],
        ),
        (
            "시트 4: 4_Waveform_Trace (오실로스코프 파형 / RF 스펙트럼 원본)",
            (565, 340, 1080, 595),
            (109, 40, 217),
            [
                "• 화면 우측 그래프에 표시된 마지막 파형/스펙트럼/스윕 포인트 전체 저장",
                "• Point Index / X축 데이터 (시간 s, 주파수 MHz, 스윕 전압 V)",
                "• Y축 데이터 (전압 V, 스펙트럼 파워 dBm, 스윕 전류 A)",
                "• 엑셀 차트나 MATLAB/Python 후처리 분석용 로우 데이터로 즉시 활용",
            ],
        ),
    ]

    for idx, (title, (x1, y1, x2, y2), hdr_color, lines) in enumerate(cards, start=1):
        draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=(255, 255, 255), outline=hdr_color, width=2)
        draw.rounded_rectangle([x1, y1, x2, y1 + 40], radius=8, fill=hdr_color)
        draw.text((x1 + 14, y1 + 9), f"[{idx}] {title}", fill=(255, 255, 255), font=f_sec)
        cy = y1 + 54
        for line in lines:
            draw.text((x1 + 16, cy), line, fill=(30, 41, 59), font=f_body)
            cy += 34

    img.save(out_path, "PNG")
    return out_path


def simulate_panel_ticks(panel: Any, n_ticks: int = 8, keep_running: bool = False) -> None:
    """Runs n_ticks of simulated measurement on a CategoryWorkspacePanel for rich GUI screenshots."""
    for cb in panel.checklist_widgets.values():
        cb.setChecked(True)
    selected_meas = panel.collect_selected_measurables()
    inputs = panel.collect_inputs()
    model = panel.get_current_model()
    panel.clear_session_data()
    headers = ["Step", "Timestamp", "Elapsed (s)"] + [
        m.label for m in panel.profile.measurable_items if m.key in selected_meas
    ]
    panel._apply_table_headers(headers)
    panel.driver = create_driver_for_category(panel.visa_mgr, panel.profile.folder_id, model.model_id)
    panel.begin_new_run(model, inputs, selected_meas)
    panel.driver.configure_and_start(inputs, selected_meas)
    panel._set_state(panel.STATE_RUNNING)
    for _ in range(n_ticks):
        panel._on_measurement_tick()
    panel.timer.stop()
    if not keep_running:
        panel.on_stop_clicked()


def capture_all_gui_screenshots() -> Dict[str, str]:
    """Launches the live PyQt6 widgets offscreen/onscreen, simulates data, and captures annotated PNGs."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    paths: Dict[str, str] = {}
    cat_keys = list(CATEGORY_PROFILES.keys())

    # 1. Installer Wizard preview
    paths["installer"] = create_installer_preview_image(
        os.path.join(SCREENSHOT_DIR, "01_installer_wizard.png")
    )

    # 2. Startup Readiness Wizard Dialog (Tall 1180x940 capture so STEP 1, STEP 2, STEP 3 cards are fully visible)
    visa_mgr = VisaConnectionManager()
    visa_mgr.connect("SIM::SCOPE_MSO54::INSTR", simulation=True, category_id=cat_keys[3], model_id="MSO_4_5_6")

    startup_dlg = StartupReadinessDialog(
        visa_mgr=visa_mgr,
        category_profiles=CATEGORY_PROFILES,
        initial_category_id=cat_keys[3],
    )
    startup_dlg.resize(1180, 940)
    startup_dlg.show()
    QApplication.processEvents()

    p_startup = os.path.join(SCREENSHOT_DIR, "02_startup_readiness_wizard.png")
    grab_widget_png(startup_dlg, p_startup)
    annotate_image_ratio(
        p_startup,
        [
            (1, (0.01, 0.105, 0.99, 0.345), "STEP 1: 장비 분류(8개 폴더) & 세부 장비 모델 선택 + [선택 모델 PDF 매뉴얼 열기]"),
            (2, (0.01, 0.358, 0.99, 0.515), "STEP 2: 통신 포트 선택 / [가상 장비 시뮬레이션 모드] 체크 / [장비 연결 및 *IDN? 응답 확인]"),
            (3, (0.01, 0.528, 0.99, 0.915), "STEP 3: 초보자용 단계별 연결 점검표 ([초보자 따라하기 가이드] & 우측 [단계별 확인] 버튼)"),
            (4, (0.725, 0.935, 0.99, 0.992), "STEP 4: [선택한 장비 화면으로 이동하여 측정 시작하기] 클릭"),
        ],
    )
    paths["startup_wizard"] = p_startup

    # Also capture a verified view of the beginner step cards after clicking [⚡ 모든 항목 한 번에 자동 점검 & 체크하기]
    startup_dlg.verify_all_steps()
    startup_dlg._check_all_manually()
    QApplication.processEvents()
    p_startup_verified = os.path.join(SCREENSHOT_DIR, "03_startup_cards_verified.png")
    grab_widget_png(startup_dlg, p_startup_verified)
    annotate_image_ratio(
        p_startup_verified,
        [
            (1, (0.018, 0.462, 0.982, 0.508), "1) STEP 2 연결 성공 배너: 응답 시간(ms)과 장비 *IDN? 식별 문자열 즉시 표시"),
            (2, (0.805, 0.555, 0.985, 0.595), "2) [모든 항목 한 번에 자동 점검 & 체크하기] 또는 각 카드 우측 [단계별 확인] 클릭"),
            (3, (0.025, 0.605, 0.972, 0.895), "3) 카드 내부 [초보자 따라하기 가이드(1~4단계)] & 초록색 [확인 완료] 응답 결과 확인"),
        ],
    )
    paths["startup_verified"] = p_startup_verified

    # Capture the detailed Beginner Connection Guide Popup ([📘 초보자 연결 가이드 보기])
    sample_prof = CATEGORY_PROFILES[cat_keys[3]]
    paths["beginner_guide_popup"] = create_beginner_guide_popup_image(
        sample_prof.checklist[0],
        sample_prof.models[0].display_name,
        os.path.join(SCREENSHOT_DIR, "03b_beginner_guide_popup.png"),
    )
    startup_dlg.close()

    # 3. Main Window Overview & Category Tabs
    main_win = TekQuickStartMainWindow(skip_startup_dialog=True)
    main_win.resize(1380, 860)
    main_win.show()
    QApplication.processEvents()

    # Run measurement ticks on Tab 0 (01. AFGs) so the graph & table have rich data
    panel_afg = main_win.category_panels[cat_keys[0]]
    simulate_panel_ticks(panel_afg, n_ticks=6, keep_running=True)
    QApplication.processEvents()

    p_main_overview = os.path.join(SCREENSHOT_DIR, "04_main_window_overview.png")
    grab_widget_png(main_win, p_main_overview)
    annotate_image_ratio(
        p_main_overview,
        [
            (1, (0.006, 0.006, 0.994, 0.056), "(1) 상단 VISA 연결 바 ([시뮬레이션 모드] / 실제 장비 연결 / 사전 준비 점검표 / 긴급 정지)"),
            (2, (0.006, 0.062, 0.81, 0.098), "(2) 7대 장비 폴더별 탭 (01.AFGs ~ 07.Tek VISA)"),
            (3, (0.012, 0.195, 0.988, 0.425), "(3) 초보자용 단계별 리모트 준비 사항 점검표 (항목별 가이드 & 개별 상태 확인)"),
            (4, (0.012, 0.445, 0.255, 0.765), "(4) 좌측: 1. 입력이 필요한 사항 (Required Input Parameters)"),
            (5, (0.260, 0.445, 0.515, 0.765), "(5) 중앙: 2. 측정이 가능한 부분 (Measurable Items & 실시간 값)"),
            (6, (0.520, 0.445, 0.988, 0.765), "(6) 우측: 3. 측정 제어(시작/일시정지/완전정지/Excel) & 실시간 파형 그래프"),
            (7, (0.006, 0.785, 0.994, 0.968), "(7) 하단 콘솔: 직접 SCPI/TSP 명령어 송수신(Write/Query) 및 실시간 통신 로그"),
        ],
    )
    paths["main_overview"] = p_main_overview

    # 4. Pre-Start Confirmation Modal Dialog
    cat_scope = main_win.category_panels[cat_keys[3]]
    main_win.category_tabs.setCurrentIndex(3)
    QApplication.processEvents()

    inputs = cat_scope.collect_inputs()
    selected_meas = cat_scope.collect_selected_measurables()
    model = cat_scope.get_current_model()
    input_summary = [
        {"label": s.label, "value": f"{inputs.get(s.key)} {s.unit}".strip()}
        for s in cat_scope.profile.input_parameters
    ]
    meas_summary = [
        {"label": m.label, "unit": m.unit, "cmd": m.scpi_or_tsp_hint}
        for m in cat_scope.profile.measurable_items
        if m.key in selected_meas
    ]

    confirm_dlg = PreStartConfirmDialog(
        category_title=cat_scope.profile.title_ko,
        model_name=model.display_name,
        resource_addr="USB0::0x0699::0x0522::C012345::INSTR",
        is_simulation=True,
        has_power_output=cat_scope.profile.has_power_output,
        unchecked_items=[],
        input_summary=input_summary,
        selected_meas_summary=meas_summary,
        parent=main_win,
    )
    confirm_dlg.resize(780, 560)
    confirm_dlg.show()
    QApplication.processEvents()

    p_confirm = os.path.join(SCREENSHOT_DIR, "05_pre_start_confirm_dialog.png")
    grab_widget_png(confirm_dlg, p_confirm)
    annotate_image_ratio(
        p_confirm,
        [
            (1, (0.015, 0.015, 0.985, 0.115), "장비 모델 / 통신 리소스 주소 요약 확인"),
            (2, (0.015, 0.155, 0.492, 0.845), "[1] 장비에 전송할 사용자 입력 파라미터 확인 표"),
            (3, (0.505, 0.155, 0.985, 0.845), "[2] 연속 수집 및 그래프/엑셀에 기록할 측정 대상 항목 표"),
            (4, (0.655, 0.910, 0.985, 0.982), "[확인 및 측정 시작 (Start Measurement)] 클릭 시 실제 동작 개시"),
        ],
    )
    paths["pre_start_confirm"] = p_confirm
    confirm_dlg.close()

    # 4b. Run History / Compare / Cursors (KickStart-style features)
    main_win.category_tabs.setCurrentIndex(1)
    panel_hist = main_win.category_panels[cat_keys[1]]
    if hasattr(panel_hist, "btn_toggle_chk"):
        panel_hist.btn_toggle_chk.setChecked(False)
    simulate_panel_ticks(panel_hist, n_ticks=14)
    simulate_panel_ticks(panel_hist, n_ticks=14)
    QApplication.processEvents()

    # (a) live graph with 2 cursors + statistics
    panel_hist.plot_tabs.setCurrentIndex(0)
    panel_hist.cursor_bar.clear_cursors()
    panel_hist.cursor_bar.add_cursor()
    panel_hist.cursor_bar.add_cursor()
    QApplication.processEvents()
    p_cursor = os.path.join(SCREENSHOT_DIR, "11_graph_cursors.png")
    grab_widget_png(main_win, p_cursor)
    annotate_image_ratio(
        p_cursor,
        [
            (1, (0.53, 0.352, 0.985, 0.388), "그래프 도구: 커서 추가 / 시리즈 표시 / 축 범위 / 자동 스케일"),
            (2, (0.53, 0.390, 0.985, 0.452), "커서 2개 사이의 통계 (N / Min / Max / Mean / Pk-Pk / Δy)"),
            (3, (0.53, 0.672, 0.985, 0.765), "컬럼 머리글 우클릭 -> 이름 변경 / 숨기기 (표·내보내기에 반영)"),
        ],
    )
    paths["graph_cursors"] = p_cursor

    # (b) Run History tab with compared runs
    panel_hist.plot_tabs.setCurrentIndex(1)
    hist = panel_hist.history_tab
    hist.refresh_list(select_ids=[r.run_id for r in panel_hist.history_store.runs])
    hist.cursor_bar.clear_cursors()
    hist.cursor_bar.add_cursor()
    hist.cursor_bar.add_cursor()
    QApplication.processEvents()
    p_hist = os.path.join(SCREENSHOT_DIR, "12_run_history.png")
    grab_widget_png(main_win, p_hist)
    annotate_image_ratio(
        p_hist,
        [
            (1, (0.531, 0.36, 0.737, 0.53), "Run 목록: 여러 개 선택 -> 겹쳐서 비교"),
            (2, (0.531, 0.535, 0.737, 0.765), "자동 내보내기 / 선택·전체 Run 내보내기"),
            (3, (0.739, 0.36, 0.976, 0.67), "선택한 Run들의 겹쳐보기 그래프 + 커서 통계"),
        ],
    )
    paths["run_history"] = p_hist
    panel_hist.plot_tabs.setCurrentIndex(0)

    # 5. Capture active measurement screens for key categories (with checklist folded so graph & table are large!)
    tab_configs = [
        (1, "02_DC_Power", "06_cat02_dcpower.png", "02. DC power Supplies - 전압/전류/전력(W) 실시간 트렌드 그래프 & 데이터 표"),
        (3, "04_Oscilloscopes", "07_cat04_oscilloscope.png", "04. Oscilloscopes - 실시간 오실로스코프 파형 캡처 및 Vpp/주파수 자동 계측"),
        (4, "05_Spectrum_Analyzers", "08_cat05_spectrum.png", "05. Spectrum Analyzers - RF 스펙트럼 트레이스(dBm) 및 피크 주파수 탐색"),
        (5, "06_SMUs", "09_cat06_smu.png", "06. SMUs (Keithley 2450/2600B) - 정밀 I-V 스윕 곡선 및 저항/전력 측정"),
        (7, "08_DMM", "09b_cat08_dmm.png", "08. Digit Multimeter (DMM6500/7510/2110/2010) - 고정밀 전압/저항/디지타이저 측정"),
    ]

    for tab_idx, alias_key, fname, desc_label in tab_configs:
        main_win.category_tabs.setCurrentIndex(tab_idx)
        real_key = cat_keys[tab_idx]
        panel = main_win.category_panels[real_key]
        # Collapse checklist box so the 3 measurement columns and graph are large and clear
        if hasattr(panel, "btn_toggle_chk"):
            panel.btn_toggle_chk.setChecked(False)
        simulate_panel_ticks(panel, n_ticks=10, keep_running=True)
        QApplication.processEvents()

        out_p = os.path.join(SCREENSHOT_DIR, fname)
        grab_widget_png(main_win, out_p)
        annotate_image_ratio(
            out_p,
            [
                (1, (0.012, 0.215, 0.255, 0.765), "1) 좌측: 입력이 필요한 사항 (Required Input Parameters)"),
                (2, (0.260, 0.215, 0.515, 0.765), "2) 중앙: 측정이 가능한 부분 (Measurable Items & 실시간 측정값)"),
                (3, (0.520, 0.215, 0.988, 0.765), f"3) 우측: {desc_label}"),
            ],
        )
        paths[alias_key] = out_p

    main_win.close()

    # 6. Excel Report 4-sheet preview
    paths["excel_preview"] = create_excel_report_preview_image(
        os.path.join(SCREENSHOT_DIR, "10_excel_report_preview.png")
    )

    return paths


def get_guide_pages(screenshots: Dict[str, str]) -> List[Dict[str, Any]]:
    """Defines the 14 structured pages/slides of the Beginner User Guide."""
    return [
        {
            "page_no": 1,
            "badge": "초보자용 완벽 매뉴얼",
            "title": "Tektronix & Keithley QuickStart Program v1.2 사용자 가이드",
            "subtitle": "설치(Setup.exe)부터 8대 제품군 장비 연결·사전 점검·실시간 측정·그래프·Run History·Excel 저장까지 초보자용 단계별 안내서",
            "image": screenshots["main_overview"],
            "steps": [
                ("목적", "계측기 프로그래밍이나 SCPI/TSP 명령어를 전혀 모르는 초보자도 안내 화면만 따라 하면 8대 제품군 계측기를 안전하게 연결하고 측정·저장할 수 있습니다."),
                ("설치 파일 배포", "다른 PC에 Python이나 라이브러리가 전혀 없어도 TekQuickStart_Setup.exe 설치 파일 하나로 모든 필수 파일과 30종 PDF 매뉴얼이 자동 설치됩니다."),
                ("가상 연습 모드 기본 내장", "실제 장비가 책상에 없어도 [VIRTUAL] 가상 시뮬레이션 모드로 모든 장비의 파형과 측정 동작을 100% 동일하게 연습할 수 있습니다."),
                ("4단계 안전 워크플로우", "① 사전 준비 점검 마법사 → ② 입력 파라미터 & 측정 항목 설정 → ③ 동작 전 최종 확인 팝업 → ④ 실시간 그래프 측정 및 Excel(.xlsx) 저장"),
            ],
            "tip": "💡 본 가이드는 실제 프로그램 GUI 화면에 표시된 번호([1], [2], [3]...) 순서대로만 클릭하면 누구나 즉시 측정할 수 있도록 구성되었습니다.",
        },
        {
            "page_no": 2,
            "badge": "핵심 구성 요약",
            "title": "프로그램 4대 핵심 기능 및 8개 계측기 폴더 구성",
            "subtitle": "docs >> Tek_Manuals 내 8개 폴더·30종 공식 프로그래머/레퍼런스 매뉴얼 기반 통합 퀵스타트 아키텍처",
            "image": screenshots["main_overview"],
            "steps": [
                ("1. 8개 매뉴얼 폴더별 전용 탭 분리", "• 01. AFGs (함수발생기)  • 02. DC power Supplies  • 03. DC Precision Test (MP5000)  • 04. Oscilloscopes\n• 05. Spectrum Analyzers (RSA)  • 06. SMUs (소스미터)  • 07. Tek VISA  • 08. Digit Multimeter (DMM)"),
                ("2. [입력 필수 사항]과 [측정 가능 항목] 분리", "장비에 인가할 설정값(주파수·전압·전류제한·NPLC 등)과 읽어올 측정 항목(전압·전류·저항·Vpp·피크파워 등)을 명확히 구분하고, 시작 전 확인 팝업으로 오동작을 방지합니다."),
                ("3. 직관적인 측정 제어 & 그래프 & 엑셀", "• [▶ 측정 및 동작 시작]  • [⏸ 일시정지 / ▶ 재개]  • [⏹ 완전 정지 (출력 즉시 OFF 안전 차단)]\n• 우측 실시간 파형/트렌드 그래프(pyqtgraph), 커서 통계, Run History 비교 및 4-시트 Excel(.xlsx) 저장"),
                ("4. 초보자용 단계별 장비 연결 점검표", "케이블 연결부터 장비 화면 메뉴 설정, 통신 응답(*IDN?, *LANG?, :ROUT:TERM?, 에러 큐)까지 항목별 [⚡ 상태 확인] 버튼으로 즉시 진단합니다."),
            ],
            "tip": "💡 각 폴더 탭에서 [📖 매뉴얼 열기] 버튼을 누르면 해당 장비의 공식 PDF 프로그래머 매뉴얼 원본이 즉시 열립니다.",
        },
        {
            "page_no": 3,
            "badge": "STEP 0 : 프로그램 설치",
            "title": "다른 PC에 프로그램 설치하기 (TekQuickStart_Setup.exe)",
            "subtitle": "아무것도 설치되지 않은 새 Windows PC에서 통합 설치 마법사로 원클릭 설치하는 방법",
            "image": screenshots["installer"],
            "steps": [
                ("[1] 설치 폴더 경로 확인", "• 배포 폴더(06.Release)의 TekQuickStart_Setup.exe 파일을 실행합니다.\n• 기본 설치 경로는 C:\\TekQuickStart 이며, [폴더 찾아보기...] 버튼으로 원하는 위치로 변경할 수 있습니다."),
                ("[2] 바로가기 및 자동 실행 옵션 선택", "• [바탕화면에 실행 바로가기 아이콘 생성]: 바탕화면에 'Tektronix QuickStart' 아이콘을 만듭니다.\n• [설치 완료 후 즉시 실행]: 설치가 끝나자마자 자동으로 프로그램을 띄워줍니다."),
                ("[3] [🚀 프로그램 설치 시작] 버튼 클릭", "• 버튼을 클릭하면 내장된 실행 엔진(TekQuickStart.exe), 런타임 DLL, 26종 PDF 매뉴얼이 자동 압축 해제됩니다.\n• 설치 완료 메시지 확인 후 프로그램이 곧바로 실행됩니다."),
                ("무설치(Portable) 실행 방법", "• 설치 과정 없이 06.Release\\TekQuickStart_Portable\\TekQuickStart.exe 파일을 직접 더블클릭해도 동일하게 실행됩니다."),
            ],
            "tip": "💡 실제 장비를 USB 케이블로 연결할 PC라면 TekVISA 또는 NI-VISA 드라이버를 함께 설치해 두면 USB 장비가 자동 검색됩니다.",
        },
        {
            "page_no": 4,
            "badge": "STEP 1 : 첫 실행 연결 가이드 팝업 (1/3)",
            "title": "프로그램 첫 시작 시 뜨는 [초보자용 장비-PC 연결 가이드 팝업창] 전체 구조",
            "subtitle": "TekQuickStart.exe를 실행하면 가장 먼저 열리는 연결 마법사 팝업창의 4단계(STEP 1 ~ STEP 4) 구성 안내",
            "image": screenshots["startup_wizard"],
            "steps": [
                ("[1] STEP 1. 연결할 장비 종류(8개 폴더)와 세부 모델 선택", "• ① 장비 분류(01.AFGs ~ 08.Digit Multimeter)와 ② 세부 장비 모델을 선택합니다.\n• 선택 즉시 아래 파란색 요약 박스에 해당 모델의 [지원 연결 인터페이스(USB/LAN/GPIB)], [채널 수], [매뉴얼 핵심 연결 안내]가 자동 표시되며, 우측 [📖 선택 모델 PDF 매뉴얼 열기]로 원본 매뉴얼을 바로 볼 수 있습니다."),
                ("[2] STEP 2. PC와 장비 통신 포트 선택 및 연결 확인", "• 현재 감지된 VISA 엔진과 통신 포트(리소스) 목록을 보여줍니다. 케이블 연결 후 [🔄 포트 다시 찾기]로 검색합니다.\n• 실제 장비 없이 연습할 때는 보라색 [☑ 가상 장비 시뮬레이션 모드 사용]을 체크한 상태로 진행합니다."),
                ("[3] STEP 3. 초보자용 단계별 연결 점검표 (스크롤 영역)", "• 선택한 장비 전용 점검 카드(1단계 케이블 연결 ~ 4단계 설정 확인)가 순서대로 나열됩니다.\n• 각 카드 안에는 파란색 [📘 초보자 따라하기 가이드 - 장비/PC 조작 순서]가 펼쳐져 있어 그대로 따라 할 수 있습니다."),
                ("[4] 메인 측정 화면으로 이동", "• 점검이 끝나면 우측 하단 파란색 [🚀 선택한 장비 화면으로 이동하여 측정 시작하기]를 클릭해 메인 화면으로 진입합니다."),
            ],
            "tip": "💡 메인 화면에 들어간 뒤에도 언제든 상단 바의 파란색 [📋 사전 준비 점검표] 버튼을 누르면 이 연결 가이드 팝업창을 다시 열 수 있습니다.",
        },
        {
            "page_no": 5,
            "badge": "STEP 1 : 첫 실행 연결 가이드 팝업 (2/3)",
            "title": "시작 팝업창에서 장비 연결 테스트 및 단계별 [확인] 버튼 실행하기",
            "subtitle": "[📡 STEP 2: 장비 연결 및 *IDN? 응답 확인]과 [⚡ 모든 항목 한 번에 자동 점검]으로 통신 상태를 즉시 진단하는 방법",
            "image": screenshots["startup_verified"],
            "steps": [
                ("[1] [📡 STEP 2: 장비 연결 및 *IDN? 응답 확인] 클릭", "• 초록색 버튼을 누르면 장비에 *IDN? 식별 명령을 보내고, 아래 상태줄이 초록색 [✅ 연결 성공 (1.1 ms) | *IDN? 응답: TEKTRONIX,...]으로 바뀌며 통신 개통 여부를 즉시 알려줍니다."),
                ("[2] 개별 확인 [🔍 1단계 확인] 또는 일괄 확인 [⚡ 자동 점검]", "• 각 점검 카드 우측의 파란색 [🔍 1단계/2단계 확인] 버튼을 하나씩 눌러 단계별로 검증하거나,\n• 우측 상단 보라색 [⚡ 모든 항목 한 번에 자동 점검 & 체크하기] 버튼 하나로 전체 단계를 한 번에 자동 검사할 수 있습니다."),
                ("[3] 카드 내부 초록색 [✅ 확인 완료] 결과 및 자동 체크", "• 통신 검증에 성공한 카드는 테두리와 하단 결과창이 초록색([✅ 확인 완료 | 명령: *IDN? → 응답: ...])으로 바뀌며 좌측 체크박스(☑)가 자동으로 체크됩니다."),
                ("점검 진행률 실시간 표시", "• 좌측 상단 '점검 진행률: 3 / 3 단계 확인 완료'가 초록색으로 바뀌면 모든 사전 준비가 완벽히 끝난 것입니다."),
            ],
            "tip": "💡 만약 실제 장비가 아직 준비되지 않았다면 좌측 하단 [☑ 수동으로 전체 체크]를 누르거나 가상 시뮬레이션 모드로 통과할 수 있습니다.",
        },
        {
            "page_no": 6,
            "badge": "STEP 1 : 초보자 연결 가이드 상세 (3/3)",
            "title": "[📘 초보자 연결 가이드 보기] 팝업창 및 장비별 케이블·메뉴 조작법",
            "subtitle": "시작 팝업창의 카드 내부 안내 및 메인 화면에서 [📘 초보자 연결 가이드 보기] 클릭 시 뜨는 상세 안내 팝업창",
            "image": screenshots["beginner_guide_popup"],
            "steps": [
                ("[1] 점검 항목 제목 및 핵심 설명 확인", "• 시작 팝업창의 각 카드 또는 메인 화면 점검표에서 [📘 초보자 연결 가이드 보기] 버튼을 누르면 위와 같은 상세 연결 가이드 팝업이 열립니다.\n• 초보자가 가장 흔히 실수하는 부분(예: USB 메모리용 Host 포트와 PC 연결용 Device 포트 구분, 전면/후면 단자 스위치 등)을 먼저 알려줍니다."),
                ("[2] 1단계 ~ 4단계 따라하기 순서 (장비/PC 조작 순서)", "• 1) 장비의 어느 포트에 무슨 케이블(USB Type-B, USB 3.0, LAN, 바나나잭/트라이액셜)을 꽂아야 하는지,\n• 2) 장비 전면 패널에서 어떤 버튼(예: Utility > I/O, MENU > System > Communication, INPUTS Front/Rear 스위치)을 눌러야 하는지 번호 순서대로 자세히 설명합니다."),
                ("[3] 자동 검증 명령어 및 정상 응답 기준 명시", "• 우측 [🔍 상태 확인] 버튼을 눌렀을 때 프로그램이 내부적으로 어떤 SCPI/TSP 명령어(*IDN?, *LANG?, :ROUT:TERM?, SYST:ERR?)를 보내고 어떤 응답이 와야 정상인지 명확히 보여줍니다."),
                ("8대 제품군 30종 전 모델 맞춤 가이드 내장", "• 오실로스코프, AFG, 파워서플라이, MP5000, 스펙트럼 분석기, SMU, Tek VISA, DMM(DMM6500/7510/2110/2010) 각 모델의 매뉴얼 연결 절차가 모두 한국어로 수록되어 있습니다."),
            ],
            "tip": "💡 장비 연결이 막힐 때는 당황하지 말고 [📘 초보자 연결 가이드 보기]의 1~4번 순서와 [📖 선택 모델 PDF 매뉴얼 열기]를 차례대로 확인하세요.",
        },
        {
            "page_no": 6,
            "badge": "STEP 2 : 메인 화면 구조",
            "title": "메인 프로그램 전체 화면 구성 한눈에 보기 (6대 영역)",
            "subtitle": "어떤 장비 탭을 선택하든 동일한 위치와 사용법으로 통일된 6대 작업 영역",
            "image": screenshots["main_overview"],
            "steps": [
                ("① 상단 VISA 리소스 연결 바 & ② 장비 폴더 탭", "• ① 상단 바에서 연결할 장비 주소를 고르고 [🔗 연결], [🆔 *IDN? 조회], [🔄 *RST 리셋]을 수행합니다.\n• ② 바로 아래 7개 탭(01.AFGs ~ 07.Tek VISA) 중 사용할 장비 폴더를 클릭해 전환합니다."),
                ("③ 좌측 패널 (모델·점검표·입력 파라미터)", "• 사용할 세부 장비 모델 선택 및 [📖 매뉴얼 열기]\n• 해당 장비의 [사전 준비 점검표] 및 장비에 설정할 [사용자 입력 필수 파라미터] 입력 폼이 위치합니다."),
                ("④ 중앙 패널 (측정 항목 & 시작/일시정지/정지)", "• 장비에서 읽어올 [측정 가능 항목 (Measurable Items)] 체크박스 목록\n• [▶ 측정 시작], [⏸ 일시정지], [⏹ 완전 정지], [📊 Excel(.xlsx) 저장] 제어 버튼이 모여 있습니다."),
                ("⑤ 우측 그래프/데이터 표 & ⑥ 하단 I/O 콘솔", "• ⑤ 우측에는 실시간 파형/트렌드 그래프와 시계열 측정값 표가 실시간 업데이트됩니다.\n• ⑥ 하단 콘솔에서는 모든 SCPI/TSP 송수신 명령어 로그와 응답 시간(ms)을 투명하게 확인할 수 있습니다."),
            ],
            "tip": "💡 각 영역 사이의 경계선(Splitter)을 마우스로 드래그하거나, 점검표/로그 표의 [접기] 버튼을 누르면 작은 노트북 화면에서도 넓게 쓸 수 있습니다.",
        },
        {
            "page_no": 7,
            "badge": "STEP 3 : 장비 연결 (가상 vs 실제)",
            "title": "상단 VISA 리소스 연결 바 사용법 ([VIRTUAL] vs 실제 계측기)",
            "subtitle": "가상 장비로 안전하게 연습하거나 USB / LAN 케이블로 실제 계측기에 연결하는 방법",
            "image": screenshots["main_overview"],
            "steps": [
                ("방법 A: 장비 없이 연습할 때 ([VIRTUAL] 모드)", "• 상단 우측의 [🟢 [VIRTUAL] 가상 시뮬레이션 모드 (장비 없이 테스트)] 버튼이 켜져(초록색) 있으면 가상 모드입니다.\n• 실제 계측기가 없어도 7개 폴더의 모든 장비가 실제 물리 공식대로 파형과 측정값을 생성합니다."),
                ("방법 B: 실제 계측기에 연결할 때 (USB / LAN)", "1) 장비에 USB 또는 LAN 케이블을 연결하고 전원을 켭니다.\n2) 상단 [🔍 리소스 검색] 버튼을 누른 뒤 드롭다운에서 검색된 장비 주소(예: USB0::0x0699::...::INSTR)를 선택합니다.\n3) 우측의 [VIRTUAL] 버튼을 클릭해 [⚪ 실제 장비 VISA 모드]로 전환하고 [🔗 연결]을 누릅니다."),
                ("연결 상태 즉시 확인 ([🆔 *IDN? 조회])", "• [🆔 *IDN? 조회] 버튼을 클릭했을 때 팝업 창에 제조사, 모델명, 시리얼 번호, 펌웨어 버전이 나타나면 통신이 100% 성공한 것입니다."),
                ("장비 초기화 ([🔄 *RST 리셋])", "• 측정 전 장비 설정을 공장 초기 상태로 깔끔하게 되돌리고 싶을 때 [🔄 *RST 리셋] 버튼을 클릭합니다."),
            ],
            "tip": "💡 LAN(이더넷)으로 장비를 연결할 때는 드롭다운에 TCPIP0::<장비IP주소>::inst0::INSTR 또는 ::5025::SOCKET 형식으로 직접 입력해도 됩니다.",
        },
        {
            "page_no": 8,
            "badge": "STEP 4 : 좌측 패널 설정",
            "title": "장비 모델 선택, 매뉴얼 열기 및 [사용자 입력 필수 파라미터] 설정",
            "subtitle": "측정 및 동작 시작 전에 장비에 인가할 조건(전압, 주파수, 채널, 제한값 등)을 입력하는 방법",
            "image": screenshots["main_overview"],
            "steps": [
                ("1. 장비 모델 선택 & [📖 매뉴얼 열기]", "• 좌측 상단 드롭다운에서 현재 사용하는 장비 모델(예: AFG31000, MSO54, Keithley 2450 등)을 선택합니다.\n• [📖 매뉴얼 열기]를 클릭하면 해당 모델의 PDF 프로그래머 매뉴얼이 즉시 열립니다."),
                ("2. 좌측 [사전 준비 점검표] 확인", "• 아직 체크하지 않은 점검 항목이 있다면 카드 내 [⚡ 상태 확인]을 누르거나 [☑ 모두 체크 완료]를 클릭합니다.\n• 점검이 끝난 뒤에는 [🔼 점검표 접기]를 눌러 아래 입력 파라미터 공간을 넓게 볼 수 있습니다."),
                ("3. [사용자 입력 필수 파라미터] 값 입력", "• 좌측 하단 박스에서 장비 동작에 필요한 파라미터를 설정합니다.\n• 각 입력칸에는 안전한 최소~최대 범위와 단위(Hz, V, A, dBm, ms)가 지정되어 있으며, 마우스를 올리면 매뉴얼 기반 상세 툴팁과 SCPI 명령어가 표시됩니다."),
                ("4. 측정 수집 주기 (Poll Interval) 설정", "• 데이터를 몇 ms 간격으로 읽어올지 설정합니다 (기본값 300~500 ms, 빠른 파형 갱신은 100~200 ms 권장)."),
            ],
            "tip": "💡 입력 파라미터 값을 변경한 뒤 [▶ 측정 및 동작 시작]을 누르면 프로그램이 자동으로 해당 SCPI/TSP 설정 명령을 장비에 전송합니다.",
        },
        {
            "page_no": 9,
            "badge": "STEP 5 : 측정 항목 선택 & 시작 전 확인",
            "title": "[측정 가능 항목] 선택 및 동작 전 최종 확인 팝업 (안전 장치)",
            "subtitle": "사용자가 입력한 설정값과 측정 항목을 동작 직전에 한 번 더 확인하여 장비와 회로를 보호합니다",
            "image": screenshots["pre_start_confirm"],
            "steps": [
                ("[1] 중앙 패널에서 [측정 가능 항목] 체크", "• 중앙 상단 박스에서 장비로부터 측정할 항목(예: 출력 전압, 출력 전류, Vpp, 주파수, 피크 파워 등)을 체크합니다.\n• [전체 선택] 또는 [전체 해제] 버튼으로 손쉽게 원하는 측정 항목만 고를 수 있습니다."),
                ("[2] [▶ 측정 및 동작 시작] 버튼 클릭", "• 설정이 끝나면 중앙 패널의 초록색 [▶ 측정 및 동작 시작 (Start)] 버튼을 클릭합니다.\n• 즉시 장비 출력이 나가는 대신, 안전을 위해 위 화면과 같은 [동작 및 측정 시작 전 최종 확인] 창이 먼저 열립니다."),
                ("[3] 입력 파라미터 및 측정 항목 최종 검토", "• 팝업 창의 [1]번 표에서 장비에 인가될 전압/전류/주파수 설정값이 안전한지 확인합니다.\n• [2]번 표에서 수집할 측정 항목과 SCPI/TSP 쿼리 명령어를 확인합니다."),
                ("[4] [🚀 확인 완료 - 측정 및 동작 시작] 승인", "• 이상이 없으면 우측 하단 초록색 승인 버튼을 클릭합니다. 이 순간 장비 설정이 전송되고 실시간 측정이 시작됩니다."),
            ],
            "tip": "💡 만약 사전 준비 점검표에 미확인(미체크) 항목이 남아 있으면 팝업 상단에 주황색 경고 배너로 친절히 알려줍니다.",
        },
        {
            "page_no": 10,
            "badge": "STEP 6 : 측정 제어 (시작/일시정지/완전정지)",
            "title": "실시간 측정 제어 (▶시작 / ⏸일시정지 / ⏹완전정지) 및 그래프 분석",
            "subtitle": "실시간 파형·트렌드 그래프 확인과 비상시 장비 출력을 안전하게 즉시 차단하는 방법",
            "image": screenshots["04_Oscilloscopes"],
            "steps": [
                ("▶ 측정 진행 중 (RUNNING 상태)", "• 측정이 시작되면 상단 상태 배너가 초록색 [🟢 동작 및 측정 진행 중 (RUNNING)]으로 바뀝니다.\n• 우측 상단에는 실시간 그래프가 그려지고, 우측 하단 표에는 시각별 측정 데이터가 자동 누적됩니다."),
                ("⏸ 일시정지 및 ▶ 재개 (PAUSE / RESUME)", "• 측정 도중 화면 그래프를 멈춰서 자세히 관찰하고 싶을 때 주황색 [⏸ 일시정지 (Pause)] 버튼을 누릅니다.\n• 다시 [▶ 측정 재개 (Resume)] 버튼을 누르면 기존 데이터에 이어서 연속으로 측정이 계속됩니다."),
                ("⏹ 완전 정지 및 출력 안전 차단 (COMPLETE STOP)", "• 측정을 끝낼 때는 빨간색 [⏹ 완전 정지 (Stop & Output OFF)] 버튼을 클릭합니다.\n• 단순 수집 중단뿐만 아니라 신호발생기/파워서플라이/SMU의 출력을 즉시 안전 차단(OUTP OFF)하여 회로를 보호합니다."),
                ("실시간 그래프 마우스 조작 팁", "• 그래프 위에서 마우스 휠을 굴리면 확대/축소(Zoom)되며, 좌측 하단 'A' 버튼을 누르면 자동 스케일로 복구됩니다."),
            ],
            "tip": "💡 새로운 조건으로 처음부터 다시 측정하고 싶다면 [🧹 그래프 및 데이터 초기화] 버튼을 눌러 표와 그래프를 깨끗이 비울 수 있습니다.",
        },
        {
            "page_no": 11,
            "badge": "장비별 실습 가이드 ①",
            "title": "01. AFGs (함수발생기) & 02. DC Power / 03. MP5000 측정 실습",
            "subtitle": "신호 발생기 파형 출력 및 직류 전원공급기 전압·전류·전력(W) 실시간 모니터링",
            "image": screenshots["02_DC_Power"],
            "steps": [
                ("01. AFGs (AFG31000 / AFG3000C 시리즈)", "• [입력 파라미터]: 출력 채널(CH1/CH2), 파형 형태(SIN/SQU/RAMP/PULS), 주파수(Hz), 진폭(Vpp), 오프셋(V), 부하 임피던스(50Ω/High-Z) 설정\n• [실시간 그래프]: 설정한 주파수·진폭·파형에 따른 실시간 출력 파형 프리뷰 및 상태 확인"),
                ("02. DC power Supplies (PWS4000 / Keithley 2280S / 2230G)", "• [입력 파라미터]: 목표 출력 전압(V), 과전류 보호 제한값(Current Limit A), 과전압 보호(OVP V) 설정\n• [측정 항목 & 그래프]: 실제 부하에 공급되는 전압(V), 전류(A), 소비 전력(W)의 실시간 시계열 트렌드 그래프"),
                ("03. DC Precision Test (MP5000 모듈형 시스템)", "• [특징]: Keithley TSP(Test Script Processor) 명령어 체계(slot[1].smu / psu) 자동 지원\n• [점검 포인트]: 사전 준비 점검표에서 장비 명령어 세트가 TSP 모드로 설정되어 있는지 [⚡ 상태 확인]으로 검증"),
                ("안전 정지 동작", "• 세 장비 모두 [⏹ 완전 정지] 클릭 시 즉시 출력(Output State)이 OFF로 전환되어 시험 대상 보드를 안전하게 보호합니다."),
            ],
            "tip": "💡 전원공급기(02. DC Power) 사용 시에는 부하 회로의 최대 허용 전류보다 [전류 제한 (Current Limit)]을 약간 낮게 설정하는 것이 안전합니다.",
        },
        {
            "page_no": 12,
            "badge": "장비별 실습 가이드 ②",
            "title": "04. Oscilloscopes (오실로스코프) & 05. Spectrum Analyzers 측정 실습",
            "subtitle": "시간 영역 고속 파형 캡처(Vpp/Freq) 및 주파수 영역 RF 스펙트럼 피크(dBm/MHz) 분석",
            "image": screenshots["05_Spectrum_Analyzers"],
            "steps": [
                ("04. Oscilloscopes (MSO2 / MSO4·5·6 / DPO4000B / TDS2000C)", "• [입력 파라미터]: 측정 소스 채널(CH1~CH4), 수직 스케일(V/div), 수평 타임베이스(s/div), 트리거 레벨(V) 설정\n• [측정 항목]: 첨두간 전압(Vpp), 주파수(Freq), 평균 전압(Mean), 실효치(RMS), 상승시간(Rise Time) 자동 계측\n• [실시간 그래프]: CURVe? 고속 바이너리/아스키 파형 데이터를 실시간으로 화면에 렌더링"),
                ("05. Spectrum Analyzers (RSA306B/500A/600A & 5/6 시리즈 Spectrum View)", "• [입력 파라미터]: 중심 주파수(Center Freq MHz), 주파수 스팬(Span MHz), 기준 레벨(Ref Level dBm), RBW 설정\n• [측정 항목]: 피크 파워(Peak Power dBm), 피크 주파수(Peak Freq MHz), 채널 파워, OBW 계측\n• [실시간 그래프]: 주파수(MHz) 대 파워(dBm) RF 스펙트럼 트레이스 및 피크 마커 실시간 표시"),
                ("USB 3.0 연결 주의사항 (RSA306B / RSA500A)", "• 휴대용 USB 스펙트럼 분석기는 파란색 USB 3.0 포트에 연결하고 SignalVu-PC가 실행 중이어야 VISA 통신이 활성화됩니다."),
            ],
            "tip": "💡 오실로스코프 파형이 화면 위아래로 잘릴 때는 좌측 입력 파라미터의 [수직 스케일 (V/div)] 값을 더 크게 늘려주면 됩니다.",
        },
        {
            "page_no": 13,
            "badge": "장비별 실습 가이드 ③",
            "title": "06. SMUs · 07. Tek VISA · 08. Digit Multimeter(DMM) 측정 실습",
            "subtitle": "SMU I-V 특성 곡선, 범용 VISA 명령어 콘솔 및 5½~7½ 디지트 DMM(DMM6500/7510/2110/2010) 고정밀 측정",
            "image": screenshots["08_DMM"],
            "steps": [
                ("06. SMUs (Keithley 2450 / 2400 / 2600B 시리즈 SourceMeter)", "• [입력 파라미터]: 소스 모드(전압/전류), 스윕 범위(Start~Stop V), 컴플라이언스 한계(Limit A), 2선식/4선식 선택\n• [실시간 그래프]: 전압(V) 대 전류(A) I-V 특성 곡선 실시간 플로팅 및 저항(Ω)·전력(W) 자동 계산"),
                ("08. Digit Multimeter (Keithley DMM6500 / DMM7510 / 2110 / 2010)", "• [입력 파라미터]: 측정 기능(DC/AC 전압·전류, 2선/4선 저항, 주파수, 온도, 커패시턴스, 1MS/s 디지타이저), NPLC, AutoZero 설정\n• [측정 항목 & 그래프]: 주 측정값, 누적 평균(Mean), 변동폭(Pk-Pk), 활성 단자(Front/Rear) 확인 및 디지타이저 파형 플로팅"),
                ("07. Tek VISA & 하단 실시간 I/O 로그 콘솔", "• [07. Tek VISA]: 커스텀 SCPI/TSP 명령어를 반복 실행하며 응답 수치와 통신 지연 시간(Latency ms)을 연속 로깅합니다.\n• 어느 탭에서든 화면 하단 콘솔에서 *IDN?, :ROUT:TERM?, SYST:ERR? 등을 직접 Query하고 응답을 즉시 확인할 수 있습니다."),
            ],
            "tip": "💡 DMM6500 / DMM7510 및 2450 SMU는 SCPI와 TSP 모드를 모두 지원하며, 'AUTO' 선택 시 *LANG?으로 현재 모드를 자동 감지합니다.",
        },
        {
            "page_no": 14,
            "badge": "STEP 7 : 엑셀 리포트 & FAQ",
            "title": "측정 데이터 Excel (.xlsx) 4-시트 자동 저장 및 초보자 FAQ",
            "subtitle": "원클릭으로 요약·설정값·통계치·원본 파형까지 완벽 정리된 엑셀 보고서를 생성하는 방법",
            "image": screenshots["excel_preview"],
            "steps": [
                ("[📊 측정 데이터 Excel (.xlsx) 저장] 버튼 클릭", "• 측정 중이거나 정지한 후 중앙 패널 하단의 파란색 [📊 측정 데이터 Excel (.xlsx) 저장] 버튼을 클릭합니다.\n• 기본 저장 폴더(05.data\\02.Processed)에 장비명과 날짜_시각이 포함된 파일명이 자동 제안됩니다."),
                ("자동 생성되는 4개의 엑셀 시트 구성", "• [1_Summary_Checklist]: 측정 시각, 모델명, 매뉴얼명, VISA 주소, *IDN? 정보 및 사전 점검 체크 기록\n• [2_Input_Configuration]: 사용자가 입력한 필수 파라미터 설정값 및 선택한 측정 항목 기록\n• [3_Measured_Data]: 시계열 측정 데이터 전체 + 하단 평균(Mean)/최대(Max)/최소(Min)/표준편차(StdDev) 자동 계산\n• [4_Waveform_Trace]: 오실로스코프 파형 / RF 스펙트럼 / SMU I-V 스윕 포인트 원본 데이터 전체"),
                ("초보자 자주 묻는 질문 (FAQ)", "• Q. 장비가 검색되지 않아요! → A. 케이블 연결 후 상단 [🔍 리소스 검색]을 누르거나, 연습 시에는 [VIRTUAL] 모드를 켜세요.\n• Q. 화면이 작은 노트북에서도 잘 보이나요? → A. 상단 [🖥️ 화면 크기 자동 맞춤] 클릭 또는 점검표/로그 표 [접기]를 사용하세요."),
            ],
            "tip": "💡 저장된 엑셀 파일은 별도 편집 없이 그대로 실험 보고서나 품질 검증 성적서로 제출할 수 있도록 표 서식과 통계치가 자동 적용되어 있습니다.",
        },
        {
            "page_no": 15,
            "badge": "추가 기능 ① : 실행 이력 & 비교",
            "title": "Run History (실행 이력) · 여러 Run 겹쳐보기 · 자동 내보내기",
            "subtitle": "측정을 새로 시작해도 이전 결과가 사라지지 않고, 언제든 다시 보거나 비교하고 자동 저장할 수 있습니다",
            "image": screenshots["run_history"],
            "steps": [
                ("[1] Run 목록에서 선택", "• 측정을 [▶ 시작]할 때마다 'Run #1, #2 ...'가 자동 기록됩니다 (상태: 🟢RUNNING / 🟡PAUSED / 🔴STOPPED).\n• 오른쪽 [📜 실행 이력] 탭에서 Run을 클릭하면 그래프·표를 다시 볼 수 있고, 여러 개를 선택하면 한 그래프에 겹쳐 비교합니다."),
                ("[2] 내보내기 & 자동 내보내기", "• [선택한 Run 내보내기] / [전체 Run 내보내기]로 표(Excel/CSV)와 그래프(PNG)를 선택해 저장합니다.\n• [자동 내보내기]를 체크하면 측정을 정지하거나 스윕이 끝날 때마다 지정 폴더에 자동 저장됩니다."),
                ("[3] 비교 그래프 + 커서", "• 범례 이름 앞에 'Run #n:'이 붙어 어느 측정인지 구분됩니다.\n• 상단 [📤 내보내기 옵션] 버튼은 현재 화면의 측정을 바로 내보냅니다."),
            ],
            "tip": "💡 측정 중인 Run은 삭제할 수 없고, [🗑 초기화]는 화면만 비우며 이력의 Run은 그대로 남습니다.",
        },
        {
            "page_no": 16,
            "badge": "추가 기능 ② : 그래프 커서 & 표 편집",
            "title": "그래프 커서(구간 통계) · 축 범위 · 시리즈 표시 · 표 컬럼 편집",
            "subtitle": "두 지점 사이의 통계를 바로 확인하고, 그래프와 표를 원하는 모양으로 조정합니다",
            "image": screenshots["graph_cursors"],
            "steps": [
                ("[1] 그래프 도구 모음", "• [➕ 커서 추가]: 세로 커서(최대 2개). 그래프를 더블클릭해도 그 위치에 추가됩니다. 커서는 마우스로 끌어 이동합니다.\n• [👁 시리즈 표시/숨김]: 범례 체크박스처럼 원하는 데이터만 표시합니다.\n• [📐 축 범위]: X/Y 최소·최대값 직접 입력, [🔍 자동 스케일]: 전체 보기."),
                ("[2] 커서 구간 통계", "• 커서가 1개면 해당 위치의 값, 2개면 Δx와 구간 N / Min / Max / Mean / Pk-Pk / Δy를 시리즈별로 표시합니다."),
                ("[3] 표 컬럼 이름 변경 / 숨기기", "• 표의 컬럼 머리글을 우클릭하면 이름 변경, 숨기기, 숨김 해제, 초기화를 할 수 있고, 변경한 이름/숨김은 Excel·CSV 내보내기에도 반영됩니다."),
            ],
            "tip": "💡 실행 이력 탭의 비교 그래프에도 동일한 커서/축/시리즈 도구가 있어 Run 간 차이를 수치로 확인할 수 있습니다.",
        },    ]


def build_powerpoint_guide(pages: List[Dict[str, Any]], out_pptx: str) -> str:
    """Generates a 16:9 Widescreen PowerPoint presentation (.pptx) with annotated GUI screenshots."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    for page in pages:
        slide = prs.slides.add_slide(blank_layout)

        # Dark slate background strip & light body background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = RGBColor(241, 245, 249)
        bg.line.fill.background()

        # Top Header Bar
        hdr = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = RGBColor(15, 23, 42)
        hdr.line.fill.background()

        # Cyan accent bar under header
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.15), Inches(13.333), Inches(0.06))
        accent.fill.solid()
        accent.fill.fore_color.rgb = RGBColor(2, 132, 199)
        accent.line.fill.background()

        # Step Badge pill in header
        badge_shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.35), Inches(0.18), Inches(2.6), Inches(0.34)
        )
        badge_shape.fill.solid()
        badge_shape.fill.fore_color.rgb = RGBColor(2, 132, 199)
        badge_shape.line.fill.background()
        tf_b = badge_shape.text_frame
        tf_b.word_wrap = False
        p_b = tf_b.paragraphs[0]
        p_b.text = f" {page['badge']}  ({page['page_no']}/{len(pages)})"
        p_b.font.name = "Malgun Gothic"
        p_b.font.size = Pt(11)
        p_b.font.bold = True
        p_b.font.color.rgb = RGBColor(255, 255, 255)
        p_b.alignment = PP_ALIGN.CENTER

        # Title & Subtitle in header
        title_box = slide.shapes.add_textbox(Inches(3.05), Inches(0.10), Inches(10.0), Inches(0.55))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        p_t = tf_t.paragraphs[0]
        p_t.text = page["title"]
        p_t.font.name = "Malgun Gothic"
        p_t.font.size = Pt(20)
        p_t.font.bold = True
        p_t.font.color.rgb = RGBColor(248, 250, 252)

        sub_box = slide.shapes.add_textbox(Inches(0.35), Inches(0.64), Inches(12.6), Inches(0.42))
        tf_s = sub_box.text_frame
        tf_s.word_wrap = True
        p_s = tf_s.paragraphs[0]
        p_s.text = page["subtitle"]
        p_s.font.name = "Malgun Gothic"
        p_s.font.size = Pt(12)
        p_s.font.color.rgb = RGBColor(148, 163, 184)

        # Left side: Annotated GUI Screenshot frame (Inches 0.30 to 7.45)
        img_card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.28), Inches(1.35), Inches(7.25), Inches(5.35)
        )
        img_card.fill.solid()
        img_card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        img_card.line.color.rgb = RGBColor(203, 213, 225)
        img_card.line.width = Pt(1.5)

        img_path = page["image"]
        if os.path.exists(img_path):
            with Image.open(img_path) as im:
                iw, ih = im.size
            max_w = Inches(7.05)
            max_h = Inches(5.15)
            scale = min(max_w / iw, max_h / ih)
            disp_w = int(iw * scale)
            disp_h = int(ih * scale)
            left_x = int(Inches(0.28) + (Inches(7.25) - disp_w) / 2)
            top_y = int(Inches(1.35) + (Inches(5.35) - disp_h) / 2)
            slide.shapes.add_picture(
                img_path, Emu(left_x), Emu(top_y), width=Emu(disp_w), height=Emu(disp_h)
            )

        # Right side: Step-by-step explanation cards (Inches 7.70 to 13.05)
        steps = page["steps"]
        card_top = 1.35
        card_h = 1.26
        gap = 0.09
        for idx, (st_title, st_desc) in enumerate(steps):
            cy = card_top + idx * (card_h + gap)
            st_card = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.68), Inches(cy), Inches(5.37), Inches(card_h)
            )
            st_card.fill.solid()
            st_card.fill.fore_color.rgb = RGBColor(255, 255, 255)
            st_card.line.color.rgb = RGBColor(186, 230, 253)
            st_card.line.width = Pt(1.2)

            # Left color stripe on step card
            stripe = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(7.68), Inches(cy), Inches(0.10), Inches(card_h)
            )
            stripe.fill.solid()
            stripe.fill.fore_color.rgb = RGBColor(2, 132, 199)
            stripe.line.fill.background()

            tb = slide.shapes.add_textbox(Inches(7.85), Inches(cy + 0.04), Inches(5.12), Inches(card_h - 0.08))
            tf = tb.text_frame
            tf.word_wrap = True

            p1 = tf.paragraphs[0]
            p1.text = f"▶ {st_title}"
            p1.font.name = "Malgun Gothic"
            p1.font.size = Pt(12)
            p1.font.bold = True
            p1.font.color.rgb = RGBColor(3, 105, 161)

            p2 = tf.add_paragraph()
            p2.text = st_desc
            p2.font.name = "Malgun Gothic"
            p2.font.size = Pt(10)
            p2.font.color.rgb = RGBColor(30, 41, 59)

        # Bottom Tip Bar
        tip_bar = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.28), Inches(6.82), Inches(12.77), Inches(0.52)
        )
        tip_bar.fill.solid()
        tip_bar.fill.fore_color.rgb = RGBColor(224, 242, 254)
        tip_bar.line.color.rgb = RGBColor(56, 189, 248)
        tip_bar.line.width = Pt(1.0)

        tf_tip = tip_bar.text_frame
        tf_tip.word_wrap = True
        p_tip = tf_tip.paragraphs[0]
        p_tip.text = page["tip"]
        p_tip.font.name = "Malgun Gothic"
        p_tip.font.size = Pt(11)
        p_tip.font.bold = True
        p_tip.font.color.rgb = RGBColor(12, 74, 110)

    os.makedirs(os.path.dirname(out_pptx), exist_ok=True)
    prs.save(out_pptx)
    return out_pptx


def build_pdf_guide(pages: List[Dict[str, Any]], out_pdf: str) -> str:
    """Renders a crisp 300-DPI Landscape A4 PDF User Guide using PyQt6 QPdfWriter & QPainter."""
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    writer = QPdfWriter(out_pdf)
    writer.setResolution(300)
    page_layout = QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Landscape,
        QMarginsF(0, 0, 0, 0),
    )
    writer.setPageLayout(page_layout)

    painter = QPainter(writer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    pw = float(writer.width())
    ph = float(writer.height())

    f_badge = QFont("Malgun Gothic", 9, QFont.Weight.Bold)
    f_title = QFont("Malgun Gothic", 16, QFont.Weight.Bold)
    f_sub = QFont("Malgun Gothic", 10, QFont.Weight.Normal)
    f_step_t = QFont("Malgun Gothic", 10, QFont.Weight.Bold)
    f_step_b = QFont("Malgun Gothic", 8, QFont.Weight.Normal)
    f_tip = QFont("Malgun Gothic", 9, QFont.Weight.Bold)

    for idx, page in enumerate(pages):
        if idx > 0:
            writer.newPage()

        # Page background
        painter.fillRect(QRectF(0, 0, pw, ph), QColor("#F1F5F9"))

        # Top Header Bar
        hdr_h = ph * 0.145
        painter.fillRect(QRectF(0, 0, pw, hdr_h), QColor("#0F172A"))
        painter.fillRect(QRectF(0, hdr_h, pw, ph * 0.008), QColor("#0284C7"))

        # Badge pill
        bx = pw * 0.025
        by = ph * 0.022
        bw = pw * 0.20
        bh = ph * 0.048
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#0284C7")))
        painter.drawRoundedRect(QRectF(bx, by, bw, bh), 12.0, 12.0)

        painter.setFont(f_badge)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            QRectF(bx, by, bw, bh),
            int(Qt.AlignmentFlag.AlignCenter),
            f"{page['badge']} ({page['page_no']}/{len(pages)})",
        )

        # Title
        painter.setFont(f_title)
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(
            QRectF(bx + bw + pw * 0.015, ph * 0.018, pw * 0.73, ph * 0.06),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            page["title"],
        )

        # Subtitle
        painter.setFont(f_sub)
        painter.setPen(QColor("#CBD5E1"))
        painter.drawText(
            QRectF(bx, ph * 0.085, pw * 0.95, ph * 0.048),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            page["subtitle"],
        )

        # Left Image Card
        img_box = QRectF(pw * 0.022, ph * 0.175, pw * 0.535, ph * 0.715)
        painter.setPen(QPen(QColor("#CBD5E1"), 3.0))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawRoundedRect(img_box, 16.0, 16.0)

        qimg = QImage(page["image"])
        if not qimg.isNull():
            pad = pw * 0.01
            avail_w = img_box.width() - 2 * pad
            avail_h = img_box.height() - 2 * pad
            scale = min(avail_w / qimg.width(), avail_h / qimg.height())
            dw = qimg.width() * scale
            dh = qimg.height() * scale
            dx = img_box.left() + (img_box.width() - dw) / 2.0
            dy = img_box.top() + (img_box.height() - dh) / 2.0
            painter.drawImage(QRectF(dx, dy, dw, dh), qimg)

        # Right 4 Step Cards
        rx = pw * 0.572
        rw = pw * 0.405
        top_y = ph * 0.175
        total_h = ph * 0.715
        gap = ph * 0.014
        card_h = (total_h - 3 * gap) / 4.0

        for s_idx, (st_title, st_desc) in enumerate(page["steps"]):
            cy = top_y + s_idx * (card_h + gap)
            c_rect = QRectF(rx, cy, rw, card_h)
            painter.setPen(QPen(QColor("#BAE6FD"), 3.0))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRoundedRect(c_rect, 14.0, 14.0)

            # Left accent bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#0284C7")))
            painter.drawRoundedRect(QRectF(rx, cy, pw * 0.007, card_h), 6.0, 6.0)

            # Step title
            painter.setFont(f_step_t)
            painter.setPen(QColor("#0369A1"))
            t_rect = QRectF(rx + pw * 0.014, cy + ph * 0.008, rw - pw * 0.022, card_h * 0.28)
            painter.drawText(
                t_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                f"▶ {st_title}",
            )

            # Step body
            painter.setFont(f_step_b)
            painter.setPen(QColor("#1E293B"))
            b_rect = QRectF(rx + pw * 0.014, cy + card_h * 0.31, rw - pw * 0.022, card_h * 0.65)
            painter.drawText(
                b_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                st_desc,
            )

        # Bottom Tip Bar
        tip_rect = QRectF(pw * 0.022, ph * 0.908, pw * 0.955, ph * 0.068)
        painter.setPen(QPen(QColor("#38BDF8"), 3.0))
        painter.setBrush(QBrush(QColor("#E0F2FE")))
        painter.drawRoundedRect(tip_rect, 12.0, 12.0)

        painter.setFont(f_tip)
        painter.setPen(QColor("#0C4A6E"))
        painter.drawText(
            QRectF(tip_rect.left() + pw * 0.015, tip_rect.top(), tip_rect.width() - pw * 0.03, tip_rect.height()),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            page["tip"],
        )

    painter.end()
    return out_pdf


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Malgun Gothic", 9))

    print("[1/4] Capturing live PyQt6 GUI screenshots and adding visual step callouts...")
    screenshots = capture_all_gui_screenshots()
    print(f"      Captured {len(screenshots)} annotated GUI screenshots in: {SCREENSHOT_DIR}")

    pages = get_guide_pages(screenshots)
    for idx, p in enumerate(pages, start=1):
        p["page_no"] = idx

    print("[2/4] Building PowerPoint presentation (.pptx)...")
    build_powerpoint_guide(pages, PPTX_PATH)
    print(f"      Created PowerPoint Guide: {PPTX_PATH}")

    print("[3/4] Building PDF User Manual (.pdf)...")
    build_pdf_guide(pages, PDF_PATH)
    print(f"      Created PDF User Manual:  {PDF_PATH}")

    print("[4/4] Copying PPTX and PDF User Guides to 06.Release folder...")
    if os.path.exists(RELEASE_DIR):
        shutil.copy2(PPTX_PATH, os.path.join(RELEASE_DIR, os.path.basename(PPTX_PATH)))
        shutil.copy2(PDF_PATH, os.path.join(RELEASE_DIR, os.path.basename(PDF_PATH)))
        print(f"      Copied to: {RELEASE_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
