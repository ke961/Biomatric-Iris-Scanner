// ==============================================================================
//  CYBER BIOMETRIC DASHBOARD CONTROLLER
// ==============================================================================

class BiometricDashboardApp {
  constructor() {
    this.telemetryInterval = null;
    this.lastState = 'IDLE';
    this.ecgPoints = [];
    this.ecgIndex = 0;
    this.initECG();
  }

  init() {
    this.bindEvents();
    this.startTelemetryLoop();
    this.loadProfiles();
    this.loadAuditLogs();
    this.loadSnapshots();
    this.updateAudioButtonState();
  }

  bindEvents() {
    // Scan Trigger
    const scanBtn = document.getElementById('btnTriggerScan');
    if (scanBtn) {
      scanBtn.addEventListener('click', () => this.triggerScan());
    }

    // Snapshot Capture
    const snapBtn = document.getElementById('btnCaptureSnapshot');
    if (snapBtn) {
      snapBtn.addEventListener('click', () => this.captureSnapshot());
    }

    // Audio Toggle
    const audioBtn = document.getElementById('btnToggleAudio');
    if (audioBtn) {
      audioBtn.addEventListener('click', () => {
        const enabled = window.cyberAudio.toggle();
        this.updateAudioButtonState();
      });
    }

    // Theme Switchers
    document.querySelectorAll('.theme-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const themeKey = e.target.getAttribute('data-theme');
        this.setTheme(themeKey);
      });
    });

    // Enrollment Modal
    const enrollOpenBtn = document.getElementById('btnOpenEnroll');
    const enrollCloseBtn = document.getElementById('btnCloseEnroll');
    const enrollCancelBtn = document.getElementById('btnCancelEnroll');
    const enrollForm = document.getElementById('enrollForm');

    if (enrollOpenBtn) {
      enrollOpenBtn.addEventListener('click', () => this.openEnrollModal());
    }
    if (enrollCloseBtn) {
      enrollCloseBtn.addEventListener('click', () => this.closeEnrollModal());
    }
    if (enrollCancelBtn) {
      enrollCancelBtn.addEventListener('click', () => this.closeEnrollModal());
    }
    if (enrollForm) {
      enrollForm.addEventListener('submit', (e) => this.handleEnrollSubmit(e));
    }

    // Refresh buttons
    const refLogsBtn = document.getElementById('btnRefreshLogs');
    if (refLogsBtn) {
      refLogsBtn.addEventListener('click', () => this.loadAuditLogs());
    }

    const refProfBtn = document.getElementById('btnRefreshProfiles');
    if (refProfBtn) {
      refProfBtn.addEventListener('click', () => this.loadProfiles());
    }
  }

  updateAudioButtonState() {
    const btn = document.getElementById('btnToggleAudio');
    if (btn) {
      btn.textContent = window.cyberAudio.enabled ? '🔊 SOUND ON' : '🔇 MUTED';
      btn.style.color = window.cyberAudio.enabled ? 'var(--accent-cyan)' : 'var(--text-muted)';
    }
  }

  startTelemetryLoop() {
    this.pollTelemetry();
    this.telemetryInterval = setInterval(() => this.pollTelemetry(), 250);
  }

  async pollTelemetry() {
    try {
      const res = await fetch('/api/telemetry');
      if (!res.ok) return;
      const data = await res.json();
      this.updateTelemetryUI(data);
    } catch (err) {
      console.warn('Telemetry poll error:', err);
    }
  }

  updateTelemetryUI(data) {
    // FPS & Metrics
    const fpsBadge = document.getElementById('liveFpsBadge');
    if (fpsBadge) fpsBadge.textContent = `${data.fps} FPS`;

    const targetVal = document.getElementById('valActiveTargets');
    if (targetVal) targetVal.textContent = data.active_targets;

    const blinkVal = document.getElementById('valBlinkCount');
    if (blinkVal) blinkVal.textContent = `${data.blinks} BLINKS`;

    const hashVal = document.getElementById('valBioHash');
    if (hashVal) hashVal.textContent = data.bio_hash || '0x--------';

    const statusVal = document.getElementById('valSystemStatus');
    if (statusVal) {
      statusVal.textContent = data.scan_state;
      statusVal.className = 'metric-value';
      if (data.scan_state === 'VERIFIED') statusVal.classList.add('emerald');
      else if (data.scan_state === 'FAILED') statusVal.classList.add('crimson');
      else if (data.scan_state === 'SCANNING') statusVal.classList.add('amber');
    }

    // Polar map image
    const polarContainer = document.getElementById('polarViewer');
    if (polarContainer) {
      if (data.polar_map_b64) {
        polarContainer.innerHTML = `<img src="data:image/png;base64,${data.polar_map_b64}" alt="Daugman Polar Map" />`;
      }
    }

    // Sound cues on state transition
    if (data.scan_state !== this.lastState) {
      if (data.scan_state === 'SCANNING') {
        window.cyberAudio.playScanPulse();
      } else if (data.scan_state === 'VERIFIED') {
        window.cyberAudio.playSuccessChime();
        this.loadAuditLogs();
      } else if (data.scan_state === 'FAILED') {
        window.cyberAudio.playDangerAlarm();
        this.loadAuditLogs();
      }
      this.lastState = data.scan_state;
    }

    // Active Theme highlight
    document.querySelectorAll('.theme-btn').forEach(btn => {
      if (btn.getAttribute('data-theme') === data.current_theme) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    document.body.setAttribute('data-theme', data.current_theme);
  }

  async triggerScan() {
    window.cyberAudio.playLockBeep();
    try {
      const res = await fetch('/api/scan', { method: 'POST' });
      const json = await res.json();
      console.log('Scan result:', json);
    } catch (err) {
      console.error('Trigger scan error:', err);
    }
  }

  async setTheme(themeKey) {
    try {
      const res = await fetch('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: themeKey })
      });
      if (res.ok) {
        document.body.setAttribute('data-theme', themeKey);
        window.cyberAudio.playLockBeep();
      }
    } catch (err) {
      console.error('Theme change error:', err);
    }
  }

  async captureSnapshot() {
    window.cyberAudio.playShutterClick();
    try {
      const res = await fetch('/api/snapshot', { method: 'POST' });
      const json = await res.json();
      if (json.status === 'ok') {
        this.loadSnapshots();
      }
    } catch (err) {
      console.error('Capture snapshot error:', err);
    }
  }

  openEnrollModal() {
    const modal = document.getElementById('enrollModal');
    if (modal) modal.classList.add('active');
  }

  closeEnrollModal() {
    const modal = document.getElementById('enrollModal');
    if (modal) modal.classList.remove('active');
  }

  async handleEnrollSubmit(e) {
    e.preventDefault();
    const nameInput = document.getElementById('enrollName');
    const clearanceInput = document.getElementById('enrollClearance');

    if (!nameInput || !nameInput.value.trim()) return;

    try {
      const res = await fetch('/api/enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: nameInput.value.trim(),
          clearance: clearanceInput ? clearanceInput.value : 'LEVEL 2 // OPERATOR'
        })
      });

      if (res.ok) {
        window.cyberAudio.playSuccessChime();
        this.closeEnrollModal();
        nameInput.value = '';
        this.loadProfiles();
      }
    } catch (err) {
      console.error('Enrollment error:', err);
    }
  }

  async loadProfiles() {
    const container = document.getElementById('profilesList');
    if (!container) return;

    try {
      const res = await fetch('/api/profiles');
      const profiles = await res.json();

      container.innerHTML = '';
      const keys = Object.keys(profiles);

      if (keys.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:12px;">No enrolled profiles</div>';
        return;
      }

      keys.forEach(id => {
        const p = profiles[id];
        const card = document.createElement('div');
        card.className = 'profile-card';
        card.innerHTML = `
          <div class="profile-info">
            <div class="profile-name">${p.name}</div>
            <div class="profile-clearance">${p.clearance}</div>
            <div class="profile-id-tag">ID: ${id} | HASH: 0x${p.hash || '----'}</div>
          </div>
          <div class="profile-actions">
            <button class="btn-icon-del" data-id="${id}">🗑️</button>
          </div>
        `;

        card.querySelector('.btn-icon-del').addEventListener('click', () => this.deleteProfile(id));
        container.appendChild(card);
      });
    } catch (err) {
      console.error('Load profiles error:', err);
    }
  }

  async deleteProfile(profileId) {
    if (!confirm(`Revoke biometric authorization for profile ${profileId}?`)) return;
    try {
      const res = await fetch(`/api/profiles/${profileId}`, { method: 'DELETE' });
      if (res.ok) {
        window.cyberAudio.playDangerAlarm();
        this.loadProfiles();
      }
    } catch (err) {
      console.error('Delete profile error:', err);
    }
  }

  async loadAuditLogs() {
    const tbody = document.getElementById('auditTableBody');
    if (!tbody) return;

    try {
      const res = await fetch('/api/logs');
      const logs = await res.json();

      tbody.innerHTML = '';
      if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No scan audit logs recorded yet.</td></tr>';
        return;
      }

      logs.forEach(log => {
        const tr = document.createElement('tr');
        const isGranted = log.Status === 'ACCESS_GRANTED';
        const badgeClass = isGranted ? 'badge-granted' : 'badge-denied';
        const badgeText = isGranted ? 'GRANTED' : 'DENIED';

        tr.innerHTML = `
          <td>${log.Timestamp}</td>
          <td><span style="color:var(--accent-cyan)">${log['Profile ID']}</span></td>
          <td><strong>${log.Name}</strong></td>
          <td><span class="${badgeClass}">${badgeText}</span></td>
          <td>${log.Confidence}</td>
          <td>${log.Liveness}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error('Load logs error:', err);
    }
  }

  async loadSnapshots() {
    const gallery = document.getElementById('snapshotsGallery');
    if (!gallery) return;

    try {
      const res = await fetch('/api/snapshots');
      const snapshots = await res.json();

      gallery.innerHTML = '';
      if (snapshots.length === 0) {
        gallery.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px;">No captures recorded</div>';
        return;
      }

      snapshots.slice(0, 6).forEach(snap => {
        const item = document.createElement('a');
        item.href = snap.url;
        item.target = '_blank';
        item.style.display = 'block';
        item.style.width = '70px';
        item.style.height = '48px';
        item.style.borderRadius = '4px';
        item.style.overflow = 'hidden';
        item.style.border = '1px solid var(--border-subtle)';

        item.innerHTML = `<img src="${snap.url}" style="width:100%;height:100%;object-fit:cover;" alt="Iris snapshot" />`;
        gallery.appendChild(item);
      });
    } catch (err) {
      console.error('Load snapshots error:', err);
    }
  }

  initECG() {
    const canvas = document.getElementById('ecgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let x = 0;
    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      const mid = h / 2;

      ctx.fillStyle = 'rgba(5, 8, 16, 0.08)';
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = 'rgba(0, 229, 255, 0.8)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();

      const time = Date.now() * 0.005;
      const beat = Math.sin(time * 3);
      let spike = 0;

      if (beat > 0.85) {
        spike = (Math.random() - 0.5) * 35;
      }

      const y = mid + Math.sin(time) * 4 + spike;

      ctx.arc(x, y, 1.2, 0, Math.PI * 2);
      ctx.stroke();

      x = (x + 2) % w;
      requestAnimationFrame(draw);
    };

    draw();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.dashboardApp = new BiometricDashboardApp();
  window.dashboardApp.init();
});
