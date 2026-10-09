/**
 * app.js — Main Application Controller for TG Trails / OutLoot PWA
 */

import { cues } from './cues.js';
import { MapController } from './map.js';
import { HUDController } from './hud.js';
import { SimulatorController } from './sim.js';

class App {
  constructor() {
    this.token = localStorage.getItem('tgt_token') || null;
    this.userId = localStorage.getItem('tgt_user_id') || null;
    this.currentSession = null;
    this.currentMission = null;
    this.latestPosition = null;
    this.pendingSamples = [];
    this.sampleBatchInterval = null;
    this.watchId = null;

    this.screenActiveTimeSeconds = 0;
    this.sessionStartTimestamp = null;
    this.isScreenTouched = true;

    this.mapCtrl = new MapController('map');
    this.hudCtrl = null;
    this.simCtrl = null;

    this.init();
  }

  async init() {
    this.hudCtrl = new HUDController();
    this.simCtrl = new SimulatorController((sample) => this.handleSimSample(sample));

    this.setupNavigation();
    this.setupScreenTimeTracker();
    this.setupWakeLock();

    await this.ensureAuth();
    await this.fetchPoints();
    await this.checkActiveSession();

    // Setup simulator toggle
    const simBtn = document.getElementById('sim-toggle-btn');
    if (simBtn) {
      simBtn.addEventListener('click', () => {
        const running = this.simCtrl.toggle();
        simBtn.classList.toggle('active', running);
        simBtn.textContent = running ? '⚡ SIM ON' : 'SIM MODE';
      });
    }

    // Setup start walk button on welcome screen
    const startWalkBtn = document.getElementById('btn-start-walk');
    if (startWalkBtn) {
      startWalkBtn.addEventListener('click', () => this.startSessionFlow());
    }

    // Setup HUD controls
    const btnPause = document.getElementById('btn-pause-walk');
    if (btnPause) {
      btnPause.addEventListener('click', () => this.togglePauseSession());
    }

    const btnEnd = document.getElementById('btn-end-walk');
    if (btnEnd) {
      btnEnd.addEventListener('click', () => this.endSessionFlow());
    }

    const btnCollect = document.getElementById('btn-collect-action');
    if (btnCollect) {
      btnCollect.addEventListener('click', () => this.performCollection());
    }

    const btnCloseSheet = document.getElementById('btn-close-sheet');
    if (btnCloseSheet) {
      btnCloseSheet.addEventListener('click', () => this.closeCollectSheet());
    }
  }

  async ensureAuth() {
    if (this.token && this.userId) return;

    try {
      const resp = await fetch('/api/auth/anon', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        this.token = data.token;
        this.userId = data.user_id;
        localStorage.setItem('tgt_token', this.token);
        localStorage.setItem('tgt_user_id', this.userId);
      }
    } catch (e) {
      console.error('Auth failure', e);
    }
  }

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };
  }

  setupNavigation() {
    const navButtons = document.querySelectorAll('.tab-btn');
    navButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const screenId = btn.dataset.screen;
        this.showScreen(screenId);
      });
    });
  }

  showScreen(screenId) {
    document.querySelectorAll('.screen').forEach((s) => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));

    const targetScreen = document.getElementById(screenId);
    if (targetScreen) targetScreen.classList.add('active');

    const targetTab = document.querySelector(`.tab-btn[data-screen="${screenId}"]`);
    if (targetTab) targetTab.classList.add('active');

    if (screenId === 'screen-map') {
      setTimeout(() => {
        if (this.mapCtrl.map) this.mapCtrl.map.invalidateSize();
      }, 100);
    }

    if (screenId === 'screen-rewards') {
      this.loadRewardsScreen();
    }

    if (screenId === 'screen-me') {
      this.loadMeScreen();
    }
  }

  setupScreenTimeTracker() {
    setInterval(() => {
      if (this.currentSession && document.visibilityState === 'visible') {
        this.screenActiveTimeSeconds += 1;
      }
    }, 1000);
  }

  async setupWakeLock() {
    if ('wakeLock' in navigator) {
      try {
        await navigator.wakeLock.request('screen');
      } catch (err) {
        console.log('Wake Lock not supported or denied');
      }
    }
  }

  async fetchPoints() {
    try {
      const resp = await fetch('/api/points', { headers: this.getHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        const badge = document.getElementById('user-points-display');
        if (badge) badge.textContent = `${data.balance} pts`;
      }
    } catch (e) {
      console.error(e);
    }
  }

  async checkActiveSession() {
    try {
      const resp = await fetch('/api/session/active', { headers: this.getHeaders() });
      if (resp.ok) {
        this.currentSession = await resp.json();
        this.onSessionStarted();
      }
    } catch (e) {
      // No active session
    }
  }

  async startSessionFlow() {
    let startLat = 13.0827;
    let startLon = 80.2707;

    if (this.latestPosition) {
      startLat = this.latestPosition.lat;
      startLon = this.latestPosition.lon;
    }

    try {
      const resp = await fetch('/api/session/start', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          display_name: 'Trail Explorer',
          start_lat: startLat,
          start_lon: startLon
        })
      });

      if (resp.ok) {
        this.currentSession = await resp.json();
        this.sessionStartTimestamp = Date.now();
        this.screenActiveTimeSeconds = 0;
        this.onSessionStarted();
      }
    } catch (e) {
      console.error('Session start error', e);
    }
  }

  onSessionStarted() {
    this.showScreen('screen-map');
    this.mapCtrl.init();
    this.hudCtrl.update(this.currentSession);
    this.startLocationWatcher();
    this.startSampleBatchPoster();
    this.fetchAIMission();
  }

  startLocationWatcher() {
    if ('geolocation' in navigator) {
      this.watchId = navigator.geolocation.watchPosition(
        (pos) => {
          const sample = {
            t: pos.timestamp / 1000.0,
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy || 5.0
          };
          this.handleNewSample(sample);
        },
        (err) => console.warn('GPS error', err),
        { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 }
      );
    }
  }

  handleSimSample(sample) {
    this.handleNewSample(sample);
  }

  handleNewSample(sample) {
    this.latestPosition = sample;
    this.pendingSamples.push(sample);
    this.mapCtrl.updateUserPosition(sample.lat, sample.lon, sample.accuracy_m);
  }

  startSampleBatchPoster() {
    if (this.sampleBatchInterval) clearInterval(this.sampleBatchInterval);

    this.sampleBatchInterval = setInterval(async () => {
      if (!this.currentSession || this.pendingSamples.length === 0) return;

      const batch = [...this.pendingSamples];
      this.pendingSamples = [];

      try {
        const resp = await fetch(`/api/session/${this.currentSession.id}/samples`, {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({ samples: batch })
        });

        if (resp.ok) {
          const res = await resp.json();
          this.currentSession.cycle_progress_s = res.cycle_progress_s;
          this.currentSession.distance_m = res.distance_m;
          this.currentSession.state = res.session_state;
          if (res.next_item) {
            this.currentSession.next_item = res.next_item;
          }

          const wasAvailable = this.isItemAvailable;
          this.isItemAvailable = res.item_available;

          if (!wasAvailable && this.isItemAvailable) {
            cues.playReadyCue();
            this.showCollectSheet();
          }

          this.hudCtrl.update(this.currentSession, this.isItemAvailable);
          this.mapCtrl.updateItemDrop(
            this.currentSession.next_item,
            this.latestPosition?.lat,
            this.latestPosition?.lon,
            () => this.showCollectSheet()
          );
        }
      } catch (e) {
        console.error('Batch post failed', e);
      }
    }, 4000);
  }

  async fetchAIMission() {
    try {
      const resp = await fetch('/api/ai/mission', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          minutes: 20,
          interest: 'nature and architecture',
          intensity: 'easy'
        })
      });

      if (resp.ok) {
        this.currentMission = await resp.json();
        this.renderMissionCard(this.currentMission);
      }
    } catch (e) {
      console.error('Mission error', e);
    }
  }

  renderMissionCard(mission) {
    const container = document.getElementById('active-mission-card-container');
    if (!container || !mission) return;

    const badgeClass = mission.source === 'gemma-local' ? 'ai-source-badge' : 'ai-source-badge fallback';
    const badgeText = mission.source === 'gemma-local' ? `Gemma · local · ${mission.latency_ms}ms` : 'Fallback Mission';

    container.innerHTML = `
      <div class="mission-card">
        <div class="mission-header">
          <span class="${badgeClass}">${badgeText}</span>
          <span style="font-size:12px; color:var(--on-dark-mute);">⏱ ${mission.payload.est_minutes} min</span>
        </div>
        <h3 class="mission-title">${mission.payload.title}</h3>
        <p class="mission-desc">${mission.payload.description}</p>
        <p class="mission-tip">💡 ${mission.payload.tip}</p>
      </div>
    `;
  }

  showCollectSheet() {
    const sheet = document.getElementById('collect-sheet');
    const item = this.currentSession?.next_item;
    if (!sheet || !item) return;

    document.getElementById('sheet-item-name').textContent = item.name || 'Unknown Relic';
    const badge = document.getElementById('sheet-item-badge');
    badge.className = `item-badge ${item.rarity.toLowerCase()}`;
    badge.textContent = `${item.rarity} · +${item.base_points} pts`;

    const lore = this.currentMission?.payload?.item_lore || 'An ancient trail relic unearthed by continuous footwork.';
    document.getElementById('sheet-item-lore').textContent = `"${lore}"`;

    const statusMsg = document.getElementById('sheet-status-message');
    statusMsg.className = 'sheet-status-message';
    statusMsg.textContent = 'Walk near the glowing pulse to collect this item.';

    sheet.classList.add('visible');
  }

  closeCollectSheet() {
    const sheet = document.getElementById('collect-sheet');
    if (sheet) sheet.classList.remove('visible');
  }

  async performCollection() {
    const item = this.currentSession?.next_item;
    if (!item) return;

    const lat = this.latestPosition ? this.latestPosition.lat : (item.lat || 13.0827);
    const lon = this.latestPosition ? this.latestPosition.lon : (item.lon || 80.2707);
    const accuracy_m = this.latestPosition ? this.latestPosition.accuracy_m : 5.0;

    const idempotency_key = `col_key_${item.id}_${Date.now()}`;
    const statusMsg = document.getElementById('sheet-status-message');

    try {
      const resp = await fetch(`/api/session/${this.currentSession.id}/collect`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          spawn_id: item.id,
          lat: lat,
          lon: lon,
          accuracy_m: accuracy_m,
          idempotency_key: idempotency_key
        })
      });

      const res = await resp.json();
      if (res.result === 'SUCCESS' || res.result === 'REPLAY') {
        cues.playCollectedCue();
        statusMsg.className = 'sheet-status-message success';
        statusMsg.textContent = res.message;
        await this.fetchPoints();
        setTimeout(() => {
          this.closeCollectSheet();
        }, 1800);
      } else {
        statusMsg.className = 'sheet-status-message error';
        statusMsg.textContent = res.message;
      }
    } catch (e) {
      statusMsg.className = 'sheet-status-message error';
      statusMsg.textContent = 'Network error during collection. Please retry.';
    }
  }

  async togglePauseSession() {
    if (!this.currentSession) return;
    const isPaused = this.currentSession.state === 'PAUSED';
    const action = isPaused ? 'resume' : 'pause';

    try {
      const resp = await fetch(`/api/session/${this.currentSession.id}/${action}`, {
        method: 'POST',
        headers: this.getHeaders()
      });
      if (resp.ok) {
        this.currentSession = await resp.json();
        this.hudCtrl.update(this.currentSession, this.isItemAvailable);
        const btn = document.getElementById('btn-pause-walk');
        if (btn) btn.textContent = isPaused ? 'Pause' : 'Resume';
      }
    } catch (e) {
      console.error(e);
    }
  }

  async endSessionFlow() {
    if (!this.currentSession) return;

    try {
      const resp = await fetch(`/api/session/${this.currentSession.id}/end`, {
        method: 'POST',
        headers: this.getHeaders()
      });
      if (resp.ok) {
        const finalSession = await resp.json();
        this.renderSummaryScreen(finalSession);
        this.currentSession = null;
        if (this.sampleBatchInterval) clearInterval(this.sampleBatchInterval);
        if (this.watchId) navigator.geolocation.clearWatch(this.watchId);
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderSummaryScreen(session) {
    this.showScreen('screen-summary');
    const outdoorMins = Math.max(1, Math.round((session.session_elapsed_s || 0) / 60));
    const screenMins = Math.max(0, Math.round(this.screenActiveTimeSeconds / 60));
    const screenSecs = this.screenActiveTimeSeconds % 60;

    document.getElementById('sum-dist').textContent = `${(session.distance_m || 0).toFixed(0)} m`;
    document.getElementById('sum-pts').textContent = `+${session.points_earned || 0}`;
    document.getElementById('sum-outdoor-time').textContent = `${outdoorMins} min`;
    document.getElementById('sum-screen-time').textContent = `${screenMins}m ${screenSecs}s`;

    const summaryMissionContainer = document.getElementById('summary-mission-card');
    if (summaryMissionContainer && this.currentMission) {
      const m = this.currentMission;
      summaryMissionContainer.innerHTML = `
        <div class="mission-card" style="background:rgba(21,85,85,0.8);">
          <div class="mission-header">
            <span class="ai-source-badge">${m.source}</span>
          </div>
          <h4 style="color:#fff; font-size:15px;">${m.payload.title}</h4>
          <p style="color:rgba(255,255,255,0.8); font-size:13px;">${m.payload.description}</p>
        </div>
      `;
    }
  }

  async loadRewardsScreen() {
    const grid = document.getElementById('rewards-grid');
    if (!grid) return;

    try {
      const resp = await fetch('/api/rewards');
      if (resp.ok) {
        const rewards = await resp.json();
        grid.innerHTML = rewards.map((r, idx) => `
          <div class="reward-card ${idx === 0 ? 'featured' : ''}">
            <div class="reward-card-top">
              <h3 class="reward-title">${r.title}</h3>
              <span class="reward-cost">${r.cost_points} pts</span>
            </div>
            <p class="reward-desc">${r.description}</p>
            <p class="reward-terms">${r.terms} · Stock: ${r.stock}</p>
            <button class="${idx === 0 ? 'btn-hero-pill' : 'btn-primary'}" onclick="window.appInstance.redeemReward('${r.id}', ${r.cost_points})" style="margin-top:8px;">
              Redeem Code
            </button>
          </div>
        `).join('');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async redeemReward(rewardId, cost) {
    const idempotency_key = `rdm_key_${rewardId}_${Date.now()}`;
    try {
      const resp = await fetch(`/api/rewards/${rewardId}/redeem`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ idempotency_key })
      });

      const res = await resp.json();
      if (resp.ok) {
        alert(`🎉 Successfully redeemed ${res.reward_title}!\n\nVoucher Code: ${res.code}\n\n(Saved to your Me tab)`);
        await this.fetchPoints();
        this.loadRewardsScreen();
      } else {
        alert(`Redemption Error: ${res.message}`);
      }
    } catch (e) {
      alert('Network error while redeeming reward.');
    }
  }

  async loadMeScreen() {
    try {
      const resp = await fetch('/api/points', { headers: this.getHeaders() });
      const redResp = await fetch('/api/redemptions', { headers: this.getHeaders() });

      if (resp.ok) {
        const pts = await resp.json();
        document.getElementById('me-balance-display').textContent = `${pts.balance} pts`;

        const historyList = document.getElementById('me-history-list');
        if (historyList && pts.recent_transactions) {
          historyList.innerHTML = pts.recent_transactions.map((tx) => `
            <div class="history-item">
              <div>
                <strong style="font-size:13px;">${tx.kind.replace('_', ' ')}</strong>
                <div style="font-size:11px; color:var(--ink-mute);">${tx.note || ''}</div>
              </div>
              <span class="history-delta ${tx.delta > 0 ? 'positive' : 'negative'}">
                ${tx.delta > 0 ? '+' : ''}${tx.delta} pts
              </span>
            </div>
          `).join('');
        }
      }

      if (redResp.ok) {
        const redList = await redResp.json();
        const codeContainer = document.getElementById('me-voucher-codes');
        if (codeContainer) {
          if (redList.length === 0) {
            codeContainer.innerHTML = '<p style="font-size:13px; color:var(--ink-mute);">No voucher codes redeemed yet.</p>';
          } else {
            codeContainer.innerHTML = redList.map((r) => `
              <div style="margin-bottom:12px;">
                <div style="font-size:13px; font-weight:600; margin-bottom:4px;">${r.reward_title}</div>
                <div class="voucher-code-box">${r.code}</div>
              </div>
            `).join('');
          }
        }
      }
    } catch (e) {
      console.error(e);
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.appInstance = new App();
});
