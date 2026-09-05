/**
 * Iliadbox Cyber Dashboard - Client Engine (Vanilla JS)
 * Handles real-time polling, interactive tab switches, pairing handshake,
 * 1-click optimization executions, terminal logs, and Before & After analytics.
 */

let state = {
  activeTab: 'telemetry',
  auth: null,
  status: null,
  isOptimizing: false,
  pollTimer: null
};

// ---------------- Initialization ----------------
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  checkAuthAndLoad();
  // Live polling every 4 seconds
  state.pollTimer = setInterval(loadStatus, 4000);
});

// ---------------- Tab Navigation ----------------
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.toggle('active', pane.id === `tab-${tabId}`);
  });

  if (tabId === 'before-after') {
    loadBeforeAfter();
  }
}

// ---------------- Auth & Pairing Flow ----------------
async function checkAuthAndLoad() {
  try {
    const res = await fetch('/api/auth_status');
    const auth = await res.json();
    state.auth = auth;

    const authRibbon = document.getElementById('val-auth-status');
    const authDot = document.querySelector('.status-dot');

    if (!auth.online) {
      authRibbon.textContent = 'Disconnesso';
      authDot.style.background = '#ff0055';
      logTerminal('error', `[BOX OFFLINE] ${auth.error}`);
      return;
    }

    if (!auth.authenticated) {
      authRibbon.textContent = 'Da Associare';
      authDot.style.background = '#ffb703';
      showPairingModal();
      return;
    }

    authRibbon.textContent = 'Autenticato';
    authDot.style.background = 'var(--emerald-neon)';

    // Check settings permission
    const permWarning = document.getElementById('permission-warning');
    if (auth.has_token && !auth.has_settings_permission) {
      permWarning.classList.remove('hidden');
    } else {
      permWarning.classList.add('hidden');
    }

    // Load full status
    loadStatus();
    loadBeforeAfter();
  } catch (err) {
    console.error('Error checking auth:', err);
  }
}

async function openIliadboxAdmin() {
  try {
    await fetch('/api/open_admin', { method: 'POST' });
    logTerminal('info', '[SHORTCUT] Apertura schermata Gestione Accessi Iliadbox (http://192.168.1.254/#app.access)...');
  } catch (e) {
    console.error('Failed to call /api/open_admin:', e);
  }
  try {
    window.open('http://192.168.1.254/#app.access', '_blank');
  } catch (e) {
    // Ignore fallback errors
  }
}

async function showPairingModal() {
  const modal = document.getElementById('pairing-modal');
  modal.classList.remove('hidden');

  try {
    const res = await fetch('/api/pair/request', { method: 'POST' });
    const data = await res.json();

    if (!data.success) {
      document.getElementById('pairing-status-text').textContent = `Errore: ${data.error}`;
      return;
    }

    const trackId = data.track_id;
    pollPairingStatus(trackId);
  } catch (err) {
    document.getElementById('pairing-status-text').textContent = `Errore di connessione: ${err}`;
  }
}

async function pollPairingStatus(trackId) {
  const statusEl = document.getElementById('pairing-status-text');
  let attempts = 0;
  const maxAttempts = 40;

  const interval = setInterval(async () => {
    attempts++;
    try {
      const res = await fetch(`/api/pair/status/${trackId}`);
      const data = await res.json();

      if (data.status === 'granted') {
        clearInterval(interval);
        statusEl.textContent = '✔ Autorizzazione concessa dall\'Iliadbox!';
        logTerminal('success', '[AUTH] Autorizzazione concessa dall\'Iliadbox! Token salvato.');
        setTimeout(() => {
          closePairingModal();
          checkAuthAndLoad();
        }, 1500);
      } else if (data.status === 'denied') {
        clearInterval(interval);
        statusEl.textContent = '❌ Richiesta rifiutata sul display della Iliadbox.';
      } else if (attempts >= maxAttempts) {
        clearInterval(interval);
        statusEl.textContent = '⏱️ Tempo scaduto per la conferma.';
      }
    } catch (e) {
      // Retry
    }
  }, 1500);
}

function closePairingModal() {
  document.getElementById('pairing-modal').classList.add('hidden');
}

// ---------------- Telemetry & Status ----------------
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();
    state.status = data;

    renderHeaderRibbon(data);
    renderTelemetryTab(data);
    renderSwitchPorts(data.switch_ports || []);
    renderWifiStations(data.wifi || {});
    updateOptimizerModuleStatus(data);
  } catch (err) {
    console.error('Status fetch error:', err);
  }
}

function renderHeaderRibbon(data) {
  const sys = data.system || {};
  const conn = data.connection || {};

  document.getElementById('val-box-model').textContent = sys.board_name || 'iliadbox (r1)';
  document.getElementById('val-optical-rx').textContent = conn.sfp_rx_dbm ? `${conn.sfp_rx_dbm.toFixed(2)} dBm` : '-- dBm';
  document.getElementById('val-wan-ip').textContent = conn.is_full_stack ? 'IPv4 Full Stack' : `IPv4 MAP-E (${conn.ports_count || 8192}p)`;
}

function renderTelemetryTab(data) {
  const conn = data.connection || {};
  const sys = data.system || {};

  // Optical gauge
  if (conn.sfp_rx_dbm) {
    document.getElementById('gauge-sfp-rx').textContent = conn.sfp_rx_dbm.toFixed(2);
    document.getElementById('val-sfp-tx').textContent = `${conn.sfp_tx_dbm.toFixed(2)} dBm`;
    document.getElementById('badge-optical-health').textContent = conn.optical_health || 'Segnale Ottimale';
  }

  // Bandwidth rates
  document.getElementById('live-rate-down').innerHTML = `${conn.rate_down_kb || 0.0} <span class="unit">KB/s</span>`;
  document.getElementById('live-rate-up').innerHTML = `${conn.rate_up_kb || 0.0} <span class="unit">KB/s</span>`;
  
  // Thermals & Uptime
  const uptimeHours = (sys.uptime_seconds || 0) / 3600;
  document.getElementById('val-router-uptime').textContent = `Uptime: ${uptimeHours.toFixed(1)}h`;
  document.getElementById('val-cpu-temp').textContent = sys.temp_cpu ? `${sys.temp_cpu}°C` : 'Normale';
  document.getElementById('val-firmware').textContent = sys.firmware || '4.9.18.2';

  // MAP-E section
  document.getElementById('val-public-ipv4').textContent = conn.ipv4 || 'N/A';
  const pr = conn.ipv4_port_range || [57344, 65535];
  document.getElementById('val-port-range').textContent = `${pr[0]} - ${pr[1]} (${conn.ports_count || 8192} porte)`;
  document.getElementById('val-public-ipv6').textContent = conn.ipv6 || 'N/A';

  const badgeMape = document.getElementById('badge-mape-status');
  if (conn.is_full_stack) {
    badgeMape.textContent = 'IPv4 Full Stack (Tutte le porte aperte)';
    badgeMape.className = 'badge badge-success';
  } else {
    badgeMape.textContent = 'MAP-E (1/4 Porte Condivise)';
    badgeMape.className = 'badge badge-purple';
  }

  // Active port bar
  const startPct = (pr[0] / 65535) * 100;
  const widthPct = ((pr[1] - pr[0] + 1) / 65535) * 100;
  const bar = document.getElementById('port-bar-active');
  if (bar) {
    bar.style.left = `${startPct}%`;
    bar.style.width = `${Math.max(widthPct, 3)}%`;
  }
}

function renderSwitchPorts(ports) {
  const container = document.getElementById('switch-ports-container');
  if (!container) return;

  if (!ports || ports.length === 0) {
    container.innerHTML = '<p class="dim">Nessuna porta rilevata.</p>';
    return;
  }

  container.innerHTML = ports.map(p => {
    const isUp = p.link;
    const is25G = p.is_2_5g;
    const devName = p.devices && p.devices.length ? p.devices.join(', ') : 'Nessun dispositivo';

    return `
      <div class="physical-port-card ${isUp ? 'port-up' : ''} ${is25G ? 'is-25g' : ''}">
        <div class="port-card-top">
          <span class="port-name">${p.name || 'Ethernet'}</span>
          <span class="port-status-led ${isUp ? 'active' : ''}"></span>
        </div>
        <div class="port-speed-badge">${isUp ? `${p.speed} Mbps` : 'Non collegato'}</div>
        <div class="port-device-name" title="${devName}">💻 ${devName}</div>
        <span class="port-cap-tag ${is25G ? 'highlight-25g' : ''}">
          ${is25G ? '⚡ Porta 2.5 Gbps' : '1.0 Gbps'}
        </span>
      </div>
    `;
  }).join('');
}

function renderWifiStations(wifiData) {
  const tbody = document.getElementById('wifi-stations-tbody');
  const countEl = document.getElementById('val-stations-count');
  const stations = wifiData.stations || [];

  if (countEl) countEl.textContent = `${stations.length} Dispositivi`;
  if (!tbody) return;

  if (stations.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center dim">Nessun dispositivo Wi-Fi attivo al momento.</td></tr>';
    return;
  }

  tbody.innerHTML = stations.map(st => {
    const sigClass = st.signal_dbm > -65 ? 'text-emerald' : (st.signal_dbm > -75 ? 'text-cyan' : 'text-purple');
    const stdBadge = st.raw_standard === 'be' ? '<span class="badge badge-cyan">Wi-Fi 7</span>' :
                     st.raw_standard === 'ax' ? '<span class="badge badge-success">Wi-Fi 6</span>' :
                     `<span class="badge badge-outline">${st.standard}</span>`;

    return `
      <tr>
        <td><strong>${st.hostname}</strong><div class="dim" style="font-size: 11px;">${st.mac || ''}</div></td>
        <td><span class="${sigClass} font-mono">${st.signal_dbm} dBm</span></td>
        <td><span class="font-mono">${st.bitrate_mbps} Mbps</span></td>
        <td>${stdBadge}</td>
        <td><span class="font-mono dim">${(st.band || '5g').toUpperCase()}</span></td>
      </tr>
    `;
  }).join('');
}

function updateOptimizerModuleStatus(data) {
  const s = data.settings || {};
  const wifi = data.wifi || {};

  const dnsStatus = document.getElementById('status-turbo-dns');
  if (dnsStatus) {
    dnsStatus.innerHTML = (s.dhcp_v4_is_turbo && s.dhcp_v6_is_turbo) ?
      '<span class="text-emerald">✔ Attivo al 100% (IPv4 + IPv6)</span>' :
      '<span class="text-cyan">Parziale o Relay Locale</span>';
  }

  const upnpStatus = document.getElementById('status-upnp');
  const btnUpnp = document.getElementById('btn-toggle-upnp');
  if (upnpStatus && btnUpnp) {
    if (s.upnp_enabled) {
      upnpStatus.innerHTML = '<span class="text-emerald">✔ Abilitato (Open NAT)</span>';
      btnUpnp.textContent = 'Disattiva UPnP';
    } else {
      upnpStatus.innerHTML = '<span class="text-purple">Disabilitato</span>';
      btnUpnp.textContent = 'Attiva UPnP';
    }
  }

  const wifiStatus = document.getElementById('status-wifi-tuning');
  if (wifiStatus) {
    wifiStatus.innerHTML = (!wifi.power_saving) ?
      '<span class="text-emerald">✔ Power Saving Spento (Zero Jitter)</span>' :
      '<span class="text-purple">Risparmio Attivo</span>';
  }

  const debloatStatus = document.getElementById('status-debloat');
  if (debloatStatus) {
    debloatStatus.innerHTML = (s.services_debloated) ?
      '<span class="text-emerald">✔ Servizi Spenti (Zero Overhead)</span>' :
      '<span class="text-purple">Servizi Attivi</span>';
  }
}

// ---------------- 1-Click Optimizer Trigger ----------------
async function triggerOptimization(action) {
  if (state.isOptimizing) return;
  state.isOptimizing = true;

  const btn = document.getElementById('btn-optimize-all');
  if (btn) btn.classList.add('loading');

  logTerminal('system', `[TUNING] Avvio operazione: ${action.toUpperCase()}...`);

  try {
    const res = await fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action, upnp_state: true })
    });

    const data = await res.json();
    if (data.success && data.logs) {
      data.logs.forEach(l => {
        logTerminal(l.status, `[${l.step}] ${l.msg}`);
      });
      logTerminal('success', '✔ Operazione completata con successo sulla Iliadbox!');
    } else {
      logTerminal('error', `Errore ottimizzazione: ${JSON.stringify(data)}`);
    }

    // Refresh telemetry and before-after
    await loadStatus();
    await loadBeforeAfter();
  } catch (err) {
    logTerminal('error', `Eccezione di rete: ${err}`);
  } finally {
    state.isOptimizing = false;
    if (btn) btn.classList.remove('loading');
  }
}

async function toggleUpnp() {
  const current = state.status?.settings?.upnp_enabled || false;
  const target = !current;
  logTerminal('system', `[UPNP] Richiesta impostazione UPnP a: ${target ? 'ATTIVO' : 'DISATTIVATO'}`);

  try {
    const res = await fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'upnp', upnp_state: target })
    });
    const data = await res.json();
    if (data.logs) {
      data.logs.forEach(l => logTerminal(l.status, l.msg));
    }
    loadStatus();
    loadBeforeAfter();
  } catch (err) {
    logTerminal('error', `Errore UPnP: ${err}`);
  }
}

// ---------------- Terminal Log Helper ----------------
function logTerminal(type, text) {
  const term = document.getElementById('terminal-output');
  if (!term) return;

  const line = document.createElement('div');
  line.className = `term-line ${type}`;
  const now = new Date().toLocaleTimeString();
  line.textContent = `[${now}] ${text}`;
  term.appendChild(line);
  term.scrollTop = term.scrollHeight;
}

function clearTerminal() {
  const term = document.getElementById('terminal-output');
  if (term) term.innerHTML = '<div class="term-line system">[SYSTEM] Log ripulito.</div>';
}

// ---------------- Before & After Module ----------------
async function loadBeforeAfter() {
  const container = document.getElementById('comparison-cards-container');
  if (!container) return;

  try {
    const res = await fetch('/api/before_after');
    const data = await res.json();
    const list = data.comparison || [];

    container.innerHTML = list.map(item => {
      const isOpt = item.active;
      return `
        <div class="cyber-card glass-panel comparison-card ${isOpt ? 'is-optimized' : ''}">
          <div class="comp-header">
            <span class="comp-title">${item.metric}</span>
            <span class="comp-badge">${item.badge}</span>
          </div>
          <div class="comp-body">
            <div class="comp-col before">
              <span class="comp-label">Di Fabbrica (Default)</span>
              <span class="comp-val">${item.before}</span>
            </div>
            <div class="comp-col after">
              <span class="comp-label">Ottimizzato (Cyber)</span>
              <span class="comp-val ${isOpt ? 'text-emerald font-bold' : ''}">${item.after}</span>
            </div>
          </div>
          <div class="comp-impact">
            <strong>Impatto:</strong> ${item.impact}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = '<p class="dim">Errore nel caricamento del confronto.</p>';
  }
}

// ---------------- Live Benchmark Tool ----------------
async function runBenchmark() {
  const btn = document.getElementById('btn-run-benchmark');
  const container = document.getElementById('benchmark-container');
  if (btn) btn.disabled = true;

  container.innerHTML = `
    <div style="text-align: center; padding: 40px 0;">
      <div class="spinner-cyber" style="margin: 0 auto 16px auto;"></div>
      <p class="cyan-glow font-mono">Esecuzione benchmark di latenza e peering in corso...</p>
    </div>
  `;

  try {
    const res = await fetch('/api/benchmark');
    const data = await res.json();

    const pings = data.ping || [];
    const dnsList = data.dns || [];

    let pingHtml = pings.map(p => `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td><code class="val-code">${p.host}</code></td>
        <td><span class="font-mono text-cyan">${p.avg_ms} ms</span></td>
        <td><span class="badge ${p.avg_ms < 15 ? 'badge-success' : 'badge-cyan'}">${p.avg_ms < 15 ? 'Ultra Basso' : 'Ottimale'}</span></td>
      </tr>
    `).join('');

    let dnsHtml = dnsList.map(d => `
      <tr class="${d.fastest ? 'table-highlight' : ''}">
        <td><strong>${d.name}</strong> ${d.fastest ? '<span class="badge badge-success">PIÙ VELOCE ⚡</span>' : ''}</td>
        <td><code class="val-code">${d.ip}</code></td>
        <td><span class="font-mono ${d.fastest ? 'text-emerald font-bold' : ''}">${d.avg_ms} ms</span></td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 24px;">
        <div>
          <h4 style="margin-bottom: 12px; color: #fff;">1. Latenza Peering & Server Gaming</h4>
          <table class="cyber-table">
            <thead>
              <tr><th>Destinazione</th><th>IP / Host</th><th>Latenza Media</th><th>Diagnosi</th></tr>
            </thead>
            <tbody>${pingHtml}</tbody>
          </table>
        </div>
        <div>
          <h4 style="margin-bottom: 12px; color: #fff;">2. Benchmark Risoluzione DNS a Confronto</h4>
          <table class="cyber-table">
            <thead>
              <tr><th>Resolver</th><th>IP Anycast</th><th>Tempo Medio Risoluzione</th></tr>
            </thead>
            <tbody>${dnsHtml}</tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p class="text-crimson">Errore benchmark: ${err}</p>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}
