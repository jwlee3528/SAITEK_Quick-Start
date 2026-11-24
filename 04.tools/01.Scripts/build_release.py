# -*- coding: utf-8 -*-
r"""
Tektronix & Keithley Multi-Category QuickStart Program
Automated Release Builder (Standalone Executable + Self-Contained Setup Installer)

Outputs to: F:\02.Project\06. Tek Quickstart program\06.Release
1. 06.Release\TekQuickStart_Portable\TekQuickStart.exe  (Direct executable package)
2. 06.Release\TekQuickStart_Setup.exe                   (Single-file GUI Setup Installer)
"""

import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
import time


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(BASE_DIR, "02.src")
RELEASE_DIR = os.path.join(BASE_DIR, "06.Release")
PORTABLE_DIR = os.path.join(RELEASE_DIR, "TekQuickStart_Portable")

# Use local C: temp directory for PyInstaller work/dist assembly to avoid external drive I/O bottlenecks
LOCAL_BUILD_ROOT = os.path.join(tempfile.gettempdir(), "TekQuickStart_Build_Temp")
LOCAL_DIST_DIR = os.path.join(LOCAL_BUILD_ROOT, "dist")
LOCAL_PORTABLE_DIR = os.path.join(LOCAL_DIST_DIR, "TekQuickStart_Portable")
PAYLOAD_ZIP = os.path.join(LOCAL_BUILD_ROOT, "TekQuickStart_Payload.zip")

INSTALLER_SCRIPT = os.path.join(BASE_DIR, "04.tools", "01.Scripts", "installer_gui.py")
MAIN_APP_SCRIPT = os.path.join(SRC_DIR, "06.Main", "main_app.py")

# Exclude heavy unrelated global packages so build is fast and compact
EXCLUDED_MODULES = [
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "scipy",
    "matplotlib",
    "pandas",
    "sqlalchemy",
    "cryptography",
    "bcrypt",
    "pydantic",
    "rich",
    "pygments",
    "jinja2",
    "fsspec",
    "sqlite3",
    "sklearn",
    "scikit_learn",
    "chromadb",
    "onnxruntime",
    "langchain",
    "streamlit",
    "fastapi",
    "uvicorn",
    "grpc",
    "tensorflow",
    "sympy",
    "pyarrow",
    "PIL",
    "cv2",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "PyQt6.QtTest",
    "PyQt6.QtBluetooth",
    "PyQt6.QtNfc",
    "PyQt6.QtPositioning",
    "PyQt6.QtQuick",
    "PyQt6.QtQml",
    "PyQt6.QtSensors",
    "PyQt6.QtSerialPort",
    "PyQt6.QtSql",
    "PyQt6.QtTextToSpeech",
    "PyQt6.QtWebChannel",
    "PyQt6.QtWebSockets",
    "PyQt6.QtXml",
]


def run_step(cmd: list[str], desc: str) -> None:
    print(f"\n{'=' * 76}")
    print(f"[BUILD] {desc}")
    print(f"{'=' * 76}")
    t0 = time.perf_counter()
    res = subprocess.run(cmd, cwd=BASE_DIR)
    dt = time.perf_counter() - t0
    if res.returncode != 0:
        raise RuntimeError(f"Step failed ({res.returncode}): {desc}")
    print(f"[OK] Completed in {dt:.1f}s: {desc}")


def step1_build_main_executable() -> None:
    """Compiles 02.src/06.Main/main_app.py into TekQuickStart_Portable/TekQuickStart.exe."""
    if os.path.exists(LOCAL_BUILD_ROOT):
        shutil.rmtree(LOCAL_BUILD_ROOT, ignore_errors=True)
    os.makedirs(LOCAL_DIST_DIR, exist_ok=True)
    os.makedirs(RELEASE_DIR, exist_ok=True)

    src_subpaths = [
        os.path.join(SRC_DIR, sub)
        for sub in ("01.Core", "02.Modules", "03.Drivers", "04.Utils", "05.Config", "06.Main")
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        "TekQuickStart",
        "--distpath",
        LOCAL_DIST_DIR,
        "--workpath",
        os.path.join(LOCAL_BUILD_ROOT, "app_work"),
        "--specpath",
        LOCAL_BUILD_ROOT,
    ]

    for p in src_subpaths:
        cmd.extend(["--paths", p])

    hidden_imports = [
        "instrument_profiles",
        "visa_manager",
        "instrument_drivers",
        "excel_exporter",
        "dialogs",
        "category_panel",
        "run_history",
        "pyqtgraph.exporters",
        "pyvisa",
        "pyvisa_py",
        "openpyxl",
        "numpy",
        "pyqtgraph",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
    ]
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    for ex in EXCLUDED_MODULES:
        cmd.extend(["--exclude-module", ex])

    cmd.append(MAIN_APP_SCRIPT)
    run_step(cmd, "Stage 1: Compile Standalone Executable (TekQuickStart.exe)")

    built_folder = os.path.join(LOCAL_DIST_DIR, "TekQuickStart")
    if os.path.exists(built_folder):
        os.rename(built_folder, LOCAL_PORTABLE_DIR)

    # Copy 01.docs/10. Tek_Manuals, logo image, and 05.data into LOCAL_PORTABLE_DIR
    for logo_name in ("로고 이미지.png", "logo.png"):
        src_logo = os.path.join(BASE_DIR, logo_name)
        if os.path.exists(src_logo):
            shutil.copy2(src_logo, os.path.join(LOCAL_PORTABLE_DIR, logo_name))

    src_manuals = os.path.join(BASE_DIR, "01.docs", "10. Tek_Manuals")
    dst_manuals = os.path.join(LOCAL_PORTABLE_DIR, "01.docs", "10. Tek_Manuals")
    if os.path.exists(src_manuals):
        print(f"[COPY] Bundling 26 PDF manuals -> {dst_manuals}")
        shutil.copytree(src_manuals, dst_manuals, dirs_exist_ok=True)

    os.makedirs(os.path.join(LOCAL_PORTABLE_DIR, "05.data", "02.Processed"), exist_ok=True)
    src_samples = os.path.join(BASE_DIR, "05.data", "03.Samples")
    dst_samples = os.path.join(LOCAL_PORTABLE_DIR, "05.data", "03.Samples")
    if os.path.exists(src_samples):
        shutil.copytree(src_samples, dst_samples, dirs_exist_ok=True)


def step2_create_payload_zip() -> None:
    """Compresses TekQuickStart_Portable into TekQuickStart_Payload.zip for the Setup Installer."""
    print(f"\n{'=' * 76}")
    print(f"[BUILD] Stage 2: Creating Compressed Installer Payload ({PAYLOAD_ZIP})")
    print(f"{'=' * 76}")
    t0 = time.perf_counter()

    if os.path.exists(PAYLOAD_ZIP):
        os.remove(PAYLOAD_ZIP)

    file_count = 0
    with zipfile.ZipFile(PAYLOAD_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _dirs, files in os.walk(LOCAL_PORTABLE_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, LOCAL_PORTABLE_DIR)
                zf.write(abs_path, rel_path)
                file_count += 1

    size_mb = os.path.getsize(PAYLOAD_ZIP) / (1024 * 1024)
    dt = time.perf_counter() - t0
    print(f"[OK] Packed {file_count} files ({size_mb:.1f} MB) in {dt:.1f}s")


def step3_build_setup_installer() -> None:
    """Compiles installer_gui.py + TekQuickStart_Payload.zip into single-file TekQuickStart_Setup.exe."""
    add_data_arg = f"{PAYLOAD_ZIP};."
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "TekQuickStart_Setup",
        "--distpath",
        LOCAL_DIST_DIR,
        "--workpath",
        os.path.join(LOCAL_BUILD_ROOT, "installer_work"),
        "--specpath",
        LOCAL_BUILD_ROOT,
        "--add-data",
        add_data_arg,
    ]
    for ex in EXCLUDED_MODULES + ["PyQt6", "pyqtgraph", "numpy", "openpyxl", "pyvisa", "pyvisa_py"]:
        cmd.extend(["--exclude-module", ex])

    cmd.append(INSTALLER_SCRIPT)
    run_step(cmd, "Stage 3: Compile Self-Contained Single-File Setup Installer (TekQuickStart_Setup.exe)")


def step4_publish_to_release_dir() -> None:
    """Copies the built TekQuickStart_Setup.exe and TekQuickStart_Portable into 06.Release."""
    print(f"\n{'=' * 76}")
    print(f"[BUILD] Stage 4: Publishing Release Artifacts to {RELEASE_DIR}")
    print(f"{'=' * 76}")

    # Clean up any leftover partial build in RELEASE_DIR
    for stale_name in ("TekQuickStart", "TekQuickStart_Portable"):
        stale_p = os.path.join(RELEASE_DIR, stale_name)
        if os.path.exists(stale_p):
            shutil.rmtree(stale_p, ignore_errors=True)

    local_setup_exe = os.path.join(LOCAL_DIST_DIR, "TekQuickStart_Setup.exe")
    target_setup_exe = os.path.join(RELEASE_DIR, "TekQuickStart_Setup.exe")

    # Copy single-file Setup Installer
    with open(local_setup_exe, "rb") as fsrc, open(target_setup_exe, "wb") as fdst:
        while True:
            chunk = fsrc.read(4 * 1024 * 1024)
            if not chunk:
                break
            fdst.write(chunk)
    print(f"[OK] Published Setup Installer -> {target_setup_exe}")

    # Extract payload directly into 06.Release\TekQuickStart_Portable (uses small buffered writes)
    os.makedirs(PORTABLE_DIR, exist_ok=True)
    with zipfile.ZipFile(PAYLOAD_ZIP, "r") as zf:
        zf.extractall(PORTABLE_DIR)
    print(f"[OK] Published Portable EXE Folder -> {PORTABLE_DIR}")


def cleanup_temp() -> None:
    if os.path.exists(LOCAL_BUILD_ROOT):
        shutil.rmtree(LOCAL_BUILD_ROOT, ignore_errors=True)
    old_temp = os.path.join(BASE_DIR, "build_temp")
    if os.path.exists(old_temp):
        shutil.rmtree(old_temp, ignore_errors=True)


def main() -> int:
    t_start = time.perf_counter()
    step1_build_main_executable()
    step2_create_payload_zip()
    step3_build_setup_installer()
    step4_publish_to_release_dir()
    cleanup_temp()

    exe_path = os.path.join(PORTABLE_DIR, "TekQuickStart.exe")
    setup_path = os.path.join(RELEASE_DIR, "TekQuickStart_Setup.exe")
    setup_mb = os.path.getsize(setup_path) / (1024 * 1024) if os.path.exists(setup_path) else 0.0

    print(f"\n{'=' * 76}")
    print(f"🎉 [RELEASE BUILD COMPLETE] Total time: {time.perf_counter() - t_start:.1f}s")
    print(f"  1) 실행 파일 패키지 (Portable EXE): {exe_path}")
    print(f"  2) 통합 설치 파일 (Setup Installer): {setup_path} ({setup_mb:.1f} MB)")
    print(f"{'=' * 76}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
