"""
Network Benchmark and Diagnostics Suite for Iliadbox Wi-Fi 7
Analyzes local link, DNS latency, Italian & European IXP peering, gaming servers, and MTU.
"""

import subprocess
import time
import socket
import re
import sys
from typing import Dict, List, Tuple, Any

# Ensure stdout handles utf-8 safely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import dns.resolver
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console(safe_box=True)

DNS_SERVERS = {
    "Iliadbox Local Relay": "192.168.1.254",
    "Cloudflare (1.1.1.1)": "1.1.1.1",
    "Cloudflare Security (1.1.1.2)": "1.1.1.2",
    "Quad9 Security (9.9.9.9)": "9.9.9.9",
    "Google Public (8.8.8.8)": "8.8.8.8",
    "OpenDNS (208.67.222.222)": "208.67.222.222"
}

TEST_DOMAINS = [
    "google.com",
    "cloudflare.com",
    "amazon.it",
    "github.com",
    "netflix.com"
]

PEERING_TARGETS = {
    "Cloudflare Milan Edge (Anycast)": "1.1.1.1",
    "Google Milan/Rome Edge": "8.8.8.8",
    "Quad9 Milan Edge": "9.9.9.9",
    "AWS Milan (eu-south-1)": "ec2.eu-south-1.amazonaws.com",
    "Valve / Steam EU Core": "155.133.248.1",
    "Riot Games EU Server": "162.249.72.1",
    "Fastly CDN Italy": "fastly.com"
}

def ping_target(host: str, count: int = 4) -> Dict[str, Any]:
    """Runs ping via Windows system ping command with robust multi-language parsing and no console popup."""
    cmd = ["ping", "-n", str(count), "-w", "1000", host]
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            startupinfo=startupinfo,
            creationflags=creationflags
        )
        output = proc.stdout
        
        # Match "durata=15ms", "durata<1ms", "time=15ms", "time<1ms"
        # If <1ms, count as 0.5ms
        times = []
        for m in re.finditer(r"(?:durata|time)([=<])(\d+)ms", output, re.IGNORECASE):
            comp, val = m.group(1), float(m.group(2))
            if comp == "<":
                times.append(0.5)
            else:
                times.append(val)
                
        loss_pct = 100.0
        loss_match = re.search(r"\((\d+)%\s*(?:persi|loss)\)", output, re.IGNORECASE)
        if loss_match:
            loss_pct = float(loss_match.group(1))
        elif times:
            loss_pct = 0.0
        
        if times:
            return {
                "min": min(times),
                "avg": sum(times) / len(times),
                "max": max(times),
                "jitter": max(times) - min(times),
                "loss": loss_pct,
                "success": True
            }
    except Exception:
        pass
    return {"min": 0, "avg": 0, "max": 0, "jitter": 0, "loss": 100.0, "success": False}

def benchmark_dns() -> List[Dict[str, Any]]:
    results = []
    for name, server_ip in DNS_SERVERS.items():
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [server_ip]
        resolver.timeout = 2.0
        resolver.lifetime = 2.0
        
        query_times = []
        errors = 0
        
        for domain in TEST_DOMAINS:
            t0 = time.perf_counter()
            try:
                resolver.resolve(domain, "A")
                dt = (time.perf_counter() - t0) * 1000
                query_times.append(dt)
            except Exception:
                errors += 1
                
        avg_time = sum(query_times) / len(query_times) if query_times else 999.0
        min_time = min(query_times) if query_times else 999.0
        results.append({
            "name": name,
            "ip": server_ip,
            "avg_ms": avg_time,
            "min_ms": min_time,
            "errors": errors
        })
    results.sort(key=lambda x: x["avg_ms"])
    return results

def test_mtu(gateway: str = "192.168.1.254") -> int:
    """Finds maximum non-fragmented packet size on the local link."""
    optimal_size = 1472
    for size in [1472, 1464, 1452, 1400]:
        cmd = ["ping", "-f", "-l", str(size), "-n", "1", "-w", "500", gateway]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if "100%" not in proc.stdout and ("framment" not in proc.stdout.lower() and "fragment" not in proc.stdout.lower()):
            optimal_size = size
            break
    return optimal_size + 28

def run_full_benchmark():
    console.print(Panel.fit("[bold cyan]ILIADBOX WI-FI 7: SUITE DI BENCHMARK E DIAGNOSTICA RETE[/bold cyan]", box=box.ROUNDED))
    
    # 1. Gateway local ping
    console.print("\n[bold yellow][1/4] Analisi Collegamento Locale Iliadbox (192.168.1.254)...[/bold yellow]")
    gw_stats = ping_target("192.168.1.254", count=6)
    if gw_stats["success"]:
        console.print(f"  [green][OK] Connessione locale eccellente:[/green] Latenza Media = [bold]{gw_stats['avg']:.1f} ms[/bold], Jitter = [bold]{gw_stats['jitter']:.1f} ms[/bold], Perdita = [bold]{gw_stats['loss']}%[/bold]")
    else:
        console.print("  [red][X] Errore nel ping verso il gateway locale.[/red]")

    # 2. MTU test
    console.print("\n[bold yellow][2/4] Verifica MTU Locale & Incapsulamento FTTH...[/bold yellow]")
    effective_mtu = test_mtu()
    if effective_mtu >= 1500:
        console.print(f"  [green][OK] MTU Standard 1500 Byte integro[/green] (Nessuna frammentazione pacchetti rilevata)")
    else:
        console.print(f"  [yellow][!] MTU limitato a {effective_mtu} Byte[/yellow] (Possibile overhead di tunneling/MSS)")

    # 3. DNS Benchmark
    console.print("\n[bold yellow][3/4] Benchmark Prestazioni DNS (Risoluzione Domini in ms)...[/bold yellow]")
    dns_res = benchmark_dns()
    
    dns_table = Table(title="Confronto Server DNS", box=box.SIMPLE_HEAVY)
    dns_table.add_column("Provider DNS", style="bold white")
    dns_table.add_column("Indirizzo IP", style="cyan")
    dns_table.add_column("Latenza Media", justify="right")
    dns_table.add_column("Miglior Tempo", justify="right")
    dns_table.add_column("Valutazione", justify="center")

    for r in dns_res:
        avg = r["avg_ms"]
        if avg < 25:
            eval_str = "[bold green]Fulmineo (Consigliato)[/bold green]"
            color_avg = f"[green]{avg:.1f} ms[/green]"
        elif avg < 50:
            eval_str = "[green]Ottimo[/green]"
            color_avg = f"[green]{avg:.1f} ms[/green]"
        elif avg < 80:
            eval_str = "[yellow]Discreto[/yellow]"
            color_avg = f"[yellow]{avg:.1f} ms[/yellow]"
        else:
            eval_str = "[red]Lento (Collo di bottiglia)[/red]"
            color_avg = f"[red]{avg:.1f} ms[/red]"
            
        dns_table.add_row(r["name"], r["ip"], color_avg, f"{r['min_ms']:.1f} ms", eval_str)
    console.print(dns_table)

    # 4. Peering & Gaming targets
    console.print("\n[bold yellow][4/4] Test Latenza Peering Italiano, Nodi CDN e Server Gaming...[/bold yellow]")
    peer_table = Table(title="Latenza verso Nodi Chiave e Gaming", box=box.SIMPLE_HEAVY)
    peer_table.add_column("Destinazione / Servizio", style="bold white")
    peer_table.add_column("Host / IP", style="cyan")
    peer_table.add_column("Min", justify="right")
    peer_table.add_column("Media", justify="right")
    peer_table.add_column("Max / Jitter", justify="right")
    peer_table.add_column("Stato", justify="center")

    for target_name, target_host in PEERING_TARGETS.items():
        st = ping_target(target_host, count=4)
        if st["success"]:
            avg_color = "[green]" if st["avg"] < 25 else ("[yellow]" if st["avg"] < 50 else "[red]")
            peer_table.add_row(
                target_name,
                target_host,
                f"{st['min']:.0f} ms",
                f"{avg_color}{st['avg']:.1f} ms[/]",
                f"{st['max']:.0f} ms (+-{st['jitter']:.0f})",
                "[green]Ottimale[/green]" if st["loss"] == 0 else f"[yellow]{st['loss']}% persi[/yellow]"
            )
        else:
            peer_table.add_row(target_name, target_host, "-", "-", "-", "[red]Non Raggiungibile[/red]")
            
    console.print(peer_table)
    console.print("\n[bold green]Diagnostica di rete completata con successo![/bold green]\n")

if __name__ == "__main__":
    run_full_benchmark()
