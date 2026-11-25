# -*- coding: utf-8 -*-
"""
Integration & Headless GUI Test for Tektronix QuickStart Program
Verifies:
1. All 7 manual folders (01. AFGs ~ 07. Tek VISA) and 24+ instrument models load and map to existing PDF manuals
2. Required Inputs vs Measurable Items separation for each category
3. Start -> Acquire Steps -> Pause -> Resume -> Complete Stop & Safe Output OFF lifecycle
4. Excel (.xlsx) multi-sheet export for all 7 categories
5. PyQt6 GUI instantiation and tab switching across all 7 categories
"""

import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(BASE_DIR, "02.src")
for sub in ("01.Core", "02.Modules", "03.Drivers", "04.Utils", "05.Config", "06.Main"):
    p = os.path.join(SRC_DIR, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from PyQt6.QtWidgets import QApplication
import openpyxl

from instrument_profiles import CATEGORY_PROFILES
from visa_manager import VisaConnectionManager
from instrument_drivers import create_driver_for_category
from excel_exporter import export_session_to_excel
from main_app import TekQuickStartMainWindow
from dialogs import StartupReadinessDialog


class TestTekQuickStartSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.manuals_dir = os.path.join(BASE_DIR, "01.docs", "10. Tek_Manuals")
        cls.sample_out_dir = os.path.join(BASE_DIR, "05.data", "03.Samples")
        os.makedirs(cls.sample_out_dir, exist_ok=True)

    def test_01_all_seven_manual_categories_and_pdf_links(self):
        self.assertEqual(len(CATEGORY_PROFILES), 8, "Must have all 8 manual categories (01.AFGs ~ 08.Tek VISA)")
        expected_order = [
            "01_AFG",
            "02_DC_POWER",
            "08_DMM",
            "04_OSCILLOSCOPE",
            "05_SPECTRUM",
            "06_SMU",
            "03_DC_PRECISION",
            "07_TEK_VISA",
        ]
        self.assertEqual(list(CATEGORY_PROFILES.keys()), expected_order)
        for cat_id, profile in CATEGORY_PROFILES.items():
            self.assertTrue(len(profile.models) >= 1)
            self.assertTrue(len(profile.checklist) >= 3, f"{cat_id} missing remote readiness checklist")
            self.assertTrue(len(profile.input_parameters) >= 4, f"{cat_id} missing input parameters")
            self.assertTrue(len(profile.measurable_items) >= 4, f"{cat_id} missing measurable items")
            for m in profile.models:
                pdf_full = os.path.normpath(os.path.join(self.manuals_dir, m.manual_file))
                self.assertTrue(os.path.exists(pdf_full), f"Manual PDF not found: {pdf_full}")

    def test_02_all_drivers_lifecycle_and_excel_export(self):
        visa = VisaConnectionManager()
        for cat_id, profile in CATEGORY_PROFILES.items():
            for model in profile.models:
                ok, msg = visa.connect(
                    "SIM::USB0::0x0699::INSTR",
                    simulation=True,
                    category_id=cat_id,
                    model_id=model.model_id,
                )
                self.assertTrue(ok, msg)

                # Requirement 4: status check
                st_report = visa.verify_instrument_status(protocol=model.protocol)
                self.assertIn("*IDN?", st_report)

                # Collect default inputs & all measurables
                inputs = {spec.key: spec.default for spec in profile.input_parameters}
                selected_meas = [m.key for m in profile.measurable_items]

                driver = create_driver_for_category(visa, cat_id, model.model_id)
                driver.configure_and_start(inputs, selected_meas)

                rows = []
                last_res = None
                for step in range(3):
                    res = driver.acquire_step(inputs, selected_meas)
                    self.assertTrue(len(res.scalars) > 0, f"No scalars returned for {cat_id}/{model.model_id}")
                    row = {"Step": res.step_index, "Timestamp": res.timestamp_str, "Elapsed (s)": res.elapsed_s}
                    for m in profile.measurable_items:
                        row[m.label] = res.scalars.get(m.key, "")
                    rows.append(row)
                    last_res = res

                driver.pause_measurement(inputs)
                driver.resume_measurement(inputs)
                driver.stop_and_safe_shutdown(inputs)

                # Export sample Excel for first model of each category
                if model == profile.models[0]:
                    excel_path = os.path.join(
                        self.sample_out_dir, f"Sample_{cat_id}_{model.model_id}.xlsx"
                    )
                    export_session_to_excel(
                        filepath=excel_path,
                        category_title=profile.title_ko,
                        model_name=model.display_name,
                        manual_file=model.manual_file,
                        resource_addr="SIM::USB0::0x0699::INSTR",
                        is_simulation=True,
                        idn_string=st_report.get("*IDN?", ""),
                        checklist_status=[{"title": c.title, "checked": True} for c in profile.checklist],
                        input_params=inputs,
                        selected_meas_labels={m.key: m.label for m in profile.measurable_items},
                        measured_rows=rows,
                        last_waveform_x=last_res.waveform_x if last_res else None,
                        last_waveform_y=last_res.waveform_y if last_res else None,
                        waveform_x_label=last_res.waveform_x_label if last_res else "X",
                        waveform_y_label=last_res.waveform_y_label if last_res else "Y",
                    )
                    self.assertTrue(os.path.exists(excel_path))
                    wb = openpyxl.load_workbook(excel_path)
                    self.assertIn("1_Summary_Checklist", wb.sheetnames)
                    self.assertIn("2_Input_Configuration", wb.sheetnames)
                    self.assertIn("3_Measured_Data", wb.sheetnames)
                    wb.close()

    def test_03_gui_main_window_and_tabs(self):
        win = TekQuickStartMainWindow(skip_startup_dialog=True)
        self.assertEqual(win.category_tabs.count(), len(CATEGORY_PROFILES))
        for i in range(len(CATEGORY_PROFILES)):
            win.category_tabs.setCurrentIndex(i)
            panel = win.category_tabs.currentWidget()
            self.assertIsNotNone(panel)
            if not hasattr(panel, "collect_inputs"):
                continue
            # Programmatically run 2 ticks without modal dialog
            inputs = panel.collect_inputs()
            sel_meas = panel.collect_selected_measurables()
            panel.driver = create_driver_for_category(
                win.visa_mgr, panel.profile.folder_id, panel.get_current_model().model_id
            )
            panel.driver.configure_and_start(inputs, sel_meas)
            panel._set_state(panel.STATE_RUNNING)
            panel._on_measurement_tick()
            panel._on_measurement_tick()
            self.assertEqual(len(panel.measured_rows), 2)
            panel.on_pause_clicked()
            self.assertEqual(panel.state, panel.STATE_PAUSED)
            panel.on_pause_clicked()
            self.assertEqual(panel.state, panel.STATE_RUNNING)
            panel.on_stop_clicked()
            self.assertEqual(panel.state, panel.STATE_STOPPED)

        # Verify StartupReadinessDialog per-equipment selection & per-item verification
        dlg = StartupReadinessDialog(win.visa_mgr, CATEGORY_PROFILES, initial_category_id="06_SMU", parent=win)
        self.assertEqual(dlg.selected_category_id, "06_SMU")
        self.assertTrue(len(dlg.step_cards) >= 3)
        dlg.verify_all_steps()
        chk_map = dlg.get_checked_map()
        self.assertTrue(all(chk_map.values()), "All checklist items should be auto-checked after verify_all_steps()")
        dlg.close()
        win.close()

    def test_04_run_history_compare_cursors_and_export(self):
        import tempfile

        win = TekQuickStartMainWindow(skip_startup_dialog=True)
        out_dir = tempfile.mkdtemp(prefix="tek_hist_")
        for tab_idx in (1, 3, 5):  # DC Power, Oscilloscope, SMU
            win.category_tabs.setCurrentIndex(tab_idx)
            panel = win.category_tabs.currentWidget()
            hist = panel.history_tab
            hist.chk_auto.setChecked(True)
            hist.edt_auto_folder.setText(out_dir)
            hist.chk_auto_csv.setChecked(True)

            run_ids = []
            for _ in range(2):  # two runs -> history keeps both
                panel.clear_session_data()
                inputs = panel.collect_inputs()
                sel_meas = panel.collect_selected_measurables()
                model = panel.get_current_model()
                panel._apply_table_headers(
                    ["Step", "Timestamp", "Elapsed (s)"]
                    + [m.label for m in panel.profile.measurable_items if m.key in sel_meas]
                )
                panel.driver = create_driver_for_category(win.visa_mgr, panel.profile.folder_id, model.model_id)
                run = panel.begin_new_run(model, inputs, sel_meas)
                run_ids.append(run.run_id)
                panel.driver.configure_and_start(inputs, sel_meas)
                panel._set_state(panel.STATE_RUNNING)
                for _t in range(4):
                    panel._on_measurement_tick()
                panel.on_stop_clicked()
                self.assertEqual(run.status, "STOPPED")
            self.assertEqual(len(panel.history_store.runs), 2)
            self.assertEqual(len(panel.history_store.runs[0].rows), 4)

            # Compare: select both runs -> overlay (legend names prefixed with Run label)
            hist.refresh_list(select_ids=run_ids)
            names = [it.name() for it in hist.plot.getPlotItem().listDataItems()]
            self.assertTrue(len(names) >= 2, names)
            self.assertTrue(any(n and n.startswith("Run #") for n in names), names)

            # Cursors: two cursors -> statistics label visible
            hist.cursor_bar.add_cursor()
            hist.cursor_bar.add_cursor()
            self.assertEqual(len(hist.cursor_bar.cursors), 2)
            self.assertFalse(hist.cursor_bar.lbl_stats.isHidden())
            hist.cursor_bar.clear_cursors()

            # Column rename / hide applied to export rows
            first_meas_col = panel._table_headers[3]
            panel.column_aliases[first_meas_col] = "RENAMED_COL"
            panel.hidden_columns.add("Timestamp")
            rows = panel._export_rows_for(panel.history_store.runs[0])
            self.assertIn("RENAMED_COL", rows[0])
            self.assertNotIn("Timestamp", rows[0])
            panel.column_aliases.clear()
            panel.hidden_columns.clear()

                # Auto export produced xlsx + csv + png for each run
        files = os.listdir(out_dir)
        self.assertTrue(any(f.endswith(".xlsx") for f in files), files)
        self.assertTrue(any(f.endswith(".csv") for f in files), files)
        self.assertTrue(any(f.endswith(".png") and os.path.getsize(os.path.join(out_dir, f)) > 1000 for f in files), files)

        # Verify multi-channel oscilloscope simultaneous selection (CH1, CH2, CH3)
        win.category_tabs.setCurrentIndex(3)
        scope_panel = win.category_tabs.currentWidget()
        ch_w = scope_panel.input_widgets.get("channel")
        self.assertIsNotNone(ch_w)
        self.assertTrue(hasattr(ch_w, "_multi_checkboxes"))
        cbs = getattr(ch_w, "_multi_checkboxes")
        for idx_cb, cb in enumerate(cbs):
            cb.setChecked(idx_cb in (0, 1, 2))  # Select CH1, CH2, CH3
        scope_inputs = scope_panel.collect_inputs()
        self.assertEqual(scope_inputs["channel"], "CH1, CH2, CH3")

        scope_panel.clear_session_data()
        sel_meas = scope_panel.collect_selected_measurables()
        scope_model = scope_panel.get_current_model()
        scope_panel.driver = create_driver_for_category(win.visa_mgr, scope_panel.profile.folder_id, scope_model.model_id)
        scope_run = scope_panel.begin_new_run(scope_model, scope_inputs, sel_meas)
        scope_panel.driver.configure_and_start(scope_inputs, sel_meas)
        scope_panel._set_state(scope_panel.STATE_RUNNING)
        scope_panel._on_measurement_tick()
        scope_panel.on_stop_clicked()
        self.assertEqual(len(scope_run.waveform_multi_y), 3)
        self.assertIn("CH1 Voltage (V)", scope_run.waveform_multi_y)
        self.assertIn("CH2 Voltage (V)", scope_run.waveform_multi_y)
        self.assertIn("CH3 Voltage (V)", scope_run.waveform_multi_y)
        plot_names = [it.name() for it in scope_panel.primary_plot.getPlotItem().listDataItems()]
        self.assertEqual(len(plot_names), 3, plot_names)

        # Verify detachable Graph and Data Table floating windows (Pop-out & Redock)
        scope_panel.toggle_detach_graph()
        self.assertIsNotNone(scope_panel.graph_float_dialog)
        self.assertFalse(scope_panel.lbl_graph_detached.isHidden())
        scope_panel.toggle_detach_table()
        self.assertIsNotNone(scope_panel.table_float_dialog)
        self.assertFalse(scope_panel.lbl_table_detached.isHidden())
        scope_panel.toggle_detach_graph()
        self.assertIsNone(scope_panel.graph_float_dialog)
        self.assertTrue(scope_panel.lbl_graph_detached.isHidden())
        scope_panel.toggle_detach_table()
        self.assertIsNone(scope_panel.table_float_dialog)
        self.assertTrue(scope_panel.lbl_table_detached.isHidden())

        # Verify SAITEK logo, program title, and technical support contact display
        self.assertIn("SAITEK Tektronix Quick Start SW", win.windowTitle())
        self.assertIsNotNone(win.lbl_logo)
        self.assertIsNotNone(win.lbl_support_footer)
        self.assertIn("사이텍(주)", win.lbl_support_footer.text())
        self.assertIn("ssaitek@ssaitek.com", win.lbl_support_footer.text())
        self.assertIn("041-698-4242", win.lbl_support_footer.text())

        win.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
