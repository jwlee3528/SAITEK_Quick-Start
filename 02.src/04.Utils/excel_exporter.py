# -*- coding: utf-8 -*-
"""
SAITEK Tektronix Quick Start SW - Excel (.xlsx) Multi-Sheet Exporter
Exports Summary Metadata, Remote Readiness Checklist, Input Parameters,
Time-Series Measured Data (+ Min/Max/Mean/StdDev statistics), and Waveform/Spectrum Trace Data.
"""

import os
import time
from typing import Dict, Any, List, Optional
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def export_session_to_excel(
    filepath: str,
    category_title: str,
    model_name: str,
    manual_file: str,
    resource_addr: str,
    is_simulation: bool,
    idn_string: str,
    checklist_status: List[Dict[str, Any]],
    input_params: Dict[str, Any],
    selected_meas_labels: Dict[str, str],
    measured_rows: List[Dict[str, Any]],
    last_waveform_x: Optional[np.ndarray] = None,
    last_waveform_y: Optional[np.ndarray] = None,
    waveform_x_label: str = "X",
    waveform_y_label: str = "Y",
    last_waveform_multi_y: Optional[Dict[str, np.ndarray]] = None,
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    wb = Workbook()

    # Styling definitions
    header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
    sub_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    stat_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    header_font = Font(name="Malgun Gothic", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Malgun Gothic", size=10, bold=True)
    reg_font = Font(name="Malgun Gothic", size=10)
    thin_border = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    # 1. Summary & Checklist Sheet
    ws_sum = wb.active
    if ws_sum is None:
        ws_sum = wb.create_sheet(title="1_Summary_Checklist")
    else:
        ws_sum.title = "1_Summary_Checklist"
    summary_rows = [
        ("항목 (Field)", "내용 (Value)"),
        ("측정 리포트 생성 시각", time.strftime("%Y-%m-%d %H:%M:%S")),
        ("장비 폴더 분류 (Category)", category_title),
        ("선택 장비 모델 (Model)", model_name),
        ("참조 매뉴얼 파일 (Manual)", manual_file),
        ("VISA 리소스 주소", resource_addr),
        ("동작 모드 (Real / Simulation)", "가상 시뮬레이션 (Simulation)" if is_simulation else "실제 하드웨어 (Real VISA)"),
        ("장비 식별 정보 (*IDN?)", idn_string),
        ("총 기록된 데이터 포인트 수", len(measured_rows)),
    ]
    for r_idx, (k, v) in enumerate(summary_rows, start=1):
        c1 = ws_sum.cell(row=r_idx, column=1, value=k)
        c2 = ws_sum.cell(row=r_idx, column=2, value=str(v))
        c1.border = thin_border
        c2.border = thin_border
        if r_idx == 1:
            c1.fill = header_fill
            c2.fill = header_fill
            c1.font = header_font
            c2.font = header_font
        else:
            c1.fill = sub_fill
            c1.font = bold_font
            c2.font = reg_font

    # Append Checklist verification record
    start_chk = len(summary_rows) + 2
    ws_sum.cell(row=start_chk, column=1, value="리모트 준비 사항 항목 (Remote Readiness Check)").fill = header_fill
    ws_sum.cell(row=start_chk, column=1).font = header_font
    ws_sum.cell(row=start_chk, column=2, value="사용자 확인 상태").fill = header_fill
    ws_sum.cell(row=start_chk, column=2).font = header_font

    for idx, item in enumerate(checklist_status, start=start_chk + 1):
        c1 = ws_sum.cell(row=idx, column=1, value=item.get("title", ""))
        c2 = ws_sum.cell(row=idx, column=2, value="확인 완료 (Checked)" if item.get("checked") else "미확인 (Unchecked)")
        c1.font = reg_font
        c2.font = bold_font
        c1.border = thin_border
        c2.border = thin_border

    ws_sum.column_dimensions["A"].width = 45
    ws_sum.column_dimensions["B"].width = 65

    # 2. Input Parameters & Selected Measurable Items Sheet
    ws_cfg = wb.create_sheet(title="2_Input_Configuration")
    ws_cfg.cell(row=1, column=1, value="구분 (Type)").fill = header_fill
    ws_cfg.cell(row=1, column=1).font = header_font
    ws_cfg.cell(row=1, column=2, value="파라미터 / 측정 항목 이름").fill = header_fill
    ws_cfg.cell(row=1, column=2).font = header_font
    ws_cfg.cell(row=1, column=3, value="설정값 / 선택 상태").fill = header_fill
    ws_cfg.cell(row=1, column=3).font = header_font

    cfg_row = 2
    for k, v in input_params.items():
        ws_cfg.cell(row=cfg_row, column=1, value="사용자 입력 파라미터 (Required Input)").font = bold_font
        ws_cfg.cell(row=cfg_row, column=2, value=str(k)).font = reg_font
        ws_cfg.cell(row=cfg_row, column=3, value=str(v)).font = reg_font
        for col in range(1, 4):
            ws_cfg.cell(row=cfg_row, column=col).border = thin_border
        cfg_row += 1

    for mk, mlbl in selected_meas_labels.items():
        ws_cfg.cell(row=cfg_row, column=1, value="선택된 측정 항목 (Measurable Item)").font = bold_font
        ws_cfg.cell(row=cfg_row, column=2, value=f"{mlbl} ({mk})").font = reg_font
        ws_cfg.cell(row=cfg_row, column=3, value="Active (측정 수행)").font = reg_font
        for col in range(1, 4):
            ws_cfg.cell(row=cfg_row, column=col).border = thin_border
        cfg_row += 1

    ws_cfg.column_dimensions["A"].width = 34
    ws_cfg.column_dimensions["B"].width = 45
    ws_cfg.column_dimensions["C"].width = 35

    # 3. Measured Data & Statistics Sheet
    ws_data = wb.create_sheet(title="3_Measured_Data")
    if measured_rows:
        cols: List[str] = list(measured_rows[0].keys())
        for row_dict in measured_rows[1:]:
            for k in row_dict.keys():
                if k not in cols:
                    cols.append(k)
        for c_idx, col_name in enumerate(cols, start=1):
            cell = ws_data.cell(row=1, column=c_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        for r_idx, row_dict in enumerate(measured_rows, start=2):
            for c_idx, col_name in enumerate(cols, start=1):
                val = row_dict.get(col_name, "")
                cell = ws_data.cell(row=r_idx, column=c_idx, value=val)
                cell.font = reg_font
                cell.border = thin_border

        # Calculate Summary Statistics (Min, Max, Mean, Std) for numeric columns
        stat_start = len(measured_rows) + 3
        stat_names = [("평균 (Mean)", "mean"), ("최댓값 (Max)", "max"), ("최솟값 (Min)", "min"), ("표준편차 (StdDev)", "std")]
        for s_offset, (s_label, s_func) in enumerate(stat_names):
            r_cur = stat_start + s_offset
            lbl_cell = ws_data.cell(row=r_cur, column=1, value=s_label)
            lbl_cell.fill = stat_fill
            lbl_cell.font = bold_font
            lbl_cell.border = thin_border
            for c_idx, col_name in enumerate(cols[1:], start=2):
                num_vals: List[float] = []
                for row_dict in measured_rows:
                    raw_v = row_dict.get(col_name)
                    if raw_v is not None and raw_v != "":
                        try:
                            f_v = float(raw_v)
                            if not np.isnan(f_v):
                                num_vals.append(f_v)
                        except (ValueError, TypeError):
                            pass
                if len(num_vals) > 0:
                    arr = np.array(num_vals, dtype=float)
                    if s_func == "mean":
                        s_val = float(np.mean(arr))
                    elif s_func == "max":
                        s_val = float(np.max(arr))
                    elif s_func == "min":
                        s_val = float(np.min(arr))
                    else:
                        s_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
                    c_stat = ws_data.cell(row=r_cur, column=c_idx, value=round(s_val, 6))
                else:
                    c_stat = ws_data.cell(row=r_cur, column=c_idx, value="-")
                c_stat.fill = stat_fill
                c_stat.font = bold_font
                c_stat.border = thin_border

        for c_idx in range(1, len(cols) + 1):
            col_letter = get_column_letter(c_idx)
            ws_data.column_dimensions[col_letter].width = 22
    else:
        ws_data.cell(row=1, column=1, value="기록된 측정 데이터가 없습니다.").font = bold_font

    # 4. Waveform / Spectrum Trace Sheet (if available)
    if last_waveform_x is not None and len(last_waveform_x) > 0 and (
        last_waveform_y is not None or (last_waveform_multi_y and len(last_waveform_multi_y) > 0)
    ):
        ws_wfm = wb.create_sheet(title="4_Waveform_Trace")
        c_idx_h = ws_wfm.cell(row=1, column=1, value="Point Index")
        c_x_h = ws_wfm.cell(row=1, column=2, value=waveform_x_label)
        for c in (c_idx_h, c_x_h):
            c.fill = header_fill
            c.font = header_font
            c.border = thin_border
        ws_wfm.column_dimensions["A"].width = 15
        ws_wfm.column_dimensions["B"].width = 24

        if last_waveform_multi_y and len(last_waveform_multi_y) > 1:
            y_items = list(last_waveform_multi_y.items())
            for col_offset, (s_name, _) in enumerate(y_items):
                c_yh = ws_wfm.cell(row=1, column=3 + col_offset, value=s_name)
                c_yh.fill = header_fill
                c_yh.font = header_font
                c_yh.border = thin_border
                ws_wfm.column_dimensions[get_column_letter(3 + col_offset)].width = 24

            n_pts = min([len(last_waveform_x)] + [len(arr) for _, arr in y_items])
            for i in range(n_pts):
                ws_wfm.cell(row=i + 2, column=1, value=i + 1).font = reg_font
                ws_wfm.cell(row=i + 2, column=2, value=float(last_waveform_x[i])).font = reg_font
                for col_offset, (_, arr) in enumerate(y_items):
                    ws_wfm.cell(row=i + 2, column=3 + col_offset, value=float(arr[i])).font = reg_font
        elif last_waveform_y is not None:
            c_y_h = ws_wfm.cell(row=1, column=3, value=waveform_y_label)
            c_y_h.fill = header_fill
            c_y_h.font = header_font
            c_y_h.border = thin_border
            ws_wfm.column_dimensions["C"].width = 24

            n_pts = min(len(last_waveform_x), len(last_waveform_y))
            for i in range(n_pts):
                ws_wfm.cell(row=i + 2, column=1, value=i + 1).font = reg_font
                ws_wfm.cell(row=i + 2, column=2, value=float(last_waveform_x[i])).font = reg_font
                ws_wfm.cell(row=i + 2, column=3, value=float(last_waveform_y[i])).font = reg_font

    wb.save(filepath)
    return filepath
