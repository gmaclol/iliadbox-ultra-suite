#!/usr/bin/env python3
"""
Iliadbox Ultra Suite - Desktop Native Application
Self-contained executable: manages the internal FastAPI/Uvicorn server,
dynamically checks free ports (with automatic dynamic port allocation if all defaults are busy),
and displays the native desktop application window.
"""

import sys
import os
import time
import socket
import asyncio
import threading
import urllib.request
import webbrowser
import subprocess
from typing import Optional, List

# Ensure safe streams and handle missing stdout/stderr in windowed mode
class NullWriter:
    def write(self, s): pass
    def flush(self): pass
    def isatty(self): return False

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Determine correct asset base directory (supports PyInstaller onefile frozen bundle)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BASE_DIR

os.environ["ILIADBOX_BASE_DIR"] = BASE_DIR
os.environ["ILIADBOX_EXE_DIR"] = EXE_DIR

LOG_FILE = os.path.join(EXE_DIR, "iliadbox_app.log")

def log(msg: str):
    """Writes timestamped diagnostic message to log file and stdout if available."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

log("=== Avvio Iliadbox Ultra Suite ===")
log(f"Cartella eseguibile: {EXE_DIR}")
log(f"Cartella asset: {BASE_DIR}")

import uvicorn
from server import app

def is_port_really_free(port: int, host: str = "127.0.0.1") -> bool:
    """Verifies that a port can actually be bound and listened on without conflicts."""
    if not isinstance(port, int) or port < 1024 or port > 65535:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # On Windows, DO NOT use SO_REUSEADDR here because it can allow binding to ports
            # already in use by other processes. Plain bind and listen tests real exclusivity.
            s.bind((host, port))
            s.listen(1)
            return True
    except OSError:
        return False

def invent_free_port(host: str = "127.0.0.1") -> int:
    """
    Invents an available free port dynamically from the OS kernel.
    Falls back to scanning high random ports if needed.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            s.listen(1)
            invented = s.getsockname()[1]
            if invented and 1024 < invented < 65535:
                return invented
    except Exception as e:
        log(f"Avviso binding porta 0: {e}")

    import random
    for _ in range(100):
        cand = random.randint(10000, 60000)
        if is_port_really_free(cand, host):
            return cand

    return 8080

def find_or_invent_free_port(candidate_port: Optional[int] = None, host: str = "127.0.0.1") -> int:
    """
    1. If candidate_port is supplied and free, uses it.
    2. Otherwise checks the standard default ports (8080, 8081, 8082, 8888, 5000, 3000, 9000, 9090, 7777).
    3. If NONE of the default ports are free, INVENTS a free port dynamically.
    """
    default_ports = [8080, 8081, 8082, 8888, 5000, 3000, 9000, 9090, 7777]

    # Check candidate first
    if candidate_port and is_port_really_free(candidate_port, host):
        log(f"Porta candidata {candidate_port} verificata ed e' libera.")
        return candidate_port

    # Check default list
    log(f"Verifica disponibilita' porte di default: {default_ports}")
    for p in default_ports:
        if is_port_really_free(p, host):
            log(f"Porta libera trovata nella lista di default: {p}")
            return p

    # If all defaults are occupied or blocked, INVENT a port!
    log("Nessuna delle porte di default e' libera! Invenzione di una porta libera dal sistema operativo...")
    invented = invent_free_port(host)
    log(f"Porta dinamica inventata dal sistema con successo: {invented}")
    return invented

class ServerThread(threading.Thread):
    """Runs uvicorn in an isolated asyncio loop with precise readiness signaling."""
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.started_event = threading.Event()
        self.error = None
        self.server = None

    def run(self):
        try:
            # log_config=None is mandatory to prevent PyInstaller crash 'Unable to configure formatter default'
            config = uvicorn.Config(
                app=app,
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False,
                log_config=None
            )
            self.server = uvicorn.Server(config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def wait_until_ready():
                while not self.server.started and not self.server.should_exit:
                    await asyncio.sleep(0.03)
                self.started_event.set()

            loop.create_task(wait_until_ready())
            loop.run_until_complete(self.server.serve())
        except Exception as e:
            self.error = e
            self.started_event.set()
            log(f"Errore avvio server uvicorn: {e}")

def wait_for_http_ok(url: str, timeout: float = 6.0) -> bool:
    """Polls the health endpoint to guarantee the server is accepting HTTP requests."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{url}/api/health", headers={"User-Agent": "Iliadbox-Launcher/1.0"})
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False

def open_standalone_window(url: str):
    """Tries Edge/Chrome app mode or default browser as fallback."""
    log(f"Apertura browser in modalita' applicazione desktop: {url}")
    browser_candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW

    for b in browser_candidates:
        if os.path.exists(b):
            try:
                proc = subprocess.Popen(
                    [b, f"--app={url}", "--window-size=1340,880"],
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                return proc
            except Exception as err:
                log(f"Errore lancio browser {b}: {err}")

    # Generic fallback
    webbrowser.open(url)
    return None

def main():
    # 1. Parse port argument if passed by launcher or command line
    candidate_port = None
    if len(sys.argv) > 1:
        try:
            candidate_port = int(sys.argv[1])
        except ValueError:
            pass

    # 2. Find or invent free port
    host = "127.0.0.1"
    port = find_or_invent_free_port(candidate_port, host)
    server_url = f"http://{host}:{port}"
    log(f"URL server locale stabilito: {server_url}")

    # 3. Start server in worker thread
    server_thread = ServerThread(host, port)
    server_thread.start()

    # 4. Wait for server readiness event
    log("In attesa che il server FastAPI sia pronto ad accettare connessioni...")
    server_thread.started_event.wait(timeout=5.0)

    # 5. If initial attempt failed, immediately invent a new port from the OS and retry
    if server_thread.error or not server_thread.server or not server_thread.server.started:
        log(f"Server non partito su porta {port} (errore: {server_thread.error}). Invenzione nuova porta libera...")
        port = invent_free_port(host)
        server_url = f"http://{host}:{port}"
        log(f"Riavvio server su nuova porta inventata: {server_url}")
        server_thread = ServerThread(host, port)
        server_thread.start()
        server_thread.started_event.wait(timeout=5.0)

    # 6. Confirm HTTP 200 on /api/health
    is_ready = wait_for_http_ok(server_url, timeout=6.0)
    if is_ready:
        log("✔ Server web operativo al 100%! Risposta HTTP 200 ricevuta con successo.")
    else:
        log("ATTENZIONE: Timeout verifica HTTP health, procedo comunque con l'apertura.")

    # 7. Launch the Native Window
    try:
        import webview
        log("Inizializzazione finestra nativa Windows tramite Microsoft Edge WebView2...")
        window = webview.create_window(
            title="Iliadbox Ultra Suite",
            url=server_url,
            width=1340,
            height=880,
            min_size=(1024, 680),
            background_color="#070a12",
            text_select=True
        )
        log("Avvio webview.start()...")
        webview.start(gui="edgechromium", debug=False)
        log("Finestra nativa chiusa dall'utente. Uscita regolare.")
    except Exception as e:
        log(f"pywebview non utilizzabile ({e}). Lancio finestra applicativa standalone Edge/Chrome...")
        browser_proc = open_standalone_window(server_url)
        if browser_proc:
            try:
                browser_proc.wait()
            except Exception:
                pass
        else:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        log("Processo terminato.")

if __name__ == "__main__":
    main()
