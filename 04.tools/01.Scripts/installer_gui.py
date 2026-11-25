# -*- coding: utf-8 -*-
"""
SAITEK Tektronix Quick Start SW
Self-Contained Windows GUI Installer (SAITEK Tektronix Quick Start SW_Setup.exe)

Extracts the embedded SAITEK Tektronix Quick Start SW_Payload.zip (containing SAITEK Tektronix Quick Start SW.exe,
all Python/PyQt6/PyVISA runtime DLLs, 30 PDF manuals across 8 categories,
and data folders) to the user-selected installation folder on any clean Windows PC.
"""

import os
import sys
import zipfile
import shutil
import subprocess
import threading
from typing import Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "SAITEK Tektronix Quick Start SW"
EXE_FILENAME = "SAITEK Tektronix Quick Start SW.exe"
PAYLOAD_ZIP_NAME = "SAITEK Tektronix Quick Start SW_Payload.zip"
DEFAULT_INSTALL_DIR = r"C:\SAITEK Tektronix Quick Start SW"


def get_embedded_payload_path() -> str:
    """Locates the embedded SAITEK Tektronix Quick Start SW_Payload.zip inside PyInstaller _MEIPASS or script dir."""
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(bundle_dir, PAYLOAD_ZIP_NAME)


def create_windows_shortcut(target_exe: str, shortcut_path: str, working_dir: str, description: str) -> bool:
    """Creates a Windows .lnk shortcut using PowerShell WScript.Shell COM object."""
    try:
        ps_script = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{target_exe}"; '
            f'$s.WorkingDirectory = "{working_dir}"; '
            f'$s.Description = "{description}"; '
            f'$s.IconLocation = "{target_exe},0"; '
            f'$s.Save()'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        return os.path.exists(shortcut_path)
    except Exception:
        return False


def create_uninstaller_bat(install_dir: str) -> str:
    """Creates an Uninstall_SAITEK Tektronix Quick Start SW.bat file in the installation directory."""
    uninstaller_path = os.path.join(install_dir, "Uninstall_SAITEK Tektronix Quick Start SW.bat")
    content = f"""@echo off
chcp 65001 >nul
echo ============================================================================
echo   SAITEK Tektronix Quick Start SW 제거 (Uninstaller)
echo ============================================================================
echo.
echo 설치 경로: "{install_dir}"
echo 바탕화면 및 시작 메뉴 바로가기를 삭제하고 설치 폴더를 정리합니다...
del /f /q "%USERPROFILE%\\Desktop\\SAITEK Tektronix Quick Start SW.lnk" 2>nul
del /f /q "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\SAITEK Tektronix Quick Start SW.lnk" 2>nul
echo.
echo 바로가기가 제거되었습니다.
echo 프로그램 폴더("{install_dir}")를 완전히 삭제하려면 창을 닫고 폴더를 삭제하세요.
pause
"""
    with open(uninstaller_path, "w", encoding="utf-8") as f:
        f.write(content)
    return uninstaller_path


def run_silent_install(target_dir: str) -> int:
    """Performs non-interactive installation for automated testing or silent deployment."""
    payload_zip = get_embedded_payload_path()
    if not os.path.exists(payload_zip):
        print(f"[ERROR] Payload archive not found: {payload_zip}")
        return 1

    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(payload_zip, "r") as zf:
        zf.extractall(target_dir)

    create_uninstaller_bat(target_dir)
    exe_path = os.path.join(target_dir, EXE_FILENAME)
    if not os.path.exists(exe_path):
        print(f"[ERROR] Extracted executable not found: {exe_path}")
        return 2

    print(f"[OK] Successfully installed to: {target_dir}")
    print(f"[OK] Executable verified: {exe_path}")
    return 0


class TekInstallerWizard:
    """Clean Windows GUI Setup Wizard for Tektronix & Keithley QuickStart Program."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} - 통합 설치 마법사 (Setup Wizard)")
        self.root.geometry("700x540")
        self.root.minsize(660, 500)
        self.root.configure(bg="#0F172A")

        self.install_dir_var = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.desktop_shortcut_var = tk.BooleanVar(value=True)
        self.startmenu_shortcut_var = tk.BooleanVar(value=True)
        self.launch_after_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="설치 경로와 옵션을 확인한 후 [설치 시작 (Install)] 버튼을 클릭하세요.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.is_installing = False

        self._center_window()
        self._build_ui()

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = 700
        h = 540
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        # Top Header Banner
        header = tk.Frame(self.root, bg="#1E293B", padx=20, pady=16, highlightthickness=1, highlightbackground="#38BDF8")
        header.pack(fill=tk.X, padx=14, pady=(14, 8))

        title_lbl = tk.Label(
            header,
            text="⚡ SAITEK Tektronix Quick Start SW 통합 설치 마법사",
            font=("Malgun Gothic", 14, "bold"),
            fg="#38BDF8",
            bg="#1E293B",
            anchor="w",
        )
        title_lbl.pack(fill=tk.X)

        sub_lbl = tk.Label(
            header,
            text=(
                "다른 PC에 Python이나 별도 패키지가 전혀 설치되어 있지 않아도 실행에 필요한 모든 런타임 파일,\n"
                "8개 장비 폴더별 30종 PDF 매뉴얼, 가상 시뮬레이터 및 실행 파일(SAITEK Tektronix Quick Start SW.exe)을 한 번에 설치합니다."
            ),
            font=("Malgun Gothic", 9),
            fg="#CBD5E1",
            bg="#1E293B",
            justify=tk.LEFT,
            anchor="w",
        )
        sub_lbl.pack(fill=tk.X, pady=(6, 0))

        # Included Components Box
        comp_frame = tk.LabelFrame(
            self.root,
            text=" 📦 설치 포함 구성 요소 (Included Components) ",
            font=("Malgun Gothic", 10, "bold"),
            fg="#38BDF8",
            bg="#0F172A",
            padx=14,
            pady=10,
        )
        comp_frame.pack(fill=tk.X, padx=14, pady=6)

        components_text = (
            "  • 실행 파일 (SAITEK Tektronix Quick Start SW.exe) + 내장 Python / PyQt6 / PyQtGraph / NumPy / OpenPyXL / PyVISA-py 엔진\n"
            "  • 8대 계측기 폴더별 모듈 (01.AFGs / 02.DC Power / 03.DMM / 04.Scopes / 05.RSA / 06.SMUs / 07.DC Precision / 08.Tek VISA)\n"
            "  • 초보자용 단계별 장비 연결 점검 마법사 + 30종 공식 프로그래머 매뉴얼 PDF 원본 (01.docs/10. Tek_Manuals)\n"
            "  • 물리 엔진 기반 가상 장비 시뮬레이터 ([VIRTUAL] 모드) + Run History 비교 + Excel/CSV/PNG 리포트 출력기"
        )
        comp_lbl = tk.Label(
            comp_frame,
            text=components_text,
            font=("Malgun Gothic", 9),
            fg="#E2E8F0",
            bg="#0F172A",
            justify=tk.LEFT,
            anchor="w",
        )
        comp_lbl.pack(fill=tk.X)

        # Target Directory Selection
        dir_frame = tk.LabelFrame(
            self.root,
            text=" 📁 설치 폴더 선택 (Installation Directory) ",
            font=("Malgun Gothic", 10, "bold"),
            fg="#38BDF8",
            bg="#0F172A",
            padx=14,
            pady=10,
        )
        dir_frame.pack(fill=tk.X, padx=14, pady=6)

        entry_row = tk.Frame(dir_frame, bg="#0F172A")
        entry_row.pack(fill=tk.X)

        self.dir_entry = tk.Entry(
            entry_row,
            textvariable=self.install_dir_var,
            font=("Consolas", 10),
            bg="#1E293B",
            fg="#F8FAFC",
            insertbackground="#38BDF8",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#475569",
        )
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))

        self.browse_btn = tk.Button(
            entry_row,
            text="폴더 찾아보기...",
            command=self._on_browse,
            font=("Malgun Gothic", 9, "bold"),
            bg="#334155",
            fg="#F8FAFC",
            activebackground="#475569",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
        )
        self.browse_btn.pack(side=tk.RIGHT)

        # Shortcut & Post-Install Options
        opt_frame = tk.LabelFrame(
            self.root,
            text=" ⚙️ 바로가기 및 실행 옵션 (Shortcut & Launch Options) ",
            font=("Malgun Gothic", 10, "bold"),
            fg="#38BDF8",
            bg="#0F172A",
            padx=14,
            pady=8,
        )
        opt_frame.pack(fill=tk.X, padx=14, pady=6)

        cb_style = {
            "font": ("Malgun Gothic", 9),
            "fg": "#E2E8F0",
            "bg": "#0F172A",
            "selectcolor": "#1E293B",
            "activebackground": "#0F172A",
            "activeforeground": "#38BDF8",
            "anchor": "w",
        }
        tk.Checkbutton(
            opt_frame,
            text="바탕화면에 [SAITEK Tektronix Quick Start SW] 실행 바로가기 아이콘 생성 (권장)",
            variable=self.desktop_shortcut_var,
            **cb_style,
        ).pack(fill=tk.X, pady=1)

        tk.Checkbutton(
            opt_frame,
            text="Windows 시작 메뉴에 [SAITEK Tektronix Quick Start SW] 프로그램 등록",
            variable=self.startmenu_shortcut_var,
            **cb_style,
        ).pack(fill=tk.X, pady=1)

        tk.Checkbutton(
            opt_frame,
            text="설치 완료 후 SAITEK Tektronix Quick Start SW 즉시 실행 (SAITEK Tektronix Quick Start SW.exe)",
            variable=self.launch_after_var,
            **cb_style,
        ).pack(fill=tk.X, pady=1)

        # Progress Bar & Status Label
        prog_frame = tk.Frame(self.root, bg="#0F172A", padx=14, pady=6)
        prog_frame.pack(fill=tk.X)

        self.status_lbl = tk.Label(
            prog_frame,
            textvariable=self.status_var,
            font=("Malgun Gothic", 9, "bold"),
            fg="#A7F3D0",
            bg="#0F172A",
            anchor="w",
        )
        self.status_lbl.pack(fill=tk.X, pady=(0, 4))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Tek.Horizontal.TProgressbar",
            troughcolor="#1E293B",
            background="#0284C7",
            bordercolor="#334155",
            lightcolor="#38BDF8",
            darkcolor="#0369A1",
        )
        self.progress_bar = ttk.Progressbar(
            prog_frame,
            variable=self.progress_var,
            maximum=100.0,
            style="Tek.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.X, ipady=4)

        # Bottom Action Buttons
        btn_frame = tk.Frame(self.root, bg="#0F172A", padx=14, pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.cancel_btn = tk.Button(
            btn_frame,
            text="닫기 / 취소 (Cancel)",
            command=self.root.destroy,
            font=("Malgun Gothic", 10, "bold"),
            bg="#334155",
            fg="#E2E8F0",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        self.cancel_btn.pack(side=tk.LEFT)

        self.install_btn = tk.Button(
            btn_frame,
            text="🚀 프로그램 설치 시작 (Install Now)",
            command=self._start_installation,
            font=("Malgun Gothic", 11, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=22,
            pady=8,
            cursor="hand2",
        )
        self.install_btn.pack(side=tk.RIGHT)

    def _on_browse(self) -> None:
        if self.is_installing:
            return
        chosen = filedialog.askdirectory(
            parent=self.root,
            title="SAITEK Tektronix Quick Start SW 설치 폴더 선택",
            initialdir=self.install_dir_var.get() or r"C:\\",
        )
        if chosen:
            norm = os.path.normpath(chosen)
            if not norm.lower().endswith("saitek tektronix quick start sw"):
                norm = os.path.join(norm, "SAITEK Tektronix Quick Start SW")
            self.install_dir_var.set(norm)

    def _start_installation(self) -> None:
        if self.is_installing:
            return

        target_dir = self.install_dir_var.get().strip()
        if not target_dir:
            messagebox.showwarning("설치 경로 확인", "설치할 폴더 경로를 입력해 주세요.", parent=self.root)
            return

        payload_zip = get_embedded_payload_path()
        if not os.path.exists(payload_zip):
            messagebox.showerror(
                "설치 패키지 오류",
                f"내장된 설치 패키지({PAYLOAD_ZIP_NAME})를 찾을 수 없습니다.\n경로: {payload_zip}",
                parent=self.root,
            )
            return

        self.is_installing = True
        self.install_btn.configure(state=tk.DISABLED, text="⏳ 설치 진행 중...")
        self.browse_btn.configure(state=tk.DISABLED)

        worker = threading.Thread(target=self._extract_worker, args=(payload_zip, target_dir), daemon=True)
        worker.start()

    def _update_progress(self, pct: float, msg: str) -> None:
        self.root.after(0, lambda: (self.progress_var.set(pct), self.status_var.set(msg)))

    def _extract_worker(self, payload_zip: str, target_dir: str) -> None:
        try:
            self._update_progress(2.0, f"설치 폴더 준비 중: {target_dir}")
            os.makedirs(target_dir, exist_ok=True)

            with zipfile.ZipFile(payload_zip, "r") as zf:
                members = zf.infolist()
                total = max(1, len(members))
                for idx, member in enumerate(members, start=1):
                    zf.extract(member, target_dir)
                    if idx % 20 == 0 or idx == total:
                        pct = 5.0 + (idx / total) * 85.0
                        short_name = os.path.basename(member.filename) or member.filename
                        self._update_progress(pct, f"파일 설치 중 ({idx}/{total}): {short_name}")

            exe_path = os.path.join(target_dir, EXE_FILENAME)
            create_uninstaller_bat(target_dir)

            # Create shortcuts if requested
            if self.desktop_shortcut_var.get():
                self._update_progress(93.0, "바탕화면 바로가기 아이콘 생성 중...")
                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.isdir(desktop_dir):
                    lnk_path = os.path.join(desktop_dir, "SAITEK Tektronix Quick Start SW.lnk")
                    create_windows_shortcut(
                        exe_path,
                        lnk_path,
                        target_dir,
                        "SAITEK Tektronix Quick Start SW",
                    )

            if self.startmenu_shortcut_var.get():
                self._update_progress(96.0, "Windows 시작 메뉴 바로가기 생성 중...")
                appdata = os.environ.get("APPDATA", "")
                start_menu_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                if os.path.isdir(start_menu_dir):
                    lnk_path = os.path.join(start_menu_dir, "SAITEK Tektronix Quick Start SW.lnk")
                    create_windows_shortcut(
                        exe_path,
                        lnk_path,
                        target_dir,
                        "SAITEK Tektronix Quick Start SW",
                    )

            self._update_progress(100.0, f"✅ 설치 완료! ({exe_path})")
            self.root.after(0, lambda: self._on_install_success(target_dir, exe_path))

        except Exception as e:
            self.root.after(0, lambda: self._on_install_error(str(e)))

    def _on_install_success(self, target_dir: str, exe_path: str) -> None:
        self.is_installing = False
        self.install_btn.configure(state=tk.NORMAL, text="✅ 설치 완료 (Installed)", bg="#059669")
        self.cancel_btn.configure(text="마법사 닫기 (Finish)")

        messagebox.showinfo(
            "설치 완료 (Installation Complete)",
            f"SAITEK Tektronix Quick Start SW 설치가 완료되었습니다!\n\n"
            f"• 설치 폴더: {target_dir}\n"
            f"• 실행 파일: {exe_path}\n\n"
            f"바탕화면의 [SAITEK Tektronix Quick Start SW] 아이콘 또는 설치 폴더의 'SAITEK Tektronix Quick Start SW.exe'를 실행하여 바로 사용할 수 있습니다.",
            parent=self.root,
        )

        if self.launch_after_var.get() and os.path.exists(exe_path):
            try:
                subprocess.Popen([exe_path], cwd=target_dir)
                self.root.destroy()
            except Exception as e:
                messagebox.showwarning("실행 안내", f"자동 실행 중 오류: {e}\n직접 {exe_path}를 실행해 주세요.")

    def _on_install_error(self, err_msg: str) -> None:
        self.is_installing = False
        self.install_btn.configure(state=tk.NORMAL, text="🚀 프로그램 설치 시작 (Install Now)")
        self.browse_btn.configure(state=tk.NORMAL)
        self.status_var.set(f"❌ 설치 오류 발생: {err_msg}")
        messagebox.showerror("설치 오류", f"설치 중 오류가 발생했습니다:\n{err_msg}", parent=self.root)


def main() -> int:
    # Support silent CLI install: TekQuickStart_Setup.exe --silent --target "C:\TekQuickStart"
    if "--silent" in sys.argv:
        target = DEFAULT_INSTALL_DIR
        if "--target" in sys.argv:
            idx = sys.argv.index("--target")
            if idx + 1 < len(sys.argv):
                target = sys.argv[idx + 1]
        return run_silent_install(target)

    root = tk.Tk()
    _wizard = TekInstallerWizard(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
