# -*- coding: utf-8 -*-
"""
Root Entry Point for Tektronix QuickStart Program
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "02.src")
for sub in ("01.Core", "02.Modules", "03.Drivers", "04.Utils", "05.Config", "06.Main"):
    p = os.path.join(SRC_DIR, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from main_app import main

if __name__ == "__main__":
    main()
