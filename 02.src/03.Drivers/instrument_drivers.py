# -*- coding: utf-8 -*-
"""
Tektronix QuickStart Program - Instrument Drivers for all 7 Manual Folders
Translates user-configured Input Parameters and Selected Measurable Items into exact SCPI / TSP commands
from the 26 Tektronix / Keithley Programmer & Reference Manuals.
"""

import math
import time
import re
from typing import Dict, Any, List, Tuple, Optional
import numpy as np


class MeasurementResult:
    """
    Holds one cycle/step of measurement data returned by an instrument driver.
    """

    def __init__(self):
        self.timestamp_str: str = time.strftime("%Y-%m-%d %H:%M:%S") + f".{int((time.time() % 1) * 1000):03d}"
        self.elapsed_s: float = 0.0
        self.step_index: int = 0
        self.scalars: Dict[str, Any] = {}          # key -> measured scalar value (float or str)
        self.primary_plot_x: Optional[float] = None
        self.primary_plot_y: Dict[str, float] = {} # series_name -> value for time-series or X-Y chart
        self.waveform_x: Optional[np.ndarray] = None
        self.waveform_y: Optional[np.ndarray] = None
        self.waveform_y2: Optional[np.ndarray] = None
        self.waveform_x_label: str = "Time (s)"
        self.waveform_y_label: str = "Voltage (V)"
        self.waveform_title: str = ""
        self.is_completed_sweep: bool = False


class BaseCategoryDriver:
    def __init__(self, visa_mgr, category_id: str, model_id: str):
        self.visa = visa_mgr
        self.category_id = category_id
        self.model_id = model_id
        self.start_epoch = time.time()
        self.step_count = 0

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        self.start_epoch = time.time()
        self.step_count = 0
        self.visa.set_category_model(self.category_id, self.model_id)

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        raise NotImplementedError

    def pause_measurement(self, inputs: Dict[str, Any]):
        """Called when user pauses measurement."""
        pass

    def resume_measurement(self, inputs: Dict[str, Any]):
        """Called when user resumes measurement."""
        pass

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        """Called when user presses Complete Stop (완전 정지)."""
        pass


class AFGDriver(BaseCategoryDriver):
    """
    01. AFGs Driver (AFG1000, AFG2021, AFG31000 Series)
    Ref: AFG1000-Programmer-Manual, AFG2021_Programmer Manual, AFG31000_Series_ProgrammersManual
    """

    def _get_channels(self, ch_choice: str) -> List[int]:
        if "Dual" in ch_choice:
            return [1, 2]
        return [2] if "CH2" in ch_choice else [1]

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        channels = self._get_channels(inputs.get("channel", "CH1"))
        func_raw = inputs.get("function", "SINusoid")
        func_scpi = func_raw[:3].upper() if func_raw != "PRNoise" else "PRN"
        freq = float(inputs.get("frequency_hz", 1000.0))
        amp = float(inputs.get("amplitude_vpp", 2.0))
        offset = float(inputs.get("offset_v", 0.0))
        phase = float(inputs.get("phase_deg", 0.0))
        duty = float(inputs.get("duty_cycle", 50.0))
        imp_str = inputs.get("impedance", "50 Ω")
        imp_cmd = "INF" if "INF" in imp_str else ("1000" if "1000" in imp_str else "50")
        run_mode = inputs.get("run_mode", "Continuous (연속 출력)")

        for ch in channels:
            self.visa.write(f"OUTPut{ch}:IMPedance {imp_cmd}")
            self.visa.write(f"SOURce{ch}:FUNCtion:SHAPe {func_scpi}")
            self.visa.write(f"SOURce{ch}:FREQuency:FIXed {freq}Hz")
            self.visa.write(f"SOURce{ch}:VOLTage:LEVel:IMMediate:AMPLitude {amp}Vpp")
            self.visa.write(f"SOURce{ch}:VOLTage:LEVel:IMMediate:OFFSet {offset}V")
            if func_scpi != "PUL" and func_scpi != "DC":
                self.visa.write(f"SOURce{ch}:PHASe:ADJust {phase}DEG")
            if func_scpi == "PUL":
                self.visa.write(f"SOURce{ch}:PULSe:DCYCle {duty}")

            if "Sweep" in run_mode:
                stop_f = float(inputs.get("sweep_stop_hz", 10000.0))
                self.visa.write(f"SOURce{ch}:FREQuency:STARt {freq}Hz")
                self.visa.write(f"SOURce{ch}:FREQuency:STOP {stop_f}Hz")
                self.visa.write(f"SOURce{ch}:FREQuency:MODE SWEep")
            elif "AM" in run_mode:
                self.visa.write(f"SOURce{ch}:AM:STATe ON")
            elif "Burst" in run_mode:
                self.visa.write(f"SOURce{ch}:BURSt:STATe ON")

            self.visa.write(f"OUTPut{ch}:STATe ON")

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        res = MeasurementResult()
        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        self.step_count += 1
        res.step_index = self.step_count

        channels = self._get_channels(inputs.get("channel", "CH1"))
        ch = channels[0]

        # Sweep frequency progression if in Sweep mode
        freq_start = float(inputs.get("frequency_hz", 1000.0))
        run_mode = inputs.get("run_mode", "Continuous")
        if "Sweep" in run_mode:
            stop_f = float(inputs.get("sweep_stop_hz", 10000.0))
            frac = ((self.step_count - 1) % 20) / 19.0
            cur_f = freq_start + frac * (stop_f - freq_start)
            self.visa.write(f"SOURce{ch}:FREQuency:FIXed {cur_f}Hz")

        if "out_state" in selected_meas:
            st, _ = self.visa.query(f"OUTPut{ch}:STATe?")
            res.scalars["out_state"] = "ON" if st.strip() in ("1", "ON") else "OFF"
        if "act_func" in selected_meas:
            fn, _ = self.visa.query(f"SOURce{ch}:FUNCtion:SHAPe?")
            res.scalars["act_func"] = fn
        if "act_freq_hz" in selected_meas:
            fq, _ = self.visa.query(f"SOURce{ch}:FREQuency?")
            val_f = float(fq)
            res.scalars["act_freq_hz"] = val_f
            res.primary_plot_y["Frequency (Hz)"] = val_f
        if "act_amp_vpp" in selected_meas:
            am, _ = self.visa.query(f"SOURce{ch}:VOLTage:AMPLitude?")
            val_a = float(am)
            res.scalars["act_amp_vpp"] = val_a
            res.primary_plot_y["Amplitude (Vpp)"] = val_a
        if "act_offset_v" in selected_meas:
            of, _ = self.visa.query(f"SOURce{ch}:VOLTage:OFFSet?")
            val_o = float(of)
            res.scalars["act_offset_v"] = val_o
            res.primary_plot_y["Offset (V)"] = val_o
        if "act_phase_deg" in selected_meas:
            ph, _ = self.visa.query(f"SOURce{ch}:PHASe?")
            res.scalars["act_phase_deg"] = float(ph)
        if "act_imp_ohm" in selected_meas:
            im, _ = self.visa.query(f"OUTPut{ch}:IMPedance?")
            res.scalars["act_imp_ohm"] = im
        if "sys_err" in selected_meas:
            er, _ = self.visa.query("SYSTem:ERRor:NEXT?")
            res.scalars["sys_err"] = er

        # Construct real-time synthesized waveform preview of the configured output
        f_now = float(res.scalars.get("act_freq_hz", inputs.get("frequency_hz", 1000.0)))
        a_now = float(res.scalars.get("act_amp_vpp", inputs.get("amplitude_vpp", 2.0)))
        o_now = float(res.scalars.get("act_offset_v", inputs.get("offset_v", 0.0)))
        p_now = math.radians(float(inputs.get("phase_deg", 0.0)))
        period = 1.0 / max(1e-6, f_now)
        t = np.linspace(0, 3.0 * period, 600)
        omega_t = 2 * np.pi * f_now * t + p_now
        fn_type = inputs.get("function", "SINusoid").upper()

        if fn_type.startswith("SQU"):
            y = o_now + (a_now / 2.0) * np.sign(np.sin(omega_t))
        elif fn_type.startswith("PUL"):
            duty = float(inputs.get("duty_cycle", 50.0)) / 100.0
            phase_mod = np.mod(omega_t / (2 * np.pi), 1.0)
            y = o_now + np.where(phase_mod < duty, a_now / 2.0, -a_now / 2.0)
        elif fn_type.startswith("RAM"):
            phase_mod = np.mod(omega_t / (2 * np.pi), 1.0)
            y = o_now + a_now * (phase_mod - 0.5)
        elif fn_type.startswith("PRN"):
            y = o_now + np.random.normal(0, a_now / 4.0, size=len(t))
        elif fn_type.startswith("DC"):
            y = np.full_like(t, o_now)
        elif fn_type.startswith("SIN") and not fn_type.startswith("SINC"):
            y = o_now + (a_now / 2.0) * np.sin(omega_t)
        else:
            x_sinc = (t - 1.5 * period) * f_now * 4.0
            y = o_now + (a_now / 2.0) * np.sinc(x_sinc)

        res.waveform_x = t * 1e3  # ms
        res.waveform_y = y
        res.waveform_x_label = "Time (ms)"
        res.waveform_y_label = "Output Voltage (V)"
        res.waveform_title = f"AFG CH{ch} Output Preview ({fn_type}, {f_now:g} Hz, {a_now:g} Vpp)"
        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        for ch in self._get_channels(inputs.get("channel", "CH1")):
            try:
                self.visa.write(f"OUTPut{ch}:STATe OFF")
            except Exception:
                pass


class DCPowerDriver(BaseCategoryDriver):
    """
    02. DC Power Supplies Driver (Series 2200 Multichannel & Series 2260B)
    Ref: 2220S-907-01B_Dec_2013_Prog.pdf, 2260B_Programming_Oct2024.pdf
    """

    def __init__(self, visa_mgr, category_id: str, model_id: str):
        super().__init__(visa_mgr, category_id, model_id)
        self._applied_cfg: Dict[str, Any] = {}

    def _apply_psu_settings(self, inputs: Dict[str, Any], turn_output_on: bool = False):
        ch_sel = inputs.get("channel", "CH1")
        v_target = float(inputs.get("voltage_v", 5.0))
        i_lim = float(inputs.get("current_limit_a", 1.0))
        ovp = float(inputs.get("ovp_v", 12.0))

        if self.model_id == "SERIES_2200":
            comb = inputs.get("combine_mode", "OFF")
            if "SERies" in comb:
                self.visa.write("INSTrument:COMbine:SERies")
            elif "PARAllel" in comb:
                self.visa.write("INSTrument:COMbine:PARAllel")
            elif "TRACk" in comb:
                self.visa.write("INSTrument:COMbine:TRACk")
            else:
                self.visa.write("INSTrument:COMbine:OFF")

            target_ch = "CH1" if "ALL" in ch_sel else ch_sel
            self.visa.write(f"INSTrument:SELect {target_ch}")
            self.visa.write(f"SOURce:VOLTage:LIMit:LEVel {ovp}")
            self.visa.write("SOURce:VOLTage:LIMit:STATe ON")
            self.visa.write(f"SOURce:VOLTage:LEVel:IMMediate:AMPLitude {v_target}")
            self.visa.write(f"SOURce:CURRent:LEVel:IMMediate:AMPLitude {i_lim}")
            if turn_output_on:
                self.visa.write("OUTPut:STATe ON")
        else:
            # 2260B Series
            mode_str = inputs.get("slew_priority", "CVHS")
            mode_code = mode_str.split(" ")[0]
            self.visa.write(f":OUTPut:MODE {mode_code}")
            self.visa.write(f":SOURce:VOLTage:PROTection:LEVel {ovp}")
            ocp_on = "ON" if inputs.get("ocp_enable", True) else "OFF"
            self.visa.write(f":SOURce:CURRent:PROTection:STATe {ocp_on}")
            slew_v = float(inputs.get("slew_rate_vs", 60.0))
            self.visa.write(f":SOURce:VOLTage:SLEW:RISing {slew_v}")
            int_r = float(inputs.get("internal_res_ohm", 0.0))
            if int_r > 0:
                self.visa.write(f":SOURce:RESistance {int_r}")
            self.visa.write(f":SOURce:VOLTage {v_target}")
            self.visa.write(f":SOURce:CURRent {i_lim}")
            if turn_output_on:
                self.visa.write(":OUTPut:STATe:IMMediate ON")

        self._applied_cfg = {
            k: inputs.get(k)
            for k in ("channel", "combine_mode", "voltage_v", "current_limit_a", "ovp_v", "ocp_enable", "slew_priority", "slew_rate_vs", "internal_res_ohm")
        }

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        self._apply_psu_settings(inputs, turn_output_on=True)
        self.start_epoch = time.time()

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        cur_cfg = {
            k: inputs.get(k)
            for k in ("channel", "combine_mode", "voltage_v", "current_limit_a", "ovp_v", "ocp_enable", "slew_priority", "slew_rate_vs", "internal_res_ohm")
        }
        if self._applied_cfg and cur_cfg != self._applied_cfg:
            self._apply_psu_settings(inputs, turn_output_on=False)

        res = MeasurementResult()
        self.step_count += 1
        res.step_index = self.step_count

        ch_sel = inputs.get("channel", "CH1")
        ch_arg = " ALL" if (self.model_id == "SERIES_2200" and "ALL" in ch_sel) else ""

        v_val, i_val, p_val = 0.0, 0.0, 0.0
        if "meas_v" in selected_meas or "calc_load_r" in selected_meas:
            v_str, _ = self.visa.query(f"MEASure:SCALar:VOLTage:DC?{ch_arg}")
            v_val = float(v_str.split(",")[0].strip())
            if "meas_v" in selected_meas:
                res.scalars["meas_v"] = round(v_val, 5)
                res.primary_plot_y["Voltage (V)"] = v_val

        if "meas_i" in selected_meas or "calc_load_r" in selected_meas:
            i_str, _ = self.visa.query(f"MEASure:SCALar:CURRent:DC?{ch_arg}")
            i_val = float(i_str.split(",")[0].strip())
            if "meas_i" in selected_meas:
                res.scalars["meas_i"] = round(i_val, 6)
                res.primary_plot_y["Current (A)"] = i_val

        if "meas_p" in selected_meas:
            p_str, _ = self.visa.query(f"MEASure:SCALar:POWer:DC?{ch_arg}")
            p_val = float(p_str.split(",")[0].strip())
            res.scalars["meas_p"] = round(p_val, 5)
            res.primary_plot_y["Power (W)"] = p_val

        if "calc_load_r" in selected_meas:
            r_calc = v_val / i_val if abs(i_val) > 1e-7 else 0.0
            res.scalars["calc_load_r"] = round(r_calc, 4)

        if "prot_tripped" in selected_meas:
            if self.model_id == "SERIES_2260B":
                tr, _ = self.visa.query(":OUTPut:PROTection:TRIPped?")
            else:
                tr, _ = self.visa.query("STATus:QUEStionable:EVENt?")
            res.scalars["prot_tripped"] = "TRIPPED" if tr.strip() not in ("0", "+0") else "NORMAL (0)"

        if "out_state" in selected_meas:
            st, _ = self.visa.query("OUTPut:STATe?")
            res.scalars["out_state"] = "ON" if st.strip() in ("1", "ON") else "OFF"

        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        try:
            self.visa.write("OUTPut:STATe OFF")
        except Exception:
            pass


class MP5000Driver(BaseCategoryDriver):
    """
    03. DC Precision Test Driver (MP5000 Series Modular Precision Test System)
    Ref: 077189504_MP5000_Programmer_Manual_Aug2026.pdf
    Uses Test Script Processor (TSP) Lua commands: slot[Z].smu[X].* and slot[Z].psu[X].*
    """

    def _get_prefix(self, inputs: Dict[str, Any]) -> Tuple[str, bool]:
        slot_z = int(inputs.get("slot_no", "Slot 1").split()[-1])
        ch_x = int(inputs.get("channel_no", "Channel 1").split()[-1])
        is_smu = "SMU" in inputs.get("module_type", "SMU")
        mod_type = "smu" if is_smu else "psu"
        return f"slot[{slot_z}].{mod_type}[{ch_x}]", is_smu

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        pwd = inputs.get("auth_password", "").strip()
        if pwd:
            self.visa.write(f"login {pwd}")

        prefix, is_smu = self._get_prefix(inputs)
        self.visa.write(f"{prefix}.reset()")
        nplc = float(inputs.get("nplc", 1.0))
        self.visa.write(f"{prefix}.measure.nplc = {nplc}")

        is_v_source = "Voltage" in inputs.get("source_func", "Voltage") or not is_smu
        lvl = float(inputs.get("source_level", 3.3))
        lim = float(inputs.get("limit_val", 0.1))

        if is_smu:
            sense_str = inputs.get("sense_mode", "2-Wire")
            sense_val = f"{prefix}.SENSE_4WIRE" if "4-Wire" in sense_str else f"{prefix}.SENSE_2WIRE"
            self.visa.write(f"{prefix}.sense = {sense_val}")
            if is_v_source:
                self.visa.write(f"{prefix}.source.func = {prefix}.FUNC_DC_VOLTAGE")
                self.visa.write(f"{prefix}.source.levelv = {lvl}")
                self.visa.write(f"{prefix}.source.limiti = {lim}")
            else:
                self.visa.write(f"{prefix}.source.func = {prefix}.FUNC_DC_CURRENT")
                self.visa.write(f"{prefix}.source.leveli = {lvl}")
                self.visa.write(f"{prefix}.source.limitv = {lim}")
        else:
            self.visa.write(f"{prefix}.source.levelv = {lvl}")
            self.visa.write(f"{prefix}.source.limiti = {lim}")

        self.visa.write(f"{prefix}.source.output = 1")

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        res = MeasurementResult()
        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        self.step_count += 1
        res.step_index = self.step_count

        prefix, is_smu = self._get_prefix(inputs)
        test_mode = inputs.get("test_mode", "Continuous")
        is_v_source = "Voltage" in inputs.get("source_func", "Voltage") or not is_smu
        start_val = float(inputs.get("source_level", 1.0))
        stop_val = float(inputs.get("sweep_stop", 5.0))
        pts = max(2, int(inputs.get("sweep_points", 11)))

        if "Sweep" in test_mode:
            idx = self.step_count - 1
            if "Logarithmic" in test_mode:
                s0 = max(1e-6, abs(start_val))
                s1 = max(1e-6, abs(stop_val))
                cur_lvl = math.copysign(np.geomspace(s0, s1, pts)[min(idx, pts - 1)], stop_val)
            else:
                cur_lvl = np.linspace(start_val, stop_val, pts)[min(idx, pts - 1)]
            attr = "levelv" if is_v_source else "leveli"
            self.visa.write(f"{prefix}.source.{attr} = {cur_lvl:.6f}")
            if self.step_count >= pts:
                res.is_completed_sweep = True

        v_str, _ = self.visa.query(f"print({prefix}.measure.v())")
        i_str, _ = self.visa.query(f"print({prefix}.measure.i())")
        v_val = float(v_str.split()[0])
        i_val = float(i_str.split()[0])

        res.primary_plot_x = v_val
        if "meas_v" in selected_meas:
            res.scalars["meas_v"] = round(v_val, 6)
            res.primary_plot_y["Voltage (V)"] = v_val
        if "meas_i" in selected_meas:
            res.scalars["meas_i"] = round(i_val, 8)
            res.primary_plot_y["Current (A)"] = i_val
        if "calc_r" in selected_meas:
            r_val = v_val / i_val if abs(i_val) > 1e-12 else 0.0
            res.scalars["calc_r"] = round(r_val, 4)
        if "calc_p" in selected_meas:
            p_val = v_val * i_val
            res.scalars["calc_p"] = round(p_val, 7)
            res.primary_plot_y["Power (W)"] = p_val
        if "at_limit" in selected_meas:
            lim_attr = "source.atlimit" if is_smu else "source.constantcurrent"
            lim_str, _ = self.visa.query(f"print({prefix}.{lim_attr})")
            res.scalars["at_limit"] = lim_str
        if is_smu and "contact_r" in selected_meas:
            cr, _ = self.visa.query(f"print({prefix}.contact.r())")
            res.scalars["contact_r"] = float(cr)
        if is_smu and "slot_temp" in selected_meas:
            td, _ = self.visa.query(f"print({prefix}.acal.temperaturedelta())")
            res.scalars["slot_temp"] = float(td)

        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        prefix, _ = self._get_prefix(inputs)
        try:
            self.visa.write(f"{prefix}.source.output = 0")
        except Exception:
            pass


class OscilloscopeDriver(BaseCategoryDriver):
    """
    04. Oscilloscopes Driver (TBS1000C, TBS2000B, 2 Series MSO, 3 Series MDO, 4/5/6 Series MSO, 7 Series DPO, DPO70000)
    Ref: 7 Oscilloscope Programmer Manuals in 04. Oscilloscopes
    """

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        ch_choice = inputs.get("channel", "CH1")
        ch_main = "CH1" if "Dual" in ch_choice else ch_choice

        self.visa.write("HEADer OFF")
        self.visa.write(f"SELect:{ch_main} ON")
        if "Dual" in ch_choice:
            self.visa.write("SELect:CH2 ON")

        if inputs.get("use_autoset", False):
            self.visa.write("AUTOSet EXECute")
        else:
            coup = inputs.get("coupling", "DC")
            v_scale = float(inputs.get("v_scale", 1.0))
            v_off = float(inputs.get("v_offset", 0.0))
            h_scale = float(inputs.get("h_scale", 0.001))
            trig_src = inputs.get("trig_source", "CH1")
            trig_lvl = float(inputs.get("trig_level", 0.0))
            trig_slp = inputs.get("trig_slope", "RISe")
            acq_mode = inputs.get("acq_mode", "SAMple")

            self.visa.write(f"{ch_main}:COUPling {coup}")
            self.visa.write(f"{ch_main}:SCAle {v_scale}")
            self.visa.write(f"{ch_main}:OFFSet {v_off}")
            self.visa.write(f"HORizontal:SCAle {h_scale}")
            self.visa.write(f"TRIGger:A:EDGE:SOUrce {trig_src}")
            self.visa.write(f"TRIGger:A:EDGE:SLOpe {trig_slp}")
            self.visa.write(f"TRIGger:A:LEVel {trig_lvl}")
            self.visa.write(f"ACQuire:MODe {acq_mode}")

        rec_pts = int(inputs.get("record_pts", 1000))
        self.visa.write(f"DATa:SOUrce {ch_main}")
        self.visa.write("DATa:ENCdg ASCIi")
        self.visa.write("DATa:WIDth 1")
        self.visa.write("DATa:STARt 1")
        self.visa.write(f"DATa:STOP {rec_pts}")
        self.visa.write("ACQuire:STATE RUN")

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        res = MeasurementResult()
        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        self.step_count += 1
        res.step_index = self.step_count

        ch_choice = inputs.get("channel", "CH1")
        ch_main = "CH1" if "Dual" in ch_choice else ch_choice

        # Automated immediate measurements
        meas_map = {
            "meas_freq": ("FREQuency", "Frequency (Hz)"),
            "meas_period": ("PERIod", "Period (s)"),
            "meas_pk2pk": ("PK2Pk", "Vpp (V)"),
            "meas_mean": ("MEAN", "Vmean (V)"),
            "meas_rms": ("CRMs", "Vrms (V)"),
            "meas_max": ("MAXImum", "Vmax (V)"),
            "meas_min": ("MINImum", "Vmin (V)"),
        }
        for key, (scpi_type, plot_lbl) in meas_map.items():
            if key in selected_meas:
                self.visa.write(f"MEASUrement:IMMed:SOUrce1 {ch_main}")
                self.visa.write(f"MEASUrement:IMMed:TYPe {scpi_type}")
                val_str, _ = self.visa.query("MEASUrement:IMMed:VALue?")
                try:
                    val = float(val_str.split()[-1])
                except ValueError:
                    val = 0.0
                res.scalars[key] = round(val, 6)
                res.primary_plot_y[plot_lbl] = val

        # Waveform CURVe? transfer and scaling: Y = YZERO + YMULT * (data - YOFF)
        if "wfm_curve" in selected_meas:
            v_scale = float(inputs.get("v_scale", 1.0))
            h_scale = float(inputs.get("h_scale", 0.001))
            curve_str, _ = self.visa.query("CURVe?")
            try:
                raw_pts = np.array([float(x) for x in curve_str.split(",") if x.strip()], dtype=float)
            except Exception:
                raw_pts = np.zeros(500)
            ymult = v_scale / 25.0
            yoff = 0.0
            yzero = float(inputs.get("v_offset", 0.0))
            v_wave = yzero + ymult * (raw_pts - yoff)
            t_wave = np.linspace(0, h_scale * 10.0, len(v_wave)) * 1e3  # ms

            res.waveform_x = t_wave
            res.waveform_y = v_wave
            res.waveform_x_label = "Time (ms)"
            res.waveform_y_label = f"{ch_main} Voltage (V)"
            res.waveform_title = f"Oscilloscope {ch_main} Waveform ({len(v_wave)} pts, {v_scale} V/div, {h_scale*1e3:g} ms/div)"
            res.scalars["wfm_curve"] = f"{len(v_wave)} samples captured"

        return res

    def pause_measurement(self, inputs: Dict[str, Any]):
        try:
            self.visa.write("ACQuire:STATE STOP")
        except Exception:
            pass

    def resume_measurement(self, inputs: Dict[str, Any]):
        try:
            self.visa.write("ACQuire:STATE RUN")
        except Exception:
            pass

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        try:
            self.visa.write("ACQuire:STATE STOP")
        except Exception:
            pass


class SpectrumAnalyzerDriver(BaseCategoryDriver):
    """
    05. Spectrum Analyzers Driver (SignalVu-PC / RSA300/500/600 & RSA5000/6000)
    Ref: SignalVu-Programmer-Manual_EN-US_077-0223-10_077022310.pdf, Programming_Appnote_37W-61459-0.pdf
    """

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        cf_mhz = float(inputs.get("center_freq_mhz", 1000.0))
        span_mhz = float(inputs.get("span_mhz", 40.0))
        ref_dbm = float(inputs.get("ref_level_dbm", 0.0))
        rbw_auto = inputs.get("rbw_auto", True)
        rbw_khz = float(inputs.get("rbw_khz", 100.0))
        tr_func = inputs.get("trace_func", "NORMal")

        # Note from manual p.7: Ensure Spectrum view is active before sending spectrum commands
        self.visa.write("DISPlay:GENeral:MEASview:NEW SPECtrum")
        self.visa.write(f"SENSe:SPECtrum:FREQuency:CENTer {cf_mhz}MHz")
        self.visa.write(f"SENSe:SPECtrum:FREQuency:SPAN {span_mhz}MHz")
        self.visa.write(f"INPut:MLEVel {ref_dbm}dBm")
        if rbw_auto:
            self.visa.write("SENSe:SPECtrum:BANDwidth:RESolution:AUTO ON")
        else:
            self.visa.write("SENSe:SPECtrum:BANDwidth:RESolution:AUTO OFF")
            self.visa.write(f"SENSe:SPECtrum:BANDwidth:RESolution {rbw_khz}kHz")
        self.visa.write(f"TRACe1:SPECtrum:FUNCtion {tr_func}")
        self.visa.write("INITiate:CONTinuous ON")

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        res = MeasurementResult()
        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        self.step_count += 1
        res.step_index = self.step_count

        cf_mhz = float(inputs.get("center_freq_mhz", 1000.0))
        span_mhz = float(inputs.get("span_mhz", 40.0))

        trace_str, _ = self.visa.query("READ:SPECtrum:TRACe1?")
        try:
            power_dbm = np.array([float(x) for x in trace_str.split(",") if x.strip()], dtype=float)
        except Exception:
            power_dbm = np.full(801, -90.0)

        freqs_mhz = np.linspace(cf_mhz - span_mhz / 2.0, cf_mhz + span_mhz / 2.0, len(power_dbm))

        if "spec_trace" in selected_meas:
            res.waveform_x = freqs_mhz
            res.waveform_y = power_dbm
            res.waveform_x_label = "Frequency (MHz)"
            res.waveform_y_label = "Amplitude (dBm)"
            res.waveform_title = f"RF Spectrum Trace1 (Center={cf_mhz:g} MHz, Span={span_mhz:g} MHz)"
            res.scalars["spec_trace"] = f"{len(power_dbm)} bins"

        self.visa.write("CALCulate:SPECtrum:MARKer1:MAXimum")
        if "peak_freq_mhz" in selected_meas:
            pk_f_str, _ = self.visa.query("CALCulate:SPECtrum:MARKer1:X?")
            pk_f_mhz = float(pk_f_str) / 1e6
            res.scalars["peak_freq_mhz"] = round(pk_f_mhz, 6)
            res.primary_plot_y["Peak Freq (MHz)"] = pk_f_mhz

        if "peak_amp_dbm" in selected_meas:
            pk_y_str, _ = self.visa.query("CALCulate:SPECtrum:MARKer1:Y?")
            pk_y_dbm = float(pk_y_str)
            res.scalars["peak_amp_dbm"] = round(pk_y_dbm, 2)
            res.primary_plot_y["Peak Power (dBm)"] = pk_y_dbm

        if "noise_floor_dbm" in selected_meas and len(power_dbm) > 0:
            nf = float(np.median(power_dbm))
            res.scalars["noise_floor_dbm"] = round(nf, 2)
            res.primary_plot_y["Noise Floor (dBm)"] = nf

        if "ch_power_dbm" in selected_meas and len(power_dbm) > 0:
            lin_mw = np.sum(10.0 ** (power_dbm / 10.0)) / len(power_dbm)
            ch_p = 10.0 * math.log10(max(1e-15, lin_mw))
            res.scalars["ch_power_dbm"] = round(ch_p, 2)

        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        try:
            self.visa.write("ABORt")
            self.visa.write("INITiate:CONTinuous OFF")
        except Exception:
            pass


class SMUDriver(BaseCategoryDriver):
    """
    06. SMUs Driver (Keithley 2450/2460/2461/2470 SCPI/TSP & 2600B/2601B-PULSE/2606B/2651A TSP)
    Ref: 8 Reference Manuals in 06. SMUs
    """

    def __init__(self, visa_mgr, category_id: str, model_id: str):
        super().__init__(visa_mgr, category_id, model_id)
        self.active_lang = "SCPI"

    def _determine_lang(self, inputs: Dict[str, Any]) -> str:
        if self.model_id.startswith("SMU_26"):
            return "TSP"
        choice = inputs.get("cmd_lang", "AUTO")
        if "SCPI" in choice:
            return "SCPI"
        if "TSP" in choice:
            return "TSP"
        try:
            lang_resp, _ = self.visa.query("*LANG?")
            return "TSP" if "TSP" in lang_resp.upper() else "SCPI"
        except Exception:
            return "SCPI"

    def _get_tsp_smu(self, inputs: Dict[str, Any]) -> str:
        if self.model_id.startswith("SMU_24"):
            return "smu"
        ch = inputs.get("smu_channel", "smua")
        return "smub" if "smub" in ch else "smua"

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        self.active_lang = self._determine_lang(inputs)
        is_v_src = "Voltage" in inputs.get("source_func", "Voltage")
        lvl = float(inputs.get("source_level", 1.0))
        lim = float(inputs.get("compliance_limit", 0.05))
        nplc = float(inputs.get("nplc", 1.0))
        is_4wire = "4-Wire" in inputs.get("sense_wire", "2-Wire")

        if self.active_lang == "SCPI":
            self.visa.write("*RST")
            term = "REAR" if "REAR" in inputs.get("terminals", "FRONt") else "FRONt"
            self.visa.write(f":ROUTe:TERMinals {term}")
            sense_fn = "CURRent" if is_v_src else "VOLTage"
            self.visa.write(f':SENSe:FUNCtion "{sense_fn}"')
            self.visa.write(f":SENSe:{sense_fn}:NPLCycles {nplc}")
            self.visa.write(f":SENSe:{sense_fn}:RSENse {'ON' if is_4wire else 'OFF'}")
            if is_v_src:
                self.visa.write(":SOURce:FUNCtion VOLTage")
                self.visa.write(f":SOURce:VOLTage:LEVel {lvl}")
                self.visa.write(f":SOURce:VOLTage:ILIMit {lim}")
            else:
                self.visa.write(":SOURce:FUNCtion CURRent")
                self.visa.write(f":SOURce:CURRent:LEVel {lvl}")
                self.visa.write(f":SOURce:CURRent:VLIMit {lim}")
            self.visa.write(":OUTPut:STATe ON")
        else:
            smu = self._get_tsp_smu(inputs)
            self.visa.write(f"{smu}.reset()")
            if self.model_id == "SMU_2601B_PULSE":
                # Manual p.2-8: Must disable pulser before normal DC SMU operation
                self.visa.write(f"{smu}.pulser.enable = {smu}.DISABLE")
            self.visa.write(f"{smu}.measure.nplc = {nplc}")
            if self.model_id.startswith("SMU_24"):
                self.visa.write(f"{smu}.measure.sense = {smu}.{'SENSE_4WIRE' if is_4wire else 'SENSE_2WIRE'}")
                if is_v_src:
                    self.visa.write(f"{smu}.source.func = {smu}.FUNC_DC_VOLTAGE")
                    self.visa.write(f"{smu}.source.level = {lvl}")
                    self.visa.write(f"{smu}.source.ilimit.level = {lim}")
                    self.visa.write(f"{smu}.measure.func = {smu}.FUNC_DC_CURRENT")
                else:
                    self.visa.write(f"{smu}.source.func = {smu}.FUNC_DC_CURRENT")
                    self.visa.write(f"{smu}.source.level = {lvl}")
                    self.visa.write(f"{smu}.source.vlimit.level = {lim}")
                    self.visa.write(f"{smu}.measure.func = {smu}.FUNC_DC_VOLTAGE")
                self.visa.write(f"{smu}.source.output = {smu}.ON")
            else:
                # 2600B Series TSP syntax
                self.visa.write(f"{smu}.sense = {smu}.{'SENSE_REMOTE' if is_4wire else 'SENSE_LOCAL'}")
                if inputs.get("high_cap", False):
                    self.visa.write(f"{smu}.source.highc = {smu}.ENABLE")
                if is_v_src:
                    self.visa.write(f"{smu}.source.func = {smu}.OUTPUT_DCVOLTS")
                    self.visa.write(f"{smu}.source.levelv = {lvl}")
                    self.visa.write(f"{smu}.source.limiti = {lim}")
                else:
                    self.visa.write(f"{smu}.source.func = {smu}.OUTPUT_DCAMPS")
                    self.visa.write(f"{smu}.source.leveli = {lvl}")
                    self.visa.write(f"{smu}.source.limitv = {lim}")
                self.visa.write(f"{smu}.source.output = {smu}.OUTPUT_ON")

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        res = MeasurementResult()
        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        self.step_count += 1
        res.step_index = self.step_count

        op_mode = inputs.get("op_mode", "Continuous")
        is_v_src = "Voltage" in inputs.get("source_func", "Voltage")
        start_val = float(inputs.get("source_level", 1.0))
        stop_val = float(inputs.get("sweep_stop", 5.0))
        pts = max(2, int(inputs.get("sweep_points", 21)))
        smu = self._get_tsp_smu(inputs)

        if "Sweep" in op_mode:
            idx = min(self.step_count - 1, pts - 1)
            cur_lvl = float(np.linspace(start_val, stop_val, pts)[idx])
            if self.active_lang == "SCPI":
                cmd_src = "VOLTage" if is_v_src else "CURRent"
                self.visa.write(f":SOURce:{cmd_src}:LEVel {cur_lvl:.6f}")
            else:
                if self.model_id.startswith("SMU_24"):
                    self.visa.write(f"{smu}.source.level = {cur_lvl:.6f}")
                else:
                    attr = "levelv" if is_v_src else "leveli"
                    self.visa.write(f"{smu}.source.{attr} = {cur_lvl:.6f}")
            if self.step_count >= pts:
                res.is_completed_sweep = True

        if self.active_lang == "SCPI":
            v_str, _ = self.visa.query(":MEASure:VOLTage?")
            i_str, _ = self.visa.query(":MEASure:CURRent?")
            v_val = float(v_str.split(",")[0])
            i_val = float(i_str.split(",")[0])
        else:
            v_str, _ = self.visa.query(f"print({smu}.measure.v())")
            i_str, _ = self.visa.query(f"print({smu}.measure.i())")
            v_val = float(v_str.split()[0])
            i_val = float(i_str.split()[0])

        r_val = v_val / i_val if abs(i_val) > 1e-12 else 0.0
        p_val = v_val * i_val

        res.primary_plot_x = v_val
        if "meas_v" in selected_meas:
            res.scalars["meas_v"] = round(v_val, 6)
            res.primary_plot_y["Voltage (V)"] = v_val
        if "meas_i" in selected_meas:
            res.scalars["meas_i"] = round(i_val, 8)
            res.primary_plot_y["Current (A)"] = i_val
        if "meas_r" in selected_meas:
            res.scalars["meas_r"] = round(r_val, 4)
        if "meas_p" in selected_meas:
            res.scalars["meas_p"] = round(p_val, 7)
            res.primary_plot_y["Power (W)"] = p_val
        if "compliance_state" in selected_meas:
            lim = float(inputs.get("compliance_limit", 0.05))
            tripped = abs(abs(i_val if is_v_src else v_val) - abs(lim)) < (abs(lim) * 0.02)
            res.scalars["compliance_state"] = "LIMIT TRIPPED" if tripped else "NORMAL"

        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        try:
            if self.active_lang == "SCPI":
                self.visa.write(":OUTPut:STATe OFF")
            else:
                smu = self._get_tsp_smu(inputs)
                off_const = f"{smu}.OFF" if self.model_id.startswith("SMU_24") else f"{smu}.OUTPUT_OFF"
                self.visa.write(f"{smu}.source.output = {off_const}")
        except Exception:
            pass


class TekVISATalkerDriver(BaseCategoryDriver):
    """
    07. Tek VISA Driver (OpenChoice Talker/Listener Script & Loop Runner)
    Ref: TekVISA_OpenChoice_Talker_Listener_EN_US_077178600.pdf, TekVISA_Programmer_Manual
    """

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        init_cmd = inputs.get("init_cmd", "").strip()
        if init_cmd:
            self.visa.write(init_cmd)

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        res = MeasurementResult()
        res.elapsed_s = round(time.time() - self.start_epoch, 3)
        self.step_count += 1
        res.step_index = self.step_count

        q_cmd = inputs.get("query_cmd", "*IDN?").strip()
        if not q_cmd:
            q_cmd = "*IDN?"

        resp, latency_ms = self.visa.query(q_cmd)
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", resp)
        val1 = float(nums[0]) if len(nums) >= 1 else 0.0
        val2 = float(nums[1]) if len(nums) >= 2 else 0.0

        if "parsed_val_1" in selected_meas:
            res.scalars["parsed_val_1"] = val1
            res.primary_plot_y["Query Value #1"] = val1
        if "parsed_val_2" in selected_meas:
            res.scalars["parsed_val_2"] = val2
            if len(nums) >= 2:
                res.primary_plot_y["Query Value #2"] = val2
        if "latency_ms" in selected_meas:
            res.scalars["latency_ms"] = round(latency_ms, 2)
            res.primary_plot_y["Latency (ms)"] = round(latency_ms, 2)
        if "raw_response" in selected_meas:
            res.scalars["raw_response"] = resp
        if "stb_val" in selected_meas:
            stb, _ = self.visa.query("*STB?")
            res.scalars["stb_val"] = stb

        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        stop_cmd = inputs.get("stop_cmd", "").strip()
        if stop_cmd:
            try:
                self.visa.write(stop_cmd)
            except Exception:
                pass


class DMMDriver(BaseCategoryDriver):
    """
    08. Digit Multimeter (DMM) Driver (Keithley DMM6500 / DMM7510 SCPI & TSP, Model 2110 & Model 2010 SCPI)
    Ref: 4 Reference / User Manuals in 08. Digit Multimeter(DMM)
    """

    def __init__(self, visa_mgr, category_id: str, model_id: str):
        super().__init__(visa_mgr, category_id, model_id)
        self.active_lang = "SCPI"
        self.reading_buffer: List[float] = []
        self.scpi_func = "VOLTage:DC"
        self.unit_label = "V"
        self.cached_terminals = "FRON"
        self._applied_cfg: Dict[str, Any] = {}

    def _determine_lang(self, inputs: Dict[str, Any]) -> str:
        if self.model_id in ("DMM_2110", "DMM_2010"):
            return "SCPI"
        choice = inputs.get("cmd_lang", "AUTO")
        if "SCPI" in choice:
            return "SCPI"
        if "TSP" in choice:
            return "TSP"
        try:
            lang_resp, _ = self.visa.query("*LANG?")
            return "TSP" if "TSP" in lang_resp.upper() else "SCPI"
        except Exception:
            return "SCPI"

    @staticmethod
    def _parse_func_selection(func_choice: str) -> tuple[str, str, str]:
        """Returns (scpi_func, tsp_func_const, unit_str)."""
        fc = func_choice.upper()
        if "VOLT:AC" in fc:
            return "VOLTage:AC", "dmm.FUNC_AC_VOLTAGE", "V"
        if "CURR:DC" in fc:
            return "CURRent:DC", "dmm.FUNC_DC_CURRENT", "A"
        if "CURR:AC" in fc:
            return "CURRent:AC", "dmm.FUNC_AC_CURRENT", "A"
        if "FRES" in fc:
            return "FRESistance", "dmm.FUNC_4W_RESISTANCE", "Ω"
        if "RES" in fc:
            return "RESistance", "dmm.FUNC_RESISTANCE", "Ω"
        if "FREQ" in fc:
            return "FREQuency", "dmm.FUNC_FREQUENCY", "Hz"
        if "TEMP" in fc:
            return "TEMPerature", "dmm.FUNC_TEMPERATURE", "°C"
        if "CAP" in fc:
            return "CAPacitance", "dmm.FUNC_CAPACITANCE", "F"
        if "DIG" in fc:
            return "DIGitize:VOLTage", "dmm.FUNC_DIGITIZE_VOLTAGE", "V"
        return "VOLTage:DC", "dmm.FUNC_DC_VOLTAGE", "V"

    def _apply_dmm_settings(self, inputs: Dict[str, Any], full_reset: bool = False):
        scpi_fn, tsp_fn, unit_lbl = self._parse_func_selection(str(inputs.get("dmm_func", "VOLT:DC")))
        self.scpi_func = scpi_fn
        self.unit_label = unit_lbl

        rng = float(inputs.get("meas_range", 0.0))
        nplc = float(inputs.get("nplc", 0.1))
        az_choice = str(inputs.get("auto_zero", "ONCE"))
        lsync = bool(inputs.get("line_sync", False))
        avg_choice = str(inputs.get("avg_filter", "OFF"))
        ocomp = bool(inputs.get("offset_comp", False))
        dig_rate = int(inputs.get("digitize_rate", 100000))
        dig_cnt = max(10, int(inputs.get("digitize_count", 200)))

        if self.active_lang == "SCPI":
            if full_reset:
                self.visa.write("*RST")
                self.visa.write("*CLS")
            if scpi_fn.startswith("DIGitize"):
                self.visa.write(':SENSe:DIGitize:FUNCtion "VOLTage"')
                self.visa.write(f":SENSe:DIGitize:VOLTage:SRATe {dig_rate}")
                self.visa.write(f":SENSe:DIGitize:COUNt {dig_cnt}")
            elif self.model_id == "DMM_2110":
                self.visa.write(f"CONFigure:{scpi_fn}")
                if scpi_fn in ("VOLTage:DC", "CURRent:DC", "RESistance", "FRESistance"):
                    self.visa.write(f"SENSe:{scpi_fn}:NPLCycles {nplc}")
            else:
                self.visa.write(f':SENSe:FUNCtion "{scpi_fn}"')
                if rng <= 0.0:
                    self.visa.write(f":SENSe:{scpi_fn}:RANGe:AUTO ON")
                else:
                    self.visa.write(f":SENSe:{scpi_fn}:RANGe {rng}")
                if scpi_fn in ("VOLTage:DC", "CURRent:DC", "RESistance", "FRESistance", "TEMPerature"):
                    self.visa.write(f":SENSe:{scpi_fn}:NPLCycles {nplc}")
                    if "ONCE" in az_choice.upper():
                        self.visa.write(f":SENSe:{scpi_fn}:AZERo OFF")
                        if self.model_id in ("DMM6500", "DMM7510"):
                            self.visa.write(":SENSe:AZERo:ONCE")
                    elif "OFF" in az_choice.upper():
                        self.visa.write(f":SENSe:{scpi_fn}:AZERo OFF")
                    else:
                        self.visa.write(f":SENSe:{scpi_fn}:AZERo ON")
                    if self.model_id in ("DMM6500", "DMM7510"):
                        self.visa.write(f":SENSe:{scpi_fn}:LINE:SYNC {'ON' if lsync else 'OFF'}")
                    elif self.model_id == "DMM_2010":
                        self.visa.write(f":SENSe:{scpi_fn}:LSYNc {'ON' if lsync else 'OFF'}")
                if scpi_fn == "FRESistance" and ocomp:
                    self.visa.write(":SENSe:FRESistance:OCOMpensated ON")
                if "OFF" not in avg_choice:
                    tcon = "REPeat" if "REP" in avg_choice.upper() else "MOVing"
                    self.visa.write(f":SENSe:{scpi_fn}:AVERage:TCONtrol {tcon}")
                    self.visa.write(f":SENSe:{scpi_fn}:AVERage:COUNt 10")
                    self.visa.write(f":SENSe:{scpi_fn}:AVERage:STATe ON")
                elif not full_reset:
                    self.visa.write(f":SENSe:{scpi_fn}:AVERage:STATe OFF")
            if self.model_id in ("DMM6500", "DMM7510") and full_reset:
                self.visa.write(f':TRACe:POINts { max(dig_cnt, 1000) }, "defbuffer1"')
        else:
            # TSP mode (DMM6500 / DMM7510)
            if full_reset:
                self.visa.write("reset()")
            if scpi_fn.startswith("DIGitize"):
                self.visa.write("dmm.digitize.func = dmm.FUNC_DIGITIZE_VOLTAGE")
                self.visa.write(f"dmm.digitize.samplerate = {dig_rate}")
                self.visa.write(f"dmm.digitize.count = {dig_cnt}")
            else:
                self.visa.write(f"dmm.measure.func = {tsp_fn}")
                if rng <= 0.0:
                    self.visa.write("dmm.measure.autorange = dmm.ON")
                else:
                    self.visa.write(f"dmm.measure.range = {rng}")
                self.visa.write(f"dmm.measure.nplc = {nplc}")
                if "ONCE" in az_choice.upper():
                    self.visa.write("dmm.measure.autozero = dmm.OFF")
                    self.visa.write("dmm.measure.autozero = dmm.ONCE")
                elif "OFF" in az_choice.upper():
                    self.visa.write("dmm.measure.autozero = dmm.OFF")
                else:
                    self.visa.write("dmm.measure.autozero = dmm.ON")
                self.visa.write(f"dmm.measure.linesync = {'dmm.ON' if lsync else 'dmm.OFF'}")
                if scpi_fn == "FRESistance" and ocomp:
                    self.visa.write("dmm.measure.offsetcompensation = dmm.OCOMP_ON")

        self._applied_cfg = {
            k: inputs.get(k)
            for k in ("dmm_func", "meas_range", "nplc", "auto_zero", "line_sync", "avg_filter", "offset_comp", "digitize_rate", "digitize_count")
        }

    def configure_and_start(self, inputs: Dict[str, Any], selected_meas: List[str]):
        super().configure_and_start(inputs, selected_meas)
        self.reading_buffer.clear()
        self.active_lang = self._determine_lang(inputs)
        self._apply_dmm_settings(inputs, full_reset=True)
        try:
            if self.active_lang == "SCPI":
                t_str, _ = self.visa.query(":ROUTe:TERMinals?")
            else:
                t_str, _ = self.visa.query("print(localnode.terminals)")
            self.cached_terminals = t_str.strip() or "FRON"
        except Exception:
            self.cached_terminals = "FRON"
        # Reset start_epoch AFTER *RST and initial config so Step 1 starts at 0.00s
        self.start_epoch = time.time()

    def acquire_step(self, inputs: Dict[str, Any], selected_meas: List[str]) -> MeasurementResult:
        # Dynamically apply any DMM parameter changes made by the user while running
        cur_cfg = {
            k: inputs.get(k)
            for k in ("dmm_func", "meas_range", "nplc", "auto_zero", "line_sync", "avg_filter", "offset_comp", "digitize_rate", "digitize_count")
        }
        if self._applied_cfg and cur_cfg != self._applied_cfg:
            self._apply_dmm_settings(inputs, full_reset=False)

        res = MeasurementResult()
        self.step_count += 1
        res.step_index = self.step_count

        if self.active_lang == "SCPI":
            if self.scpi_func.startswith("DIGitize"):
                val_str, _ = self.visa.query(":READ:DIGitize?")
            elif self.model_id == "DMM_2110":
                val_str, _ = self.visa.query(f"MEASure:{self.scpi_func}?")
            else:
                val_str, _ = self.visa.query(":READ?")
        else:
            if self.scpi_func.startswith("DIGitize"):
                val_str, _ = self.visa.query("print(dmm.digitize.read())")
            else:
                val_str, _ = self.visa.query("print(dmm.measure.read())")

        res.elapsed_s = round(time.time() - self.start_epoch, 3)

        try:
            reading = float(val_str.split(",")[0].strip())
        except Exception:
            reading = 0.0

        self.reading_buffer.append(reading)
        arr = np.array(self.reading_buffer, dtype=float)
        mean_val = float(np.mean(arr))
        pk2pk_val = float(np.max(arr) - np.min(arr))
        std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0

        series_lbl = f"Reading ({self.unit_label})"
        if "primary_reading" in selected_meas:
            res.scalars["primary_reading"] = round(reading, 7)
            res.primary_plot_y[series_lbl] = reading
        if "reading_mean" in selected_meas:
            res.scalars["reading_mean"] = round(mean_val, 7)
            res.primary_plot_y[f"Mean ({self.unit_label})"] = mean_val
        if "reading_pk2pk" in selected_meas:
            res.scalars["reading_pk2pk"] = round(pk2pk_val, 7)
        if "reading_std" in selected_meas:
            res.scalars["reading_std"] = round(std_val, 7)
        if "active_terminals" in selected_meas:
            # Refresh physical front/rear switch only every 25 steps so normal steps need just 1 fast :READ? query
            if self.step_count % 25 == 0:
                try:
                    if self.active_lang == "SCPI":
                        term_str, _ = self.visa.query(":ROUTe:TERMinals?")
                    else:
                        term_str, _ = self.visa.query("print(localnode.terminals)")
                    self.cached_terminals = term_str.strip() or self.cached_terminals
                except Exception:
                    pass
            res.scalars["active_terminals"] = self.cached_terminals

        if "digitizer_trace" in selected_meas:
            cnt = max(10, int(inputs.get("digitize_count", 200)))
            if self.scpi_func.startswith("DIGitize"):
                if self.active_lang == "SCPI":
                    tr_str, _ = self.visa.query(f':TRACe:DATA? 1, {cnt}, "defbuffer1", READ')
                else:
                    tr_str, _ = self.visa.query(f"printbuffer(1, {cnt}, defbuffer1.readings)")
                try:
                    y_arr = np.array([float(x) for x in tr_str.split(",") if x.strip()], dtype=float)
                except Exception:
                    y_arr = arr[-cnt:].copy()
                rate = max(1, int(inputs.get("digitize_rate", 100000)))
                x_arr = np.arange(len(y_arr), dtype=float) * (1000.0 / rate)  # ms
                res.waveform_x_label = "Sample Time (ms)"
            else:
                # For standard DC/AC/Resistance meter modes, use in-memory rolling buffer (zero extra USB latency)
                y_arr = arr[-cnt:].copy()
                x_arr = np.arange(1, len(y_arr) + 1, dtype=float)
                res.waveform_x_label = "Buffer Reading Index"
            res.waveform_x = x_arr
            res.waveform_y = y_arr
            res.waveform_y_label = f"Amplitude ({self.unit_label})"
            res.waveform_title = f"DMM Digitizer / Buffer Trace ({len(y_arr)} pts)"
            res.scalars["digitizer_trace"] = f"{len(y_arr)} samples"

        return res

    def stop_and_safe_shutdown(self, inputs: Dict[str, Any]):
        try:
            if self.active_lang == "SCPI" and self.model_id in ("DMM6500", "DMM7510"):
                self.visa.write(":ABORt")
        except Exception:
            pass


def create_driver_for_category(visa_mgr, category_id: str, model_id: str) -> BaseCategoryDriver:
    driver_map = {
        "01_AFG": AFGDriver,
        "02_DC_POWER": DCPowerDriver,
        "03_DC_PRECISION": MP5000Driver,
        "04_OSCILLOSCOPE": OscilloscopeDriver,
        "05_SPECTRUM": SpectrumAnalyzerDriver,
        "06_SMU": SMUDriver,
        "07_TEK_VISA": TekVISATalkerDriver,
        "08_DMM": DMMDriver,
    }
    cls = driver_map.get(category_id, TekVISATalkerDriver)
    return cls(visa_mgr, category_id, model_id)
