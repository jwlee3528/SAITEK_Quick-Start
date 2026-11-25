# -*- coding: utf-8 -*-
"""
Tektronix QuickStart Program - Instrument Profiles & Manual Catalog
Derived from the 26 official Tektronix / Keithley Programmer & Reference Manuals
in 01.docs/10. Tek_Manuals (01. AFGs ~ 07. Tek VISA).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ChecklistItem:
    id: str
    title: str
    description: str
    critical: bool = True
    checked_by_default: bool = False
    how_to_steps: List[str] = field(default_factory=list)
    verify_cmd: str = "*IDN?"
    verify_label: str = "🔍 이 항목 연결/상태 즉시 확인"
    expected_hint: str = "장비 식별 문자열(*IDN?) 또는 정상 상태값 반환"


@dataclass
class InputParameterSpec:
    key: str
    label: str
    param_type: str  # "float", "int", "choice", "bool", "string"
    default: Any
    unit: str = ""
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    choices: List[str] = field(default_factory=list)
    tooltip: str = ""
    group: str = "기본 설정"


@dataclass
class MeasurableItemSpec:
    key: str
    label: str
    unit: str
    scpi_or_tsp_hint: str
    default_checked: bool = True
    description: str = ""


@dataclass
class ModelProfile:
    model_id: str
    display_name: str
    manual_file: str
    protocol: str  # "SCPI", "TSP", "DUAL_SCPI_TSP", "VISA_API"
    interfaces: List[str]
    max_channels: int
    specs_summary: str
    remote_notes: List[str]


@dataclass
class CategoryProfile:
    folder_id: str
    folder_name: str
    title_ko: str
    icon_text: str
    description: str
    models: List[ModelProfile]
    checklist: List[ChecklistItem]
    input_parameters: List[InputParameterSpec]
    measurable_items: List[MeasurableItemSpec]
    graph_modes: List[str]
    has_power_output: bool = False


CATEGORY_PROFILES: Dict[str, CategoryProfile] = {
    "01_AFG": CategoryProfile(
        folder_id="01_AFG",
        folder_name="01. AFGs",
        title_ko="01. AFGs (임의 파형/함수 발생기)",
        icon_text="🌊",
        description="AFG1000, AFG2021, AFG31000 시리즈 파형 생성, 변조/스윕 설정 및 출력 상태/파형 모니터링",
        has_power_output=True,
        graph_modes=["실시간 출력 파형 프리뷰 (CH1/CH2 Voltage vs Time)", "주파수/진폭 모니터링 트렌드"],
        models=[
            ModelProfile(
                model_id="AFG31000",
                display_name="AFG31000 Series (AFG31021~AFG31252)",
                manual_file="01. AFGs/AFG31000_Series_ProgrammersManual_Nov2020.pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)", "LAN (TCPIP/VXI-11)"],
                max_channels=2,
                specs_summary="25MHz~250MHz, 250MS/s~2GS/s, 14-bit, InstaView 실시간 부하 모니터링 지원",
                remote_notes=[
                    "후면 USB Type-B (USBTMC) 또는 RJ-45 LAN 포트 연결",
                    "전면 패널 Utility > I/O Interface 에서 LAN(DHCP/Manual) 또는 USB 활성화 확인",
                    "부하 임피던스(50Ω vs High-Z) 설정이 실제 연결된 DUT 임피던스와 일치하는지 확인 (진폭 2배 오차 방지)",
                ],
            ),
            ModelProfile(
                model_id="AFG1000",
                display_name="AFG1000 Series (AFG1022 / AFG1062)",
                manual_file="01. AFGs/AFG1000-Programmer-Manual-EN-077112902.pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)"],
                max_channels=2,
                specs_summary="25MHz/60MHz, 125MS/s~300MS/s, 14-bit, Dual-Channel",
                remote_notes=[
                    "AFG1000 시리즈는 후면 USB Type-B (USBTMC) 포트를 통해 원격 제어 지원",
                    "TekVISA 또는 NI-VISA USBTMC 드라이버 설치 필수",
                    "SI 단위(Hz, kHz, MHz, Vpp, mV) 사용 시 반드시 숫자와 단위를 함께 표기 (예: 15MHz 허용, 15M 불가)",
                ],
            ),
            ModelProfile(
                model_id="AFG2021",
                display_name="AFG2021 (20MHz Function Generator)",
                manual_file="01. AFGs/AFG2021_Programmer Manual.pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)", "LAN (Option GL)"],
                max_channels=1,
                specs_summary="20MHz, 250MS/s, 14-bit, 1채널 (Option GL 장착 시 LAN/GPIB 지원)",
                remote_notes=[
                    "기본 모델은 USB 포트 지원, Option GL 모델은 LAN/GPIB 추가 지원",
                    "Utility > I/O Interface 메뉴에서 인터페이스 설정 확인",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="afg_cable",
                title="[1단계: 케이블 연결] 장비 후면 USB Type-B 포트(사각형) 또는 LAN 포트에 케이블 연결",
                description="AFG1000은 후면 USB Type-B 전용이며, AFG2021(Opt.GL)/AFG31000은 후면 USB Type-B 및 RJ-45 LAN을 모두 지원합니다.",
                how_to_steps=[
                    "1. [USB 연결 시] 프린터 케이블 모양의 'USB Type-A to Type-B' 케이블을 준비합니다. (전면의 USB 메모리카드 포트에 꽂으면 안 됩니다!)",
                    "2. 사각형 단자(Type-B)를 AFG 장비 뒷면(Rear Panel)의 'USB' 포트에 꽂고, 반대쪽(Type-A)을 PC의 USB 포트에 꽂습니다.",
                    "3. [LAN 연결 시] 장비 뒷면의 LAN(RJ-45) 포트와 PC(또는 공유기/허브)를 랜선으로 연결합니다.",
                    "4. 장비 전원을 켜고 우측의 [🔍 통신 연결 확인] 버튼을 눌러 장비 이름(*IDN?)이 정상으로 읽히는지 확인하세요.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: 케이블 & *IDN? 통신 확인",
                expected_hint="TEKTRONIX,AFG... 모델명과 시리얼 번호가 표시되면 연결 성공",
            ),
            ChecklistItem(
                id="afg_io_menu",
                title="[2단계: 장비 화면 설정] 전면 Utility 버튼 > I/O Interface 원격 통신 및 에러 상태 확인",
                description="LAN 연결 시 IP 주소(DHCP 또는 수동 IP)가 정상 할당되었는지 확인하고 장비 내부 에러 큐를 점검합니다.",
                how_to_steps=[
                    "1. 장비 전면 패널에서 [Utility] 버튼을 누릅니다.",
                    "2. 화면 메뉴에서 [I/O Interface] (또는 Network/LAN)를 선택합니다.",
                    "3. USB 사용 시 USBTMC가 자동 활성화되며, LAN 사용 시 DHCP를 켜거나 수동 IP 주소를 확인합니다.",
                    "4. 우측의 [🔍 시스템 에러 큐 확인] 버튼을 눌러 '0, No error'가 반환되는지 확인하세요.",
                ],
                verify_cmd="SYSTem:ERRor:NEXT?",
                verify_label="🔍 2단계: 시스템 에러 상태 점검",
                expected_hint='0,"No error" 가 표시되면 장비 내부 상태 정상',
            ),
            ChecklistItem(
                id="afg_load_imp",
                title="[3단계: 부하 임피던스 점검] 측정 대상(DUT/오실로스코프)의 입력 임피던스(50Ω vs High-Z) 확인",
                description="장비의 Load Impedance 설정과 실제 연결된 장비(예: 오실로스코프 1MΩ 또는 50Ω)가 다르면 전압이 2배로 출력될 수 있습니다.",
                how_to_steps=[
                    "1. AFG의 CH1/CH2 출력 단자(BNC 케이블)를 연결할 대상 장비(오실로스코프 또는 회로)의 입력 임피던스를 확인합니다.",
                    "2. 일반 오실로스코프 기본 입력(1MΩ)에 연결할 경우, 프로그램의 '부하 임피던스'를 'INFinity (High-Z)'로 맞추거나 50Ω 종단 저항을 끼우세요.",
                    "3. 우측의 [🔍 현재 임피던스 설정 읽기] 버튼을 눌러 현재 장비에 설정된 임피던스(Ω) 값을 확인합니다.",
                ],
                verify_cmd="OUTPut1:IMPedance?",
                verify_label="🔍 3단계: 현재 부하 임피던스 읽기",
                expected_hint="50.0 (50Ω) 또는 INF/1.0E+06 (High-Z) 반환",
            ),
            ChecklistItem(
                id="afg_output_safe",
                title="[4단계: 출력 안전 점검] 현재 출력이 OFF 상태인지 확인 후 DUT에 BNC 케이블 연결",
                description="측정 시작 버튼을 누르기 전까지는 신호 출력이 꺼져(OFF) 있어야 안전합니다.",
                how_to_steps=[
                    "1. 장비 전면의 [CH1 On/Off] 버튼에 불이 꺼져 있는지 확인합니다.",
                    "2. 우측의 [🔍 출력 OFF 상태 확인] 버튼을 눌러 현재 출력이 '0 (OFF)'인지 확인한 뒤 측정 대상(DUT)에 케이블을 연결하세요.",
                ],
                verify_cmd="OUTPut1:STATe?",
                verify_label="🔍 4단계: 출력 대기(OFF) 상태 확인",
                expected_hint="0 (출력 OFF 대기 상태) 또는 1 (현재 출력 ON 상태)",
            ),
        ],
        input_parameters=[
            InputParameterSpec("channel", "제어 채널 (Channel)", "choice", "CH1", choices=["CH1", "CH2", "CH1 & CH2 (Dual)"], group="1. 채널 및 파형 설정"),
            InputParameterSpec("function", "출력 파형 (Waveform Shape)", "choice", "SINusoid", choices=["SINusoid", "SQUare", "PULSe", "RAMP", "PRNoise", "DC", "SINC", "GAUSsian", "LORentz", "ERISe", "EDECay", "HAVersine"], tooltip="SOURce<n>:FUNCtion:SHAPe", group="1. 채널 및 파형 설정"),
            InputParameterSpec("frequency_hz", "주파수 (Frequency)", "float", 1000.0, unit="Hz", min_val=1e-6, max_val=250e6, tooltip="SOURce<n>:FREQuency:FIXed", group="1. 채널 및 파형 설정"),
            InputParameterSpec("amplitude_vpp", "진폭 (Amplitude)", "float", 2.0, unit="Vpp", min_val=0.001, max_val=20.0, tooltip="SOURce<n>:VOLTage:LEVel:IMMediate:AMPLitude", group="2. 전압 및 위상 설정"),
            InputParameterSpec("offset_v", "DC 오프셋 (Offset)", "float", 0.0, unit="V", min_val=-10.0, max_val=10.0, tooltip="SOURce<n>:VOLTage:LEVel:IMMediate:OFFSet", group="2. 전압 및 위상 설정"),
            InputParameterSpec("phase_deg", "위상 (Phase)", "float", 0.0, unit="DEG", min_val=-360.0, max_val=360.0, tooltip="SOURce<n>:PHASe:ADJust", group="2. 전압 및 위상 설정"),
            InputParameterSpec("duty_cycle", "펄스 듀티비 (Pulse Duty)", "float", 50.0, unit="%", min_val=0.1, max_val=99.9, tooltip="SOURce<n>:PULSe:DCYCle (PULSe 파형 선택 시 유효)", group="2. 전압 및 위상 설정"),
            InputParameterSpec("impedance", "부하 임피던스 (Load Impedance)", "choice", "50 Ω", choices=["50 Ω", "INFinity (High-Z)", "Custom (1000 Ω)"], tooltip="OUTPut<n>:IMPedance", group="3. 출력 및 동작 모드"),
            InputParameterSpec("run_mode", "동작 모드 (Operation Mode)", "choice", "Continuous (연속 출력)", choices=["Continuous (연속 출력)", "Frequency Sweep (주파수 스윕)", "AM Modulation (진폭 변조)", "Burst (버스트 N사이클)"], group="3. 출력 및 동작 모드"),
            InputParameterSpec("sweep_stop_hz", "스윕 종료 주파수 (Sweep Stop)", "float", 10000.0, unit="Hz", min_val=1e-6, max_val=250e6, tooltip="SOURce<n>:FREQuency:STOP (Sweep 모드 시)", group="3. 출력 및 동작 모드"),
            InputParameterSpec("poll_interval_s", "상태 모니터링 주기", "float", 0.5, unit="s", min_val=0.1, max_val=60.0, group="3. 출력 및 동작 모드"),
        ],
        measurable_items=[
            MeasurableItemSpec("out_state", "출력 상태 (Output State)", "ON/OFF", "OUTPut<n>:STATe?", True, "현재 채널의 신호 출력 활성화 상태"),
            MeasurableItemSpec("act_func", "설정 파형 (Active Function)", "Shape", "SOURce<n>:FUNCtion:SHAPe?", True, "장비에 적용된 현재 파형 형태"),
            MeasurableItemSpec("act_freq_hz", "현재 주파수 (Actual Frequency)", "Hz", "SOURce<n>:FREQuency?", True, "장비에서 출력 중인 주파수 읽기"),
            MeasurableItemSpec("act_amp_vpp", "현재 진폭 (Actual Amplitude)", "Vpp", "SOURce<n>:VOLTage:AMPLitude?", True, "장비에서 출력 중인 진폭(Vpp)"),
            MeasurableItemSpec("act_offset_v", "현재 오프셋 (Actual Offset)", "V", "SOURce<n>:VOLTage:OFFSet?", True, "장비에서 출력 중인 DC 오프셋(V)"),
            MeasurableItemSpec("act_phase_deg", "현재 위상 (Actual Phase)", "DEG", "SOURce<n>:PHASe?", True, "장비에서 출력 중인 위상각(도)"),
            MeasurableItemSpec("act_imp_ohm", "부하 임피던스 (Load Impedance)", "Ω", "OUTPut<n>:IMPedance?", True, "설정된 출력 부하 임피던스"),
            MeasurableItemSpec("sys_err", "시스템 에러 상태 (Error Queue)", "Code/Msg", "SYSTem:ERRor:NEXT?", True, "장비 내부 에러 큐 상태 점검"),
        ],
    ),

    "02_DC_POWER": CategoryProfile(
        folder_id="02_DC_POWER",
        folder_name="02. DC power Supplies",
        title_ko="02. DC Power Supplies (프로그래머블 DC 전원공급기)",
        icon_text="⚡",
        description="Keithley/Tektronix Series 2200 (다채널 2220/2230/2231A) 및 Series 2260B 대전류 전원공급기 제어 및 V/I/P 로깅",
        has_power_output=True,
        graph_modes=["실시간 전압/전류/전력 시계열 그래프 (V, I, P vs Time)", "V-I 동작 영역 및 부하 변동 모니터링"],
        models=[
            ModelProfile(
                model_id="SERIES_2200",
                display_name="Series 2200 Multichannel (2220 / 2230 / 2231A)",
                manual_file="02. DC power Supplies/2220S-907-01B_Dec_2013_Prog.pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)", "GPIB (G-Version)"],
                max_channels=3,
                specs_summary="2채널(2220: 30V/1.5A×2) 또는 3채널(2230/2231A: 30V/1.5A×2 + 6V/5A), 독립/직렬/병렬/트래킹 지원",
                remote_notes=[
                    "후면 USB 2.0 포트 연결 시 USBTMC 프로토콜로 자동 인식",
                    "명령어 평균 응답 시간은 약 20ms이므로 폴링 주기를 50ms 이상으로 설정 권장",
                    "다채널 모델은 INSTrument:SELect CH1|CH2|CH3 또는 MEAS:VOLT? ALL 로 채널 지정",
                ],
            ),
            ModelProfile(
                model_id="SERIES_2260B",
                display_name="Series 2260B Programmable DC Supply (360W~1080W)",
                manual_file="02. DC power Supplies/2260B_Programming_Oct2024.pdf",
                protocol="SCPI",
                interfaces=["USB (USB-CDC Virtual COM)", "LAN (Ethernet / Socket)"],
                max_channels=1,
                specs_summary="30V~800V / 최대 108A, 슬루율(Slew Rate) 제어 및 내부 저항(Internal Resistance) 시뮬레이션 지원",
                remote_notes=[
                    "USB 사용 시: 장비 전원 OFF 상태에서 USB 연결 -> 전원 ON -> Function 키 > F-22 > '2' (USB-CDC, Auto Detect Speed) 설정 필수!",
                    "2260B의 USB는 PC 장치 관리자에서 가상 COM 포트(ASRLx::INSTR)로 인식되며 종료 문자 Line Feed (\\n) 활성화 필요",
                    "LAN 사용 시: Function 키 > F-36=1(LAN Enable), F-37=1(DHCP), F-57=1(Socket Enable)",
                    "전원 스위치 설정(F-90 CV Control=0, F-91 CC Control=0)이 Local/Remote 허용 상태인지 확인",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="psu_usb_mode",
                title="[1단계: PC 케이블 및 포트 설정] 2200(후면 USB) / 2260B(Function > F-22 = 2 USB-CDC 또는 LAN F-36=1)",
                description="2260B는 일반 USBTMC가 아닌 USB-CDC(가상 COM 포트, 종료문자 \\n)를 사용하며, 2200 시리즈는 USBTMC를 사용합니다.",
                how_to_steps=[
                    "1. [Series 2200 모델] 장비 후면의 USB 포트와 PC를 USB Type-B 케이블로 연결하고 전원을 켜면 자동으로 USBTMC 장비로 인식됩니다.",
                    "2. [Series 2260B USB 사용 시] ① 전원을 끈 상태에서 후면 USB 연결 -> ② 전원 ON -> ③ 전면 [Function] 키 누름 -> ④ 노브를 돌려 [F-22] 선택 -> ⑤ 값을 '2'(USB-CDC)로 변경 후 엔터!",
                    "3. [Series 2260B LAN 사용 시] 후면 LAN 케이블 연결 -> [Function] 키 -> [F-36]=1(LAN 켜기), [F-37]=1(자동 IP) 또는 수동 IP(F-39~42), [F-57]=1(소켓 서버 포트 2268 켜기).",
                    "4. 상단 리소스 목록에서 해당 포트(USB0::... 또는 ASRLx::INSTR 또는 TCPIP0::<IP>::2268::SOCKET)를 선택하고 우측 버튼으로 통신을 테스트하세요.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: 전원공급기 연결(*IDN?) 확인",
                expected_hint="KEITHLEY, 2220/2230/2260B 모델명 및 펌웨어 버전 반환",
            ),
            ChecklistItem(
                id="psu_local_ctrl",
                title="[2단계: 원격 제어 권한 확인] 2260B 전면 F-90(CV)=0, F-91(CC)=0 및 기동 시 출력 OFF(F-92=0) 확인",
                description="외부 아날로그 제어 모드로 설정되어 있으면 PC에서 보내는 전압/전류 명령이 동작하지 않습니다.",
                how_to_steps=[
                    "1. [2260B] 전면 [Function] 메뉴에서 F-90(CV Control)과 F-91(CC Control)이 모두 기본값 '0 (전면/원격 제어)'인지 확인합니다.",
                    "2. F-92(Power-on Output)가 '0 (전원 켤 때 출력 OFF)'으로 되어 있는지 확인합니다.",
                    "3. 우측 [🔍 보호 회로 및 상태 레지스터 확인] 버튼을 눌러 이상 트립(0=정상)이 없는지 확인하세요.",
                ],
                verify_cmd="OUTPut:STATe?",
                verify_label="🔍 2단계: 현재 출력 상태(ON/OFF) 확인",
                expected_hint="0 (출력 OFF 안전 대기 중) 또는 1 (출력 ON)",
            ),
            ChecklistItem(
                id="psu_ovp_ocp",
                title="[3단계: 과전압/과전류 보호 점검] 측정할 회로(DUT)의 최대 허용 전압(OVP)과 제한 전류(Current Limit) 확인",
                description="전원 인가 전 회로가 타지 않도록 과전압 보호(OVP)와 전류 제한값을 반드시 먼저 확인합니다.",
                how_to_steps=[
                    "1. 연결할 회로(DUT)가 견딜 수 있는 최대 전압과 전류를 확인합니다.",
                    "2. 프로그램 좌측 [1. 입력이 필요한 사항]에서 '목표 출력 전압', '전류 제한(Current Limit)', '과전압 보호 상한(OVP)'을 안전하게 입력합니다.",
                    "3. 우측 버튼을 눌러 현재 출력 단자에 걸려 있는 실제 전압(V)을 미리 읽어 확인합니다.",
                ],
                verify_cmd="MEASure:SCALar:VOLTage:DC?",
                verify_label="🔍 3단계: 현재 단자 전압(V) 사전 측정",
                expected_hint="현재 출력 단자 전압(V) 수치 반환 (출력 OFF 시 0.00V 부근)",
            ),
            ChecklistItem(
                id="psu_combine",
                title="[4단계: 출력 단자 배선] 플러스(+) 빨간색 / 마이너스(-) 검은색 리드선 결선 및 다채널 직/병렬 배선 확인",
                description="2200 다채널 모델에서 직렬(Series) 또는 병렬(Parallel) 모드 선택 시 외부 배선도 매뉴얼과 동일하게 연결해야 합니다.",
                how_to_steps=[
                    "1. 출력이 꺼진(Output OFF) 상태에서 장비 전면의 (+) 단자와 (-) 단자에 테스트 리드선을 정확히 연결합니다.",
                    "2. 2200 시리즈에서 독립 채널(Independent)로 쓸 경우 CH1, CH2, CH3 각각에 맞게 결선되었는지 확인합니다.",
                    "3. 우측 버튼으로 현재 흐르는 전류(A)가 0A(대기 상태)인지 확인한 후 체크박스를 체크하세요.",
                ],
                verify_cmd="MEASure:SCALar:CURRent:DC?",
                verify_label="🔍 4단계: 현재 출력 전류(A) 사전 측정",
                expected_hint="현재 출력 전류(A) 수치 반환",
            ),
        ],
        input_parameters=[
            InputParameterSpec("channel", "대상 채널 (Target Channel)", "choice", "CH1", choices=["CH1", "CH2", "CH3", "ALL (전체 채널 동시 측정)"], tooltip="INSTrument:SELect CHx (2200 시리즈)", group="1. 채널 및 출력 설정"),
            InputParameterSpec("combine_mode", "채널 조합 모드 (2200 Series)", "choice", "OFF (독립 채널)", choices=["OFF (독립 채널)", "SERies (CH1+CH2 직렬)", "PARAllel (CH1+CH2 병렬)", "TRACk (트래킹)"], tooltip="INSTrument:COMbine", group="1. 채널 및 출력 설정"),
            InputParameterSpec("voltage_v", "목표 출력 전압 (Target Voltage)", "float", 5.0, unit="V", min_val=0.0, max_val=800.0, tooltip="SOURce:VOLTage:LEVel:IMMediate:AMPLitude", group="1. 채널 및 출력 설정"),
            InputParameterSpec("current_limit_a", "전류 제한 (Current Limit)", "float", 1.0, unit="A", min_val=0.001, max_val=108.0, tooltip="SOURce:CURRent:LEVel:IMMediate:AMPLitude", group="1. 채널 및 출력 설정"),
            InputParameterSpec("ovp_v", "과전압 보호 상한 (OVP Level)", "float", 12.0, unit="V", min_val=0.5, max_val=880.0, tooltip="VOLTage:LIMit / VOLTage:PROTection:LEVel", group="2. 보호 회로 및 고급 제어"),
            InputParameterSpec("ocp_enable", "과전류 보호 활성화 (OCP Enable - 2260B)", "bool", True, tooltip="CURRent:PROTection:STATe", group="2. 보호 회로 및 고급 제어"),
            InputParameterSpec("slew_priority", "출력 우선순위 모드 (2260B Mode)", "choice", "CVHS (0: CV 고속 우선)", choices=["CVHS (0: CV 고속 우선)", "CCHS (1: CC 고속 우선)", "CVLS (2: CV 슬루율 제어)", "CCLS (3: CC 슬루율 제어)"], tooltip="OUTPut:MODE", group="2. 보호 회로 및 고급 제어"),
            InputParameterSpec("slew_rate_vs", "전압 상승 슬루율 (Voltage Slew Rate)", "float", 60.0, unit="V/s", min_val=0.01, max_val=1600.0, tooltip="VOLTage:SLEW:RISing (2260B)", group="2. 보호 회로 및 고급 제어"),
            InputParameterSpec("internal_res_ohm", "내부 저항 시뮬레이션 (Internal Resistance)", "float", 0.0, unit="Ω", min_val=0.0, max_val=555.0, tooltip="SOURce:RESistance (2260B 배터리 시뮬레이션용)", group="2. 보호 회로 및 고급 제어"),
            InputParameterSpec("poll_interval_s", "측정 샘플링 주기", "float", 0.25, unit="s", min_val=0.05, max_val=60.0, group="3. 로깅 설정"),
        ],
        measurable_items=[
            MeasurableItemSpec("meas_v", "출력 전압 측정 (Measured Voltage)", "V", "MEASure:SCALar:VOLTage:DC?", True, "실제 출력 단자에서 측정된 DC 전압"),
            MeasurableItemSpec("meas_i", "출력 전류 측정 (Measured Current)", "A", "MEASure:SCALar:CURRent:DC?", True, "실제 부하로 흐르는 DC 전류"),
            MeasurableItemSpec("meas_p", "출력 전력 측정 (Measured Power)", "W", "MEASure:SCALar:POWer:DC? / FETCh:POWer?", True, "실제 공급 중인 DC 전력 (W)"),
            MeasurableItemSpec("calc_load_r", "등가 부하 저항 (Calculated Load R)", "Ω", "V / I 연산", True, "측정된 전압/전류로부터 계산된 부하 저항"),
            MeasurableItemSpec("prot_tripped", "보호 회로 트립 여부 (OVP/OCP/OTP Tripped)", "0/1", "OUTPut:PROTection:TRIPped? / STATus:QUEStionable?", True, "과전압/과전류/과열 보호 트립 상태"),
            MeasurableItemSpec("out_state", "출력 상태 (Output State)", "ON/OFF", "OUTPut:STATe?", True, "전원 공급기 출력 활성화 상태"),
        ],
    ),

    "07_DC_PRECISION": CategoryProfile(
        folder_id="03_DC_PRECISION",
        folder_name="07. DC Precision test",
        title_ko="07. DC Precision test (MP5000 모듈형 정밀 테스트 시스템)",
        icon_text="🎯",
        description="MP5000 시리즈(MP5103 메인프레임 + PSU/SMU 슬롯 모듈) TSP 스크립트 기반 정밀 소스/측정 및 TriggerFlow 스윕",
        has_power_output=True,
        graph_modes=["실시간 전압/전류/저항 시계열 (V, I, R vs Time)", "스윕 특성 곡선 (I-V Curve / Power Curve)"],
        models=[
            ModelProfile(
                model_id="MP5000_MP5103",
                display_name="MP5000 Series (MP5103 Mainframe + Slot[1..3] PSU/SMU Modules)",
                manual_file="03. DC Precision Test/077189504_MP5000_Programmer_Manual_Aug2026.pdf",
                protocol="TSP",
                interfaces=["USB (USBTMC)", "LAN (HiSLIP / Raw Socket)"],
                max_channels=6,
                specs_summary="3-Slot 모듈형 메인프레임(MP5103), Lua 기반 Test Script Processor(TSP), slot[Z].psu[X] 및 slot[Z].smu[X] 제어",
                remote_notes=[
                    "MP5000은 SCPI가 아닌 Lua 기반 TSP(Test Script Processor) 명령 체계를 사용하며 응답은 print()로 출력",
                    "USBTMC는 기본 활성화되어 있으며, LAN은 기본 비활성화(Disabled) 상태임",
                    "LAN 사용 시: 전면 Home > IP Address > Config 에서 LAN 슬라이더 활성화 -> Settings > Security 에서 프로토콜(HiSLIP/Raw Socket) ON 또는 LOCK 설정",
                    "보안(PROTECT) 모드 사용 시 통신 시작 전 'login <password>' 전송 필수 ('login?'으로 인증 상태 확인)",
                    "단일 인터페이스 독점 제어: 다른 인터페이스가 점유 중이면 'remote?'가 Disallowed를 반환하며 'abort'로 이전 세션 해제 필요",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="mp5000_proto",
                title="[1단계: 케이블 및 LAN 활성화] USB(기본 켜짐) 연결 또는 LAN(전면 화면 Config에서 LAN 슬라이더 ON)",
                description="MP5103 메인프레임은 보안상 출고 시 모든 LAN 통신이 꺼져(Disabled) 있으며, USBTMC만 기본 켜져 있습니다.",
                how_to_steps=[
                    "1. [USB 연결 시 - 초보자 권장] 후면 USB Type-B 포트와 PC를 연결하면 별도 설정 없이 바로 USBTMC로 인식됩니다.",
                    "2. [LAN 연결 시] ① 후면 LAN 포트(TSP-Link 포트 아님 주의!)에 랜선 연결 -> ② 장비 전면 터치스크린 홈 화면에서 [IP 주소] 터치 -> ③ [Config] 터치 -> ④ [LAN] 슬라이더를 켜고(Enable) [Submit]을 누릅니다.",
                    "3. 우측 [🔍 메인프레임 *IDN? 확인] 버튼을 눌러 MP5103 메인프레임과 통신이 되는지 확인합니다.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: MP5000 메인프레임 응답 확인",
                expected_hint="TEKTRONIX,MP5103,... 메인프레임 식별 정보 반환",
            ),
            ChecklistItem(
                id="mp5000_login",
                title="[2단계: 보안 로그인 확인] 전면 Settings > Security 프로토콜(HiSLIP/Raw Socket) ON 또는 비밀번호 인증",
                description="프로토콜이 LOCK(보호 모드)으로 되어 있으면 통신 전 'login 비밀번호' 명령이 필요합니다.",
                how_to_steps=[
                    "1. 장비 전면 터치스크린에서 [Settings] > [Security] 메뉴로 들어갑니다.",
                    "2. 사용할 프로토콜(USBTMC, HiSLIP, Raw Socket)이 ON 상태인지 확인합니다. 만약 자물쇠(LOCK)가 켜져 있다면 좌측 입력창의 'LAN 보안 비밀번호' 칸에 장비 비밀번호를 입력하세요.",
                    "3. 우측 [🔍 로그인 인증 상태(login?) 확인] 버튼을 눌러 'Authenticated'가 나오는지 확인합니다.",
                ],
                verify_cmd="login?",
                verify_label="🔍 2단계: 보안 인증(login?) 상태 확인",
                expected_hint="Authenticated 반환 시 명령 수신 가능 상태",
            ),
            ChecklistItem(
                id="mp5000_remote_lock",
                title="[3단계: 원격 제어권 확인] 다른 PC나 인터페이스가 장비를 점유하고 있지 않은지(remote?) 확인",
                description="MP5000은 한 번에 하나의 통신 포트만 제어권을 갖습니다. 다른 연결이 물려 있으면 'abort'로 해제해야 합니다.",
                how_to_steps=[
                    "1. 우측의 [🔍 제어권 상태(remote?) 확인] 버튼을 클릭합니다.",
                    "2. 응답이 'Allowed' 또는 'Local'이면 정상입니다.",
                    "3. 만약 'Disallowed'가 나오면 다른 창이나 인터페이스가 점유 중인 것이므로 하단 Talker/Listener 콘솔에서 'abort'를 전송해 기존 연결을 끊을 수 있습니다.",
                ],
                verify_cmd="remote?",
                verify_label="🔍 3단계: 원격 제어 허용(remote?) 확인",
                expected_hint="Allowed 반환 시 현재 PC에서 원격 제어 가능",
            ),
            ChecklistItem(
                id="mp5000_slot_mod",
                title="[4단계: 슬롯 장착 모듈 확인] 제어할 슬롯(Slot 1~3)에 실제 꽂혀 있는 모듈(SMU vs PSU) 모델 확인",
                description="MP5103의 1~3번 슬롯 중 어느 슬롯에 SMU 또는 PSU 모듈이 장착되어 있는지 확인합니다.",
                how_to_steps=[
                    "1. 우측의 [🔍 Slot 1 장착 모듈 조회] 버튼을 눌러 1번 슬롯에 장착된 모듈 이름을 확인합니다.",
                    "2. 좌측 [1. 입력이 필요한 사항]의 '메인프레임 슬롯(Slot Z)'과 '모듈 종류(SMU vs PSU)'를 실제 장착된 모듈에 맞게 선택하세요.",
                ],
                verify_cmd="print(slot[1].model)",
                verify_label="🔍 4단계: Slot 1 장착 모듈 모델명 조회",
                expected_hint="MP5201-SMU 또는 MP5301-PSU 등 슬롯 모듈 모델명 반환",
            ),
        ],
        input_parameters=[
            InputParameterSpec("slot_no", "메인프레임 슬롯 (Slot Z)", "choice", "Slot 1", choices=["Slot 1", "Slot 2", "Slot 3"], tooltip="slot[Z]", group="1. 슬롯 및 모듈 선택"),
            InputParameterSpec("module_type", "모듈 종류 (Module Type)", "choice", "SMU Module (slot[Z].smu[X])", choices=["SMU Module (slot[Z].smu[X])", "PSU Module (slot[Z].psu[X])"], tooltip="slot[Z].smu[X] 또는 slot[Z].psu[X]", group="1. 슬롯 및 모듈 선택"),
            InputParameterSpec("channel_no", "모듈 채널 (Channel X)", "choice", "Channel 1", choices=["Channel 1", "Channel 2"], tooltip="smu[1..2] / psu[1..2]", group="1. 슬롯 및 모듈 선택"),
            InputParameterSpec("auth_password", "LAN 보안 비밀번호 (선택)", "string", "", tooltip="Protected 모드 시 login <password> 전송 (비워두면 생략)", group="1. 슬롯 및 모듈 선택"),
            InputParameterSpec("test_mode", "측정/동작 모드 (Test Mode)", "choice", "Continuous DC Source-Measure", choices=["Continuous DC Source-Measure", "Linear Staircase Sweep (TriggerFlow)", "Logarithmic Staircase Sweep", "Pulsed Sweep (Bias & Step)"], group="2. 소스 및 스윕 설정"),
            InputParameterSpec("source_func", "소스 기능 (Source Function)", "choice", "Voltage Source (levelv)", choices=["Voltage Source (levelv)", "Current Source (leveli - SMU전용)"], group="2. 소스 및 스윕 설정"),
            InputParameterSpec("source_level", "소스 출력 레벨 (Source Level / Sweep Start)", "float", 3.3, unit="V or A", min_val=-200.0, max_val=200.0, tooltip="source.levelv / source.leveli", group="2. 소스 및 스윕 설정"),
            InputParameterSpec("sweep_stop", "스윕 종료 레벨 (Sweep Stop)", "float", 5.0, unit="V or A", min_val=-200.0, max_val=200.0, tooltip="trigger.source.linearY(start, stop, points)", group="2. 소스 및 스윕 설정"),
            InputParameterSpec("sweep_points", "스윕 포인트 수 (Sweep Points)", "int", 11, unit="pts", min_val=2, max_val=1000, group="2. 소스 및 스윕 설정"),
            InputParameterSpec("limit_val", "컴플라이언스 제한 (Limit I or V)", "float", 0.1, unit="A or V", min_val=1e-9, max_val=50.0, tooltip="source.limiti / source.limitv", group="3. 제한 및 정밀 측정 설정"),
            InputParameterSpec("nplc", "적분 시간 (Measure NPLC)", "float", 1.0, unit="PLC", min_val=0.001, max_val=25.0, tooltip="measure.nplc (전원 주파수 주기 단위 적분)", group="3. 제한 및 정밀 측정 설정"),
            InputParameterSpec("sense_mode", "센싱 방식 (SMU Sense / Contact Check)", "choice", "2-Wire Local Sense", choices=["2-Wire Local Sense", "4-Wire Remote Sense", "4-Wire + Contact Check"], group="3. 제한 및 정밀 측정 설정"),
            InputParameterSpec("poll_interval_s", "측정 주기 / 스텝 딜레이", "float", 0.2, unit="s", min_val=0.02, max_val=60.0, group="3. 제한 및 정밀 측정 설정"),
        ],
        measurable_items=[
            MeasurableItemSpec("meas_v", "정밀 전압 측정 (Measured Voltage)", "V", "slot[Z].smu[X].measure.v() / psu[X].measure.v()", True, "고해상도 ADC 전압 측정값"),
            MeasurableItemSpec("meas_i", "정밀 전류 측정 (Measured Current)", "A", "slot[Z].smu[X].measure.i() / psu[X].measure.i()", True, "고해상도 ADC 전류 측정값"),
            MeasurableItemSpec("calc_r", "저항 계산값 (Calculated Resistance)", "Ω", "V / I", True, "인가/측정된 V, I로부터 산출된 저항"),
            MeasurableItemSpec("calc_p", "전력 계산값 (Calculated Power)", "W", "V * I", True, "인가/측정된 V, I로부터 산출된 전력"),
            MeasurableItemSpec("at_limit", "컴플라이언스 도달 여부 (Source At Limit)", "Bool", "slot[Z].smu[X].source.atlimit / psu[X].source.constantcurrent", True, "제한 전류/전압(Compliance) 도달 상태"),
            MeasurableItemSpec("contact_r", "접촉 저항 점검 (Contact Check R)", "Ω", "slot[Z].smu[X].contact.r()", False, "4-Wire 연결 시 리드 접촉 저항 측정 (SMU 모듈)"),
            MeasurableItemSpec("slot_temp", "초기 영점 대비 온도 변화 (Temp Delta)", "°C", "slot[Z].smu[X].acal.temperaturedelta()", False, "자동 교정(ACAL) 이후 모듈 온도 변화량"),
        ],
    ),

    "04_OSCILLOSCOPE": CategoryProfile(
        folder_id="04_OSCILLOSCOPE",
        folder_name="04. Oscilloscopes",
        title_ko="04. Oscilloscopes (디지털 오실로스코프 전 시리즈)",
        icon_text="📈",
        description="TBS1000C, TBS2000B, 2 Series MSO, 3 Series MDO, 4/5/6 Series MSO, 7 Series DPO, DPO/MSO5000/7000/70000 파형 캡처 및 자동 측정",
        has_power_output=False,
        graph_modes=["실시간 오실로스코프 파형 그래프 (Waveform CURVe? Voltage vs Time)", "자동 측정 파라미터 시계열 트렌드 (Freq, Vpp, Vrms vs Time)"],
        models=[
            ModelProfile(
                model_id="MSO_4_5_6",
                display_name="4 / 5 / 6 Series MSO (MSO4XB, MSO5XB, MSO58LP, MSO6XB, LPD64)",
                manual_file="04. Oscilloscopes/4-5-6-Series-MSO_Programmer_077189805.pdf",
                protocol="SCPI",
                interfaces=["USB 3.0 (USBTMC)", "LAN (Ethernet / VXI-11 / Socket)"],
                max_channels=8,
                specs_summary="차세대 터치 UI 오실로스코프, 동적 프로그래밍 인터페이스(MEASUrement:ADDNew / Implicit Activation) 지원",
                remote_notes=[
                    "Utility > I/O > USB Device Port 가 Enabled 인지 확인, 또는 LAN 패널에서 IP 확인",
                    "HEADer OFF 및 VERBose 설정에 따라 쿼리 응답 포맷이 달라지므로 초기화 시 HEADer OFF 전송 권장",
                    "4/5/6/7 시리즈는 동적 객체 인터페이스(MEASUrement:MEAS<x>:RESUlts:CURRentacq:MEAN? 및 하위 호환 VALue?) 지원",
                ],
            ),
            ModelProfile(
                model_id="DPO_7_SERIES",
                display_name="7 Series DPO Performance Oscilloscope (DPO714AX)",
                manual_file="04. Oscilloscopes/7-Series-DPO_Programmer_077186004.pdf",
                protocol="SCPI",
                interfaces=["USB 3.0 (USBTMC)", "LAN (Ethernet / VXI-11 / Socket)"],
                max_channels=4,
                specs_summary="초고성능 7 시리즈 DPO, 4/5/6 시리즈와 동일한 차세대 동적 SCPI 인터페이스 탑재",
                remote_notes=[
                    "Utility > I/O 메뉴에서 USB Device Port 또는 LAN/Socket Server 활성화 확인",
                ],
            ),
            ModelProfile(
                model_id="MSO_2_SERIES",
                display_name="2 Series MSO (MSO22 / MSO24)",
                manual_file="04. Oscilloscopes/2-Series-MSO-Programmer-077177608.pdf",
                protocol="SCPI",
                interfaces=["USB 2.0 (USBTMC)", "LAN (Ethernet)"],
                max_channels=4,
                specs_summary="컴팩트 포터블 2/4채널 MSO (FW v2.8 이상), 4/5/6 시리즈 호환 명령 체계",
                remote_notes=[
                    "측면 USB 2.0 Device 포트 또는 RJ-45 LAN 포트 연결 후 Utility > I/O 에서 활성화 확인",
                ],
            ),
            ModelProfile(
                model_id="MDO_3_SERIES",
                display_name="3 Series MDO (Mixed Domain Oscilloscope)",
                manual_file="04. Oscilloscopes/3SeriesMDO-Programmer-077149806.pdf",
                protocol="SCPI",
                interfaces=["USB 2.0 (USBTMC)", "LAN (Ethernet)"],
                max_channels=4,
                specs_summary="3 시리즈 MDO, 표준 Tektronix WFMOutpre / CURVe? 및 MEASUrement:IMMed / MEAS<x> 지원",
                remote_notes=[
                    "전면 Utility > Utility Page > I/O > USB (Connect to Computer) 또는 Network Configuration 확인",
                ],
            ),
            ModelProfile(
                model_id="DPO_MSO_5K_7K_70K",
                display_name="MSO/DPO5000/B, DPO7000/C, DPO/DSA/MSO70000 Series",
                manual_file="04. Oscilloscopes/Digital-Oscilloscopes-Programmer_077001026.pdf",
                protocol="SCPI",
                interfaces=["LAN (VXI-11 / Socket)", "USB (USBTMC)", "TekVISA Virtual GPIB"],
                max_channels=4,
                specs_summary="Windows 기반 고성능 디지털 오실로스코프, 내부 Virtual GPIB 및 LAN VXI-11/Socket 기본 지원",
                remote_notes=[
                    "Windows 기반 스코프는 내부 TekVISA VXI-11 Server가 실행 중이어야 원격 LAN 접속이 가능함",
                ],
            ),
            ModelProfile(
                model_id="TBS2000B",
                display_name="TBS2000B Series Digital Oscilloscope",
                manual_file="04. Oscilloscopes/TBS2000B-Programmer-Manual-EN-US-077114904.pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)", "LAN (Ethernet)"],
                max_channels=4,
                specs_summary="TBS2000B 시리즈, MEASUrement:IMMed 및 MEAS<x>:VALue?, WFMOutpre/CURVe? 지원",
                remote_notes=[
                    "후면 USB Device 포트 또는 Ethernet 포트 연결 확인",
                ],
            ),
            ModelProfile(
                model_id="TBS1000C",
                display_name="TBS1000C Series Digital Oscilloscope",
                manual_file="04. Oscilloscopes/TBS1000C-Programmer-Manual-EN-US-077169102.pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)"],
                max_channels=2,
                specs_summary="TBS1000C 2채널 오실로스코프, USBTMC 전용 원격 제어 및 최대 2500~20000 포인트 파형 전송",
                remote_notes=[
                    "후면 USB Device 포트 연결 및 프로브 감쇠비(1X / 10X) 설정 확인",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="scope_usb_lan",
                title="[1단계: PC 연결 및 I/O 설정] 오실로스코프 USB Device 포트(또는 LAN) 연결 및 Utility > I/O 활성화",
                description="USB 메모리를 꽂는 USB Host 포트(직사각형)가 아니라 PC와 연결하는 'USB Device Port'에 연결해야 합니다.",
                how_to_steps=[
                    "1. [USB 연결 시] 오실로스코프 뒷면(또는 2 시리즈는 측면)의 'USB Device' 포트와 PC를 USB 케이블(가급적 1m 이하 고품질 케이블)로 연결합니다.",
                    "2. 오실로스코프 화면 상단(또는 전면 버튼)에서 [Utility] > [I/O] 메뉴로 들어갑니다.",
                    "3. 'USB Device Port' 항목이 [On / Enabled / Connect to Computer]로 되어 있는지 확인합니다.",
                    "4. [LAN 연결 시] Utility > I/O > LAN 패널에서 Auto(DHCP)를 누르거나 IP 주소를 확인한 뒤 우측 버튼으로 통신을 확인하세요.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: 오실로스코프 연결(*IDN?) 확인",
                expected_hint="TEKTRONIX,MSO/DPO/TBS... 모델명 및 펌웨어 버전 반환",
            ),
            ChecklistItem(
                id="scope_probe",
                title="[2단계: 프로브 및 측정 신호 연결] CH1(또는 측정 채널)에 프로브 연결 및 감쇠비(1X / 10X) 점검",
                description="프로브 옆면의 스위치(1X vs 10X)와 오실로스코프 화면의 프로브 설정이 일치해야 전압이 정확히 측정됩니다.",
                how_to_steps=[
                    "1. 오실로스코프 전면 CH1 BNC 단자에 프로브를 꽂고(TekVPI 프로브는 딸깍 소리가 날 때까지 장착), 프로브 접지(악어클립)를 측정 회로의 GND에 먼저 연결합니다.",
                    "2. 프로브 팁을 측정할 신호에 연결합니다. (처음 연습할 때는 스코프 전면 우측 하단의 'Probe Comp' 기본 사각파 단자에 물리면 안전하게 파형을 볼 수 있습니다!)",
                    "3. 우측 버튼을 눌러 현재 오실로스코프가 정상 대기 중(*ESR? = 0)인지 확인하세요.",
                ],
                verify_cmd="*ESR?",
                verify_label="🔍 2단계: 장비 이벤트 상태(*ESR?) 점검",
                expected_hint="0 또는 정상 상태 바이트 반환",
            ),
            ChecklistItem(
                id="scope_header",
                title="[3단계: 데이터 전송 점검] 파형 및 자동 측정값 수신을 위한 스코프 응답 테스트",
                description="측정 시작 시 프로그램이 자동으로 HEADer OFF 및 파형 인코딩(ASCII)을 설정합니다.",
                how_to_steps=[
                    "1. 파형이 화면에 너무 크거나 작아서 안 보인다면, 좌측 입력창에서 '시작 시 Autoset 실행 여부'에 체크하거나 수직/수평 스케일(V/div, s/div)을 조절하세요.",
                    "2. 우측 버튼을 눌러 상태 바이트(*STB?) 응답이 즉시 오는지 확인합니다.",
                ],
                verify_cmd="*STB?",
                verify_label="🔍 3단계: 데이터 응답 속도(*STB?) 확인",
                expected_hint="정수 상태 바이트(예: 0, 16 등) 즉시 반환",
            ),
        ],
        input_parameters=[
            InputParameterSpec(
                "channel",
                "측정 소스 채널 (Source Channels - 다중 선택 가능)",
                "multi_choice",
                "CH1",
                choices=["CH1", "CH2", "CH3", "CH4"],
                tooltip="원하는 채널(CH1~CH4)을 1개 이상 체크하면 선택된 모든 채널의 파형과 측정값을 동시에 수집합니다 (SELect:CH<x> ON / DATa:SOUrce CH<x>)",
                group="1. 수직축(Vertical) 설정",
            ),
            InputParameterSpec("coupling", "입력 커플링 (Coupling)", "choice", "DC", choices=["DC", "AC", "GND", "DCREJect"], tooltip="CH<x>:COUPling", group="1. 수직축(Vertical) 설정"),
            InputParameterSpec("v_scale", "수직 스케일 (Vertical Scale)", "float", 1.0, unit="V/div", min_val=0.001, max_val=100.0, tooltip="CH<x>:SCAle", group="1. 수직축(Vertical) 설정"),
            InputParameterSpec("v_offset", "수직 오프셋 (Vertical Offset)", "float", 0.0, unit="V", min_val=-500.0, max_val=500.0, tooltip="CH<x>:OFFSet", group="1. 수직축(Vertical) 설정"),
            InputParameterSpec("h_scale", "수평 시간축 스케일 (Horizontal Scale)", "float", 0.001, unit="s/div", min_val=1e-9, max_val=100.0, tooltip="HORizontal:SCAle", group="2. 수평축(Horizontal) 및 트리거"),
            InputParameterSpec("trig_source", "트리거 소스 (Trigger Source)", "choice", "CH1", choices=["CH1", "CH2", "CH3", "CH4", "LINE", "AUX"], tooltip="TRIGger:A:EDGE:SOUrce", group="2. 수평축(Horizontal) 및 트리거"),
            InputParameterSpec("trig_level", "트리거 레벨 (Trigger Level)", "float", 0.0, unit="V", min_val=-500.0, max_val=500.0, tooltip="TRIGger:A:LEVel", group="2. 수평축(Horizontal) 및 트리거"),
            InputParameterSpec("trig_slope", "트리거 슬로프 (Trigger Slope)", "choice", "RISe", choices=["RISe", "FALL", "EITHer"], tooltip="TRIGger:A:EDGE:SLOpe", group="2. 수평축(Horizontal) 및 트리거"),
            InputParameterSpec("acq_mode", "획득 모드 (Acquisition Mode)", "choice", "SAMple", choices=["SAMple", "PEAKdetect", "HIRes", "AVErage"], tooltip="ACQuire:MODe", group="3. 파형 획득 옵션"),
            InputParameterSpec("use_autoset", "시작 시 Autoset 실행 여부", "bool", False, tooltip="AUTOSet EXECUTE (체크 시 수동 스케일 대신 자동 스케일 조정)", group="3. 파형 획득 옵션"),
            InputParameterSpec("record_pts", "파형 전송 포인트 수 (Curve Points)", "int", 1000, unit="pts", min_val=100, max_val=10000, tooltip="DATa:STARt 1; DATa:STOP <N>", group="3. 파형 획득 옵션"),
            InputParameterSpec("poll_interval_s", "파형/측정 갱신 주기", "float", 0.5, unit="s", min_val=0.1, max_val=60.0, group="3. 파형 획득 옵션"),
        ],
        measurable_items=[
            MeasurableItemSpec("wfm_curve", "실시간 파형 데이터 (Waveform CURVe? & Preamble)", "V(t)", "WFMOutpre?; CURVe?", True, "Y = YZERO + YMULT * (data - YOFF) 공식으로 환산된 전압 파형"),
            MeasurableItemSpec("meas_freq", "주파수 (Frequency)", "Hz", "MEASUrement:IMMed:TYPe FREQuency", True, "신호 주파수 자동 측정"),
            MeasurableItemSpec("meas_period", "주기 (Period)", "s", "MEASUrement:IMMed:TYPe PERIod", True, "신호 주기 자동 측정"),
            MeasurableItemSpec("meas_pk2pk", "최대-최소 진폭 (Peak-to-Peak)", "Vpp", "MEASUrement:IMMed:TYPe PK2Pk", True, "파형의 Peak-to-Peak 전압"),
            MeasurableItemSpec("meas_mean", "평균 전압 (Mean Voltage)", "V", "MEASUrement:IMMed:TYPe MEAN", True, "파형의 산술 평균 전압"),
            MeasurableItemSpec("meas_rms", "실효값 전압 (RMS Voltage)", "Vrms", "MEASUrement:IMMed:TYPe CRMs / RMS", True, "파형의 주기 RMS 전압"),
            MeasurableItemSpec("meas_max", "최대 전압 (Maximum)", "V", "MEASUrement:IMMed:TYPe MAXImum", False, "파형의 최대 피크 전압"),
            MeasurableItemSpec("meas_min", "최소 전압 (Minimum)", "V", "MEASUrement:IMMed:TYPe MINImum", False, "파형의 최소 피크 전압"),
        ],
    ),

    "05_SPECTRUM": CategoryProfile(
        folder_id="05_SPECTRUM",
        folder_name="05. Spectrum Analyzers",
        title_ko="05. Spectrum Analyzers (SignalVu / USB 실시간 스펙트럼 애널라이저)",
        icon_text="📡",
        description="Tektronix RSA300/500/600 USB 스펙트럼 애널라이저 및 SignalVu-PC / RSA5000/6000 스펙트럼 트레이스 및 마커 피크 분석",
        has_power_output=False,
        graph_modes=["실시간 RF 스펙트럼 트레이스 (Amplitude dBm vs Frequency MHz)", "피크 주파수 및 피크 파워 시계열 트렌드"],
        models=[
            ModelProfile(
                model_id="SIGNALVU_PC_RSA",
                display_name="SignalVu-PC & RSA300 / RSA500 / RSA600 USB Spectrum Analyzers",
                manual_file="05. Spectrum Analyzers/Programming_Appnote_37W-61459-0.pdf",
                protocol="SCPI",
                interfaces=["Local/Remote TekVISA VXI-11 (TCPIP0::127.0.0.1::INSTR)", "Socket Server"],
                max_channels=1,
                specs_summary="9kHz~7.5GHz, 40MHz 실시간 대역폭, SignalVu-PC PI(SCPI)를 통한 스펙트럼/DPX/변조 분석",
                remote_notes=[
                    "USB RSA(RSA306B/500A/600A)를 SCPI로 제어하려면 먼저 PC에서 SignalVu-PC 소프트웨어를 실행하고 장비와 Connect 해야 합니다!",
                    "SignalVu-PC와 TekVISA가 설치된 상태에서 로컬 주소 'TCPIP0::127.0.0.1::INSTR' (또는 원격 NUC PC의 IP)로 접속합니다.",
                    "SignalVu-PC에서 명령을 보낼 측정 뷰(예: Spectrum 뷰)가 화면에 활성화되어 있지 않으면 실행 에러가 발생하므로 'DISPlay:GENeral:MEASview:NEW SPECtrum'으로 뷰를 활성화합니다.",
                ],
            ),
            ModelProfile(
                model_id="RSA5000_6000_BENCH",
                display_name="SignalVu Benchtop RSA Series (RSA5000 / RSA6100B)",
                manual_file="05. Spectrum Analyzers/SignalVu-Programmer-Manual_EN-US_077-0223-10_077022310.pdf",
                protocol="SCPI",
                interfaces=["LAN (TCPIP / VXI-11)", "USB"],
                max_channels=1,
                specs_summary="벤치탑 실시간 스펙트럼 애널라이저, SignalVu 내장 SCPI 프로그래밍 인터페이스",
                remote_notes=[
                    "LAN 포트 연결 후 TekVISA VXI-11 또는 Socket 주소로 연결",
                    "과입력 방지를 위해 RF 입력 신호 인가 전 Reference Level과 감쇠기(Attenuator) 설정 필수",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="rsa_signalvu_run",
                title="[1단계: SignalVu-PC 실행 (USB RSA 필독)] PC에서 SignalVu-PC를 먼저 켜고 USB 스펙트럼 장비와 Connect",
                description="RSA306B/500A/600A 같은 USB 스펙트럼 애널라이저는 장비 자체에 SCPI 서버가 없고 'SignalVu-PC' 프로그램이 명령을 중계합니다.",
                how_to_steps=[
                    "1. [USB형 RSA306B/500/600 사용 시] 파란색 USB 3.0 케이블로 장비와 PC의 USB 3.0 포트를 연결합니다.",
                    "2. PC 바탕화면에서 먼저 **SignalVu-PC** 프로그램과 **TekVISA**를 실행합니다.",
                    "3. SignalVu-PC 상단 메뉴에서 [Live Link] > [Connect to Instrument]를 눌러 하드웨어와 연결(초록색 Live 표시)합니다.",
                    "4. 본 퀵스타트 프로그램 상단 VISA 리소스에서 `TCPIP0::127.0.0.1::INSTR` (현재 PC 내부의 SignalVu-PC 접속 주소)를 선택하고 우측 버튼으로 연결을 확인하세요.",
                    "5. [벤치탑 RSA5000/6000 사용 시] 장비에 내장된 SignalVu가 실행 중이므로 장비의 LAN IP 주소(`TCPIP0::<IP>::INSTR`)로 바로 연결하면 됩니다.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: SignalVu / RSA 통신(*IDN?) 확인",
                expected_hint="TEKTRONIX,RSA... 및 SignalVu-PC 버전 정보 반환",
            ),
            ChecklistItem(
                id="rsa_measview",
                title="[2단계: 측정 뷰(Spectrum View) 준비] SignalVu 화면에 Spectrum 창 활성화 및 에러 점검",
                description="매뉴얼 필독 사항: SignalVu 화면에 열려 있지 않은 측정 뷰의 명령을 보내면 Execution Error가 발생합니다.",
                how_to_steps=[
                    "1. 본 프로그램은 측정 시작 시 자동으로 `DISPlay:GENeral:MEASview:NEW SPECtrum` 명령을 보내 Spectrum 화면을 띄워줍니다.",
                    "2. 우측 버튼을 눌러 현재 SignalVu에 설치된 분석 옵션(*OPT?)이 정상 조회되는지 확인하세요.",
                ],
                verify_cmd="*OPT?",
                verify_label="🔍 2단계: 설치된 분석 옵션(*OPT?) 조회",
                expected_hint="장비/소프트웨어 옵션 목록 반환",
            ),
            ChecklistItem(
                id="rsa_ref_level",
                title="[3단계: RF 입력 보호 점검] 안테나 또는 RF 케이블 연결 전 최대 입력 파워(dBm) 및 Reference Level 확인",
                description="RF Input 단자에 허용치(보통 +20~+30dBm)를 넘는 고출력을 직접 넣으면 수신부가 손상됩니다.",
                how_to_steps=[
                    "1. 측정하려는 RF 신호의 예상 출력(dBm)을 확인하고, 고출력 송신기라면 반드시 RF 감쇠기(Attenuator)를 끼운 뒤 RF Input 커넥터에 연결하세요.",
                    "2. 좌측 입력창의 '기준 레벨(Reference Level)'을 입력 신호의 최대 파워보다 약간 높게(예: 0 dBm) 설정하세요.",
                    "3. 우측 버튼으로 이벤트 레지스터(*ESR?)가 정상(0)인지 확인합니다.",
                ],
                verify_cmd="*ESR?",
                verify_label="🔍 3단계: 상태 레지스터(*ESR?) 정상 확인",
                expected_hint="0 반환 시 에러 없음",
            ),
        ],
        input_parameters=[
            InputParameterSpec("center_freq_mhz", "중심 주파수 (Center Frequency)", "float", 1000.0, unit="MHz", min_val=0.009, max_val=26500.0, tooltip="SENSe:SPECtrum:FREQuency:CENTer", group="1. 주파수(Frequency) 설정"),
            InputParameterSpec("span_mhz", "주파수 스팬 (Span)", "float", 40.0, unit="MHz", min_val=0.001, max_val=10000.0, tooltip="SENSe:SPECtrum:FREQuency:SPAN", group="1. 주파수(Frequency) 설정"),
            InputParameterSpec("ref_level_dbm", "기준 레벨 (Reference Level)", "float", 0.0, unit="dBm", min_val=-130.0, max_val=30.0, tooltip="INPut:MLEVel", group="2. 진폭 및 대역폭(RBW) 설정"),
            InputParameterSpec("rbw_auto", "분해능 대역폭 자동 설정 (RBW Auto)", "bool", True, tooltip="SENSe:SPECtrum:BANDwidth:RESolution:AUTO", group="2. 진폭 및 대역폭(RBW) 설정"),
            InputParameterSpec("rbw_khz", "수동 RBW (Manual RBW)", "float", 100.0, unit="kHz", min_val=0.001, max_val=10000.0, tooltip="SENSe:SPECtrum:BANDwidth:RESolution (RBW Auto 해제 시)", group="2. 진폭 및 대역폭(RBW) 설정"),
            InputParameterSpec("trace_func", "트레이스 처리 모드 (Trace Function)", "choice", "NORMal", choices=["NORMal", "AVERage", "MAXHold", "MINHold"], tooltip="TRACe1:SPECtrum:FUNCtion", group="3. 트레이스 및 획득 설정"),
            InputParameterSpec("trace_points", "트레이스 포인트 수 (Trace Points)", "choice", "801", choices=["801", "1601", "2401", "4001"], tooltip="SENSe:SPECtrum:POINts:COUNt", group="3. 트레이스 및 획득 설정"),
            InputParameterSpec("poll_interval_s", "스펙트럼 갱신 주기", "float", 0.4, unit="s", min_val=0.1, max_val=60.0, group="3. 트레이스 및 획득 설정"),
        ],
        measurable_items=[
            MeasurableItemSpec("spec_trace", "스펙트럼 트레이스 데이터 (Spectrum Trace1)", "dBm(f)", "READ:SPECtrum:TRACe1? / FETCh:SPECtrum:TRACe1?", True, "설정된 주파수 Span 구간의 스펙트럼 파워 배열 (IEEE 488.2 Float Binary 또는 ASCII)"),
            MeasurableItemSpec("peak_freq_mhz", "마커 최대 피크 주파수 (Peak Frequency)", "MHz", "CALCulate:SPECtrum:MARKer1:MAXimum; :CALC:SPEC:MARK1:X?", True, "스펙트럼 내 최대 피크 신호의 주파수 (MHz)"),
            MeasurableItemSpec("peak_amp_dbm", "마커 최대 피크 파워 (Peak Amplitude)", "dBm", "CALCulate:SPECtrum:MARKer1:Y?", True, "스펙트럼 내 최대 피크 신호의 전력 레벨 (dBm)"),
            MeasurableItemSpec("noise_floor_dbm", "평균 노이즈 플로어 (Noise Floor Est.)", "dBm", "Trace Median / Mean", True, "스펙트럼 트레이스의 평균 기저 노이즈 레벨"),
            MeasurableItemSpec("ch_power_dbm", "대역 통합 파워 (Integrated Band Power)", "dBm", "Integrated Trace Power", True, "현재 Span 내 총 통합 RF 전력"),
        ],
    ),

    "06_SMU": CategoryProfile(
        folder_id="06_SMU",
        folder_name="06. SMUs",
        title_ko="06. SMUs (Keithley SourceMeter® 2400 / 2600B 시리즈)",
        icon_text="🔬",
        description="Keithley 2450/2460/2461/2470 (Touchscreen SCPI/TSP) 및 2600B/2601B-PULSE/2606B/2651A (System TSP) 정밀 소스-측정 및 I-V 스윕",
        has_power_output=True,
        graph_modes=["I-V 특성 곡선 및 전력 곡선 (Current & Power vs Voltage)", "실시간 V / I / R / P 시계열 트렌드"],
        models=[
            ModelProfile(
                model_id="SMU_2450",
                display_name="Model 2450 SourceMeter (200V, 1A, 20W)",
                manual_file="06. SMUs/2450-901-01E_Sept_2019_Ref.pdf",
                protocol="DUAL_SCPI_TSP",
                interfaces=["USB (USBTMC)", "LAN (VXI-11 / Socket)", "GPIB"],
                max_channels=1,
                specs_summary="200V / 1A / 20W 범용 터치스크린 SMU, SCPI(기본값) 및 TSP 명령셋 모두 지원 (*LANG? 쿼리로 자동 감지)",
                remote_notes=[
                    "장비의 현재 명령셋(MENU > System > Settings > Command Set)이 SCPI인지 TSP인지 '*LANG?' 쿼리로 자동 확인합니다.",
                    "전원 ON/OFF 전에는 과도 전압으로부터 보호하기 위해 반드시 DUT 연결을 분리하세요.",
                ],
            ),
            ModelProfile(
                model_id="SMU_2460",
                display_name="Model 2460 High-Current SourceMeter (100V, 7A DC / 7A Pulse, 100W)",
                manual_file="06. SMUs/2460-901-01C_Sept_2019_Ref.pdf",
                protocol="DUAL_SCPI_TSP",
                interfaces=["USB (USBTMC)", "LAN", "GPIB"],
                max_channels=1,
                specs_summary="100V / 7A 대전류 터치스크린 SMU, SCPI 및 TSP 듀얼 지원",
                remote_notes=[
                    "대전류(최대 7A) 측정 시 리드 저항 오차를 제거하기 위해 4-Wire(Remote Sense) 결선 권장",
                ],
            ),
            ModelProfile(
                model_id="SMU_2461",
                display_name="Model 2461 High-Current Pulse SourceMeter (100V, 7A DC / 10A Pulse)",
                manual_file="06. SMUs/2461-901-01B_Sept_2019_Ref.pdf",
                protocol="DUAL_SCPI_TSP",
                interfaces=["USB (USBTMC)", "LAN", "GPIB"],
                max_channels=1,
                specs_summary="100V / 7A DC (10A/100V 펄스), 듀얼 1MS/s 디지타이저 내장, SCPI 및 TSP 지원",
                remote_notes=[
                    "SCPI 및 TSP 명령셋을 모두 지원하며 *LANG? 으로 현재 모드를 자동 판별합니다.",
                ],
            ),
            ModelProfile(
                model_id="SMU_2470",
                display_name="Model 2470 High-Voltage SourceMeter (1100V, 1A, 20W)",
                manual_file="06. SMUs/2470-901-01D_Oct_2024_Ref.pdf",
                protocol="DUAL_SCPI_TSP",
                interfaces=["USB (USBTMC)", "LAN", "GPIB"],
                max_channels=1,
                specs_summary="1100V 고전압 SourceMeter, 후면 안전 인터록(Safety Interlock) 필수",
                remote_notes=[
                    "[안전 경고] ±42V 초과 고전압 출력 시 반드시 후면 패널 Safety Interlock 회로가 체결(전면 녹색 INTERLOCK LED 점등)되어야 합니다!",
                    "LO 단자와 보호 접지(Safety Ground)는 내부적으로 분리되어 있으므로 안전을 위해 사용하는 패널(전면/후면)의 LO 단자를 섀시 접지에 연결하세요.",
                ],
            ),
            ModelProfile(
                model_id="SMU_2600B",
                display_name="Series 2600B System SourceMeter (2601B/2602B/2611B/2612B/2635B/2636B)",
                manual_file="06. SMUs/2600BS-901-01F_2600B_Reference_Aug2021.pdf",
                protocol="TSP",
                interfaces=["USB (USBTMC)", "LAN (VXI-11 / Raw Socket)", "GPIB", "RS-232"],
                max_channels=2,
                specs_summary="1채널/2채널(smua, smub) 시스템 SMU, Lua 기반 TSP 전용 명령셋 사용",
                remote_notes=[
                    "2600B 시리즈는 TSP(smua.source.*, smua.measure.*) 명령어를 사용합니다.",
                    "한 번에 하나의 원격 인터페이스만 제어권을 가집니다.",
                ],
            ),
            ModelProfile(
                model_id="SMU_2601B_PULSE",
                display_name="Model 2601B-PULSE System SourceMeter (10A/10V Pulser + 40V/1A DC SMU)",
                manual_file="06. SMUs/2601B-PULSE-901-01B_Nov2021_Ref.pdf",
                protocol="TSP",
                interfaces=["USB (USBTMC)", "LAN", "GPIB"],
                max_channels=1,
                specs_summary="10A @ 10V 고속 펄서(10μs~500μs) + DC SMU 통합 모델, TSP 전용",
                remote_notes=[
                    "[중요] 일반 DC SMU 기능으로 동작시키려면 반드시 먼저 펄서를 비활성화('smua.pulser.enable = smua.DISABLE') 해야 합니다!",
                ],
            ),
            ModelProfile(
                model_id="SMU_2606B",
                display_name="Model 2606B High-Density 4-Channel System SMU (20V, 3A × 4CH)",
                manual_file="06. SMUs/2606B-901-01C_Nov_2021_Reference.pdf",
                protocol="TSP",
                interfaces=["USB (USBTMC)", "LAN"],
                max_channels=4,
                specs_summary="1U 랙마운트 고밀도 4채널 SMU, 전면 USB Type-B 및 LAN 지원, TSP 전용",
                remote_notes=[
                    "전면 패널이 없는 1U 폼팩터이므로 LAN 웹 인터페이스(Virtual Front Panel) 또는 USB/LAN TSP 명령으로 제어합니다.",
                ],
            ),
            ModelProfile(
                model_id="SMU_2651A",
                display_name="Model 2651A High-Power System SourceMeter (40V, 50A Pulse / 20A DC)",
                manual_file="06. SMUs/2651A-901-01C_Oct_2021_Ref.pdf",
                protocol="TSP",
                interfaces=["LAN", "GPIB", "RS-232"],
                max_channels=1,
                specs_summary="최대 2000W 고전력(50A 펄스 / 20A DC) 시스템 SMU, TSP 전용",
                remote_notes=[
                    "고전력 출력 시 후면 Interlock 체결 및 전용 고전류 트라이액셜/포스-센스 케이블 결선 상태를 반드시 확인하세요.",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="smu_cmd_set",
                title="[1단계: 케이블 연결 및 명령어 모드(*LANG?) 확인] USB/LAN 연결 및 SCPI vs TSP 모드 자동 진단",
                description="2450/2460/2461/2470은 SCPI와 TSP를 모두 지원하며, 2600B/2601B-PULSE/2606B/2651A는 TSP 전용입니다.",
                how_to_steps=[
                    "1. [케이블 연결] 측정 대상(DUT)을 분리한 상태에서 SMU 후면(2606B는 전면)의 USB Type-B 또는 LAN 포트를 PC와 연결하고 전원을 켭니다.",
                    "2. [2450/2460/2461/2470 주소 확인 방법] 전면 [MENU] 키 > System 아래의 [Communication] 터치 > [USB] 또는 [LAN] 탭을 누르면 화면에 VISA 주소와 IP가 표시됩니다.",
                    "3. [명령어 세트 확인] 전면 [MENU] 키 > System 아래의 [Settings] > [Command Set]에서 현재 모드를 볼 수 있으며, 본 프로그램은 좌측 '명령어 프로토콜'을 'AUTO'로 두면 `*LANG?` 명령으로 SCPI인지 TSP인지 자동 감지하여 맞춰줍니다!",
                    "4. 우측 버튼을 눌러 장비 식별 정보(*IDN?)가 정상 응답하는지 확인하세요.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: SMU 연결 및 *IDN? 확인",
                expected_hint="KEITHLEY INSTRUMENTS, MODEL 24xx / 26xx 응답 반환",
            ),
            ChecklistItem(
                id="smu_interlock",
                title="[2단계: 명령어 언어 감지 & 고전압 안전 인터록] *LANG? 확인 및 ±42V 초과 시 후면 Interlock 체결",
                description="2470 / 2600B / 2651A 등에서 ±42V 이상의 고전압을 출력하려면 후면 녹색 Safety Interlock 커넥터가 닫혀 있어야 합니다.",
                how_to_steps=[
                    "1. ±42V 이하의 일반 저전압 테스트라면 인터록 없이도 안전하게 동작합니다.",
                    "2. ±42V를 초과하는 고전압 테스트 시: 테스트 지그(Test Fixture) 뚜껑이 닫힐 때 후면 Interlock 핀이 단락되도록 연결하고, 전면 패널의 녹색 [INTERLOCK] 표시등이 켜졌는지 확인하세요.",
                    "3. 우측 [🔍 현재 명령어 모드(*LANG?) 조회] 버튼을 눌러 현재 장비의 명령 언어(SCPI 또는 TSP)를 확인합니다.",
                ],
                verify_cmd="*LANG?",
                verify_label="🔍 2단계: 명령어 세트(*LANG?) 자동 조회",
                expected_hint="SCPI 또는 TSP 반환 (2600B 시리즈는 TSP 전용)",
            ),
            ChecklistItem(
                id="smu_terminals",
                title="[3단계: 단자 위치(Front/Rear) 및 2-Wire vs 4-Wire 배선 확인] 바나나잭(전면) 또는 트라이액셜(후면) 결선",
                description="4-Wire(원격 센싱)를 선택했는데 Sense HI/LO 선을 연결하지 않으면 전압 피드백이 안 되어 과전압이 걸릴 수 있으므로 주의하세요!",
                how_to_steps=[
                    "1. 장비 전면의 바나나 잭(INPUT/OUTPUT HI, LO)에 연결했다면 좌측 입력창의 '입출력 단자'를 반드시 [FRONt (전면 단자)]로 선택하세요. 후면 단자에 연결했다면 [REAR]로 선택합니다.",
                    "2. [2-Wire 결선 - 초보자 기본] Force HI(빨강)와 Force LO(검정) 2가닥만 측정 소자(저항/다이오드 등) 양단에 연결하고 좌측 '센싱 결선 방식'을 [2-Wire (Local Sense)]로 둡니다.",
                    "3. [4-Wire 결선 - 정밀 저저항 측정] Force HI/LO 외에 Sense HI/LO 2가닥을 소자 양단에 추가로 총 4가닥 연결했을 때만 [4-Wire (Remote Sense)]를 선택하세요.",
                ],
                verify_cmd="*ESR?",
                verify_label="🔍 3단계: SMU 상태 레지스터(*ESR?) 확인",
                expected_hint="0 반환 시 정상 대기 중",
            ),
            ChecklistItem(
                id="smu_pulser",
                title="[4단계: 컴플라이언스(제한값) 및 2601B-PULSE 점검] 소자 보호용 제한 전류/전압(Compliance) 확인",
                description="전압을 인가할 때는 최대 허용 전류(Limit I)를, 전류를 인가할 때는 최대 허용 전압(Limit V)을 소자 정격 이하로 설정해야 합니다.",
                how_to_steps=[
                    "1. 좌측 입력창의 '컴플라이언스 제한(Compliance Limit)' 값이 측정할 소자(DUT)가 견딜 수 있는 최대 전류(A) 또는 전압(V) 이하로 안전하게 설정되었는지 확인하세요.",
                    "2. [2601B-PULSE 모델인 경우] 본 프로그램이 측정 시작 시 자동으로 펄서 비활성화(`smua.pulser.enable = smua.DISABLE`) 명령을 전송하여 안전하게 DC SMU 모드로 초기화합니다.",
                ],
                verify_cmd="*STB?",
                verify_label="🔍 4단계: 출력 전 최종 응답(*STB?) 확인",
                expected_hint="상태 바이트 정상 반환 시 측정 시작 준비 완료",
            ),
        ],
        input_parameters=[
            InputParameterSpec("smu_channel", "SMU 채널 (2600B Series)", "choice", "smua (Channel A / 24xx Single)", choices=["smua (Channel A / 24xx Single)", "smub (Channel B - 2602B/2612B/2636B)"], group="1. 채널 및 명령 모드"),
            InputParameterSpec("cmd_lang", "명령어 프로토콜 (Command Language)", "choice", "AUTO (*LANG? 자동 감지)", choices=["AUTO (*LANG? 자동 감지)", "SCPI (2450/2460/2461/2470)", "TSP (2600B / 24xx TSP Mode)"], group="1. 채널 및 명령 모드"),
            InputParameterSpec("terminals", "입출력 단자 (Terminals - 24xx)", "choice", "FRONt (전면 단자)", choices=["FRONt (전면 단자)", "REAR (후면 단자)"], tooltip=":ROUTe:TERMinals FRONt|REAR", group="1. 채널 및 명령 모드"),
            InputParameterSpec("sense_wire", "센싱 결선 방식 (Sense Mode)", "choice", "2-Wire (Local Sense)", choices=["2-Wire (Local Sense)", "4-Wire (Remote Sense)"], tooltip="smu.sense / :SENSe:REMOTE", group="1. 채널 및 명령 모드"),
            InputParameterSpec("op_mode", "동작 모드 (Operation Mode)", "choice", "Continuous DC Source-Measure", choices=["Continuous DC Source-Measure", "I-V Linear Staircase Sweep (스윕)", "Resistance Measurement (옴 측정 모드)"], group="2. 소스 및 스윕 파라미터"),
            InputParameterSpec("source_func", "소스 기능 (Source Function)", "choice", "Voltage Source (SVMI)", choices=["Voltage Source (SVMI)", "Current Source (SIMV)"], group="2. 소스 및 스윕 파라미터"),
            InputParameterSpec("source_level", "소스 출력값 / 스윕 시작값 (Level / Start)", "float", 1.0, unit="V or A", min_val=-1100.0, max_val=1100.0, group="2. 소스 및 스윕 파라미터"),
            InputParameterSpec("sweep_stop", "스윕 종료값 (Sweep Stop)", "float", 5.0, unit="V or A", min_val=-1100.0, max_val=1100.0, group="2. 소스 및 스윕 파라미터"),
            InputParameterSpec("sweep_points", "스윕 포인트 수 (Sweep Points)", "int", 21, unit="pts", min_val=2, max_val=500, group="2. 소스 및 스윕 파라미터"),
            InputParameterSpec("compliance_limit", "컴플라이언스 제한 (Compliance Limit I or V)", "float", 0.05, unit="A or V", min_val=1e-9, max_val=1100.0, tooltip="SOURce:VOLT:ILIM / smua.source.limiti", group="3. 컴플라이언스 및 측정 정확도"),
            InputParameterSpec("nplc", "적분 시간 (NPLC Speed)", "float", 1.0, unit="PLC", min_val=0.01, max_val=10.0, tooltip="SENSe:NPLCycles / smua.measure.nplc", group="3. 컴플라이언스 및 측정 정확도"),
            InputParameterSpec("high_cap", "고용량 부하 모드 (High-Capacitance Mode)", "bool", False, tooltip="부하 커패시턴스가 큰 경우 발진 방지", group="3. 컴플라이언스 및 측정 정확도"),
            InputParameterSpec("poll_interval_s", "측정 주기 / 스텝 간격", "float", 0.2, unit="s", min_val=0.02, max_val=60.0, group="3. 컴플라이언스 및 측정 정확도"),
        ],
        measurable_items=[
            MeasurableItemSpec("meas_v", "측정 전압 (Measured Voltage)", "V", ":MEAS:VOLT? / smua.measure.v()", True, "SMU에서 측정된 정밀 DC 전압"),
            MeasurableItemSpec("meas_i", "측정 전류 (Measured Current)", "A", ":MEAS:CURR? / smua.measure.i()", True, "SMU에서 측정된 정밀 DC 전류"),
            MeasurableItemSpec("meas_r", "측정 저항 (Measured Resistance)", "Ω", ":MEAS:RES? / smua.measure.r()", True, "V/I 기반 정밀 저항 측정값"),
            MeasurableItemSpec("meas_p", "측정 전력 (Measured Power)", "W", "smua.measure.p() / V*I", True, "소비/공급 전력 계산값 (W)"),
            MeasurableItemSpec("compliance_state", "컴플라이언스 제한 도달 (Compliance Tripped)", "Bool", "smua.source.compliance / STAT:OPER?", True, "설정된 전류/전압 제한(Compliance) 도달 여부"),
        ],
    ),

    "07_TEK_VISA": CategoryProfile(
        folder_id="07_TEK_VISA",
        folder_name="08. Tek VISA",
        title_ko="08. Tek VISA (OpenChoice Talker/Listener & 리소스 매니저)",
        icon_text="🔌",
        description="TekVISA 리소스 검색(viFindRsrc), 연결 속성 진단, OpenChoice Talker/Listener 대화형 명령 송수신 및 반복 루프 로깅",
        has_power_output=False,
        graph_modes=["쿼리 응답 수치 실시간 로깅 그래프 (Numeric Query Value vs Time)", "명령어 응답 지연시간(Latency ms) 모니터링 그래프"],
        models=[
            ModelProfile(
                model_id="TEKVISA_TALKER_LISTENER",
                display_name="TekVISA OpenChoice Talker/Listener & VISA v3.0 Engine",
                manual_file="07. Tek VISA/TekVISA_OpenChoice_Talker_Listener_EN_US_077178600.pdf",
                protocol="VISA_API",
                interfaces=["USB (USB?*INSTR)", "LAN (TCPIP?*INSTR / SOCKET)", "Serial (ASRL?*INSTR)", "GPIB (GPIB?*INSTR)"],
                max_channels=1,
                specs_summary="VISA 리소스 검색, Write / Read / Query 단일 실행, 스크립트 Step/Loop 반복 실행 및 응답 시간/데이터 로깅",
                remote_notes=[
                    "TekVISA 또는 NI-VISA(64-bit VISA Shared Components) 또는 PyVISA-py 백엔드를 통해 모든 USB/LAN 장비와 통신합니다.",
                    "Talker/Listener의 Loop 기능을 활용하여 임의의 SCPI/TSP 쿼리(예: *IDN?, :MEAS:VOLT?, print(smua.measure.v()))를 주기적으로 전송하고 그래프와 엑셀로 저장할 수 있습니다.",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="visa_runtime",
                title="[1단계: VISA 드라이버 확인] PC 내 TekVISA / NI-VISA 또는 내장 PyVISA-py 엔진 로드 확인",
                description="USB(USBTMC)로 실제 장비를 인식하려면 TekVISA 또는 NI-VISA 드라이버가 설치되어 있어야 하며, LAN 소켓/가상 모드는 즉시 동작합니다.",
                how_to_steps=[
                    "1. 상단 바 또는 사전 준비 점검표의 '감지된 VISA 엔진'에 System VISA 또는 PyVISA-py가 표시되는지 확인합니다.",
                    "2. 실제 USB 장비를 꽂았는데 목록에 안 뜬다면 Tektronix 홈페이지(tek.com/downloads)에서 'TekVISA' 또는 'Keithley I/O Layer(NI-VISA 포함)'를 설치하세요.",
                    "3. 우측 버튼을 눌러 현재 선택된 리소스와 기본 통신(*IDN?)이 되는지 테스트합니다.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: VISA 세션 & *IDN? 테스트",
                expected_hint="현재 연결된 장비(또는 가상 장비)의 *IDN? 문자열 반환",
            ),
            ChecklistItem(
                id="visa_term_char",
                title="[2단계: 종료 문자 및 타임아웃] Termination Character(LF \\n) 및 타임아웃(5000ms) 설정 확인",
                description="Tektronix 및 Keithley 장비는 명령어 끝에 줄바꿈 문자(Line Feed, \\n)가 있어야 명령을 인식합니다.",
                how_to_steps=[
                    "1. 좌측 입력창의 '수신 종료 문자'와 '송신 종료 문자'가 기본값인 `LF (\\n)`으로 되어 있는지 확인합니다.",
                    "2. 우측 버튼을 눌러 에러 큐(*ESR?) 쿼리가 타임아웃 없이 즉시 응답하는지 확인하세요.",
                ],
                verify_cmd="*ESR?",
                verify_label="🔍 2단계: 종료문자 & 쿼리 응답(*ESR?) 확인",
                expected_hint="타임아웃 없이 0 반환 시 종료문자 일치",
            ),
            ChecklistItem(
                id="visa_rsrc_syntax",
                title="[3단계: 주소 형식 확인] USB(`USB0::...::INSTR`), LAN(`TCPIP0::<IP>::INSTR` 또는 `::SOCKET`), COM(`ASRLx::INSTR`)",
                description="장비 연결 방식에 맞는 올바른 VISA 주소 형식이 선택되었는지 확인합니다.",
                how_to_steps=[
                    "1. USB 연결: `USB0::0x0699::<모델코드>::<시리얼>::INSTR` (Tektronix: 0x0699, Keithley: 0x05e6)",
                    "2. LAN VXI-11 연결: `TCPIP0::192.168.1.100::inst0::INSTR`",
                    "3. LAN Raw Socket 연결: `TCPIP0::192.168.1.100::5025::SOCKET` (2260B는 포트 `2268`, 스코프는 보통 `4000`)",
                    "4. 우측 버튼을 눌러 상태 바이트(*STB?)를 읽고 통신 지연을 점검하세요.",
                ],
                verify_cmd="*STB?",
                verify_label="🔍 3단계: 상태 바이트(*STB?) 통신 확인",
                expected_hint="16 등 정수 상태 바이트 즉시 반환",
            ),
        ],
        input_parameters=[
            InputParameterSpec("query_cmd", "반복 실행할 SCPI/TSP 쿼리 또는 스크립트", "string", "*ESR?; :MEASure:VOLTage:DC?", tooltip="측정 시작 시 주기적으로 Query할 명령어 (세미콜론 또는 줄바꿈 구분)", group="1. Talker/Listener 루프 명령 설정"),
            InputParameterSpec("init_cmd", "시작 시 1회 초기화 명령 (Optional)", "string", "*CLS", tooltip="측정 시작 직후 1회만 Write할 명령어", group="1. Talker/Listener 루프 명령 설정"),
            InputParameterSpec("stop_cmd", "정지 시 1회 종료 명령 (Optional)", "string", "", tooltip="완전 정지 시 1회 전송할 안전 명령어", group="1. Talker/Listener 루프 명령 설정"),
            InputParameterSpec("read_termination", "수신 종료 문자 (Read Termination)", "choice", "LF (\\n)", choices=["LF (\\n)", "CRLF (\\r\\n)", "CR (\\r)"], group="2. VISA 세션 속성 (Attributes)"),
            InputParameterSpec("write_termination", "송신 종료 문자 (Write Termination)", "choice", "LF (\\n)", choices=["LF (\\n)", "CRLF (\\r\\n)", "CR (\\r)"], group="2. VISA 세션 속성 (Attributes)"),
            InputParameterSpec("timeout_ms", "통신 타임아웃 (VI_ATTR_TMO_VALUE)", "int", 5000, unit="ms", min_val=100, max_val=60000, group="2. VISA 세션 속성 (Attributes)"),
            InputParameterSpec("poll_interval_s", "Talker/Listener Loop 주기", "float", 0.5, unit="s", min_val=0.05, max_val=60.0, group="2. VISA 세션 속성 (Attributes)"),
        ],
        measurable_items=[
            MeasurableItemSpec("parsed_val_1", "응답 수치 데이터 #1 (Parsed Numeric 1)", "Value", "Query Response #1", True, "쿼리 응답 문자열에서 추출된 첫 번째 실수값"),
            MeasurableItemSpec("parsed_val_2", "응답 수치 데이터 #2 (Parsed Numeric 2)", "Value", "Query Response #2", True, "다중 값 응답 시 두 번째 실수값"),
            MeasurableItemSpec("latency_ms", "통신 응답 시간 (Query Latency)", "ms", "Round-trip I/O Time", True, "명령 전송부터 응답 수신까지 걸린 시간 (ms)"),
            MeasurableItemSpec("raw_response", "원시 응답 문자열 (Raw Response String)", "Text", "viRead / query()", True, "장비가 반환한 전체 텍스트 응답"),
            MeasurableItemSpec("stb_val", "상태 바이트 레지스터 (*STB?)", "Byte", "*STB?", False, "IEEE 488.2 Status Byte 값"),
        ],
    ),

    # =========================================================================
    # 03. DMM (Digit Multimeter) (4 Reference / User Manuals)
    # =========================================================================
    "08_DMM": CategoryProfile(
        folder_id="08_DMM",
        folder_name="03. DMM",
        title_ko="03. DMM (Digit Multimeter - 정밀 디지털 멀티미터)",
        icon_text="📟",
        description="5½ ~ 7½ 디지트 고정밀 벤치/시스템 디지털 멀티미터 (DC/AC 전압·전류, 2선/4선 저항, 주파수, 온도 및 1MS/s 고속 디지타이저 파형 측정)",
        has_power_output=False,
        graph_modes=[
            "실시간 측정값 시계열 트렌드 그래프 (Time-Series Reading Trend)",
            "고속 디지타이저 / 리딩 버퍼 파형 그래프 (Digitizer / Buffer Waveform)",
        ],
        models=[
            ModelProfile(
                model_id="DMM6500",
                display_name="Model DMM6500 6½-Digit Bench/System Multimeter with Scanning (1 MS/s Digitizer)",
                manual_file="08. Digit Multimeter(DMM)/DMM6500-901-01C_April_2026_Ref.pdf",
                protocol="DUAL_SCPI_TSP",
                interfaces=["USB 2.0 (USBTMC)", "LAN (LXI / VXI-11 / Socket 5025)", "GPIB (Optional)", "TSP-Link"],
                max_channels=10,
                specs_summary="6½ 디지트, 15가지 측정 기능(DC/AC V·I, 2W/4W 저항, 온도, 커패시턴스), 1MS/s 16-bit 디지타이저, 10채널 스캐너 옵션, SCPI & TSP 지원",
                remote_notes=[
                    "전면 [MENU] > System > Settings > Command Set에서 SCPI와 TSP 모드를 전환할 수 있으며, 본 프로그램은 *LANG? 쿼리로 현재 명령어 모드를 자동 감지합니다.",
                    "전면/후면 입력 단자 선택은 장비 전면의 물리적 [INPUTS (Front/Rear)] 푸시 버튼으로 전환하며, `:ROUTe:TERMinals?` 명령으로 현재 스위치 상태를 확인할 수 있습니다.",
                ],
            ),
            ModelProfile(
                model_id="DMM7510",
                display_name="Model DMM7510 7½-Digit Graphical Sampling Multimeter (14 ppm DCV, 1 MS/s 18-bit)",
                manual_file="08. Digit Multimeter(DMM)/DMM7510-901-01C_Sept_2019_Ref.pdf",
                protocol="DUAL_SCPI_TSP",
                interfaces=["USB 2.0 (USBTMC)", "LAN (LXI / VXI-11 / Socket 5025)", "GPIB (IEEE-488)", "TSP-Link"],
                max_channels=1,
                specs_summary="7½ 디지트 표준급 정밀도(14ppm 1년 DCV 정확도), 100pV / 1fA / 10nΩ 초고분해능, 1MS/s 18-bit 고속 디지타이저, SCPI & TSP 지원",
                remote_notes=[
                    "초정밀 측정을 위해 AutoZero(AZERo ON) 및 Line Sync 활성화가 권장되며, 미세 저항 측정 시 Offset-Compensated Ohms를 지원합니다.",
                    "1MS/s 디지타이저 모드(DIGitize:VOLTage / CURRent)를 사용하면 오실로스코프처럼 과도 응답 파형을 캡처할 수 있습니다.",
                ],
            ),
            ModelProfile(
                model_id="DMM_2110",
                display_name="Model 2110 5½-Digit Dual-Display USB Multimeter (200 readings/s)",
                manual_file="08. Digit Multimeter(DMM)/2110-901-01(C-Aug2013)(Ref).pdf",
                protocol="SCPI",
                interfaces=["USB (USBTMC)", "GPIB (Optional 2110-GPIB)"],
                max_channels=1,
                specs_summary="5½ 디지트 듀얼 디스플레이, DC/AC 전압·전류, 2선/4선 저항, 주파수/주기, 커패시턴스, 열전대/RTD 온도 측정, 표준 SCPI 전용",
                remote_notes=[
                    "후면 USB Type-B 포트를 PC에 연결하면 표준 USBTMC 장비로 즉시 인식되며 `CONFigure:<func>`, `READ?`, `MEASure:<func>?` 표준 SCPI 명령으로 동작합니다.",
                ],
            ),
            ModelProfile(
                model_id="DMM_2010",
                display_name="Model 2010 7½-Digit Low-Noise Multimeter (Dry Circuit Ohms & 10-Ch Scanner)",
                manual_file="08. Digit Multimeter(DMM)/2010-900-01_F_August_2016.pdf",
                protocol="SCPI",
                interfaces=["GPIB (IEEE-488.2)", "RS-232 (Serial)"],
                max_channels=10,
                specs_summary="7½ 디지트 저잡음 멀티미터, 커넥터/릴레이 접촉 저항 측정용 Dry Circuit(20mV 클램프), Offset-Compensated Ohms, 10채널 스캐너 슬롯",
                remote_notes=[
                    "GPIB 또는 RS-232 인터페이스를 사용하며, 전면 [SHIFT] + [GPIB] 또는 [SHIFT] + [RS232] 버튼으로 통신 주소와 보드레이트를 확인합니다.",
                ],
            ),
        ],
        checklist=[
            ChecklistItem(
                id="dmm_conn_lang",
                title="[1단계: 케이블 연결 및 명령어 세트(*LANG?) 확인] USB/LAN/GPIB 연결 및 SCPI vs TSP 모드 자동 진단",
                description="DMM6500/DMM7510은 SCPI와 TSP를 모두 지원하며, Model 2110/2010은 표준 SCPI 명령어로 동작합니다.",
                how_to_steps=[
                    "1. [케이블 연결] DMM 후면의 USB Type-B 포트(또는 LAN / GPIB 포트)를 PC와 연결하고 전원을 켭니다.",
                    "2. [DMM6500 / DMM7510 주소 및 명령어 확인] 전면 [MENU] 키 > System > [Communication]에서 USB/LAN 주소를 확인하고, [Settings] > [Command Set]에서 현재 모드(SCPI 또는 TSP)를 확인합니다. (본 프로그램은 'AUTO' 선택 시 *LANG?으로 자동 감지합니다.)",
                    "3. [Model 2110 / 2010 확인] 2110은 USB 연결 시 자동 인식되며, 2010은 전면 [SHIFT] + [GPIB](또는 [RS232])를 눌러 통신 인터페이스가 활성화되어 있는지 확인합니다.",
                    "4. 우측 버튼을 눌러 장비 식별 정보(*IDN?)가 정상 응답하는지 확인하세요.",
                ],
                verify_cmd="*IDN?",
                verify_label="🔍 1단계: DMM 연결 및 *IDN? 확인",
                expected_hint="KEITHLEY INSTRUMENTS, MODEL DMM6500 / DMM7510 / 2110 / 2010 응답 반환",
            ),
            ChecklistItem(
                id="dmm_terminals",
                title="[2단계: 전면/후면 단자(INPUTS Front/Rear) 스위치 및 측정 단자 결선 확인] 전압/저항(HI/LO) vs 전류(AMPS) 구분",
                description="DMM의 전면/후면 단자 전환은 소프트웨어가 아니라 전면 패널의 물리적 [INPUTS (Front/Rear)] 버튼 스위치로 결정됩니다.",
                how_to_steps=[
                    "1. 장비 전면의 [INPUTS] 푸시 버튼(Front / Rear)이 현재 테스트 리드를 꽂은 위치(전면 바나나잭 사용 시 Front)로 눌려 있는지 확인하세요.",
                    "2. [전압 / 저항 / 주파수 / 커패시턴스 측정] 빨간색 리드를 `INPUT HI`, 검은색 리드를 `INPUT LO` 단자에 연결합니다.",
                    "3. [전류(DC/AC Current) 측정] 빨간색 리드를 전류 전용 `AMPS` 단자(DMM6500/7510/2010은 전면 3A 또는 후면 10A)에 연결하고 측정 회로와 직렬(Series)로 연결합니다.",
                    "4. 우측 버튼을 눌러 현재 장비의 활성 단자 위치(:ROUTe:TERMinals?)를 조회합니다.",
                ],
                verify_cmd=":ROUTe:TERMinals?",
                verify_label="🔍 2단계: 활성 단자(Front/Rear) 스위치 확인",
                expected_hint="FRON (전면 단자 활성) 또는 REAR (후면 단자 활성) 반환",
            ),
            ChecklistItem(
                id="dmm_4wire_safety",
                title="[3단계: 2선(2-Wire) vs 4선(4-Wire) 저항 결선 및 안전 점검] 전류 단자 전압 인가 금지 & 에러 큐 확인",
                description="전류(AMPS) 단자에 리드를 꽂은 상태로 전압원을 병렬 연결하면 내부 퓨즈가 단선되므로 측정 기능과 리드 위치를 반드시 일치시키세요.",
                how_to_steps=[
                    "1. [2-Wire 저항 측정] `INPUT HI`와 `INPUT LO` 2가닥만 저항 양단에 연결합니다.",
                    "2. [4-Wire 정밀 저저항 측정] `INPUT HI/LO`(전류 공급) 외에 `SENSE HI/LO`(전압 감지) 2가닥을 저항 양단에 추가로 총 4가닥(Kelvin 결선) 연결해야 정확한 4선 저항이 측정됩니다.",
                    "3. 우측 버튼을 눌러 장비 에러 큐(SYSTem:ERRor?)에 오류가 없는지 확인합니다.",
                ],
                verify_cmd="SYSTem:ERRor?",
                verify_label="🔍 3단계: 에러 큐(SYST:ERR?) 상태 확인",
                expected_hint='0,"No error" 반환 시 정상',
            ),
            ChecklistItem(
                id="dmm_nplc_autozero",
                title="[4단계: 적분 시간(NPLC) 및 오토제로(AutoZero) 설정 확인] 정밀도 vs 측정 속도 최적화",
                description="1 NPLC(60Hz 기준 16.67ms) 이상과 AutoZero ON을 사용하면 전원 노이즈가 제거되어 최고 정밀도를 얻을 수 있습니다.",
                how_to_steps=[
                    "1. 고정밀·저잡음 측정이 필요할 때는 좌측 입력 파라미터의 '적분 시간(NPLC)'을 `1.0` ~ `10.0` PLC로, '오토제로(AutoZero)'를 `ON`으로 설정하세요.",
                    "2. 빠른 변화나 과도 파형을 캡처할 때는 NPLC를 `0.01` ~ `0.1`로 낮추거나 측정 기능을 `Digitizer Voltage (1MS/s)`로 선택하세요.",
                    "3. 우측 버튼을 눌러 상태 레지스터(*ESR?)가 정상인지 최종 확인합니다.",
                ],
                verify_cmd="*ESR?",
                verify_label="🔍 4단계: 측정 준비(*ESR?) 최종 확인",
                expected_hint="0 반환 시 DMM 연속 측정 시작 가능",
            ),
        ],
        input_parameters=[
            InputParameterSpec(
                "dmm_func",
                "측정 기능 (Measurement Function)",
                "choice",
                "DC Voltage (직류 전압 - VOLT:DC)",
                choices=[
                    "DC Voltage (직류 전압 - VOLT:DC)",
                    "AC Voltage (교류 전압 - VOLT:AC)",
                    "DC Current (직류 전류 - CURR:DC)",
                    "AC Current (교류 전류 - CURR:AC)",
                    "2-Wire Resistance (2선 저항 - RES)",
                    "4-Wire Resistance (4선 정밀 저항 - FRES)",
                    "Frequency (주파수 - FREQ)",
                    "Temperature (온도 - TEMP)",
                    "Capacitance (커패시턴스 - CAP)",
                    "Digitizer Voltage (1MS/s 고속 파형 샘플링 - DIG:VOLT)",
                ],
                tooltip=":SENSe:FUNCtion / CONFigure:<func> / dmm.measure.func",
                group="1. 측정 기능 및 명령 모드",
            ),
            InputParameterSpec(
                "cmd_lang",
                "명령어 프로토콜 (Command Language)",
                "choice",
                "AUTO (*LANG? 자동 감지)",
                choices=[
                    "AUTO (*LANG? 자동 감지)",
                    "SCPI (표준 SCPI 모드 - 전 모델 호환)",
                    "TSP (DMM6500 / DMM7510 TSP 스크립트 모드)",
                ],
                group="1. 측정 기능 및 명령 모드",
            ),
            InputParameterSpec(
                "meas_range",
                "측정 레인지 (0 입력 시 Auto Range)",
                "float",
                0.0,
                unit="V/A/Ω (0=Auto)",
                min_val=0.0,
                max_val=100000000.0,
                tooltip=":SENSe:<func>:RANGe:AUTO ON (0일 때) 또는 고정 레인지 설정",
                group="1. 측정 기능 및 명령 모드",
            ),
            InputParameterSpec(
                "nplc",
                "적분 시간 (Integration Rate - NPLC)",
                "float",
                0.1,
                unit="PLC",
                min_val=0.0005,
                max_val=15.0,
                tooltip=":SENSe:<func>:NPLCycles / dmm.measure.nplc (0.1 PLC = 고속 6½ 디지트, 1 PLC = 16.67ms @ 60Hz)",
                group="2. 정밀도 및 노이즈 필터 설정",
            ),
            InputParameterSpec(
                "auto_zero",
                "오토제로 보정 (AutoZero)",
                "choice",
                "ONCE (시작 시 1회 보정 후 고속 측정)",
                choices=["ONCE (시작 시 1회 보정 후 고속 측정)", "OFF (고속 측정)", "ON (매 측정 보정 - 고정밀)"],
                tooltip=":SENSe:<func>:AZERo ON|OFF 및 :SENSe:AZERo:ONCE",
                group="2. 정밀도 및 노이즈 필터 설정",
            ),
            InputParameterSpec(
                "line_sync",
                "전원 라인 동기화 (Line Sync)",
                "bool",
                False,
                tooltip=":SENSe:<func>:LINE:SYNC / dmm.measure.linesync (고속 측정 시 OFF, 60Hz 정밀 억제 시 ON)",
                group="2. 정밀도 및 노이즈 필터 설정",
            ),
            InputParameterSpec(
                "avg_filter",
                "디지털 평균 필터 (Averaging Filter)",
                "choice",
                "OFF",
                choices=["OFF", "MOVing (10회 이동평균)", "REPeat (10회 반복평균)"],
                tooltip=":SENSe:<func>:AVERage:TCONtrol MOVing|REPeat",
                group="2. 정밀도 및 노이즈 필터 설정",
            ),
            InputParameterSpec(
                "offset_comp",
                "오프셋 보상 저항 (Offset-Compensated Ohms)",
                "bool",
                False,
                tooltip=":SENSe:FRESistance:OCOMpensated ON (열기전력 EMF 오차 제거)",
                group="2. 정밀도 및 노이즈 필터 설정",
            ),
            InputParameterSpec(
                "digitize_rate",
                "디지타이저 샘플링 속도 (DMM6500/7510)",
                "int",
                100000,
                unit="S/s",
                min_val=1000,
                max_val=1000000,
                tooltip=":SENSe:DIGitize:VOLTage:SRATe / dmm.digitize.samplerate",
                group="3. 디지타이저 파형 & 수집 주기",
            ),
            InputParameterSpec(
                "digitize_count",
                "파형 버퍼 캡처 샘플 수 (Waveform Points)",
                "int",
                200,
                unit="pts",
                min_val=10,
                max_val=10000,
                tooltip=":TRACe:POINts / 디지타이저 파형 포인트 수",
                group="3. 디지타이저 파형 & 수집 주기",
            ),
            InputParameterSpec(
                "poll_interval_s",
                "연속 측정 수집 주기 (Poll Interval)",
                "float",
                0.05,
                unit="s",
                min_val=0.01,
                max_val=60.0,
                group="3. 디지타이저 파형 & 수집 주기",
            ),
        ],
        measurable_items=[
            MeasurableItemSpec(
                "primary_reading",
                "주 측정값 (Primary DMM Reading)",
                "Value",
                ":READ? / dmm.measure.read()",
                True,
                "선택한 측정 기능(전압/전류/저항/주파수/온도 등)의 고정밀 측정값",
            ),
            MeasurableItemSpec(
                "reading_mean",
                "누적 평균값 (Running Mean)",
                "Value",
                "Buffer Mean Statistics",
                True,
                "측정 시작 이후 누적된 리딩의 평균값",
            ),
            MeasurableItemSpec(
                "reading_pk2pk",
                "누적 변동폭 (Peak-to-Peak Stability)",
                "Value",
                "Buffer Max - Min",
                True,
                "최댓값 - 최솟값 변동폭 (신호 안정도 및 노이즈 평가)",
            ),
            MeasurableItemSpec(
                "reading_std",
                "누적 표준편차 (Running StdDev)",
                "Value",
                "Buffer Standard Deviation",
                True,
                "측정값의 표준편차 (RMS 노이즈 수준)",
            ),
            MeasurableItemSpec(
                "active_terminals",
                "활성 입력 단자 (Active Terminals)",
                "Term",
                ":ROUTe:TERMinals?",
                True,
                "현재 선택된 물리 입력 단자 위치 (FRONt 또는 REAR)",
            ),
            MeasurableItemSpec(
                "digitizer_trace",
                "디지타이저 / 리딩 버퍼 파형 (Waveform Trace)",
                "Trace",
                ":TRACe:DATA? / Buffer Trace",
                False,
                "고속 샘플링 파형 또는 최근 리딩 버퍼 트레이스 (그래프 모드 2 및 Excel 시트 4에 기록)",
            ),
        ],
    ),
}

# Enforce the user-requested tab & category display order:
# 01. AFGs // 02. DC power Supplies // 03. DMM // 04. Oscilloscopes //
# 05. Spectrum Analyzers // 06. SMUs // 07. DC Precision test // 08. Tek VISA
_ORDERED_CATEGORY_KEYS = (
    "01_AFG",
    "02_DC_POWER",
    "08_DMM",
    "04_OSCILLOSCOPE",
    "05_SPECTRUM",
    "06_SMU",
    "07_DC_PRECISION",
    "07_TEK_VISA",
)
CATEGORY_PROFILES = {
    CATEGORY_PROFILES[k].folder_id: CATEGORY_PROFILES[k]
    for k in _ORDERED_CATEGORY_KEYS
}
