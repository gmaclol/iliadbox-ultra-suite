# ⚡ Iliadbox Ultra Suite

<p align="center">
  <img src="https://raw.githubusercontent.com/gmaclol/iliadbox-ultra-suite/main/web/assets/banner.png" alt="Iliadbox Ultra Suite Banner" width="100%" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <strong>Applicazione Desktop standalone per il monitoraggio in tempo reale, la diagnostica avanzata e l'ottimizzazione estrema della Iliadbox (Wi-Fi 7, Wi-Fi 6 e FTTH EPON 5 Gbps).</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?style=for-the-badge&logo=windows" alt="Windows"/>
  <img src="https://img.shields.io/badge/Hardware-Iliadbox%20Wi--Fi%207%20%2F%206-red?style=for-the-badge" alt="Iliadbox"/>
  <img src="https://img.shields.io/badge/Backend-FastAPI%20%2B%20Uvicorn-009688?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Frontend-WebView2%20Edge%20Chromium-informational?style=for-the-badge&logo=microsoft-edge" alt="WebView2"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"/>
</p>

---

## 🌟 Caratteristiche Principali

### 📊 1. Telemetria Live & Stato Fibra Ottica FTTH
- **Potenza Ottica Ricevuta (SFP RX / TX)**: Monitoraggio in dBm del segnale ottico con indicatore dinamico dello stato di salute della fibra.
- **Rilevamento Profilo di Rete**: Indicazione istantanea della tecnologia di rete (EPON 5 Gbps / 700-900 Mbps, GPON), indirizzo IPv4 pubblico, range di porte e prefisso IPv6 nativo.
- **Switch Ethernet Multi-Gigabit**: Diagnostica dello stato e della velocità di negoziazione di ogni singola porta fisica (Porta 2.5 GbE e porte 1 GbE).

### ⚡ 2. Centro di Ottimizzazione a 1-Click
- **Turbo DNS Diretto (IPv4 & IPv6 DHCP)**:
  - Bypassa il relay DNS locale della Iliadbox (che introduce fino a 70-80 ms di overhead) distribuendo direttamente ai client della rete i server Anycast ad altissime prestazioni (Quad9 `9.9.9.9` con filtri malware e Cloudflare `1.1.1.1`).
  - Configura automaticamente anche il server DHCPv6 (`2620:fe::fe` e `2606:4700:4700::1111`) per garantire risoluzioni a ~5 ms su smartphone e dispositivi moderni.
- **UPnP IGD per Gaming & Console**:
  - Abilita il protocollo *Universal Plug and Play Internet Gateway Device*.
  - Consente a Nintendo Switch, PlayStation 5, Xbox e PC di negoziare in autonomia le porte necessarie per ottenere **NAT Aperto (Tipo A / Tipo 1)** senza dover configurare manualmente decine di regole di port forwarding.
- **De-bloat Servizi Inutilizzati**:
  - Disattiva i server interni non utilizzati (FTP, Condivisioni SMB, Download Manager / Torrent) per liberare memoria RAM e cicli di clock della CPU della Iliadbox, massimizzando il throughput di instradamento.

### 📡 3. Radar Wi-Fi 7 & Analisi Client
- **Spettro 5 GHz a 160 MHz**: Sfrutta tutta la larghezza di banda disponibile sulle frequenze a 5 GHz, supportando modulazioni 4096-QAM e link rate Wi-Fi 7 superiori a 1.9 Gbps.
- **Client Link Monitor**: Elenco in tempo reale di tutti i dispositivi connessi (con nome host, indirizzo IP, MAC vendor, livello del segnale RSSI in dBm, standard Wi-Fi 802.11be/ax/ac/n e velocità di negoziazione in Mbps).

### 🔄 4. Resoconto "Before & After" & Live Benchmark
- Dashboard di confronto diretto tra lo stato di default di fabbrica e lo stato post-ottimizzazione.
- Test in tempo reale della latenza di rete (ping a gateway locale, nodi Anycast Milano/Roma, server Valve/Steam EU) con esecuzione invisibile in background.

---

## 🖥️ Esperienza Desktop Standalone

`Iliadbox Ultra Suite` è distribuita come **eseguibile autonomo per Windows (`Iliadbox.exe`)**:
- **Server Interno Autonomo**: Il processo exe gestisce direttamente il server API locale e la chiusura delle risorse allo spegnimento.
- **Scansione e Invenzione Dinamica della Porta**: Verifica in sequenza le porte standard (`8080`, `8081`, `8082`, `8888`, `5000`, `3000`, `9000`, `9090`, `7777`). Qualora fossero tutte occupate da altri servizi, interroga il sistema operativo per **inventare una porta libera effimera** e avviare il servizio senza errori.
- **Zero Finestre Console o Popup CMD**: Tutti i comandi di rete sono incapsulati con flag `CREATE_NO_WINDOW` e non sfarfallano mai sullo schermo.
- **Scorciatoia Diretta Permessi**: Pulsante integrato che apre con un click la schermata `http://192.168.1.254/#app.access` per consentire l'autorizzazione di modifica parametri in pochi secondi.

---

## 🚀 Download & Guida Rapida

### Metodo 1: Download dell'eseguibile (Consigliato per la maggior parte degli utenti)
1. Vai nella sezione **[Releases](https://github.com/gmaclol/iliadbox-ultra-suite/releases)** del progetto.
2. Scarica il file **`Iliadbox.exe`**.
3. Avvialo con un doppio clic: l'applicazione si aprirà in una finestra desktop nativa.

### Metodo 2: Esecuzione da sorgente (Python)
Se preferisci eseguire l'applicazione tramite Python:

```bash
# 1. Clona la repository
git clone https://github.com/gmaclol/iliadbox-ultra-suite.git
cd iliadbox-ultra-suite

# 2. Installa le dipendenze
pip install fastapi uvicorn requests pywebview dnspython rich pydantic

# 3. Avvia la suite
python app_desktop.py
# oppure fai doppio click su start_dashboard.bat
```

---

## 🔐 Primo Avvio & Associazione (Pairing)

Alla prima apertura dell'applicazione:
1. L'app invierà una richiesta sicura alla tua Iliadbox.
2. **Guarda lo schermo touch OLED della tua Iliadbox**: comparirà la scritta *"Richiesta di autorizzazione per Iliadbox Ultra Suite"*.
3. **Premi CONFERMA** (o la freccia destra) sul display per associare l'app.
4. Per applicare le ottimizzazioni (DNS, UPnP, ecc.), clicca sul pulsante **"🔗 Vai a Gestione Accessi (192.168.1.254)"** nella suite, accedi alla Iliadbox e spunta **"Modifica delle impostazioni"** sotto la voce *Iliadbox Ultra Suite*.
5. Clicca su **"🔄 Ricontrolla Permessi"**: sei pronto per ottimizzare la tua rete!

---

## 🛠️ Tecnologie Utilizzate

- **Backend**: Python 3.12, FastAPI, Uvicorn (con runtime isolato e configurazione zero-log)
- **Frontend**: HTML5, Vanilla JavaScript, Modern Cyber/Glassmorphism CSS con animazioni GPU-accelerate
- **Desktop Runtime**: Microsoft Edge WebView2 via `pywebview` & fallback standalone app mode
- **Network Protocol**: Freebox OS / Iliadbox Open REST API v15 (HMAC-SHA1 challenge-response auth)

---

## 📄 Licenza

Questo progetto è distribuito sotto licenza **MIT**. Consulta il file `LICENSE` per ulteriori dettagli.
Non affiliato ufficialmente con Iliad Italia S.p.A. o Free SAS.
