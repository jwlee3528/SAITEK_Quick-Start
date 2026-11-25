# ⚡ SAITEK Tektronix Quick Start SW (v1.2.8)

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6%20%2B%20PyQtGraph-41CD52?style=flat-square&logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![VISA](https://img.shields.io/badge/Interface-USB%20%7C%20LAN%20%7C%20GPIB%20%7C%20Virtual-orange?style=flat-square)

**계측기 프로그래밍이나 SCPI/TSP 명령어를 전혀 모르는 초보자도** 안내 화면만 따라 하면 Tektronix & Keithley 8대 제품군 계측기를 안전하게 연결하고, 실시간 측정·분석·리포트 저장까지 한 번에 수행할 수 있는 통합 퀵스타트 소프트웨어입니다.

---

## ✨ 핵심 기능 (Key Features)

* **🔌 초보자용 단계별 연결 점검 마법사**
  * 케이블 포트 위치부터 장비 전면 패널 메뉴 설정까지 한국어 따라하기 가이드 제공
  * `*IDN?`, `*LANG?`, `:ROUT:TERM?`, `SYST:ERR?` 명령어를 통한 개별/일괄 자동 통신 진단
* **🧪 가상 시뮬레이션 모드 (`[VIRTUAL]` Mode) 기본 내장**
  * 실제 계측기가 없어도 물리 엔진 기반으로 8대 제품군의 파형·측정 동작을 100% 동일하게 연습 가능
* **🛡️ 4단계 안전 워크플로우 & 긴급 차단**
  * `사전 준비 점검표` → `입력 파라미터 & 측정 항목 설정` → `동작 전 최종 확인 팝업` → `실시간 측정 및 저장`
  * **완전 정지(Output OFF)** 및 **긴급 정지(ALL STOP)** 기능으로 측정 종료/비상 시 출력 즉시 차단
* **📈 실시간 고속 그래프 & 커서 분석 (`PyQtGraph`)**
  * 실시간 파형/트렌드 플로팅, 마우스 줌/자동 스케일, 시리즈 표시/숨김 지원
  * **듀얼 커서(C1/C2)** 구간 통계(`N`, `Min`, `Max`, `Mean`, `Pk-Pk`, `Δx`, `Δy`) 실시간 계산
* **📜 실행 이력(Run History) 비교 & 자동 내보내기**
  * 측정할 때마다 `Run #1, #2...` 자동 기록 및 여러 Run을 한 그래프에 겹쳐서 비교 분석
  * 측정 종료 시 지정 폴더에 **Excel / CSV / PNG** 자동 저장 기능 지원
* **📊 4-시트 Excel (`.xlsx`) 성적서 자동 생성**
  * 요약/점검표, 입력 설정값, 시계열 데이터(평균/최대/최소/표준편차 자동 계산), 원본 파형 데이터를 4개 시트로 자동 정리
* **📖 공식 PDF 매뉴얼 30종 내장**
  * 각 장비 탭에서 `[PDF 매뉴얼]` 버튼 클릭 시 해당 모델의 공식 프로그래머 매뉴얼 즉시 열람

---

## 🛠️ 지원 계측기 제품군 (8대 제품군)

| 폴더 / 탭 | 제품군 | 주요 지원 모델 및 특징 |
| :--- | :--- | :--- |
| **01. AFGs** | 임의 파형/함수 발생기 | AFG31000, AFG3000C 시리즈 등 (파형/주파수/진폭/임피던스 제어 및 실시간 프리뷰) |
| **02. DC power Supplies** | 프로그래머블 DC 전원공급기 | Series 2200, Series 2260B (전압/전류/전력 트렌드, OVP/OCP 보호) |
| **03. DMM** | 정밀 디지털 멀티미터 | Keithley DMM6500, DMM7510, 2110, 2010 (5½~7½ 디지트 고정밀 측정, 1MS/s 디지타이저) |
| **04. Oscilloscopes** | 디지털 오실로스코프 | 2/3/4/5/6/7 Series MSO/DPO, TBS1000C/2000B (다중 채널 CH1~CH4 동시 파형 캡처, Vpp/주파수 자동 계측) |
| **05. Spectrum Analyzers** | 실시간 스펙트럼 애널라이저 | RSA306B/500A/600A, SignalVu-PC, RSA5000/6000 (RF 트레이스, 피크 마커) |
| **06. SMUs** | 소스미터 (SourceMeter) | Keithley 2450, 2460, 2461, 2470, 2600B 시리즈 (I-V 특성 곡선 실시간 플로팅, 2선/4선식 측정) |
| **07. DC Precision test** | 모듈형 정밀 테스트 시스템 | Keithley MP5000 (TSP 스크립트 명령어 체계 자동 지원) |
| **08. Tek VISA** | 범용 VISA 명령어 콘솔 | 커스텀 SCPI/TSP 명령어 송수신(Write/Query/Read) 및 응답 지연시간(ms) 로깅 |

---

## 🚀 시작하기 (Quick Start)

### 방법 1. 통합 설치 파일로 원클릭 설치 (권장)
Python이나 별도 라이브러리가 없는 일반 Windows PC에서도 바로 설치해 사용할 수 있습니다.
1. `06.Release/SAITEK Tektronix Quick Start SW_Setup.exe` 실행
2. 설치 경로 확인 (기본값: `C:\SAITEK Tektronix Quick Start SW`) 및 바로가기 옵션 선택
3. **[프로그램 설치 시작]** 클릭 → 실행 엔진 및 30종 PDF 매뉴얼 자동 설치 완료

> 💡 **무설치(Portable) 실행:** 설치 없이 `06.Release/SAITEK Tektronix Quick Start SW_Portable/SAITEK Tektronix Quick Start SW.exe`를 직접 실행해도 동일하게 동작합니다.  
> 💡 **실제 장비 연결 시:** USB/LAN 실제 계측기 연결을 위해 **TekVISA** 또는 **NI-VISA** 드라이버 설치를 권장합니다.

### 방법 2. 소스 코드로 직접 실행 (개발자용)
```bash
# 1. 저장소 클론
git clone [https://github.com/jwlee3528/SAITEK_Quick-Start.git](https://github.com/jwlee3528/SAITEK_Quick-Start.git)
cd SAITEK_Quick-Start

# 2. 필수 패키지 설치
pip install -r requirements.txt

# 3. 프로그램 실행 (배치 파일 또는 Python 직접 실행)
run_quickstart.bat
# 또는
python run_quickstart.py

📂 프로젝트 구조 (Directory Structure)

SAITEK_Quick-Start/
├── 01.docs/                 # 사용자 가이드(PPTX/PDF) 및 8대 제품군 공식 매뉴얼
├── 02.src/                  # 메인 애플리케이션 소스 코드 (Python / PyQt6)
├── 03.tests/                # 통합 테스트 코드 (02.Integration)
├── 04.tools/                # 유틸리티 및 보조 스크립트 (01.Scripts)
├── 05.data/                 # 샘플 데이터 및 자동 저장 리포트 경로 (03.Samples)
├── 06.Release/              # 배포용 설치 파일(Setup.exe) 및 Portable 빌드
├── build_release.bat        # 릴리즈 패키징 자동화 스크립트
├── requirements.txt         # Python 의존성 패키지 목록 (PyQt6, PyQtGraph, NumPy, OpenPyXL, PyVISA-py)
├── run_quickstart.bat       # Windows 원클릭 실행 스크립트
└── run_quickstart.py        # 프로그램 진입점 (Entry Point)

📊 자동 생성 Excel (.xlsx) 리포트 구성
측정 완료 후 [Excel 저장] 버튼을 클릭하면 별도 편집 없이 바로 보고서로 활용할 수 있는 4-시트 엑셀 파일이 생성됩니다.

1_Summary_Checklist: 측정 시각, 모델명, 참조 매뉴얼, VISA 주소, *IDN? 응답 및 사전 점검 기록

2_Input_Configuration: 장비에 인가한 사용자 입력 파라미터 및 선택한 측정 항목 목록 (재현성 검증용)

3_Measured_Data: 시계열 측정 데이터 전체 + 하단 핵심 통계치(평균, 최댓값, 최솟값, 표준편차) 자동 계산

4_Waveform_Trace: 오실로스코프 파형 / RF 스펙트럼 / SMU I-V 스윕 포인트 원본 로우 데이터

📄 문서 및 문의
상세 사용자 매뉴얼: 01.docs/06.development_guides/ 폴더 내 `SAITEK Tektronix Quick Start SW_Beginner_User_Guide.pptx` 및 `.pdf` 참고

기술 문의: 사이텍(주) | E-mail : ssaitek@ssaitek.com | Tel : 041-698-4242
Maintainer: @jwlee3528 (SAITEK)
