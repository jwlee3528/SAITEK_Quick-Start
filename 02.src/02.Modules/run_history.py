# -*- coding: utf-8 -*-
"""
Tektronix QuickStart Program - Run History, Run Comparison, Export Options & Graph Cursors.

Inspired by the KickStart Quick Start Guide (KKS-903-01M):
  * Run History         : every measurement run is kept; select a run to view its table / graph again.
  * Multi-run compare   : overlay several runs on one graph.
  * Export options      : table (Excel / CSV) and/or graph (PNG), for current / selected / all runs.
  * Auto export         : "Automatically export new runs" when a run is stopped.
  * Graph cursors       : two movable cursors with statistics between them, axis range, series on/off.
"""

import os
import sys
import csv
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Set, Tuple

import numpy as np

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
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import pyqtgraph as pg
import pyqtgraph.exporters  # noqa: F401  (registers ImageExporter)

from excel_exporter import export_session_to_excel


RUN_COLORS = ["#38bdf8", "#4ade80", "#facc15", "#f472b6", "#fb923c", "#a78bfa", "#2dd4bf", "#f87171"]
WAVEFORM_FOLDERS = ("01_AFG", "04_OSCILLOSCOPE", "05_SPECTRUM")
MAX_RUNS_PER_CATEGORY = 100


# =============================================================================
# DATA MODEL
# =============================================================================
@dataclass
class RunRecord:
    run_id: int
    folder_id: str
    category_title: str
    model_id: str = ""
    model_name: str = ""
    manual_file: str = ""
    resource: str = ""
    is_simulation: bool = True
    idn: str = ""
    checklist_status: List[Dict[str, Any]] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    meas_labels: Dict[str, str] = field(default_factory=dict)
    mode_idx: int = 0
    started: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    ended: str = ""
    status: str = "IDLE"
    rows: List[Dict[str, Any]] = field(default_factory=list)
    time_history: List[float] = field(default_factory=list)
    xy_x_history: List[float] = field(default_factory=list)
    series_history: Dict[str, List[float]] = field(default_factory=dict)
    waveform_x: Optional[np.ndarray] = None
    waveform_y: Optional[np.ndarray] = None
    wfm_x_label: str = "X"
    wfm_y_label: str = "Y"
    exported_paths: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"Run #{self.run_id}" if self.run_id > 0 else "Current"

    @property
    def has_data(self) -> bool:
        return bool(self.rows) or self.waveform_x is not None

    @property
    def is_active(self) -> bool:
        return self.status in ("RUNNING", "PAUSED")

    def list_text(self) -> str:
        icon = {"RUNNING": "🟢", "PAUSED": "🟡", "STOPPED": "🔴"}.get(self.status, "⚪")
        short_model = self.model_name[:26]
        return f"{icon} {self.label} | {self.started[11:]} | {len(self.rows)} pts | {self.status} | {short_model}"


class RunHistoryStore:
    def __init__(self) -> None:
        self.runs: List[RunRecord] = []
        self._counter = 0

    def new_run(self, **kwargs: Any) -> RunRecord:
        self._counter += 1
        run = RunRecord(run_id=self._counter, **kwargs)
        self.runs.append(run)
        while len(self.runs) > MAX_RUNS_PER_CATEGORY:
            for idx, r in enumerate(self.runs):
                if not r.is_active:
                    del self.runs[idx]
                    break
            else:
                break
        return run

    def remove(self, run_ids: List[int]) -> None:
        self.runs = [r for r in self.runs if r.run_id not in run_ids]

    def get(self, run_id: int) -> Optional[RunRecord]:
        for r in self.runs:
            if r.run_id == run_id:
                return r
        return None


# =============================================================================
# PLOT HELPERS
# =============================================================================
def clear_data_items(plot: Any) -> None:
    """Removes only data curves (and their legend entries) so cursors / axes stay intact."""
    plot_item = plot.getPlotItem()
    for it in list(plot_item.listDataItems()):
        plot_item.removeItem(it)


def draw_run(
    plot: Any,
    run: RunRecord,
    mode_idx: int,
    color_offset: int = 0,
    prefix: str = "",
    title_prefix: str = "",
    mode_text: str = "",
    set_title: bool = True,
) -> int:
    """Draws a run into a pyqtgraph PlotWidget. Returns number of colors consumed."""
    n_colors = len(RUN_COLORS)
    folder = run.folder_id

    is_wfm_mode = (mode_idx == 0 and folder in WAVEFORM_FOLDERS) or (mode_idx == 1 and folder == "08_DMM")
    if (
        is_wfm_mode
        and run.waveform_x is not None
        and run.waveform_y is not None
    ):
        if set_title:
            plot.setTitle(f"{title_prefix} - {mode_text}".strip(" -"), color="#e2e8f0")
        plot.setLabel("bottom", run.wfm_x_label, color="#cbd5e1")
        plot.setLabel("left", run.wfm_y_label, color="#cbd5e1")
        c = RUN_COLORS[color_offset % n_colors]
        if folder == "05_SPECTRUM" and color_offset == 0:
            c = "#facc15"
        plot.plot(
            run.waveform_x,
            run.waveform_y,
            pen=pg.mkPen(color=c, width=2),
            name=f"{prefix}{run.wfm_y_label}",
        )
        return 1

    is_iv = (folder == "06_SMU" and mode_idx == 0) or (folder == "03_DC_PRECISION" and mode_idx == 1)
    if is_iv and run.xy_x_history and "Current (A)" in run.series_history:
        if set_title:
            plot.setTitle(f"{title_prefix} - I-V Characteristic Curve", color="#e2e8f0")
        plot.setLabel("bottom", "Measured Voltage (V)", color="#cbd5e1")
        plot.setLabel("left", "Measured Current (A)", color="#cbd5e1")
        n = min(len(run.xy_x_history), len(run.series_history["Current (A)"]))
        c = RUN_COLORS[(color_offset + 1) % n_colors] if color_offset == 0 else RUN_COLORS[color_offset % n_colors]
        plot.plot(
            run.xy_x_history[:n],
            run.series_history["Current (A)"][:n],
            pen=pg.mkPen(color=c, width=2),
            symbol="o",
            symbolSize=6,
            symbolBrush=c,
            name=f"{prefix}I vs V (A)",
        )
        return 1

    if set_title:
        plot.setTitle(f"{title_prefix} - 실시간 측정 트렌드", color="#e2e8f0")
    plot.setLabel("bottom", "Elapsed Time (s)", color="#cbd5e1")
    plot.setLabel("left", "Measured Value", color="#cbd5e1")
    used = 0
    for s_name, s_vals in run.series_history.items():
        n = min(len(run.time_history), len(s_vals))
        if n <= 0:
            continue
        c = RUN_COLORS[(color_offset + used) % n_colors]
        plot.plot(
            run.time_history[:n],
            s_vals[:n],
            pen=pg.mkPen(color=c, width=2),
            symbol="o",
            symbolSize=5,
            symbolBrush=c,
            name=f"{prefix}{s_name}",
        )
        used += 1
    return max(1, used)


# =============================================================================
# GRAPH CURSOR / AXIS / SERIES TOOLBAR
# =============================================================================
class AxisRangeDialog(QDialog):
    def __init__(self, x_range: Tuple[float, float], y_range: Tuple[float, float], parent: Any = None):
        super().__init__(parent)
        self.setWindowTitle("📐 축 범위 직접 설정 (Axis Scale)")
        self.auto_requested = False
        form = QFormLayout()

        def mk(v: float) -> QDoubleSpinBox:
            sp = QDoubleSpinBox()
            sp.setDecimals(6)
            sp.setRange(-1e12, 1e12)
            sp.setValue(float(v))
            sp.setMinimumWidth(150)
            return sp

        self.sp_xmin = mk(x_range[0])
        self.sp_xmax = mk(x_range[1])
        self.sp_ymin = mk(y_range[0])
        self.sp_ymax = mk(y_range[1])
        form.addRow("X 축 최소 (X min)", self.sp_xmin)
        form.addRow("X 축 최대 (X max)", self.sp_xmax)
        form.addRow("Y 축 최소 (Y min)", self.sp_ymin)
        form.addRow("Y 축 최대 (Y max)", self.sp_ymax)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        btn_auto = QPushButton("🔍 자동 스케일로 복귀 (Autoscale)")
        btn_auto.clicked.connect(self._on_auto)
        lay.addWidget(btn_auto)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def _on_auto(self) -> None:
        self.auto_requested = True
        self.accept()


class GraphCursorBar(QWidget):
    """Compact toolbar for a pyqtgraph PlotWidget: cursors with statistics, axis range, series visibility."""

    MAX_CURSORS = 2

    def __init__(self, plot: Any, parent: Any = None):
        super().__init__(parent)
        self.plot = plot
        self.cursors: List[Any] = []
        self.hidden_series: Set[str] = set()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(4)
        style = "padding: 2px 6px; font-size: 8.5pt;"

        self.btn_add = QPushButton("➕ 커서 추가")
        self.btn_add.setToolTip("세로 커서를 추가합니다 (최대 2개). 그래프를 더블클릭해도 해당 위치에 추가됩니다.\n커서 2개 사이의 통계(N/Min/Max/Mean/Pk-Pk)가 표시됩니다.")
        self.btn_clear = QPushButton("✖ 커서 지우기")
        self.btn_series = QPushButton("👁 시리즈 표시/숨김")
        self.btn_series.setToolTip("그래프에 표시할 데이터 시리즈를 선택합니다 (범례 체크박스 기능).")
        self.btn_axis = QPushButton("📐 축 범위")
        self.btn_axis.setToolTip("X/Y 축의 최소·최대값을 직접 입력합니다.")
        self.btn_auto = QPushButton("🔍 자동 스케일")
        for b in (self.btn_add, self.btn_clear, self.btn_series, self.btn_axis, self.btn_auto):
            b.setStyleSheet(style)
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setWordWrap(True)
        self.lbl_stats.setFont(QFont("Consolas", 8))
        self.lbl_stats.setStyleSheet(
            "background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 6px;"
        )
        self.lbl_stats.setMaximumHeight(64)
        self.lbl_stats.setVisible(False)
        lay.addWidget(self.lbl_stats)

        self.btn_add.clicked.connect(lambda: self.add_cursor())
        self.btn_clear.clicked.connect(self.clear_cursors)
        self.btn_series.clicked.connect(self._show_series_menu)
        self.btn_axis.clicked.connect(self._open_axis_dialog)
        self.btn_auto.clicked.connect(self._autoscale)
        self.plot.scene().sigMouseClicked.connect(self._on_scene_click)

    # ---- cursors ----------------------------------------------------------
    def _view_x_range(self) -> Tuple[float, float]:
        xr = self.plot.getPlotItem().vb.viewRange()[0]
        return float(xr[0]), float(xr[1])

    def add_cursor(self, x: Optional[float] = None) -> None:
        if len(self.cursors) >= self.MAX_CURSORS:
            old = self.cursors.pop(0)
            self.plot.removeItem(old)
            for i, c in enumerate(self.cursors, start=1):
                c.label.setFormat(f"C{i}")
        x0, x1 = self._view_x_range()
        idx = len(self.cursors) + 1
        if x is None:
            x = x0 + (x1 - x0) * (0.25 if idx == 1 else 0.75)
        color = "#ef4444" if idx == 1 else "#22c55e"
        line = pg.InfiniteLine(
            pos=x,
            angle=90,
            movable=True,
            pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
            label=f"C{idx}",
            labelOpts={"position": 0.92, "color": color, "movable": True},
        )
        line.sigPositionChanged.connect(self.update_stats)
        self.plot.addItem(line, ignoreBounds=True)
        self.cursors.append(line)
        self.update_stats()

    def clear_cursors(self) -> None:
        for c in self.cursors:
            self.plot.removeItem(c)
        self.cursors.clear()
        self.update_stats()

    def _on_scene_click(self, event: Any) -> None:
        try:
            if not event.double():
                return
            vb = self.plot.getPlotItem().vb
            pos = event.scenePos()
            if not vb.sceneBoundingRect().contains(pos):
                return
            x = float(vb.mapSceneToView(pos).x())
            self.add_cursor(x)
        except Exception:
            pass

    # ---- statistics -------------------------------------------------------
    def _visible_items(self) -> List[Any]:
        return [it for it in self.plot.getPlotItem().listDataItems() if it.isVisible()]

    def update_stats(self) -> None:
        if not self.cursors:
            self.lbl_stats.setVisible(False)
            return
        xs = sorted(float(c.value()) for c in self.cursors)
        lines: List[str] = []
        items = self._visible_items()
        if len(xs) == 1:
            lines.append(f"C1 x = {xs[0]:.6g}")
            for it in items[:6]:
                xd, yd = it.getData()
                if xd is None or yd is None or len(xd) == 0:
                    continue
                xa = np.asarray(xd, dtype=float)
                ya = np.asarray(yd, dtype=float)
                i = int(np.argmin(np.abs(xa - xs[0])))
                lines.append(f"  {it.name() or 'series'}: y = {ya[i]:.6g}")
        else:
            lines.append(f"C1 = {xs[0]:.6g} | C2 = {xs[1]:.6g} | Δx = {xs[1] - xs[0]:.6g}")
            for it in items[:6]:
                xd, yd = it.getData()
                if xd is None or yd is None or len(xd) == 0:
                    continue
                xa = np.asarray(xd, dtype=float)
                ya = np.asarray(yd, dtype=float)
                mask = (xa >= xs[0]) & (xa <= xs[1])
                if not mask.any():
                    lines.append(f"  {it.name() or 'series'}: (구간 내 데이터 없음)")
                    continue
                ys = ya[mask]
                i1 = int(np.argmin(np.abs(xa - xs[0])))
                i2 = int(np.argmin(np.abs(xa - xs[1])))
                lines.append(
                    f"  {it.name() or 'series'}: N={len(ys)} Min={ys.min():.5g} Max={ys.max():.5g} "
                    f"Mean={ys.mean():.5g} Pk-Pk={ys.max() - ys.min():.5g} Δy={ya[i2] - ya[i1]:.5g}"
                )
        self.lbl_stats.setText("\n".join(lines))
        self.lbl_stats.setVisible(True)

    # ---- series visibility ------------------------------------------------
    def apply_visibility(self) -> None:
        for it in self.plot.getPlotItem().listDataItems():
            nm = it.name() or ""
            it.setVisible(nm not in self.hidden_series)

    def refresh(self) -> None:
        """Call after the plot's data items were rebuilt."""
        self.apply_visibility()
        self.update_stats()

    def _show_series_menu(self) -> None:
        items = self.plot.getPlotItem().listDataItems()
        menu = QMenu(self)
        if not items:
            act = menu.addAction("(표시할 데이터 시리즈 없음)")
            if act is not None:
                act.setEnabled(False)
        for it in items:
            nm = it.name() or "series"
            act = menu.addAction(nm)
            if act is None:
                continue
            act.setCheckable(True)
            act.setChecked(nm not in self.hidden_series)
            act.toggled.connect(lambda checked, n=nm: self._toggle_series(n, checked))
        menu.exec(self.btn_series.mapToGlobal(self.btn_series.rect().bottomLeft()))

    def _toggle_series(self, name: str, visible: bool) -> None:
        if visible:
            self.hidden_series.discard(name)
        else:
            self.hidden_series.add(name)
        self.apply_visibility()
        self.update_stats()

    # ---- axis ---------------------------------------------------------------
    def _open_axis_dialog(self) -> None:
        vr = self.plot.getPlotItem().vb.viewRange()
        dlg = AxisRangeDialog((vr[0][0], vr[0][1]), (vr[1][0], vr[1][1]), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.auto_requested:
            self._autoscale()
            return
        if dlg.sp_xmin.value() < dlg.sp_xmax.value():
            self.plot.setXRange(dlg.sp_xmin.value(), dlg.sp_xmax.value(), padding=0)
        if dlg.sp_ymin.value() < dlg.sp_ymax.value():
            self.plot.setYRange(dlg.sp_ymin.value(), dlg.sp_ymax.value(), padding=0)

    def _autoscale(self) -> None:
        self.plot.enableAutoRange()
        self.plot.autoRange()


# =============================================================================
# EXPORT HELPERS
# =============================================================================
def _union_columns(rows: List[Dict[str, Any]]) -> List[str]:
    cols: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)
    return cols


def export_run_excel(run: RunRecord, filepath: str, rows: Optional[List[Dict[str, Any]]] = None) -> str:
    return export_session_to_excel(
        filepath=filepath,
        category_title=run.category_title,
        model_name=run.model_name,
        manual_file=run.manual_file,
        resource_addr=run.resource or "SIMULATION",
        is_simulation=run.is_simulation,
        idn_string=run.idn,
        checklist_status=run.checklist_status,
        input_params=run.inputs,
        selected_meas_labels=run.meas_labels,
        measured_rows=rows if rows is not None else run.rows,
        last_waveform_x=run.waveform_x,
        last_waveform_y=run.waveform_y,
        waveform_x_label=run.wfm_x_label,
        waveform_y_label=run.wfm_y_label,
    )


def export_run_csv(run: RunRecord, filepath: str, rows: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    out_rows = rows if rows is not None else run.rows
    paths: List[str] = []
    cols = _union_columns(out_rows)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow({c: r.get(c, "") for c in cols})
    paths.append(filepath)
    if run.waveform_x is not None and run.waveform_y is not None:
        wpath = os.path.splitext(filepath)[0] + "_waveform.csv"
        with open(wpath, "w", newline="", encoding="utf-8-sig") as f:
            w2 = csv.writer(f)
            w2.writerow(["Point", run.wfm_x_label, run.wfm_y_label])
            for i, (xv, yv) in enumerate(zip(run.waveform_x, run.waveform_y), start=1):
                w2.writerow([i, float(xv), float(yv)])
        paths.append(wpath)
    return paths


def export_run_png(run: RunRecord, filepath: str, width: int = 1280, height: int = 720) -> str:
    plot = pg.PlotWidget()
    plot.setBackground("#0f172a")
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.addLegend(offset=(10, 10))
    plot.resize(width, height)
    plot.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    plot.show()
    QApplication.processEvents()
    draw_run(
        plot,
        run,
        run.mode_idx,
        title_prefix=f"{run.category_title} | {run.label} | {run.model_name[:40]}",
        mode_text="Graph",
    )
    QApplication.processEvents()
    exporter = pg.exporters.ImageExporter(plot.getPlotItem())
    exporter.parameters()["width"] = width
    exporter.export(filepath)
    plot.close()
    return filepath


def export_run_bundle(
    run: RunRecord,
    folder: str,
    formats: Set[str],
    rows: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """formats: subset of {'xlsx', 'csv', 'png'}. Returns the list of written files."""
    os.makedirs(folder, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"TekQuickStart_{run.folder_id}_{run.model_id or 'model'}_Run{run.run_id:03d}_{ts}"
    base_path = os.path.join(folder, base)
    written: List[str] = []
    if "xlsx" in formats:
        written.append(export_run_excel(run, base_path + ".xlsx", rows))
    if "csv" in formats:
        written.extend(export_run_csv(run, base_path + ".csv", rows))
    if "png" in formats:
        written.append(export_run_png(run, base_path + ".png"))
    run.exported_paths.extend(written)
    return written


class ExportOptionsDialog(QDialog):
    """Choose what (table / graph), which runs (current / selected / all) and where to export."""

    def __init__(self, scope_labels: List[str], default_folder: str, parent: Any = None):
        super().__init__(parent)
        self.setWindowTitle("📤 내보내기 옵션 (Export Options)")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)

        grp_fmt = QGroupBox("1. 내보낼 항목 (표 / 그래프 / 둘 다)")
        fl = QVBoxLayout(grp_fmt)
        self.chk_xlsx = QCheckBox("📊 표 + 설정 + 통계 → Excel (.xlsx, 4시트)")
        self.chk_csv = QCheckBox("📄 표 → CSV (.csv, 파형이 있으면 *_waveform.csv 추가)")
        self.chk_png = QCheckBox("🖼 그래프 → 이미지 (.png)")
        self.chk_xlsx.setChecked(True)
        self.chk_png.setChecked(True)
        for c in (self.chk_xlsx, self.chk_csv, self.chk_png):
            fl.addWidget(c)
        lay.addWidget(grp_fmt)

        grp_scope = QGroupBox("2. 내보낼 Run 범위")
        sl = QVBoxLayout(grp_scope)
        self.scope_group = QButtonGroup(self)
        for i, text in enumerate(scope_labels):
            rb = QRadioButton(text)
            if i == 0:
                rb.setChecked(True)
            self.scope_group.addButton(rb, i)
            sl.addWidget(rb)
        lay.addWidget(grp_scope)

        grp_dir = QGroupBox("3. 저장 폴더")
        dl = QHBoxLayout(grp_dir)
        self.edt_folder = QLineEdit(default_folder)
        btn_browse = QPushButton("폴더 찾아보기...")
        btn_browse.clicked.connect(self._browse)
        dl.addWidget(self.edt_folder, 1)
        dl.addWidget(btn_browse)
        lay.addWidget(grp_dir)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self._on_accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.edt_folder.text())
        if d:
            self.edt_folder.setText(d)

    def _on_accept(self) -> None:
        if not (self.chk_xlsx.isChecked() or self.chk_csv.isChecked() or self.chk_png.isChecked()):
            QMessageBox.warning(self, "항목 선택 필요", "내보낼 항목(Excel / CSV / PNG)을 하나 이상 선택해 주세요.")
            return
        if not self.edt_folder.text().strip():
            QMessageBox.warning(self, "폴더 선택 필요", "저장 폴더를 지정해 주세요.")
            return
        self.accept()

    def values(self) -> Tuple[Set[str], int, str]:
        fmts: Set[str] = set()
        if self.chk_xlsx.isChecked():
            fmts.add("xlsx")
        if self.chk_csv.isChecked():
            fmts.add("csv")
        if self.chk_png.isChecked():
            fmts.add("png")
        return fmts, max(0, self.scope_group.checkedId()), self.edt_folder.text().strip()


# =============================================================================
# RUN HISTORY TAB
# =============================================================================
class RunHistoryTab(QWidget):
    status_message_signal = pyqtSignal(str, arguments=["msg"])

    def __init__(
        self,
        store: RunHistoryStore,
        title_prefix: str,
        default_export_dir: str,
        parent: Any = None,
    ):
        super().__init__(parent)
        self.store = store
        self.title_prefix = title_prefix
        self.default_export_dir = default_export_dir
        self.row_transform: Callable[[RunRecord], List[Dict[str, Any]]] = lambda r: r.rows

        root = QHBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        # ---------------- Left: run list + actions + auto export ----------------
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(4)
        lbl = QLabel("📜 실행 이력 (Run History)\n선택한 Run을 그래프·표로 다시 보거나, 여러 개를 선택해 겹쳐 비교합니다.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 8.5pt; color: #334155;")
        ll.addWidget(lbl)

        self.list_runs = QListWidget()
        self.list_runs.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_runs.setMinimumWidth(210)
        self.list_runs.itemSelectionChanged.connect(self._on_selection_changed)
        ll.addWidget(self.list_runs, 1)

        row_btn = QHBoxLayout()
        self.btn_delete = QPushButton("🗑 선택 삭제")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_select_all = QPushButton("☑ 전체 선택")
        self.btn_select_all.clicked.connect(self.list_runs.selectAll)
        row_btn.addWidget(self.btn_select_all)
        row_btn.addWidget(self.btn_delete)
        ll.addLayout(row_btn)

        self.btn_export_sel = QPushButton("📤 선택한 Run 내보내기...")
        self.btn_export_sel.clicked.connect(lambda: self.open_export_dialog(None, preferred="selected"))
        self.btn_export_all = QPushButton("📦 전체 Run 내보내기...")
        self.btn_export_all.clicked.connect(lambda: self.open_export_dialog(None, preferred="all"))
        ll.addWidget(self.btn_export_sel)
        ll.addWidget(self.btn_export_all)

        grp_auto = QGroupBox("⚙ 자동 내보내기 (Automatically export new runs)")
        al = QVBoxLayout(grp_auto)
        self.chk_auto = QCheckBox("측정을 정지/완료하면 자동 저장")
        self.chk_auto_xlsx = QCheckBox("Excel")
        self.chk_auto_csv = QCheckBox("CSV")
        self.chk_auto_png = QCheckBox("그래프 PNG")
        self.chk_auto_xlsx.setChecked(True)
        self.chk_auto_png.setChecked(True)
        fmt_row = QHBoxLayout()
        for c in (self.chk_auto_xlsx, self.chk_auto_csv, self.chk_auto_png):
            fmt_row.addWidget(c)
        self.edt_auto_folder = QLineEdit(self.default_export_dir)
        btn_auto_browse = QPushButton("📁")
        btn_auto_browse.setMaximumWidth(34)
        btn_auto_browse.clicked.connect(self._browse_auto_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.edt_auto_folder, 1)
        folder_row.addWidget(btn_auto_browse)
        al.addWidget(self.chk_auto)
        al.addLayout(fmt_row)
        al.addLayout(folder_row)
        ll.addWidget(grp_auto)
        splitter.addWidget(left)

        # ---------------- Right: compare plot (+cursor bar) and table ----------------
        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.setChildrenCollapsible(False)

        plot_box = QWidget()
        pbl = QVBoxLayout(plot_box)
        pbl.setContentsMargins(0, 0, 0, 0)
        pbl.setSpacing(2)
        self.plot = pg.PlotWidget()
        self.plot.setMinimumHeight(130)
        self.plot.setBackground("#0f172a")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.addLegend(offset=(10, 10))
        self.cursor_bar = GraphCursorBar(self.plot)
        pbl.addWidget(self.cursor_bar)
        pbl.addWidget(self.plot, 1)
        right_split.addWidget(plot_box)

        self.table = QTableWidget(0, 0)
        self.table.setMinimumHeight(80)
        self.table.setAlternatingRowColors(True)
        h = self.table.horizontalHeader()
        if h is not None:
            h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            h.setStretchLastSection(True)
        right_split.addWidget(self.table)
        right_split.setStretchFactor(0, 3)
        right_split.setStretchFactor(1, 2)
        splitter.addWidget(right_split)
        splitter.setStretchFactor(0, 28)
        splitter.setStretchFactor(1, 72)

    # ------------------------------------------------------------------ list
    def selected_run_ids(self) -> List[int]:
        ids: List[int] = []
        for it in self.list_runs.selectedItems():
            rid = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(rid, int):
                ids.append(rid)
        return ids

    def selected_runs(self) -> List[RunRecord]:
        runs = [self.store.get(i) for i in self.selected_run_ids()]
        out = [r for r in runs if r is not None]
        out.sort(key=lambda r: r.run_id)
        return out

    def refresh_list(self, select_ids: Optional[List[int]] = None, redraw: bool = True) -> None:
        keep = select_ids if select_ids is not None else self.selected_run_ids()
        self.list_runs.blockSignals(True)
        self.list_runs.clear()
        for run in reversed(self.store.runs):
            it = QListWidgetItem(run.list_text())
            it.setData(Qt.ItemDataRole.UserRole, run.run_id)
            self.list_runs.addItem(it)
            if run.run_id in keep:
                it.setSelected(True)
        self.list_runs.blockSignals(False)
        if redraw:
            self._redraw()

    def _on_selection_changed(self) -> None:
        self._redraw()

    def _delete_selected(self) -> None:
        runs = self.selected_runs()
        if not runs:
            return
        active = [r for r in runs if r.is_active]
        if active:
            QMessageBox.warning(self, "삭제 불가", "측정 중이거나 일시정지 중인 Run은 삭제할 수 없습니다. 먼저 [완전 정지]하세요.")
            runs = [r for r in runs if not r.is_active]
            if not runs:
                return
        if QMessageBox.question(self, "Run 삭제", f"선택한 {len(runs)}개 Run을 이력에서 삭제할까요?") != QMessageBox.StandardButton.Yes:
            return
        self.store.remove([r.run_id for r in runs])
        self.refresh_list(select_ids=[])

    # ------------------------------------------------------------------ view
    def _redraw(self) -> None:
        clear_data_items(self.plot)
        runs = self.selected_runs()
        if not runs:
            self.plot.setTitle("왼쪽 목록에서 Run을 선택하세요 (여러 개 선택 시 겹쳐서 비교)", color="#94a3b8")
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.cursor_bar.refresh()
            return
        offset = 0
        multi = len(runs) > 1
        for run in runs:
            used = draw_run(
                self.plot,
                run,
                run.mode_idx,
                color_offset=offset,
                prefix=f"{run.label}: " if multi else "",
                title_prefix=self.title_prefix,
                mode_text="Graph",
                set_title=not multi,
            )
            offset += used
        if multi:
            self.plot.setTitle(f"{self.title_prefix} - Run 비교 ({len(runs)}개 겹쳐보기)", color="#e2e8f0")
        self._fill_table(runs[-1])
        self.cursor_bar.refresh()

    def _fill_table(self, run: RunRecord) -> None:
        rows = run.rows
        cols = _union_columns(rows)
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(len(rows))
        for r_i, r in enumerate(rows):
            for c_i, c in enumerate(cols):
                item = QTableWidgetItem(str(r.get(c, "")))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r_i, c_i, item)

    # ---------------------------------------------------------------- export
    def _browse_auto_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "자동 내보내기 폴더 선택", self.edt_auto_folder.text())
        if d:
            self.edt_auto_folder.setText(d)

    def auto_export_formats(self) -> Set[str]:
        fmts: Set[str] = set()
        if self.chk_auto_xlsx.isChecked():
            fmts.add("xlsx")
        if self.chk_auto_csv.isChecked():
            fmts.add("csv")
        if self.chk_auto_png.isChecked():
            fmts.add("png")
        return fmts

    def auto_export(self, run: RunRecord) -> List[str]:
        """Called by the panel when a run is stopped. No-op unless auto export is enabled."""
        if not self.chk_auto.isChecked() or not run.has_data:
            return []
        fmts = self.auto_export_formats()
        folder = self.edt_auto_folder.text().strip() or self.default_export_dir
        if not fmts:
            return []
        try:
            paths = export_run_bundle(run, folder, fmts, self.row_transform(run))
            self.status_message_signal.emit(f"[자동 내보내기] {run.label}: {len(paths)}개 파일 저장 → {folder}")
            return paths
        except Exception as e:
            self.status_message_signal.emit(f"[자동 내보내기 실패] {run.label}: {e}")
            return []

    def open_export_dialog(self, current_run: Optional[RunRecord], preferred: str = "current") -> None:
        scopes: List[Tuple[str, str, List[RunRecord]]] = []
        if current_run is not None and current_run.has_data:
            scopes.append(("current", f"현재 화면의 측정 ({current_run.label})", [current_run]))
        sel = self.selected_runs()
        if sel:
            scopes.append(("selected", f"이력에서 선택한 Run ({len(sel)}개)", sel))
        if self.store.runs:
            scopes.append(("all", f"이력의 전체 Run ({len(self.store.runs)}개)", list(self.store.runs)))
        if not scopes:
            QMessageBox.warning(self, "내보낼 데이터 없음", "내보낼 측정 데이터가 없습니다. 먼저 측정을 실행하거나 Run을 선택해 주세요.")
            return
        scopes.sort(key=lambda s: 0 if s[0] == preferred else 1)
        dlg = ExportOptionsDialog([s[1] for s in scopes], self.default_export_dir, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        fmts, scope_idx, folder = dlg.values()
        runs = scopes[min(scope_idx, len(scopes) - 1)][2]
        written: List[str] = []
        try:
            for run in runs:
                written.extend(export_run_bundle(run, folder, fmts, self.row_transform(run)))
        except Exception as e:
            QMessageBox.critical(self, "내보내기 실패", f"파일 저장 중 오류가 발생했습니다:\n{e}")
            return
        self.status_message_signal.emit(f"내보내기 완료: {len(written)}개 파일 → {folder}")
        preview = "\n".join(written[:8]) + (f"\n... 외 {len(written) - 8}개" if len(written) > 8 else "")
        QMessageBox.information(self, "내보내기 완료", f"{len(runs)}개 Run, {len(written)}개 파일이 저장되었습니다:\n\n{preview}")
