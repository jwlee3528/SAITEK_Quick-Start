# -*- coding: utf-8 -*-
"""
Tektronix QuickStart Program - VISA Connection & Simulation Manager
Supports TekVISA / NI-VISA / PyVISA-py for USB (USBTMC & USB-CDC) and LAN (TCPIP / VXI-11 / Socket),
plus a physics-based Virtual Hardware Simulation mode for all 7 Tektronix/Keithley categories.
"""

import time
import math
import random
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    pyvisa = None
    PYVISA_AVAILABLE = False


@dataclass
class IOTranscriptEntry:
    timestamp: str
    direction: str  # "WRITE", "READ", "QUERY", "INFO", "ERROR"
    resource: str
    command: str
    response: str = ""
    latency_ms: float = 0.0


class VirtualInstrumentSimulator:
    """
    Realistic SCPI & TSP simulator for all 7 Tektronix / Keithley manual folders
    so users can test every feature without physical hardware attached.
    """

    def __init__(self, category_id: str = "01_AFG", model_id: str = "AFG31000"):
        self.category_id = category_id
        self.model_id = model_id
        self.reset_state()

    def reset_state(self):
        self.start_time = time.time()
        self.output_on = False
        self.lang = "SCPI"
        self.authenticated = True
        self.remote_allowed = "Allowed"
        # AFG state
        self.afg = {
            1: {"func": "SIN", "freq": 1000.0, "amp": 2.0, "offset": 0.0, "phase": 0.0, "imp": 50.0, "out": 0, "duty": 50.0},
            2: {"func": "SQU", "freq": 1000.0, "amp": 1.0, "offset": 0.0, "phase": 90.0, "imp": 50.0, "out": 0, "duty": 50.0},
        }
        # DC Power state
        self.psu_sel_ch = 1
        self.psu_combine = "NONE"
        self.psu = {
            1: {"v_set": 5.0, "i_lim": 1.0, "ovp": 12.0, "out": 0, "load_r": 10.0},
            2: {"v_set": 12.0, "i_lim": 1.0, "ovp": 15.0, "out": 0, "load_r": 24.0},
            3: {"v_set": 3.3, "i_lim": 2.0, "ovp": 6.0, "out": 0, "load_r": 5.0},
        }
        # MP5000 & SMU state
        self.smu_func = "VOLT"  # or "CURR"
        self.smu_level = 1.0
        self.smu_limit = 0.05
        self.smu_nplc = 1.0
        self.smu_sense = "2WIRE"
        self.smu_dut_r = 250.0  # simulated DUT resistance (250 ohms + slight non-linear diode behavior)
        # Scope state
        self.scope_vscale = 1.0
        self.scope_voffset = 0.0
        self.scope_hscale = 0.001
        self.scope_source = "CH1"
        self.scope_meas_type = "FREQuency"
        self.scope_stop = 1000
        self.scope_meas_slots: Dict[int, Tuple[str, str]] = {}  # slot_idx -> (ch, meas_type)
        # Spectrum state
        self.spec_center_hz = 1000e6
        self.spec_span_hz = 40e6
        self.spec_ref_dbm = 0.0
        self.spec_rbw_hz = 100e3
        self.spec_points = 801
        # DMM state (08. Digit Multimeter)
        self.dmm_func = "VOLT:DC"
        self.dmm_range = 10.0
        self.dmm_auto_range = True
        self.dmm_nplc = 1.0
        self.dmm_terminals = "FRON"
        self.dmm_dig_rate = 100000
        self.dmm_dig_count = 200
        self.last_tsp_print = "0.0"

    def get_idn(self) -> str:
        idn_map = {
            "AFG31000": "TEKTRONIX,AFG31102,C012345,SCPI:99.0 FV:1.6.1",
            "AFG1000": "TEKTRONIX,AFG1062,C023456,SCPI:99.0 FV:1.2.4",
            "AFG2021": "TEKTRONIX,AFG2021,C034567,SCPI:99.0 FV:1.1.0",
            "SERIES_2200": "KEITHLEY INSTRUMENTS INC.,MODEL 2230G-30-1,1402938,1.04-1.06",
            "SERIES_2260B": "KEITHLEY,2260B-30-36,TW00123456,1.15",
            "MP5000_MP5103": "TEKTRONIX,MP5103,0459182,1.2.0 (Slot1:MP5201-SMU, Slot2:MP5301-PSU)",
            "MSO_4_5_6": "TEKTRONIX,MSO54B,C055123,CF:91.1CT FV:2.10.4",
            "DPO_7_SERIES": "TEKTRONIX,DPO714AX,C077101,CF:91.1CT FV:1.4.0",
            "MSO_2_SERIES": "TEKTRONIX,MSO24,C022881,CF:91.1CT FV:2.8.5",
            "MDO_3_SERIES": "TEKTRONIX,MDO34,C033912,CF:91.1CT FV:1.14.2",
            "DPO_MSO_5K_7K_70K": "TEKTRONIX,DPO70404C,C070119,CF:91.1CT FV:10.8.1",
            "TBS2000B": "TEKTRONIX,TBS2204B,C020991,CF:91.1CT FV:1.28",
            "TBS1000C": "TEKTRONIX,TBS1202C,C010551,CF:91.1CT FV:1.12",
            "SIGNALVU_PC_RSA": "TEKTRONIX,RSA306B,B029384,CF:91.1CT FV:4.3.0128 (SignalVu-PC PI)",
            "RSA5000_6000_BENCH": "TEKTRONIX,RSA5126B,B051923,CF:91.1CT FV:4.2.0",
            "SMU_2450": "KEITHLEY INSTRUMENTS,MODEL 2450,04481920,1.7.12b",
            "SMU_2460": "KEITHLEY INSTRUMENTS,MODEL 2460,04492011,1.7.12b",
            "SMU_2461": "KEITHLEY INSTRUMENTS,MODEL 2461,04501922,1.7.12b",
            "SMU_2470": "KEITHLEY INSTRUMENTS,MODEL 2470,04610293,1.7.14a",
            "SMU_2600B": "Keithley Instruments Inc., Model 2612B, 4391827, 3.4.2",
            "SMU_2601B_PULSE": "Keithley Instruments Inc., Model 2601B-PULSE, 4491023, 1.1.4",
            "SMU_2606B": "Keithley Instruments Inc., Model 2606B, 4501928, 3.4.2",
            "SMU_2651A": "Keithley Instruments Inc., Model 2651A, 4192831, 1.2.0",
            "TEKVISA_TALKER_LISTENER": "TEKTRONIX,VIRTUAL-TALKER-LISTENER,SIM0001,TekVISA:3.0.4",
            "DMM6500": "KEITHLEY INSTRUMENTS,MODEL DMM6500,04561234,1.7.14b",
            "DMM7510": "KEITHLEY INSTRUMENTS,MODEL DMM7510,04419876,1.7.12b",
            "DMM_2110": "KEITHLEY INSTRUMENTS INC.,MODEL 2110,1420912,02.03-01-20",
            "DMM_2010": "KEITHLEY INSTRUMENTS INC.,MODEL 2010,0891234,A14  /A02",
        }
        return idn_map.get(self.model_id, f"TEKTRONIX,{self.model_id},SIM001,FV:1.0.0")

    def write(self, cmd: str):
        c = cmd.strip()
        cu = c.upper()
        if cu in ("*RST", "RESET()"):
            self.reset_state()
            return
        if cu == "*CLS":
            return
        if cu.startswith("*LANG"):
            parts = cu.split()
            if len(parts) > 1:
                self.lang = parts[1]
            return
        if c.lower().startswith("login "):
            self.authenticated = True
            return
        if c.lower() == "abort":
            self.remote_allowed = "Allowed"
            return

        # Parse TSP print(...) statements
        if c.startswith("print(") and c.endswith(")"):
            inner = c[6:-1].strip()
            self.last_tsp_print = self._eval_tsp_expr(inner)
            return

        # Parse TSP assignments (e.g., slot[1].smu[1].source.levelv = 3.3 or smua.source.levelv = 2.5)
        if "=" in c and not c.startswith(":"):
            lhs, rhs = [x.strip() for x in c.split("=", 1)]
            try:
                val_num = float(rhs)
            except ValueError:
                val_num = None
            if "levelv" in lhs or "source.level" in lhs:
                if val_num is not None:
                    self.smu_level = val_num
            elif "leveli" in lhs:
                if val_num is not None:
                    self.smu_level = val_num
                    self.smu_func = "CURR"
            elif "limit" in lhs:
                if val_num is not None:
                    self.smu_limit = val_num
            elif "output" in lhs:
                self.output_on = ("ON" in rhs.upper() or rhs == "1")
            elif "func" in lhs:
                rhs_u = rhs.upper()
                if "dmm." in lhs.lower():
                    if "AC_VOLT" in rhs_u:
                        self.dmm_func = "VOLT:AC"
                    elif "DC_CURR" in rhs_u:
                        self.dmm_func = "CURR:DC"
                    elif "AC_CURR" in rhs_u:
                        self.dmm_func = "CURR:AC"
                    elif "4W_RES" in rhs_u:
                        self.dmm_func = "FRES"
                    elif "RES" in rhs_u:
                        self.dmm_func = "RES"
                    elif "FREQ" in rhs_u:
                        self.dmm_func = "FREQ"
                    elif "TEMP" in rhs_u:
                        self.dmm_func = "TEMP"
                    elif "CAP" in rhs_u:
                        self.dmm_func = "CAP"
                    elif "DIG" in lhs.upper():
                        self.dmm_func = "DIG:VOLT"
                    else:
                        self.dmm_func = "VOLT:DC"
                elif "AMP" in rhs_u or "CURR" in rhs_u:
                    self.smu_func = "CURR"
                else:
                    self.smu_func = "VOLT"
            elif "samplerate" in lhs.lower():
                if val_num is not None:
                    self.dmm_dig_rate = int(val_num)
            elif "count" in lhs.lower() and "dmm." in lhs.lower():
                if val_num is not None:
                    self.dmm_dig_count = int(val_num)
            elif "nplc" in lhs.lower() and "dmm." in lhs.lower():
                if val_num is not None:
                    self.dmm_nplc = val_num
            return

        # Parse SCPI commands
        # AFG
        m_afg_ch = re.match(r"^:?SOUR(?:CE)?([12])?:(.+)$", cu)
        if m_afg_ch:
            ch = int(m_afg_ch.group(1) or 1)
            rest = m_afg_ch.group(2)
            if rest.startswith("FUNC"):
                val = rest.split()[-1] if " " in rest else "SIN"
                self.afg[ch]["func"] = val
            elif rest.startswith("FREQ"):
                val = self._extract_float(rest, 1000.0)
                self.afg[ch]["freq"] = val
            elif "AMPL" in rest:
                self.afg[ch]["amp"] = self._extract_float(rest, 2.0)
            elif "OFFS" in rest:
                self.afg[ch]["offset"] = self._extract_float(rest, 0.0)
            elif "PHAS" in rest:
                self.afg[ch]["phase"] = self._extract_float(rest, 0.0)
            elif "DCYC" in rest:
                self.afg[ch]["duty"] = self._extract_float(rest, 50.0)

        if cu.startswith("OUTP") or cu.startswith(":OUTP"):
            ch = 2 if "OUTP2" in cu or "OUTPUT2" in cu else 1
            if "IMP" in cu:
                self.afg[ch]["imp"] = 1e6 if "INF" in cu else self._extract_float(cu, 50.0)
            elif "STAT" in cu or "ON" in cu or "OFF" in cu or cu.endswith(" 1") or cu.endswith(" 0"):
                state = ("ON" in cu or cu.endswith(" 1")) and ("OFF" not in cu)
                self.output_on = state
                self.afg[ch]["out"] = 1 if state else 0
                self.psu[self.psu_sel_ch]["out"] = 1 if state else 0

        # DC Power
        if "INST:SEL" in cu or "INSTRUMENT:SELECT" in cu:
            if "CH2" in cu:
                self.psu_sel_ch = 2
            elif "CH3" in cu:
                self.psu_sel_ch = 3
            else:
                self.psu_sel_ch = 1
        elif cu.startswith((":VOLT", "VOLT", ":SOUR:VOLT", "SOUR:VOLT")):
            v = self._extract_float(cu, 5.0)
            if "PROT" in cu or "LIM" in cu:
                self.psu[self.psu_sel_ch]["ovp"] = v
            else:
                self.psu[self.psu_sel_ch]["v_set"] = v
                self.smu_level = v
                self.smu_func = "VOLT"
        elif cu.startswith((":CURR", "CURR", ":SOUR:CURR", "SOUR:CURR")):
            i_val = self._extract_float(cu, 1.0)
            self.psu[self.psu_sel_ch]["i_lim"] = i_val
            self.smu_level = i_val
        elif cu.startswith((":APPL", "APPL")):
            nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cu)
            if len(nums) >= 1:
                self.psu[self.psu_sel_ch]["v_set"] = float(nums[0])
            if len(nums) >= 2:
                self.psu[self.psu_sel_ch]["i_lim"] = float(nums[1])

        # Scope
        m_meas_slot = re.match(r"^:?MEASU(?:REMENT)?:MEAS(\d+):(SOU(?:RCE)?1?|TYP(?:E)?)\s+(.+)$", cu)
        if m_meas_slot:
            slot_i = int(m_meas_slot.group(1))
            prop = m_meas_slot.group(2)
            val_s = m_meas_slot.group(3).strip()
            old_ch, old_ty = self.scope_meas_slots.get(slot_i, ("CH1", "FREQuency"))
            if prop.startswith("SOU"):
                self.scope_meas_slots[slot_i] = (val_s, old_ty)
            else:
                self.scope_meas_slots[slot_i] = (old_ch, val_s)
        elif "MEASUREMENT:DELETE" in cu or "MEASU:DEL" in cu:
            self.scope_meas_slots.clear()
        elif "MEASUREMENT:IMMED:TYPE" in cu or "MEASU:IMM:TYP" in cu:
            self.scope_meas_type = cu.split()[-1]
        elif "MEASUREMENT:IMMED:SOURCE" in cu or "MEASU:IMM:SOU" in cu:
            self.scope_source = cu.split()[-1]
        elif "DATA:SOURCE" in cu or "DAT:SOU" in cu:
            self.scope_source = cu.split()[-1]
        elif "DATA:STOP" in cu or "DAT:STOP" in cu:
            self.scope_stop = int(self._extract_float(cu, 1000))
        elif re.match(r"^:?CH[1-4]:SCA", cu):
            self.scope_vscale = self._extract_float(cu, 1.0)
        elif re.match(r"^:?HOR.*:SCA", cu):
            self.scope_hscale = self._extract_float(cu, 0.001)

        # Spectrum
        if "FREQ:CENT" in cu or "FREQUENCY:CENTER" in cu:
            self.spec_center_hz = self._extract_si_freq(cu, 1000e6)
        elif "FREQ:SPAN" in cu or "FREQUENCY:SPAN" in cu:
            self.spec_span_hz = self._extract_si_freq(cu, 40e6)
        elif "INP:MLEV" in cu or "INPUT:MLEVEL" in cu:
            self.spec_ref_dbm = self._extract_float(cu, 0.0)

        # DMM (08. Digit Multimeter SCPI configuration)
        if any(k in cu for k in ("SENS:FUNC", "SENSE:FUNCTION", "CONF:", "CONFIGURE:", "SENS:DIG:FUNC", "SENSE:DIGITIZE:FUNCTION")):
            if "DIG" in cu:
                self.dmm_func = "DIG:VOLT"
            elif "VOLT:AC" in cu or "VOLTAGE:AC" in cu:
                self.dmm_func = "VOLT:AC"
            elif "CURR:DC" in cu or "CURRENT:DC" in cu:
                self.dmm_func = "CURR:DC"
            elif "CURR:AC" in cu or "CURRENT:AC" in cu:
                self.dmm_func = "CURR:AC"
            elif "FRES" in cu:
                self.dmm_func = "FRES"
            elif "RES" in cu:
                self.dmm_func = "RES"
            elif "FREQ" in cu:
                self.dmm_func = "FREQ"
            elif "TEMP" in cu:
                self.dmm_func = "TEMP"
            elif "CAP" in cu:
                self.dmm_func = "CAP"
            elif "VOLT" in cu:
                self.dmm_func = "VOLT:DC"
        elif "NPLC" in cu:
            self.dmm_nplc = self._extract_float(cu, 1.0)
        elif "SRAT" in cu and "DIG" in cu:
            self.dmm_dig_rate = int(self._extract_float(cu, 100000))
        elif ("TRAC:POIN" in cu or "TRACE:POINTS" in cu or "DIG:COUN" in cu or "DIGITIZE:COUNT" in cu):
            self.dmm_dig_count = max(10, int(self._extract_float(cu, 200)))

    def query(self, cmd: str) -> str:
        c = cmd.strip()
        cu = c.upper()

        # Multi-command chain with semicolon
        if ";" in c and not c.startswith("print("):
            parts = [p.strip() for p in c.split(";") if p.strip()]
            res = []
            for p in parts:
                if p.endswith("?"):
                    res.append(self.query(p))
                else:
                    self.write(p)
            return ";".join(res) if res else "0"

        if cu == "*IDN?":
            return self.get_idn()
        if cu == "*ESR?":
            return "0"
        if cu == "*STB?":
            return "16"
        if cu == "*OPC?":
            return "1"
        if cu == "*OPT?":
            return "0"
        if cu == "*LANG?":
            return self.lang
        if c.lower() == "login?":
            return "Authenticated" if self.authenticated else "Unauthenticated"
        if c.lower() == "remote?":
            return self.remote_allowed
        if "SYST:ERR" in cu or "SYSTEM:ERROR" in cu:
            return '0,"No error"'
        if "ROUT:TERM?" in cu or "ROUTE:TERMINALS?" in cu:
            return self.dmm_terminals

        if c.startswith("print(") and c.endswith(")"):
            inner = c[6:-1].strip()
            return self._eval_tsp_expr(inner)
        if c.startswith("printbuffer(") and c.endswith(")"):
            return self._simulate_dmm_waveform_csv()

        # DMM trace / digitizer buffer queries
        if ("TRAC:DATA?" in cu or "TRACE:DATA?" in cu) and self.category_id == "08_DMM":
            return self._simulate_dmm_waveform_csv()
        if self.category_id == "08_DMM" and (
            cu.startswith(("READ", ":READ", "FETC", ":FETC"))
            or "MEAS" in cu
        ):
            return f"{self._simulate_dmm_scalar(cu):.7f}"

        # AFG queries
        m_afg_q = re.match(r"^:?SOUR(?:CE)?([12])?:(.+)\?$", cu)
        if m_afg_q:
            ch = int(m_afg_q.group(1) or 1)
            q = m_afg_q.group(2)
            st = self.afg[ch]
            if "FUNC" in q:
                return st["func"]
            if "FREQ" in q:
                return f"{st['freq']:.6f}"
            if "AMPL" in q:
                return f"{st['amp']:.4f}"
            if "OFFS" in q:
                return f"{st['offset']:.4f}"
            if "PHAS" in q:
                return f"{st['phase']:.2f}"
        if cu.startswith((":OUTP", "OUTP")) and cu.endswith("?"):
            ch = 2 if ("OUTP2" in cu or "OUTPUT2" in cu) else 1
            if "IMP" in cu:
                return f"{self.afg[ch]['imp']:.1f}"
            if "TRIP" in cu:
                return "0"
            return "1" if self.output_on else "0"

        # DC Power & SMU SCPI measurements
        if "MEAS" in cu or "FETC" in cu or cu.startswith(":READ?"):
            v, i, r, p = self._simulate_dc_vi()
            if "ALL" in cu:
                v2 = self.psu[2]["v_set"] if self.output_on else 0.0
                v3 = self.psu[3]["v_set"] if self.output_on else 0.0
                if "VOLT" in cu:
                    return f"{v:.5f}, {v2:.5f}, {v3:.5f}"
                if "CURR" in cu:
                    return f"{i:.5f}, {v2/24.0:.5f}, {v3/5.0:.5f}"
                if "POW" in cu:
                    return f"{p:.5f}, {v2*v2/24.0:.5f}, {v3*v3/5.0:.5f}"
            if "VOLT" in cu:
                return f"{v:.6f}"
            if "CURR" in cu:
                return f"{i:.6e}"
            if "RES" in cu:
                return f"{r:.4f}"
            if "POW" in cu:
                return f"{p:.6f}"
            return f"{v:.6f},{i:.6e}"

        # Scope queries
        if "MEASU" in cu and "LIST?" in cu:
            if not self.scope_meas_slots:
                return "NONE"
            return ",".join(f"MEAS{k}" for k in sorted(self.scope_meas_slots.keys()))
        if "WFMOUTPRE?" in cu or "WFMPRE?" in cu:
            return f"1;8;ASC;RP;MSB;{self.scope_stop};\"{self.scope_source}, DC coupling\";Y;{self.scope_hscale/100.0:.6e};0;\"s\";{self.scope_vscale/25.0:.6e};0.0;0.0;\"V\""
        if "CURVE?" in cu or "CURV?" in cu:
            t0 = time.time() - self.start_time
            ch_num = int(self.scope_source[-1]) if self.scope_source[-1].isdigit() else 1
            ch_phase_shift = (ch_num - 1) * (math.pi / 3.0)
            amp_factor = {1: 1.0, 2: 0.75, 3: 0.55, 4: 0.40}.get(ch_num, 1.0)
            pts = []
            for idx in range(self.scope_stop):
                phase = 2 * math.pi * (idx / max(1, self.scope_stop)) * 3.0 + t0 * 4.0 + ch_phase_shift
                if ch_num == 2:
                    # Slightly square-ish or cosine-shifted wave on CH2 for distinct visual comparison
                    val = int(60 * amp_factor * math.cos(phase) + 12 * math.sin(2 * phase) + random.gauss(0, 1.8))
                elif ch_num == 3:
                    val = int(60 * amp_factor * math.sin(2 * phase) + random.gauss(0, 1.8))
                else:
                    val = int(60 * amp_factor * math.sin(phase) + 8 * math.sin(3 * phase) + random.gauss(0, 1.8))
                pts.append(str(max(-127, min(127, val))))
            return ",".join(pts)
        if "MEASU" in cu and ("VAL" in cu or "MEAN?" in cu):
            m_slot_q = re.search(r"MEAS(\d+):", cu)
            if m_slot_q and int(m_slot_q.group(1)) in self.scope_meas_slots:
                src_ch, mt_raw = self.scope_meas_slots[int(m_slot_q.group(1))]
                mt = mt_raw.upper()
                ch_num = int(src_ch[-1]) if src_ch[-1].isdigit() else 1
            else:
                mt = self.scope_meas_type.upper()
                ch_num = int(self.scope_source[-1]) if self.scope_source[-1].isdigit() else 1
            amp_factor = {1: 1.0, 2: 0.75, 3: 0.55, 4: 0.40}.get(ch_num, 1.0)
            freq_factor = 2.0 if ch_num == 3 else 1.0
            if "FREQ" in mt:
                return f"{1000.0 * freq_factor + random.gauss(0, 0.35):.4f}"
            if "PERI" in mt:
                return f"{(0.001 / freq_factor) + random.gauss(0, 1e-7):.7e}"
            if "PK2P" in mt:
                return f"{self.scope_vscale * 4.8 * amp_factor + random.gauss(0, 0.015):.4f}"
            if "MEAN" in mt:
                return f"{self.scope_voffset + (ch_num - 1) * 0.02 + random.gauss(0, 0.004):.5f}"
            if "RMS" in mt:
                return f"{self.scope_vscale * 1.697 * amp_factor + random.gauss(0, 0.008):.4f}"
            if "MAX" in mt:
                return f"{self.scope_vscale * 2.4 * amp_factor + random.gauss(0, 0.01):.4f}"
            if "MIN" in mt:
                return f"{-self.scope_vscale * 2.4 * amp_factor + random.gauss(0, 0.01):.4f}"
            return f"{1.0 * amp_factor + random.gauss(0, 0.01):.4f}"

        # Spectrum Analyzer queries
        if "SPEC" in cu and "TRAC" in cu:
            n = self.spec_points
            f_start = self.spec_center_hz - self.spec_span_hz / 2.0
            df = self.spec_span_hz / max(1, n - 1)
            carrier_f = self.spec_center_hz + 0.05 * self.spec_span_hz
            harmonic_f = self.spec_center_hz - 0.22 * self.spec_span_hz
            vals = []
            for k in range(n):
                f = f_start + k * df
                noise = -92.0 + random.gauss(0, 1.4)
                # Carrier Gaussian peak
                bw = max(df * 2.5, self.spec_rbw_hz * 1.5)
                p_carrier = -12.0 * math.exp(-0.5 * ((f - carrier_f) / bw) ** 2)
                # Peak at -12 dBm above noise floor:
                sig1 = (-12.5 - noise) * math.exp(-0.5 * ((f - carrier_f) / bw) ** 2)
                sig2 = (-42.0 - noise) * math.exp(-0.5 * ((f - harmonic_f) / (bw * 1.2)) ** 2)
                vals.append(f"{min(self.spec_ref_dbm, noise + max(0.0, sig1) + max(0.0, sig2)):.2f}")
            return ",".join(vals)
        if "MARK" in cu and ":X?" in cu:
            carrier_f = self.spec_center_hz + 0.05 * self.spec_span_hz + random.gauss(0, 1500.0)
            return f"{carrier_f:.2f}"
        if "MARK" in cu and ":Y?" in cu:
            return f"{-12.5 + random.gauss(0, 0.18):.2f}"

        return f"{random.uniform(0.95, 1.05):.5f}"

    def _simulate_dc_vi(self) -> Tuple[float, float, float, float]:
        if not self.output_on:
            v_noise = random.gauss(0, 0.0002)
            i_noise = random.gauss(0, 1e-7)
            return v_noise, i_noise, 1e9, abs(v_noise * i_noise)

        if self.category_id == "02_DC_POWER":
            st = self.psu[self.psu_sel_ch]
            v_target = st["v_set"]
            i_lim = st["i_lim"]
            r_load = st["load_r"]
            i_ideal = v_target / max(0.1, r_load)
            if i_ideal > i_lim:
                # CC mode
                i_meas = i_lim + random.gauss(0, 0.0005)
                v_meas = i_meas * r_load + random.gauss(0, 0.002)
            else:
                # CV mode
                v_meas = v_target + random.gauss(0, 0.0015)
                i_meas = v_meas / r_load + random.gauss(0, 0.0004)
            p_meas = v_meas * i_meas
            r_calc = v_meas / max(1e-9, i_meas)
            return v_meas, i_meas, r_calc, p_meas

        # MP5000 / SMU
        if self.smu_func == "VOLT":
            v_meas = self.smu_level + random.gauss(0, 0.0003)
            # Non-linear + ohmic load for realistic I-V curve
            i_ideal = (v_meas / self.smu_dut_r) + 0.0002 * (v_meas ** 2) * (1 if v_meas >= 0 else -1)
            if abs(i_ideal) > abs(self.smu_limit):
                i_meas = math.copysign(self.smu_limit, i_ideal) + random.gauss(0, 1e-6)
                v_meas = i_meas * self.smu_dut_r
            else:
                i_meas = i_ideal + random.gauss(0, 2e-6)
        else:
            i_meas = self.smu_level + random.gauss(0, 1e-6)
            v_ideal = i_meas * self.smu_dut_r
            if abs(v_ideal) > abs(self.smu_limit):
                v_meas = math.copysign(self.smu_limit, v_ideal)
            else:
                v_meas = v_ideal + random.gauss(0, 0.0005)

        r_meas = v_meas / i_meas if abs(i_meas) > 1e-12 else 1e9
        p_meas = v_meas * i_meas
        return v_meas, i_meas, r_meas, p_meas

    def _eval_tsp_expr(self, expr: str) -> str:
        v, i, r, p = self._simulate_dc_vi()
        el = expr.lower()
        if "localnode.model" in el:
            return self.model_id
        if "localnode.version" in el:
            return "1.7.12"
        if "slot[" in el and ".model" in el:
            return "MP5201-SMU" if "slot[1]" in el else "MP5301-PSU"
        if "measure.iv(" in el:
            return f"{i:.6e}\t{v:.6f}"
        if "measure.v(" in el:
            return f"{v:.6f}"
        if "measure.i(" in el:
            return f"{i:.6e}"
        if "measure.r(" in el:
            return f"{r:.4f}"
        if "measure.p(" in el:
            return f"{p:.6e}"
        if "contact.r(" in el:
            return f"{0.18 + random.uniform(-0.02, 0.02):.3f}"
        if "temperaturedelta" in el:
            return f"{0.15 + random.uniform(-0.05, 0.05):.2f}"
        if "atlimit" in el or "compliance" in el or "constantcurrent" in el:
            at_lim = abs(abs(i) - abs(self.smu_limit)) < 1e-4 and self.output_on
            return "true" if at_lim else "false"
        if "localnode.terminals" in el:
            return "FRONT"
        if "dmm.measure.read(" in el or "dmm.digitize.read(" in el:
            return f"{self._simulate_dmm_scalar(self.dmm_func):.7f}"
        return f"{v:.6f}"

    def _simulate_dmm_scalar(self, hint: str = "") -> float:
        hu = (hint or self.dmm_func).upper()
        if "READ" in hu or "FETC" in hu:
            hu = self.dmm_func.upper()
        noise_scale = 1.0 / math.sqrt(max(0.01, self.dmm_nplc))
        t_el = time.time() - self.start_time
        if "VOLT:AC" in hu or "VOLTAGE:AC" in hu:
            return 1.767767 + 0.0004 * math.sin(t_el * 1.5) + random.gauss(0, 8e-5 * noise_scale)
        if "CURR:DC" in hu or "CURRENT:DC" in hu:
            return 0.025012 + 1e-5 * math.sin(t_el * 1.2) + random.gauss(0, 3e-6 * noise_scale)
        if "CURR:AC" in hu or "CURRENT:AC" in hu:
            return 0.014142 + random.gauss(0, 5e-6 * noise_scale)
        if "FRES" in hu:
            return 100.00042 + 0.0002 * math.sin(t_el * 0.8) + random.gauss(0, 4e-5 * noise_scale)
        if "RES" in hu:
            return 1000.145 + 0.003 * math.sin(t_el * 0.8) + random.gauss(0, 5e-4 * noise_scale)
        if "FREQ" in hu:
            return 1000.0012 + random.gauss(0, 0.0008)
        if "TEMP" in hu:
            return 24.85 + 0.08 * math.sin(t_el * 0.3) + random.gauss(0, 0.006 * noise_scale)
        if "CAP" in hu:
            return 1.002e-7 + random.gauss(0, 2e-11 * noise_scale)
        if "DIG" in hu:
            return 2.5 * math.sin(t_el * 10.0) + random.gauss(0, 0.002)
        # Default DC Voltage (e.g. 5.000012 V precision reference)
        return 5.000012 + 0.00018 * math.sin(t_el * 1.4) + random.gauss(0, 1.2e-5 * noise_scale)

    def _simulate_dmm_waveform_csv(self) -> str:
        n = max(10, min(2000, self.dmm_dig_count))
        t0 = time.time() - self.start_time
        base = self._simulate_dmm_scalar(self.dmm_func)
        pts: List[str] = []
        if "DIG" in self.dmm_func.upper() or "AC" in self.dmm_func.upper():
            for idx in range(n):
                ph = 2.0 * math.pi * 3.0 * (idx / max(1, n)) + t0 * 3.5
                v = 2.5 * math.sin(ph) + 0.15 * math.sin(5.0 * ph) + random.gauss(0, 0.008)
                pts.append(f"{v:.6f}")
        else:
            for idx in range(n):
                ph = 2.0 * math.pi * (idx / max(1, n)) + t0 * 2.0
                v = base + 0.0003 * math.sin(ph) + random.gauss(0, 3e-5)
                pts.append(f"{v:.7f}")
        return ",".join(pts)

    @staticmethod
    def _extract_float(text: str, default: float) -> float:
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
        return float(nums[-1]) if nums else default

    @staticmethod
    def _extract_si_freq(text: str, default: float) -> float:
        m = re.search(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(GHZ|MHZ|KHZ|HZ)?", text.upper().split()[-1])
        if not m or not m.group(1):
            return VirtualInstrumentSimulator._extract_float(text, default)
        val = float(m.group(1))
        unit = m.group(2) or ""
        mult = {"GHZ": 1e9, "MHZ": 1e6, "KHZ": 1e3, "HZ": 1.0}.get(unit, 1.0)
        return val * mult


class VisaConnectionManager:
    """
    Unified VISA Session & Discovery Manager supporting TekVISA, NI-VISA, PyVISA-py, and Virtual Simulator.
    """

    def __init__(self):
        self.rm: Any = None
        self.backend_info = "Not initialized"
        self.session: Any = None
        self.active_resource = ""
        self.is_simulation = True
        self.simulator = VirtualInstrumentSimulator()
        self.transcript: List[IOTranscriptEntry] = []
        self.total_logged_count: int = 0
        self._init_resource_manager()

    def _init_resource_manager(self):
        if not PYVISA_AVAILABLE or pyvisa is None:
            self.backend_info = "PyVISA 미설치 (시뮬레이션 전용)"
            return
        try:
            self.rm = pyvisa.ResourceManager()
            self.backend_info = f"System VISA ({self.rm})"
        except Exception:
            try:
                self.rm = pyvisa.ResourceManager("@py")
                self.backend_info = "PyVISA-py Built-in Backend (@py)"
            except Exception as e:
                self.rm = None
                self.backend_info = f"VISA 백엔드 로드 실패 ({e})"

    def scan_resources(self) -> List[str]:
        resources = [
            "SIM::USB0::0x0699::0x0353::C012345::INSTR (Virtual Tektronix USBTMC)",
            "SIM::TCPIP0::192.168.1.100::inst0::INSTR (Virtual Tektronix LAN VXI-11)",
            "SIM::TCPIP0::127.0.0.1::4000::SOCKET (Virtual SignalVu-PC / MP5000 Socket)",
            "SIM::ASRL7::INSTR (Virtual 2260B USB-CDC COM7)",
        ]
        if self.rm is not None:
            try:
                hw_list = list(self.rm.list_resources("?*"))
                for r in hw_list:
                    if r not in resources:
                        resources.insert(0, r)
            except Exception as e:
                self._log("ERROR", "ResourceManager", "list_resources(?*)", str(e), 0.0)
        return resources

    def connect(
        self,
        resource_str: str,
        simulation: bool = False,
        category_id: str = "01_AFG",
        model_id: str = "AFG31000",
        timeout_ms: int = 5000,
        read_term: str = "\n",
        write_term: str = "\n",
    ) -> Tuple[bool, str]:
        self.simulator = VirtualInstrumentSimulator(category_id, model_id)
        clean_res = resource_str.split(" (")[0].strip()

        if simulation or clean_res.startswith("SIM::"):
            self.disconnect()
            self.is_simulation = True
            self.active_resource = clean_res
            idn = self.simulator.get_idn()
            self._log("INFO", clean_res, f"OPEN SESSION [SIMULATION: {model_id}]", idn, 1.2)
            return True, f"[시뮬레이션 연결 성공] {idn}"

        if self.rm is None:
            return False, "VISA ResourceManager를 사용할 수 없습니다. TekVISA/NI-VISA를 설치하거나 시뮬레이션 모드를 사용하세요."

        # Reuse existing open hardware session if already connected to the same resource
        if (
            not self.is_simulation
            and self.session is not None
            and self.active_resource == clean_res
            and getattr(self.session, "_session", None) is not None
        ):
            try:
                self.session.timeout = timeout_ms
                self.session.read_termination = read_term
                self.session.write_termination = write_term
                return True, f"[실제 장비 연결 성공] {clean_res}"
            except Exception:
                pass

        self.disconnect()
        try:
            t0 = time.perf_counter()
            sess: Any = self.rm.open_resource(clean_res)
            sess.timeout = timeout_ms
            sess.read_termination = read_term
            sess.write_termination = write_term
            self.session = sess
            self.is_simulation = False
            self.active_resource = clean_res
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("INFO", clean_res, f"viOpen({clean_res}, TMO={timeout_ms}ms)", "VI_SUCCESS", dt)
            return True, f"[실제 장비 연결 성공] {clean_res}"
        except Exception as e:
            self._log("ERROR", clean_res, f"viOpen({clean_res})", str(e), 0.0)
            return False, f"VISA 연결 실패: {e}"

    def _reopen_active_session(self) -> bool:
        """Transparently re-opens the active hardware session if the VISA handle was invalidated (VI_ERROR_INV_OBJECT)."""
        if self.is_simulation or not self.active_resource or self.rm is None:
            return False
        old_sess = self.session
        self.session = None
        if old_sess is not None:
            try:
                # Detach handle before deletion so old_sess.__del__ cannot close the newly allocated handle
                old_sess._session = None
            except Exception:
                pass
        try:
            t0 = time.perf_counter()
            sess: Any = self.rm.open_resource(self.active_resource)
            sess.timeout = 5000
            sess.read_termination = "\n"
            sess.write_termination = "\n"
            self.session = sess
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("INFO", self.active_resource, f"viOpen({self.active_resource}) [Auto-Reconnect]", "VI_SUCCESS", dt)
            return True
        except Exception:
            return False

    def disconnect(self):
        if self.session is not None:
            old_sess = self.session
            self.session = None
            try:
                old_sess.close()
            except Exception:
                pass
            try:
                old_sess._session = None
            except Exception:
                pass
        if self.active_resource:
            self._log("INFO", self.active_resource, "viClose()", "Session closed", 0.1)
        self.active_resource = ""

    def set_category_model(self, category_id: str, model_id: str):
        self.simulator.category_id = category_id
        self.simulator.model_id = model_id

    def write(self, command: str) -> float:
        t0 = time.perf_counter()
        if self.is_simulation or self.session is None:
            self.simulator.write(command)
            dt = (time.perf_counter() - t0) * 1000.0 + random.uniform(0.4, 1.5)
            self._log("WRITE", self.active_resource or "SIM", command, "OK", dt)
            return dt
        try:
            self.session.write(command)
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("WRITE", self.active_resource, command, "VI_SUCCESS", dt)
            return dt
        except Exception as e:
            err_s = str(e)
            if ("VI_ERROR_INV_OBJECT" in err_s or "VI_ERROR_INV_SESSION" in err_s or "InvalidSession" in err_s) and self._reopen_active_session():
                t0 = time.perf_counter()
                self.session.write(command)
                dt = (time.perf_counter() - t0) * 1000.0
                self._log("WRITE", self.active_resource, command, "VI_SUCCESS", dt)
                return dt
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("ERROR", self.active_resource, f"WRITE: {command}", err_s, dt)
            raise

    def query(self, command: str) -> Tuple[str, float]:
        t0 = time.perf_counter()
        if self.is_simulation or self.session is None:
            resp = self.simulator.query(command)
            dt = (time.perf_counter() - t0) * 1000.0 + random.uniform(1.0, 4.5)
            self._log("QUERY", self.active_resource or "SIM", command, resp[:180], dt)
            return resp, dt
        try:
            resp = self.session.query(command).strip()
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("QUERY", self.active_resource, command, resp[:180], dt)
            return resp, dt
        except Exception as e:
            err_s = str(e)
            if ("VI_ERROR_INV_OBJECT" in err_s or "VI_ERROR_INV_SESSION" in err_s or "InvalidSession" in err_s) and self._reopen_active_session():
                t0 = time.perf_counter()
                resp = self.session.query(command).strip()
                dt = (time.perf_counter() - t0) * 1000.0
                self._log("QUERY", self.active_resource, command, resp[:180], dt)
                return resp, dt
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("ERROR", self.active_resource, f"QUERY: {command}", err_s, dt)
            raise

    def read(self) -> Tuple[str, float]:
        t0 = time.perf_counter()
        if self.is_simulation or self.session is None:
            resp = self.simulator.last_tsp_print
            dt = (time.perf_counter() - t0) * 1000.0 + 0.8
            self._log("READ", self.active_resource or "SIM", "viRead()", resp[:180], dt)
            return resp, dt
        try:
            resp = self.session.read().strip()
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("READ", self.active_resource, "viRead()", resp[:180], dt)
            return resp, dt
        except Exception as e:
            err_s = str(e)
            if ("VI_ERROR_INV_OBJECT" in err_s or "VI_ERROR_INV_SESSION" in err_s or "InvalidSession" in err_s) and self._reopen_active_session():
                t0 = time.perf_counter()
                resp = self.session.read().strip()
                dt = (time.perf_counter() - t0) * 1000.0
                self._log("READ", self.active_resource, "viRead()", resp[:180], dt)
                return resp, dt
            dt = (time.perf_counter() - t0) * 1000.0
            self._log("ERROR", self.active_resource, "viRead()", err_s, dt)
            raise

    def verify_instrument_status(self, protocol: str = "SCPI", password: str = "") -> Dict[str, str]:
        """
        Executes pre-flight remote status verification (*IDN?, *LANG?, login?, remote?, SYST:ERR?).
        """
        report: Dict[str, str] = {}
        try:
            if protocol == "TSP":
                if password:
                    self.write(f"login {password}")
                login_st, _ = self.query("login?")
                remote_st, _ = self.query("remote?")
                idn, _ = self.query("*IDN?")
                report["*IDN?"] = idn
                report["Auth (login?)"] = login_st
                report["Session (remote?)"] = remote_st
                report["Status"] = "정상 (TSP Ready)"
            elif protocol == "DUAL_SCPI_TSP":
                idn, _ = self.query("*IDN?")
                lang, _ = self.query("*LANG?")
                report["*IDN?"] = idn
                report["Command Set (*LANG?)"] = lang
                report["Status"] = f"정상 ({lang} Mode 감지됨)"
            else:
                idn, _ = self.query("*IDN?")
                esr, _ = self.query("*ESR?")
                report["*IDN?"] = idn
                report["Standard Event (*ESR?)"] = esr
                report["Status"] = "정상 (SCPI Ready)"
        except Exception as e:
            report["Status"] = f"상태 확인 실패: {e}"
        return report

    def _log(self, direction: str, resource: str, command: str, response: str, latency_ms: float):
        ts = time.strftime("%H:%M:%S") + f".{int((time.time() % 1) * 1000):03d}"
        entry = IOTranscriptEntry(
            timestamp=ts,
            direction=direction,
            resource=resource,
            command=command,
            response=response,
            latency_ms=round(latency_ms, 2),
        )
        self.transcript.append(entry)
        self.total_logged_count += 1
        if len(self.transcript) > 1000:
            self.transcript = self.transcript[-1000:]
