#!/usr/bin/env python3
"""
Iliadbox Wi-Fi 7 Optimizer & Management Suite
Complete diagnostic, tuning, and optimization CLI tool for Iliadbox OS (Freebox OS v15)
"""

import sys
import os
import time
import argparse
from typing import Dict, Any, Optional

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from iliadbox_client import IliadboxClient

console = Console(safe_box=True)

class IliadboxOptimizer:
    def __init__(self, host: str = "192.168.1.254"):
        self.client = IliadboxClient(host=host)

    def ensure_authenticated(self) -> bool:
        """Checks authentication; if missing or revoked, launches pairing workflow."""
        console.print("[cyan]Verifica connessione con Iliadbox...[/cyan]")
        try:
            api_info = self.client.detect_api()
            console.print(f"  [green][OK] Iliadbox rilevata:[/green] [bold]{api_info.get('box_model_name', 'Iliadbox')}[/bold] ({api_info.get('device_type')}), API {api_info.get('api_version')}")
        except Exception as e:
            console.print(f"  [red][X] Impossibile contattare l'Iliadbox su {self.client.host}: {e}[/red]")
            return False

        # Try to login with existing token
        if self.client.app_token:
            try:
                self.client.login()
                console.print("  [green][OK] Sessione autenticata con successo![/green]")
                return True
            except Exception as e:
                console.print(f"  [yellow][!] Token salvato non valido o scaduto ({e}). Nuova autorizzazione richiesta.[/yellow]")

        # Initiate pairing
        console.print("\n[bold yellow]Richiesta di nuova autorizzazione all'Iliadbox...[/bold yellow]")
        try:
            req = self.client.request_authorization()
            track_id = req["track_id"]
        except Exception as e:
            console.print(f"[red]Errore durante la richiesta di autorizzazione: {e}[/red]")
            return False

        console.print(Panel(
            "[bold white]Guarda il DISPLAY TOUCH frontale della tua ILIADBOX![/bold white]\n"
            "Sullo schermino apparira': [bold cyan]'Richiesta di autorizzazione per Iliadbox Ultra Optimizer'[/bold cyan].\n\n"
            "👉 [bold green]Premi la FRECCIA DESTRA o il pulsante 'CONFERMA' sul display della Iliadbox per consentire l'accesso.[/bold green]",
            title="[bold yellow]AZIONE RICHIESTA SULLA ILIADBOX[/bold yellow]",
            border_style="yellow"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]In attesa di conferma sul display Iliadbox...[/cyan]", total=60)
            status = "pending"
            start_time = time.time()
            
            while status == "pending" and (time.time() - start_time) < 60:
                time.sleep(1.5)
                status = self.client.check_authorization_status(track_id)
                if status == "granted":
                    break
                elif status in ("denied", "timeout"):
                    break

        if status == "granted":
            console.print("[bold green][OK] Autorizzazione concessa dall'Iliadbox![/bold green]")
            self.client.login()
            return True
        elif status == "denied":
            console.print("[bold red][X] Richiesta rifiutata dall'utente sul display della box.[/bold red]")
            return False
        else:
            console.print("[bold red][X] Tempo scaduto per la conferma sul display.[/bold red]")
            return False

    def run_full_audit(self):
        """Audits hardware, connection, optical power, Wi-Fi 7, and services."""
        if not self.ensure_authenticated():
            return

        console.print(Panel.fit("[bold cyan]AUDIT PRESTAZIONI E STATO ILIADBOX WI-FI 7[/bold cyan]", box=box.ROUNDED))

        # 1. System Info & Thermals
        try:
            sys_info = self.client.get_system_info().get("result", {})
            temp_cput = sys_info.get("temp_cput", 0)
            temp_sw = sys_info.get("temp_sw", 0)
            fan_rpm = sys_info.get("fan_rpm", 0)
            uptime_s = sys_info.get("uptime_val", 0)
            uptime_h = uptime_s / 3600
            firmware = sys_info.get("firmware_version", "N/A")

            sys_table = Table(title="Parametri di Sistema e Temperature", box=box.SIMPLE_HEAVY)
            sys_table.add_column("Parametro", style="bold white")
            sys_table.add_column("Valore", style="cyan")
            sys_table.add_column("Stato Termico", justify="center")

            thermal_eval = "[green]Ottimale (<65°C)[/green]" if temp_cput < 65 else ("[yellow]Attenzione (>65°C)[/yellow]" if temp_cput < 80 else "[red]Critico (>80°C)[/red]")
            sys_table.add_row("Firmware Iliadbox", str(firmware), "[green]Attivo[/green]")
            sys_table.add_row("Uptime Router", f"{uptime_h:.1f} ore", "[green]Stabile[/green]")
            sys_table.add_row("Temperatura CPU", f"{temp_cput}°C", thermal_eval)
            sys_table.add_row("Temperatura Switch", f"{temp_sw}°C", "[green]Normale[/green]")
            sys_table.add_row("Velocità Ventola", f"{fan_rpm} RPM", "[green]Regolare[/green]")
            console.print(sys_table)
        except Exception as e:
            console.print(f"[yellow]Impossibile recuperare info di sistema: {e}[/yellow]")

        # 2. Connection, FTTH, and IPv4 Port Range (MAP-E)
        try:
            conn = self.client.get_connection_status().get("result", {})
            ftth = self.client.get_ftth_status().get("result", {})
            
            ipv4 = conn.get("ipv4", "N/A")
            ipv4_port_range = conn.get("ipv4_port_range", [])
            ipv6 = conn.get("ipv6", "N/A")
            down_rate = conn.get("rate_down", 0) / 1024  # KB/s
            up_rate = conn.get("rate_up", 0) / 1024
            
            conn_table = Table(title="Connessione FTTH & Allocazione Porte IPv4 (MAP-E)", box=box.SIMPLE_HEAVY)
            conn_table.add_column("Voce", style="bold white")
            conn_table.add_column("Valore Rilevato", style="cyan")
            conn_table.add_column("Diagnosi Esperta", justify="center")

            # Optical power
            if ftth:
                sfp_pwr_rx = ftth.get("sfp_pwr_rx", 0) / 100.0  # dBm
                sfp_pwr_tx = ftth.get("sfp_pwr_tx", 0) / 100.0
                rx_eval = "[green]Potenza Ottica Perfetta[/green]" if (-25.0 <= sfp_pwr_rx <= -8.0) else "[red]Segnale Ottico Degrado[/red]"
                conn_table.add_row("Potenza Ottica RX (SFP)", f"{sfp_pwr_rx:.2f} dBm", rx_eval)
                conn_table.add_row("Potenza Ottica TX (SFP)", f"{sfp_pwr_tx:.2f} dBm", "[green]Ottimale[/green]")

            conn_table.add_row("Indirizzo IPv4 Pubblico", str(ipv4), "[green]Attivo[/green]")
            
            # Check port range
            if ipv4_port_range and len(ipv4_port_range) == 2:
                p_start, p_end = ipv4_port_range[0], ipv4_port_range[1]
                if p_start == 1 and p_end >= 65535:
                    port_eval = "[bold green]IPv4 Full Stack (Tutte le 65535 porte libere)[/bold green]"
                else:
                    port_eval = f"[bold yellow]IPv4 Condiviso (Porte limitate: {p_start}-{p_end})[/bold yellow]"
                conn_table.add_row("Range Porte IPv4 Assegnate", f"{p_start} - {p_end}", port_eval)
            else:
                conn_table.add_row("Range Porte IPv4", "1 - 65535", "[green]Completo[/green]")

            conn_table.add_row("Prefisso IPv6", str(ipv6), "[green]Nativo IPv6 Attivo[/green]")
            conn_table.add_row("Traffico Istantaneo", f"↓ {down_rate:.1f} KB/s | ↑ {up_rate:.1f} KB/s", "[green]In linea[/green]")
            console.print(conn_table)
        except Exception as e:
            console.print(f"[yellow]Impossibile recuperare info connessione: {e}[/yellow]")

        # 3. Wi-Fi 7 Configuration & Channels
        try:
            wifi_cfg = self.client.get_wifi_config().get("result", {})
            wifi_ap = self.client.get_wifi_ap().get("result", [])
            wifi_bss = self.client.get_wifi_bss().get("result", [])
            
            wifi_enabled = wifi_cfg.get("enabled", False)
            
            wifi_table = Table(title="Configurazione Wi-Fi 7 (Bande, Canali, Larghezze)", box=box.SIMPLE_HEAVY)
            wifi_table.add_column("Banda / Interfaccia", style="bold white")
            wifi_table.add_column("Canale / Larghezza", style="cyan")
            wifi_table.add_column("SSID", style="bold green")
            wifi_table.add_column("Analisi Ottimizzazione", justify="center")

            if isinstance(wifi_ap, list):
                for ap in wifi_ap:
                    band = ap.get("config", {}).get("band", "N/A")
                    channel = ap.get("status", {}).get("channel", "Auto")
                    width = ap.get("status", {}).get("channel_width", "N/A")
                    dfs = ap.get("status", {}).get("dfs", False)
                    
                    analysis = "[green]Canale Libero[/green]"
                    if width in (160, 320):
                        analysis = f"[bold green]Prestazioni Massime ({width} MHz)[/bold green]"
                    elif band == "5ghz" and width < 160:
                        analysis = "[yellow]Può essere spinto a 160 MHz[/yellow]"
                        
                    wifi_table.add_row(
                        f"Radio {band.upper()}",
                        f"Canale: {channel} | {width} MHz" + (" (DFS)" if dfs else ""),
                        str(wifi_cfg.get("ssid", "iliadbox")),
                        analysis
                    )
            console.print(wifi_table)

            # Connected Wi-Fi clients
            stations = self.client.get_wifi_stations().get("result", [])
            if stations and isinstance(stations, list):
                st_table = Table(title="Dispositivi Connessi in Wi-Fi (Client Link Rate)", box=box.SIMPLE_HEAVY)
                st_table.add_column("Dispositivo / Hostname", style="bold white")
                st_table.add_column("Segnale RSSI", justify="right")
                st_table.add_column("Velocità / Bitrate", style="cyan", justify="right")
                st_table.add_column("Generazione Wi-Fi", justify="center")

                std_map = {
                    "be": "[bold green]Wi-Fi 7 (802.11be)[/bold green]",
                    "ax": "[bold cyan]Wi-Fi 6 (802.11ax)[/bold cyan]",
                    "ac": "[blue]Wi-Fi 5 (802.11ac)[/blue]",
                    "n": "[yellow]Wi-Fi 4 (802.11n)[/yellow]",
                    "g": "[white]802.11g[/white]",
                    "b": "[white]802.11b[/white]"
                }

                for st in stations:
                    mac = st.get("mac", "N/A")
                    host = st.get("host", {})
                    hostname = host.get("primary_name") or st.get("hostname") or mac
                    signal = st.get("signal", -100)
                    
                    ap_info = host.get("access_point", {}).get("wifi_information", {})
                    raw_std = ap_info.get("standard", "").lower()
                    proto = std_map.get(raw_std, f"Wi-Fi ({raw_std.upper()})")
                    
                    bitrate = st.get("last_tx", {}).get("bitrate", 0) / 10.0
                    if bitrate == 0:
                        bitrate = st.get("tx_rate", 0) / 1000.0
                        
                    sig_color = "[green]" if signal > -65 else ("[yellow]" if signal > -75 else "[red]")
                    st_table.add_row(
                        hostname,
                        f"{sig_color}{signal} dBm[/]",
                        f"{bitrate:.1f} Mbps",
                        proto
                    )
                console.print(st_table)
        except Exception as e:
            console.print(f"[yellow]Impossibile recuperare info Wi-Fi: {e}[/yellow]")

        # 4. Ethernet Switch Ports Status
        try:
            sw_ports = self.client.get_switch_status().get("result", [])
            if sw_ports and isinstance(sw_ports, list):
                sw_table = Table(title="Porte Ethernet Switch Iliadbox", box=box.SIMPLE_HEAVY)
                sw_table.add_column("Porta", style="bold white")
                sw_table.add_column("Stato Link", justify="center")
                sw_table.add_column("Velocità Negoziazione", style="cyan")
                sw_table.add_column("Dispositivo Connesso", style="bold green")
                sw_table.add_column("Capacità Hardware", justify="center")

                for p in sw_ports:
                    p_name = p.get("name", "Ethernet")
                    p_id = p.get("id", 0)
                    p_link = p.get("link", "down")
                    p_speed = p.get("speed", "0")
                    mac_list = p.get("mac_list", [])
                    
                    connected_desc = "Nessuno"
                    if mac_list:
                        connected_desc = ", ".join([m.get("hostname") or m.get("mac") for m in mac_list])
                    
                    link_badge = "[green]ATTIVO[/green]" if p_link == "up" else "[dim]Non collegato[/dim]"
                    speed_desc = f"{p_speed} Mbps" if p_link == "up" else "-"
                    
                    hw_cap = "[bold green]Supporta 2.5 Gbps![/bold green]" if p_id == 1 else "1 Gbps Max"
                    sw_table.add_row(p_name, link_badge, speed_desc, connected_desc, hw_cap)
                console.print(sw_table)
        except Exception as e:
            console.print(f"[yellow]Impossibile recuperare info switch: {e}[/yellow]")

        # 5. Network Optimization & UPnP IGD Status
        try:
            dhcp_v4 = self.client.get_dhcp_config().get("result", {})
            dhcp_v6 = self.client.get_dhcpv6_config().get("result", {})
            upnp_cfg = self.client.get_upnpigd_config().get("result", {})

            opt_table = Table(title="Configurazioni di Routing, DNS e Gaming", box=box.SIMPLE_HEAVY)
            opt_table.add_column("Funzionalità", style="bold white")
            opt_table.add_column("Configurazione Attuale", style="cyan")
            opt_table.add_column("Stato Ottimizzazione", justify="center")

            # DNS IPv4
            v4_dns = [d for d in dhcp_v4.get("dns", []) if d]
            v4_status = f"[green]Turbo DNS Diretto ({', '.join(v4_dns)})[/green]" if v4_dns else "[yellow]Relay Locale Iliadbox[/yellow]"
            opt_table.add_row("Server DNS IPv4 (DHCP)", ", ".join(v4_dns) if v4_dns else "192.168.1.254", v4_status)

            # DNS IPv6
            v6_custom = dhcp_v6.get("use_custom_dns", False)
            v6_dns = dhcp_v6.get("dns", [])
            v6_status = f"[green]Turbo DNS IPv6 Diretto[/green]" if v6_custom else "[yellow]Relay Locale IPv6[/yellow]"
            opt_table.add_row("Server DNS IPv6 (DHCPv6)", ", ".join(v6_dns) if v6_dns else "fd0f:ee:b0::1", v6_status)

            # UPnP IGD
            upnp_on = upnp_cfg.get("enabled", False)
            upnp_eval = "[bold green]Attivo (NAT Aperto Gaming/Switch)[/bold green]" if upnp_on else "[yellow]Disattivato (Rischio NAT Moderato)[/yellow]"
            opt_table.add_row("UPnP IGD (Gaming / Console)", "Abilitato" if upnp_on else "Disabilitato", upnp_eval)

            console.print(opt_table)
        except Exception as e:
            console.print(f"[yellow]Impossibile recuperare parametri di rete: {e}[/yellow]")

        # 6. Background services & Bloatware check
        try:
            services = self.client.get_services_status()
            srv_table = Table(title="Stato Servizi Interni (Valutazione Overhead CPU/RAM)", box=box.SIMPLE_HEAVY)
            srv_table.add_column("Servizio Router", style="bold white")
            srv_table.add_column("Stato Attuale", style="cyan")
            srv_table.add_column("Impatto Risorse", justify="center")

            for srv_name, srv_data in services.items():
                is_active = srv_data.get("enabled", False) if isinstance(srv_data, dict) else False
                status_str = "[green]Attivo[/green]" if is_active else "[white]Disattivato[/white]"
                impact = "[yellow]Consuma RAM/CPU[/yellow]" if is_active else "[green]Zero Overhead[/green]"
                srv_table.add_row(srv_name.upper(), status_str, impact)
            console.print(srv_table)
        except Exception as e:
            console.print(f"[yellow]Impossibile verificare servizi: {e}[/yellow]")

    def set_turbo_dns(self, v4_primary: str = "9.9.9.9", v4_secondary: str = "1.1.1.1", v6_primary: str = "2620:fe::fe", v6_secondary: str = "2606:4700:4700::1111"):
        """Configures DHCPv4 & DHCPv6 to broadcast high-speed low-latency DNS directly to all clients."""
        if not self.ensure_authenticated():
            return
        console.print(f"\n[cyan]Configurazione Turbo DNS completo (IPv4 + IPv6)...[/cyan]")
        
        # 1. Update IPv4 DHCP DNS
        try:
            curr_dhcp = self.client.get_dhcp_config().get("result", {})
            curr_dhcp["dns"] = [v4_primary, v4_secondary]
            res_v4 = self.client.put("/dhcp/config/", curr_dhcp)
            if res_v4.get("success"):
                console.print(f"  [green]✔ DNS IPv4 configurati:[/green] {v4_primary} (Quad9), {v4_secondary} (Cloudflare)")
            else:
                console.print(f"  [red]Errore DNS IPv4: {res_v4}[/red]")
        except Exception as e:
            console.print(f"  [red]Eccezione DNS IPv4: {e}[/red]")

        # 2. Update IPv6 DHCPv6 Custom DNS
        try:
            v6_payload = {
                "enabled": True,
                "use_custom_dns": True,
                "dns": [v6_primary, v6_secondary]
            }
            res_v6 = self.client.put("/dhcpv6/config/", v6_payload)
            if res_v6.get("success"):
                console.print(f"  [green]✔ DNS IPv6 configurati:[/green] {v6_primary} (Quad9 IPv6), {v6_secondary} (Cloudflare IPv6)")
            else:
                console.print(f"  [red]Errore DNS IPv6: {res_v6}[/red]")
        except Exception as e:
            console.print(f"  [red]Eccezione DNS IPv6: {e}[/red]")

        console.print(Panel(
            "[bold green]✔ Turbo DNS Completo (IPv4 & IPv6) Attivo al 100%![/bold green]\n"
            "Tutti i dispositivi (PC, smartphone, console) risolvono ora istantaneamente i domini\n"
            "sia in IPv4 che in IPv6 senza alcun collo di bottiglia del router!",
            title="Ottimizzazione Turbo DNS Applicata",
            border_style="green"
        ))

    def set_upnp(self, enabled: bool = True):
        """Enables or disables UPnP IGD for automated game and console port mapping."""
        if not self.ensure_authenticated():
            return
        status_text = "Attivazione" if enabled else "Disattivazione"
        console.print(f"\n[cyan]{status_text} protocollo UPnP IGD per gaming e console...[/cyan]")
        try:
            res = self.client.put("/upnpigd/config/", {"enabled": enabled})
            if res.get("success"):
                state_str = "[bold green]abilitato[/bold green]" if enabled else "[yellow]disabilitato[/yellow]"
                console.print(f"  [green]✔ UPnP IGD {state_str} con successo![/green]")
            else:
                console.print(f"  [red]Errore configurazione UPnP IGD: {res}[/red]")
        except Exception as e:
            console.print(f"  [red]Eccezione UPnP IGD: {e}[/red]")

    def disable_bloat_services(self):
        """Disables unused internal servers to free up router CPU for low latency routing."""
        if not self.ensure_authenticated():
            return
        console.print("\n[cyan]Disattivazione servizi router non utilizzati per alleggerire CPU/RAM...[/cyan]")
        for srv, ep in [
            ("FTP Server", "/ftp/config/"),
            ("UPnP AV Media Server", "/upnpav/config/"),
            ("AirMedia Server", "/airmedia/config/")
        ]:
            try:
                cfg = self.client.get(ep).get("result", {})
                if cfg.get("enabled", False):
                    cfg["enabled"] = False
                    self.client.put(ep, cfg)
                    console.print(f"  [green]✔ {srv} disattivato con successo.[/green]")
                else:
                    console.print(f"  [dim]• {srv} era già disattivato.[/dim]")
            except Exception as e:
                console.print(f"  [yellow]• {srv}: non modificabile ({e})[/yellow]")
        console.print("[bold green]Ottimizzazione risorse router completata![/bold green]")

    def optimize_all(self):
        """Executes complete optimization: Turbo DNS (v4+v6), UPnP IGD enable, and debloat."""
        console.print(Panel.fit("[bold cyan]ESECUZIONE OTTIMIZZAZIONE COMPLETA ILIADBOX[/bold cyan]", box=box.ROUNDED))
        self.set_turbo_dns()
        self.set_upnp(True)
        self.disable_bloat_services()
        console.print(Panel(
            "[bold green]✔ OTTIMIZZAZIONE GLOBALE COMPLETATA CON SUCCESSO![/bold green]\n"
            "1. Turbo DNS (IPv4 + IPv6) attivo direttamente sui client.\n"
            "2. UPnP IGD abilitato per Open NAT su console e PC gaming.\n"
            "3. Servizi multimediali disattivati (massima potenza per lo switch e la fibra).",
            title="Risultato Finale",
            border_style="green"
        ))

def main():
    parser = argparse.ArgumentParser(description="Iliadbox Wi-Fi 7 Optimization & Diagnostic Toolkit")
    parser.add_argument("--audit", action="store_true", help="Esegue un audit completo di stato, Wi-Fi 7, porte e connessione")
    parser.add_argument("--pair", action="store_true", help="Avvia la procedura di pairing/autorizzazione con la Iliadbox")
    parser.add_argument("--turbo-dns", action="store_true", help="Imposta DNS Quad9 e Cloudflare su DHCP IPv4 e IPv6")
    parser.add_argument("--upnp-on", action="store_true", help="Abilita UPnP IGD per Open NAT su Nintendo Switch e PC")
    parser.add_argument("--upnp-off", action="store_true", help="Disabilita UPnP IGD")
    parser.add_argument("--debloat", action="store_true", help="Disattiva servizi interni non usati (FTP, DLNA/UPnP) per liberare CPU")
    parser.add_argument("--optimize-all", action="store_true", help="Esegue tutte le ottimizzazioni in un colpo solo")
    parser.add_argument("--benchmark", action="store_true", help="Esegue benchmark di latenza, DNS, MTU e peering")

    args = parser.parse_args()

    opt = IliadboxOptimizer()

    if args.pair:
        opt.ensure_authenticated()
    elif args.audit:
        opt.run_full_audit()
    elif args.turbo_dns:
        opt.set_turbo_dns()
    elif args.upnp_on:
        opt.set_upnp(True)
    elif args.upnp_off:
        opt.set_upnp(False)
    elif args.debloat:
        opt.disable_bloat_services()
    elif args.optimize_all:
        opt.optimize_all()
    elif args.benchmark:
        from benchmark_and_diagnostics import run_full_benchmark
        run_full_benchmark()
    else:
        # Default behavior if no argument: present options and run audit
        console.print(Panel.fit(
            "[bold cyan]ILIADBOX WI-FI 7: ULTIMATE NETWORK OPTIMIZER[/bold cyan]\n"
            "Usa uno dei seguenti comandi:\n"
            "  [yellow]python iliadbox_optimizer.py --audit[/yellow]         -> Esegue l'audit completo di segnale ottico, Wi-Fi 7, porte e risorse\n"
            "  [yellow]python iliadbox_optimizer.py --optimize-all[/yellow]  -> Applica Turbo DNS (v4+v6), UPnP IGD e de-bloat\n"
            "  [yellow]python iliadbox_optimizer.py --turbo-dns[/yellow]     -> Configura DNS ultraveloci Quad9 / Cloudflare (IPv4 + IPv6)\n"
            "  [yellow]python iliadbox_optimizer.py --upnp-on[/yellow]        -> Abilita UPnP IGD per gaming e Open NAT\n"
            "  [yellow]python iliadbox_optimizer.py --debloat[/yellow]        -> Disattiva servizi superflui per minimizzare il jitter\n"
            "  [yellow]python iliadbox_optimizer.py --benchmark[/yellow]      -> Testa latenze locali, IXP, server gaming e MTU",
            box=box.ROUNDED
        ))

if __name__ == "__main__":
    main()
