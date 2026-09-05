# Guida Completa all'Ottimizzazione Estrema: Iliadbox Wi-Fi 7

Questa suite di strumenti e questa guida tecnica sono progettate per trasformare la tua **Iliadbox Wi-Fi 7** in una centrale di rete scattante, a latenza ultra-bassa, priva di colli di bottiglia e ottimizzata per gaming, streaming 4K/8K ad altissimo bitrate e throughput multi-gigabit.

---

## 1. Architettura e Diagnostica Effettuata

Dai primi test diagnostici condotti sulla tua linea:
- **Gateway Locale**: `192.168.1.254` (Latenza: `< 0.5 ms`, Jitter: `0.0 ms`, 0% packet loss)
- **Modello Hardware**: `iliadbox (r1)` / `FreeboxServer8,1` (Versione con supporto Wi-Fi 7 nativo a 320 MHz / 160 MHz)
- **API Rilevata**: Freebox OS v15.0 (Iliadbox OS)
- **MTU Locale**: 1500 Byte (Nessuna frammentazione rilevata)
- **Risoluzione DNS**:
  - Relay locale Iliadbox standard: `~75-80 ms` (collo di bottiglia iniziale)
  - Quad9 Security (`9.9.9.9` - Nodo di Milano): `~5-6 ms` ⚡ **13x più veloce!**
  - Cloudflare (`1.1.1.1` - Anycast Milano): `~14-15 ms`
  - Google (`8.8.8.8` - Milano/Roma): `~4.8 ms`

---

## 2. Il Piano d'Azione Passo-Passo per Prestazioni Top

### Passo 1: Associazione API (Pairing con la Iliadbox)
Per consentire agli script di monitorare e applicare le ottimizzazioni alla tua Iliadbox in sicurezza:
```bash
python iliadbox_optimizer.py --pair
```
> ℹ️ **Cosa fare sul display della Iliadbox**:
> Sullo schermino OLED frontale apparirà una richiesta di autorizzazione per **"Iliadbox Ultra Optimizer"**.
> Tocca la freccia destra o premi **"Sì"** per confermare. Verrà generato e salvato localmente un token crittografico sicuro (`.iliadbox_token.json`).

---

### Passo 2: Audit Completo di Stato e Parametri Ottici
```bash
python iliadbox_optimizer.py --audit
```
Questo comando analizzerà:
1. **Potenza Ottica Ricevuta (SFP RX dBm)**: Il segnale FTTH deve essere compreso idealmente tra `-8 dBm` e `-24 dBm`. Valori superiori a `-25 dBm` indicano sporcizia sul connettore fibra ottica o attenuazione eccessiva.
2. **Temperature e Ventola**: Verifica che la CPU sia sotto i 65°C per evitare throttling termico dello switch interno.
3. **Controllo Range Porte IPv4 (MAP-E vs Full Stack)**.

---

### Passo 3: Sblocco "IPv4 Full Stack" tramite Chiamata al 177
Iliad in Italia utilizza la tecnologia **MAP-E** (Address plus Port): di default, un singolo indirizzo IPv4 pubblico viene condiviso tra 4 utenti, assegnando a ciascuno solo 1/4 delle porte.
Dall'audit effettuato, la tua linea ha attualmente assegnato il range **57344 - 65535** (solo 8.192 porte su 65.535).

> [!NOTE]
> **Non esiste un pulsante fai-da-te nell'Area Personale**: per ottenere l'IPv4 Full Stack è necessario chiamare l'assistenza tecnica telefonica Iliad al **177**. L'operazione è **completamente gratuita**.

**Cosa dire all'operatore del 177**:
1. Chiama il **177** (gratuito da linea Iliad).
2. Spiega all'operatore:
   > *"Buongiorno, ho la fibra Iliadbox e necessito dell'assegnazione dell'**IPv4 Full Stack** (tutte le 65.535 porte) per motivi di telecamere/videosorveglianza, allarme e gaming, in quanto il mio attuale range limitato (57344-65535) blocca l'apertura delle porte standard."*
3. L'operatore aprirà un ticket tecnico di secondo livello. In 24-48 ore l'IPv4 Full Stack verrà assegnato e basterà un semplice riavvio della Iliadbox.

---

### Passo 4: Turbo DNS Diretto (IPv4 + IPv6) (Risoluzioni a 5 ms)
Di default, i dispositivi connessi inviano le richieste DNS alla Iliadbox (`192.168.1.254` e `fd0f:ee:b0::1`), che poi fa da relay ai server Iliad (tempo medio ~75 ms). Inoltre, smartphone e PC moderni usano preferenzialmente IPv6 (RFC 8305):
Con il nostro script, forziamo sia il server DHCP IPv4 sia il DHCPv6 a comunicare direttamente ai client i resolver Anycast più veloci e sicuri:
- **IPv4**: Quad9 Security (`9.9.9.9`) e Cloudflare (`1.1.1.1`)
- **IPv6**: Quad9 Security (`2620:fe::fe`) e Cloudflare (`2606:4700:4700::1111`)

```bash
python iliadbox_optimizer.py --turbo-dns
```
**Risultato**: Navigazione web scattante, zero colli di bottiglia del router interno su IPv4 e IPv6, protezione anti-phishing/malware integrata alla radice.

---

### Passo 5: Gaming & Open NAT con UPnP IGD
Se in casa ci sono console da gioco (es. **Nintendo Switch**) o PC gaming, il protocollo **UPnP IGD** permette ai giochi di negoziare automaticamente l'apertura dinamica delle porte nel range assegnato (57344-65535), evitando l'errore di NAT Stretto / Type D o F.
```bash
python iliadbox_optimizer.py --upnp-on
```

---

### Passo 6: Ottimizzazione Avanzata del Wi-Fi 7 (Access Point Unificato)
Come da tua preferenza, abbiamo mantenuto **un solo punto di accesso unificato (Single SSID)**:
1. **Smart Connect & Band Steering Attivi**:
   - Una sola rete visibile in tutta la casa (`iliadbox-2560AD`).
   - Sarà la Iliadbox a smistare automaticamente i dispositivi veloci sui 5 GHz / Wi-Fi 7 (come il tuo Galaxy S23 Ultra a ~1.9 Gbps) e la domotica sui 2.4 GHz.
2. **Wi-Fi Power Saving DISATTIVATO**:
   - Abbiamo spento il risparmio energetico delle antenne. Le radio Wi-Fi 7 non entrano mai in stati di micro-sleep (DTIM), azzerando i picchi di jitter e stabilizzando il ping.
3. **Larghezza di Canale 160 MHz Attiva**:
   - La banda 5 GHz è già configurata a **160 MHz** (massima larghezza supportata) sui canali DFS puliti (Ch. 128/124).
4. **Crittografia Ibrida WPA2 / WPA3-Personal**:
   - Permette ai dispositivi Wi-Fi 7/6 moderni di usare la crittografia ad alta efficienza WPA3-SAE, garantendo allo stesso tempo la compatibilità con i vecchi dispositivi WPA2.

---

### Passo 7: Disattivazione Servizi Inutilizzati (Zero Jitter & CPU Libera)
Se non hai un hard disk USB o pennetta collegata alla Iliadbox per fare da NAS o server multimediale, disattivare i demoni in background riduce il carico sui core della CPU dell'Iliadbox:
```bash
python iliadbox_optimizer.py --debloat
```
Disattiva:
- Server FTP interno
- Server multimediale UPnP AV / DLNA
- AirMedia video streaming server

> 💡 **Comando Tutto-in-Uno**: per applicare Turbo DNS (v4+v6), UPnP IGD e de-bloat contemporaneamente:
> ```bash
> python iliadbox_optimizer.py --optimize-all
> ```

---

### Passo 8: Nota Hardware sulle Porte Ethernet (1 Gbps vs 2.5 Gbps)
Dall'audit della Iliadbox:
- La Iliadbox possiede una porta contrassegnata come **Porta 1 (2.5 Gbps)** e due porte standard a **1 Gbps** (Porte 2 e 3).
- Attualmente il tuo PC è collegato alla **Porta 3** a 1000 Mbps con una scheda di rete Gigabit *Realtek PCIe GbE*.
- Se in futuro installerai sul PC una scheda di rete 2.5 GbE (scheda PCIe interna o adattatore USB-C a 2.5G), collegando il cavo alla **Porta 1** potrai scaricare fino a **2.500 Mbps reali** sfruttando a pieno la fibra Iliad 5 Gbps!

---

### Passo 9: Come Funziona il DNS Anycast (Milano vs Catania)
- **Perché "Milano" nel benchmark?**
  I DNS impostati (`9.9.9.9`, `1.1.1.1`) utilizzano la tecnologia di instradamento globale **BGP Anycast**. Lo stesso indirizzo IP risponde contemporaneamente da decine di data center in tutto il mondo. Nel tuo caso risponde dal nodo di Milano (MIX - Milan Internet eXchange) perché Iliad ha la sua centrale di peering principale a Milano e la tua connessione aggancia quel punto di scambio in soli ~5 ms.
- **Se fossi stato a Catania?**
  L'indirizzo IP del DNS **non andrebbe cambiato**. Sarebbe sempre `9.9.9.9` e `1.1.1.1`. Il protocollo BGP di Internet instrada automaticamente i pacchetti al PoP più vicino (ad esempio i punti di scambio del Sud Italia/Sicily Hub o Roma NAMEX). L'unica differenza è data dalla fisica della fibra ottica: la distanza chilometrica tra Sicilia e i punti di interscambio principali aggiunge ~15-20 ms di tempo di viaggio della luce nel cavo, ma l'impostazione DNS ottimale rimane identica.

---

## 3. Riepilogo Script Disponibili nella Cartella

| File | Scopo |
| :--- | :--- |
| `iliadbox_client.py` | Libreria Python nativa per interagire con le API REST v15 della Iliadbox. |
| `iliadbox_optimizer.py` | CLI per pairing, audit completo, Turbo DNS (v4+v6), UPnP IGD e de-bloat. |
| `benchmark_and_diagnostics.py` | Suite per test di latenza, jitter, DNS resolver a confronto, nodi gaming e MTU. |
| `freebox-api/` | Repository ufficiale clonata per riferimento completo a tutte le funzioni firmware. |
