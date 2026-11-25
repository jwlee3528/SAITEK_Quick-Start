# SAITEK Tektronix Quick Start SW 배포 및 설치 가이드 (Release Guide)

다른 PC에 **Python, PyQt6, NumPy, OpenPyXL, PyVISA 등 어떠한 프로그램도 설치되어 있지 않더라도**, 아래 배포 파일만으로 필요한 모든 런타임과 8개 폴더 30종 PDF 매뉴얼을 설치하고 즉시 실행할 수 있습니다.

---

## 1. 생성된 배포 파일 위치 (`06.Release` 폴더)

1. **통합 설치 파일 (권장 배포용 - 단일 `.exe`)**
   - 파일 경로: `06.Release/SAITEK Tektronix Quick Start SW_Setup.exe`
   - **특징**:
     - 이 파일 **1개만 USB나 네트워크로 다른 PC에 복사해서 실행**하면 됩니다.
     - 실행 시 **통합 설치 마법사(Setup Wizard)** 창이 열리며, 지정한 폴더(기본값: `C:\SAITEK Tektronix Quick Start SW`)에 실행 파일, 내장 파이썬/GUI/VISA 런타임 DLL 일체, 8개 폴더 30종 PDF 매뉴얼(`01.docs/10. Tek_Manuals`), 데이터 저장 폴더(`05.data`)를 모두 자동 설치합니다.
     - 바탕화면 바로가기(`SAITEK Tektronix Quick Start SW.lnk`)와 시작 메뉴 바로가기를 자동 생성하며, 설치 완료 즉시 프로그램을 실행할 수 있습니다.

2. **무설치 포터블 실행 폴더 (`SAITEK Tektronix Quick Start SW_Portable`)**
   - 실행 파일 경로: `06.Release/SAITEK Tektronix Quick Start SW_Portable/SAITEK Tektronix Quick Start SW.exe`
   - **특징**:
     - 설치 과정 없이 `SAITEK Tektronix Quick Start SW_Portable` 폴더 통째로 복사한 뒤, 폴더 안의 **`SAITEK Tektronix Quick Start SW.exe`**를 더블클릭하면 즉시 실행됩니다.

---

## 2. 타겟 PC(새 컴퓨터)에서의 사용 방법

### A. 가상 장비 시뮬레이션 모드 (`[VIRTUAL]` - 별도 드라이버 설치 불필요)
- 아무것도 설치되지 않은 PC에서 `SAITEK Tektronix Quick Start SW_Setup.exe`로 설치 후 실행하면 즉시 **`[VIRTUAL]` 가상 시뮬레이션 모드**로 모든 장비(AFG, DC 파워, DMM, 오실로스코프, 스펙트럼 분석기, SMU, MP5000, Tek VISA)를 연결·측정·실시간 그래프 확인·엑셀(`.xlsx`) 저장까지 완벽하게 사용할 수 있습니다.

### B. 실제 계측기 연결 사용 시 (USB / LAN / GPIB)
- **LAN (Ethernet Socket / VXI-11) 연결**: 프로그램 내에 순수 파이썬 VISA 백엔드(`PyVISA-py`)가 기본 내장되어 있으므로, 별도 VISA 설치 없이도 LAN 케이블 연결만으로 실제 장비와 통신이 가능합니다.
- **USB (USBTMC / USB-CDC) 또는 GPIB 연결**: 타겟 PC의 Windows가 계측기 USB 드라이버를 인식할 수 있도록 **TekVISA** 또는 **NI-VISA 런타임**을 설치하면 USB 케이블로 연결된 실제 장비를 자동 검색합니다.
