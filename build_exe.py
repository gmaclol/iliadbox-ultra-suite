#!/usr/bin/env python3
"""
Build script to compile Iliadbox Ultra Suite into a single standalone .exe
"""

import os
import sys
import shutil
import subprocess

def build():
    print("\n[+] Avvio compilazione di Iliadbox.exe con PyInstaller...\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "Iliadbox",
        "--add-data", "web;web",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "webview.platforms.winforms",
        "--hidden-import", "clr",
        "--hidden-import", "pythonnet",
        "--hidden-import", "clr_loader",
        "--hidden-import", "fastapi",
        "--hidden-import", "starlette",
        "--hidden-import", "pydantic",
        "--hidden-import", "dns",
        "--hidden-import", "dns.resolver",
        "--hidden-import", "requests",
        "--hidden-import", "rich",
        "app_desktop.py"
    ]

    print("Comando:", " ".join(cmd))
    res = subprocess.run(cmd)

    if res.returncode == 0:
        dist_exe = os.path.join("dist", "Iliadbox.exe")
        target_exe = os.path.join(".", "Iliadbox.exe")
        if os.path.exists(dist_exe):
            shutil.copy2(dist_exe, target_exe)
            print(f"\n[OK] Compilazione completata con successo!")
            print(f"[OK] File eseguibile pronto in: {os.path.abspath(target_exe)}")
            print(f"[OK] Dimensioni: {os.path.getsize(target_exe) / (1024*1024):.1f} MB\n")
    else:
        print(f"\n[ERRORE] Compilazione fallita con codice {res.returncode}")
        sys.exit(res.returncode)

if __name__ == "__main__":
    build()
