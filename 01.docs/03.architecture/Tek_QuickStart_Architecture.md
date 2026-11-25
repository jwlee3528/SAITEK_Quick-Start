# SAITEK Tektronix Quick Start SW 통합 제어 및 측정 프로그램 아키텍처 명세서

## 1. 개요 (Overview)
본 문서는 `01.docs/10. Tek_Manuals` 내 8개 폴더(총 30개 프로그래머/레퍼런스 매뉴얼)를 기반으로 개발된 **SAITEK Tektronix Quick Start SW**의 시스템 구조와 장비별 리모트 준비 사항, 입력 파라미터, 측정 항목 및 동작 프로세스를 정의합니다.

---

## 2. 7개 매뉴얼 폴더 및 모듈 매핑

| 폴더 번호 및 이름 | 포함 매뉴얼 (총 26개) | 프로그램 모듈 및 드라이버 | 주요 프로토콜 |
| :--- | :--- | :--- | :--- |
| **01. AFGs** | `AFG1000`, `AFG2021`, `AFG31000 Series` (3개) | `AFGDriver`, `AFGPanel` | SCPI (`SOURce<n>`, `OUTPut<n>`) |
| **02. DC power Supplies** | `Series 2200 (2220/2230/2231A)`, `Series 2260B` (2개) | `DCPowerDriver`, `DCPowerPanel` | SCPI (`INST:SEL`, `VOLT`, `CURR`, `MEAS`) |
| **03. DC Precision Test** | `MP5000 Series (MP5103 Mainframe + PSU/SMU)` (1개) | `MP5000Driver`, `MP5000Panel` | TSP Lua (`slot[z].psu[x]`, `slot[z].smu[x]`) |
| **04. Oscilloscopes** | `TBS1000C`, `TBS2000B`, `2 Series MSO`, `3 Series MDO`, `4/5/6 Series MSO`, `7 Series DPO`, `MSO/DPO5000/7000/70000` (7개) | `OscilloscopeDriver`, `ScopePanel` | SCPI (`CH<x>`, `HOR`, `ACQ`, `MEASU`, `CURVe?`) |
| **05. Spectrum Analyzers** | `SignalVu Vector Analysis`, `RSA300/500/600 AppNote` (2개) | `SpectrumDriver`, `SpectrumPanel` | SCPI (`INIT`, `SPEC:FREQ`, `READ:SPEC:TRAC1?`, `CALC:SPEC:MARK`) |
| **06. SMUs** | `2450`, `2460`, `2461`, `2470`, `2600B`, `2601B-PULSE`, `2606B`, `2651A` (8개) | `SMUDriver`, `SMUPanel` | Dual Engine: SCPI/TSP (`24xx`) & TSP (`26xx` / `pulser`) |
| **07. Tek VISA** | `TekVISA Programmer`, `TekVISA Reference`, `OpenChoice Talker Listener` (3개) | `VisaConnectionManager`, `TalkerListenerPanel` | VISA (`USB?*INSTR`, `TCPIP?*INSTR`, `ASRL?*INSTR`) |

---

## 3. 핵심 요구사항 구현 설계

### 요구사항 1: 7개 폴더별 기능 분리
- 좌측 사이드바 및 메인 탭에서 **01. AFGs ~ 07. Tek VISA** 7개 카테고리를 독립된 모듈로 분리하여 선택 및 제어할 수 있습니다.
- 각 카테고리 안에서 해당 폴더에 속한 세부 장비 모델(`AFG1000`, `AFG2021`, `AFG31000` 등)을 선택하면 매뉴얼에 정의된 스펙과 명령어 체계로 자동 전환됩니다.

### 요구사항 2: 장비별 [입력 필요 사항]과 [측정 가능 부분] 명확한 분리 및 사전 확인
- **좌측 구역 [1. 입력 및 제어 설정 (Required Inputs)]**: 동작 전에 사용자가 반드시 지정해야 하는 소스/계측 파라미터(파형, 주파수, 전압/전류 제한, OVP/OCP, 수직/수평 스케일, 중심 주파수/Span, 스윕 범위 등)를 그룹화하고 입력값 유효성 검사를 수행합니다.
- **중앙/우측 구역 [2. 측정 가능 항목 선택 (Measurable Items)]**: 해당 장비에서 읽어올 수 있는 측정 항목들을 체크박스로 분리하여 사용자가 원하는 측정 항목을 선택할 수 있게 합니다.
- **측정 및 동작 전 사전 확인 모달 (`PreStartConfirmDialog`)**: 사용자가 **[▶ 측정 시작 (Start)]** 버튼을 누르면 실제 장비에 명령을 전송하기 전에 **1) 리모트 준비 체크 상태, 2) 사용자 입력 파라미터 요약, 3) 측정할 항목 목록, 4) 안전 경고(출력 ON 여부 등)**를 팝업으로 제시하여 최종 승인을 받습니다.

### 요구사항 3: 기본 동작 (측정 시작 & 일시정지 & 완전 정지 / 그래프 표현 / Excel 데이터 저장)
- **상태 머신 제어 (`IDLE` -> `RUNNING` <-> `PAUSED` -> `STOPPED`)**:
  - **▶ 측정 시작 (Start)**: 사전 확인 모달 승인 후 백그라운드 워커 스레드(`QThread`)에서 장비 초기화 및 주기적 측정/스윕 루프를 시작합니다.
  - **⏸ 일시정지 (Pause) / ▶ 재개 (Resume)**: 장비 세션을 유지한 채 폴링/스윕 타이머만 일시 정지하며, 필요 시 출력을 대기 상태로 유지하고 그래프 확대를 통한 분석이 가능합니다.
  - **⏹ 완전 정지 (Stop)**: 측정 루프를 즉시 종료하고, 전원/신호 인가 장비(AFG, DC Power, MP5000, SMU)의 출력을 안전하게 차단(`OUTPut OFF` / `source.output = 0`)합니다.
- **실시간 그래프 표현 (`pyqtgraph`)**:
  - 장비 특성에 맞는 실시간 차트(AFG 파형 프리뷰, DC Power V/I/P 트렌드, MP5000 및 SMU 시계열 & I-V 곡선, 오실로스코프 멀티채널 파형, 스펙트럼 애널라이저 주파수 도메인 트레이스 & 피크 마커)를 고성능으로 렌더링합니다.
- **측정 데이터 Excel 저장 (`openpyxl` / `pandas`)**:
  - **[💾 Excel 저장]** 클릭 시 다중 시트로 구성된 `.xlsx` 파일을 생성합니다:
    1. `Summary_Metadata`: 장비 카테고리, 모델명, VISA 주소, `*IDN?` 응답, 측정 시작/종료 시각, 리모트 체크리스트 결과
    2. `Input_Config`: 측정에 사용된 모든 사용자 입력 파라미터 및 선택된 측정 항목
    3. `Measured_Data`: 타임스탬프별 측정 데이터 테이블 및 최대/최소/평균/표준편차 통계
    4. `Waveform_Trace`: 오실로스코프 파형 데이터, 스펙트럼 트레이스(Frequency vs dBm), 또는 AFG 샘플 포인트

### 요구사항 4: 리모트 준비 사항 체크리스트 및 상태 확인 (프로그램 시작 시 & 장비별)
- **프로그램 시작 시 리모트 환경 점검 모달 (`StartupReadinessDialog`)**:
  - VISA 백엔드(TekVISA / NI-VISA / PyVISA-py) 로드 상태 자동 진단
  - 연결된 USB (USBTMC / USB-CDC) 및 LAN (TCPIP / VXI-11 / Socket) 리소스 자동 스캔
  - 장비별 핵심 리모트 사전 설정 체크리스트 확인 및 시뮬레이션(Virtual Hardware) 모드 전환 지원
- **각 장비 패널 상단 [리모트 준비 사항 & 상태 확인 (`RemoteReadinessChecklist`)]**:
  - 매뉴얼의 *Getting Started / Remote Communications / Safety Precautions* 섹션에서 추출한 장비별 필수 준비 사항을 체크박스로 제공하고, **[🔍 장비 상태 확인 (`*IDN?` / Error Queue / Interlock / Login)]** 버튼으로 실제 장비 상태를 즉시 검증합니다.
