"""
Iliadbox Wi-Fi 7 Python Client
Direct HTTP REST client for Freebox OS / Iliadbox OS (API v15.0)
Supports pairing, session authentication, telemetry, Wi-Fi 7 diagnostics, and optimization.
"""

import hmac
import hashlib
import json
import time
import os
import requests
from typing import Dict, Any, Optional

import sys

DEFAULT_ILIADBOX_HOST = "192.168.1.254"
EXE_DIR = os.environ.get("ILIADBOX_EXE_DIR") or (
    os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
)
DEFAULT_TOKEN_FILE = os.path.join(EXE_DIR, ".iliadbox_token.json")

class IliadboxClient:
    def __init__(
        self,
        host: str = DEFAULT_ILIADBOX_HOST,
        app_id: str = "it.iliadbox.optimizer",
        app_name: str = "Iliadbox Ultra Optimizer",
        app_version: str = "1.0.0",
        device_name: str = "Network Admin PC",
        token_file: str = DEFAULT_TOKEN_FILE
    ):
        self.host = host
        self.app_id = app_id
        self.app_name = app_name
        self.app_version = app_version
        self.device_name = device_name
        self.token_file = token_file
        
        self.base_url = f"http://{self.host}"
        self.api_version = "v15"
        self.api_url = f"{self.base_url}/api/{self.api_version}"
        
        self.app_token: Optional[str] = None
        self.track_id: Optional[int] = None
        self.session_token: Optional[str] = None
        self.session_permissions: Dict[str, bool] = {}
        
        self._load_saved_token()

    def _load_saved_token(self) -> bool:
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.app_token = data.get("app_token")
                    self.track_id = data.get("track_id")
                    if data.get("app_id"):
                        self.app_id = data.get("app_id")
                    return True
            except Exception:
                pass
        return False

    def _save_token(self):
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump({
                "app_token": self.app_token,
                "track_id": self.track_id,
                "app_id": self.app_id,
                "created_at": time.time()
            }, f, indent=2)

    def detect_api(self) -> Dict[str, Any]:
        """Detects the box model, firmware API version and capabilities."""
        resp = requests.get(f"{self.base_url}/api_version", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        raw_version = data.get("api_version", "15.0")
        major_version = raw_version.split(".")[0]
        self.api_version = f"v{major_version}"
        self.api_url = f"{self.base_url}/api/{self.api_version}"
        return data

    def request_authorization(self) -> Dict[str, Any]:
        """Requests authorization from the Iliadbox."""
        url = f"{self.api_url}/login/authorize/"
        payload = {
            "app_id": self.app_id,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "device_name": self.device_name
        }
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        res = resp.json()
        if res.get("success"):
            self.app_token = res["result"]["app_token"]
            self.track_id = res["result"]["track_id"]
            self._save_token()
            return res["result"]
        raise RuntimeError(f"Authorization request failed: {res}")

    def check_authorization_status(self, track_id: Optional[int] = None) -> str:
        """
        Polls authorization status: 'pending', 'granted', 'denied', 'timeout'.
        """
        tid = track_id or self.track_id
        if not tid:
            raise ValueError("No track_id available to check status.")
        url = f"{self.api_url}/login/authorize/{tid}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        res = resp.json()
        if res.get("success"):
            return res["result"]["status"]
        return "unknown"

    def login(self) -> bool:
        """
        Logs in using stored app_token and HMAC-SHA1 challenge.
        """
        if not self.app_token:
            raise RuntimeError("No app_token found. You must authorize first.")
        
        # 1. Get challenge
        resp = requests.get(f"{self.api_url}/login/", timeout=5)
        resp.raise_for_status()
        login_res = resp.json()
        if not login_res.get("success"):
            raise RuntimeError(f"Could not retrieve login challenge: {login_res}")
        
        challenge = login_res["result"]["challenge"]
        
        # 2. Compute HMAC-SHA1
        password = hmac.new(
            self.app_token.encode("ascii"),
            challenge.encode("ascii"),
            hashlib.sha1
        ).hexdigest()
        
        # 3. Post session
        session_resp = requests.post(
            f"{self.api_url}/login/session/",
            json={"app_id": self.app_id, "password": password},
            timeout=5
        )
        session_resp.raise_for_status()
        s_res = session_resp.json()
        
        if s_res.get("success"):
            self.session_token = s_res["result"]["session_token"]
            self.session_permissions = s_res["result"].get("permissions", {})
            return True
        else:
            raise RuntimeError(f"Login failed: {s_res}")

    def _headers(self) -> Dict[str, str]:
        if not self.session_token:
            raise RuntimeError("Not logged in. Call login() first.")
        return {
            "X-Fbx-App-Auth": self.session_token,
            "Content-Type": "application/json"
        }

    def get(self, endpoint: str) -> Dict[str, Any]:
        """Generic GET request to the authenticated API."""
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{self.api_url}{endpoint}"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic PUT request to update settings."""
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{self.api_url}{endpoint}"
        resp = requests.put(url, json=data, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generic POST request."""
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{self.api_url}{endpoint}"
        resp = requests.post(url, json=data or {}, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    # High-level helpers
    def get_system_info(self) -> Dict[str, Any]:
        return self.get("/system/")

    def get_connection_status(self) -> Dict[str, Any]:
        return self.get("/connection/")

    def get_ftth_status(self) -> Dict[str, Any]:
        try:
            return self.get("/connection/ftth/")
        except Exception:
            return {}

    def get_ipv6_config(self) -> Dict[str, Any]:
        try:
            return self.get("/connection/ipv6/config/")
        except Exception:
            return {}

    def get_wifi_config(self) -> Dict[str, Any]:
        return self.get("/wifi/config/")

    def get_wifi_ap(self) -> Dict[str, Any]:
        return self.get("/wifi/ap/")

    def get_wifi_bss(self) -> Dict[str, Any]:
        return self.get("/wifi/bss/")

    def get_wifi_stations(self) -> Dict[str, Any]:
        stations = []
        for ap_id in [0, 1]:
            try:
                res = self.get(f"/wifi/ap/{ap_id}/stations/")
                if res.get("success"):
                    stations.extend(res.get("result", []))
            except Exception:
                pass
        return {"success": True, "result": stations}

    def get_dhcp_config(self) -> Dict[str, Any]:
        return self.get("/dhcp/config/")

    def get_dhcpv6_config(self) -> Dict[str, Any]:
        try:
            return self.get("/dhcpv6/config/")
        except Exception:
            return {}

    def get_upnpigd_config(self) -> Dict[str, Any]:
        try:
            return self.get("/upnpigd/config/")
        except Exception:
            return {}

    def get_lan_hosts(self) -> Dict[str, Any]:
        try:
            return self.get("/lan/browser/pub/")
        except Exception:
            return {}

    def get_switch_status(self) -> Dict[str, Any]:
        try:
            return self.get("/switch/status/")
        except Exception:
            return {}

    def get_services_status(self) -> Dict[str, Any]:
        services = {}
        for srv, ep in [
            ("ftp", "/ftp/config/"),
            ("upnpav", "/upnpav/config/"),
            ("airmedia", "/airmedia/config/"),
            ("downloads", "/downloads/stats/"),
            ("lcd", "/lcd/config/")
        ]:
            try:
                services[srv] = self.get(ep).get("result", {})
            except Exception:
                services[srv] = {"error": "unavailable"}
        return services
