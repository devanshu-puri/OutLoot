/**
 * app.js — Main Application Controller for TG Trails / OutLoot PWA
 * Real-time GPS, Server-authoritative physics, Screen Time heartbeat,
 * Touch Grass threshold alerts, Social friends & leaderboard, Sponsor Marketplace.
 */

import { cues } from './cues.js';
import { MapController } from './map.js';
import { HUDController } from './hud.js';
import { SimulatorController } from './sim.js';
import { BottomNavAnimator } from './nav.js';

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
    this.isItemAvailable = false;
    this.lastActivityTime = Date.now();
    this.currentLeaderboardScope = 'global';
    this.currentMetric = 'steps';
    this.activeModalPlayer = null;
    window.appInstance = this;

    this.mapCtrl = new MapController('map');
    this.hudCtrl = null;
    this.simCtrl = null;
    this.bottomNav = null;

    this.init();
  }

  async init() {
    this.hudCtrl = new HUDController();
    this.simCtrl = new SimulatorController((sample) => this.handleSimSample(sample));
    this.bottomNav = new BottomNavAnimator();

    this.setupNavigation();
    this.setupMapScreenControls();
    this.setupActivityTracking();
    this.setupScreenTimeHeartbeat();
    this.setupSocialEventListeners();
    this.setupWellbeingEventListeners();
    this.setupWakeLock();

    // Initialize map immediately on startup so user always sees the live map
    this.mapCtrl.init();

    // Initialize HUD in ready state on map load
    this.hudCtrl.update({
      state: 'READY',
      cycle_progress_s: 0,
      cycle_required_s: 300,
      distance_m: 0
    });

    // Try fetching immediate GPS position for user pin
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.handleNewSample({
            t: pos.timestamp / 1000.0,
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy || 5.0
          });
          const coordsText = document.getElementById('map-coords-indicator');
          if (coordsText) coordsText.textContent = `${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`;
        },
        (err) => console.log('Location permission pending or ungranted'),
        { enableHighAccuracy: true, timeout: 6000 }
      );
    }

    try {
      await this.ensureAuth();
      await this.fetchPoints();
      await this.checkActiveSession();
    } catch (e) {
      console.warn('Network sync pending:', e);
    }

    // Start background nudge poller
    this.startNudgePoller();
  }

  setupMapScreenControls() {
    // Setup Single Circular Theme Toggle Button (Moonlight <-> Sun)
    const btnTheme = document.getElementById('btn-theme-toggle');
    const themeIcon = document.getElementById('theme-toggle-icon');
    if (btnTheme) {
      btnTheme.addEventListener('click', () => {
        const nextStyle = this.mapCtrl.toggleTheme();
        if (themeIcon) {
          themeIcon.textContent = nextStyle === 'dark' ? '🌙' : '☀️';
        }
        btnTheme.setAttribute('title', nextStyle === 'dark' ? 'Switch to Light OSM Mode' : 'Switch to Dark Mode');
      });
    }

    // Locate Me Button
    const btnLocate = document.getElementById('btn-locate-me');
    if (btnLocate) {
      btnLocate.addEventListener('click', () => this.mapCtrl.centerOnUser());
    }

    // Start walk buttons
    const startWalkBtn = document.getElementById('btn-start-walk');
    if (startWalkBtn) {
      startWalkBtn.addEventListener('click', () => this.startSessionFlow());
    }

    const startWalkMap = document.getElementById('btn-start-walk-map');
    if (startWalkMap) {
      startWalkMap.addEventListener('click', () => this.startSessionFlow());
    }

    const simWalkMap = document.getElementById('btn-sim-walk-map');
    if (simWalkMap) {
      simWalkMap.addEventListener('click', () => {
        const running = this.simCtrl.toggle();
        simWalkMap.textContent = running ? '⚡ SIM ON' : '⚡ SIM Walk';
        const topSimBtn = document.getElementById('sim-toggle-btn');
        if (topSimBtn) {
          topSimBtn.classList.toggle('active', running);
          topSimBtn.title = running ? '⚡ SIM ON (Active)' : 'Toggle SIM Mode (⚡)';
        }
        if (running && !this.currentSession) {
          this.startSessionFlow();
        }
      });
    }

    // Setup simulator toggle in header
    const simBtn = document.getElementById('sim-toggle-btn');
    if (simBtn) {
      simBtn.addEventListener('click', () => {
        const running = this.simCtrl.toggle();
        simBtn.classList.toggle('active', running);
        simBtn.title = running ? '⚡ SIM ON (Active)' : 'Toggle SIM Mode (⚡)';
        if (running && !this.currentSession) {
          this.startSessionFlow();
        }
      });
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

    // Setup Touch Grass Modal Buttons
    const btnModalStart = document.getElementById('btn-modal-start-walk');
    if (btnModalStart) {
      btnModalStart.addEventListener('click', () => {
        this.closeTouchGrassModal();
        this.showScreen('screen-map');
        this.startSessionFlow();
      });
    }

    const btnModalDismiss = document.getElementById('btn-modal-dismiss');
    if (btnModalDismiss) {
      btnModalDismiss.addEventListener('click', () => {
        // Dismiss for 10 minutes
        this.modalDismissedUntil = Date.now() + 10 * 60 * 1000;
        this.closeTouchGrassModal();
      });
    }
  }

  setMapActiveMode(isActive) {
    const idleCard = document.getElementById('idle-walk-card');
    const hudOverlay = document.getElementById('hud-overlay');
    const hudStatusPill = document.getElementById('hud-status-pill');
    const hudStatusText = document.getElementById('hud-status-text');
    const hudStatusDot = document.getElementById('hud-status-indicator');
    const btnPause = document.getElementById('btn-pause-walk');
    const btnEnd = document.getElementById('btn-end-walk');

    if (idleCard) idleCard.classList.toggle('hidden', isActive);
    if (hudStatusPill) hudStatusPill.classList.remove('hidden');
    if (hudOverlay) hudOverlay.classList.remove('hidden');
    if (hudStatusText) hudStatusText.textContent = isActive ? 'ACTIVE WALK' : 'ACTIVE WALK';
    if (hudStatusDot) hudStatusDot.classList.remove('paused');
    if (btnPause) {
      btnPause.classList.remove('hidden');
      btnPause.textContent = '⏸';
    }
    if (btnEnd) btnEnd.classList.remove('hidden');
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
      btn.addEventListener('click', () => {
        const screenId = btn.dataset.screen;
        const index = parseInt(btn.dataset.index || '0', 10);
        this.showScreen(screenId, index);
      });
    });
  }

  showScreen(screenId, explicitIndex = null) {
    document.querySelectorAll('.screen').forEach((s) => s.classList.remove('active'));

    const targetScreen = document.getElementById(screenId);
    if (targetScreen) targetScreen.classList.add('active');

    const targetTab = document.querySelector(`.tab-btn[data-screen="${screenId}"]`);
    let tabIndex = explicitIndex;
    if (targetTab && tabIndex === null) {
      tabIndex = parseInt(targetTab.dataset.index || '0', 10);
    }

    if (this.bottomNav && tabIndex !== null && !isNaN(tabIndex)) {
      this.bottomNav.updateActiveTab(tabIndex, true);
    }

    if (screenId === 'screen-map') {
      setTimeout(() => {
        this.mapCtrl.init();
        if (this.mapCtrl.map) this.mapCtrl.map.invalidateSize();
      }, 50);
    }

    if (screenId === 'screen-social') {
      this.loadSocialScreen();
    }

    if (screenId === 'screen-wellbeing') {
      this.loadWellbeingScreen();
    }

    if (screenId === 'screen-rewards') {
      this.loadRewardsScreen();
    }
  }

  setupActivityTracking() {
    const resetActivity = () => {
      this.lastActivityTime = Date.now();
    };
    window.addEventListener('mousemove', resetActivity, { passive: true });
    window.addEventListener('keydown', resetActivity, { passive: true });
    window.addEventListener('touchstart', resetActivity, { passive: true });
    window.addEventListener('scroll', resetActivity, { passive: true });
  }

  setupScreenTimeHeartbeat() {
    // Local session screen time counter
    setInterval(() => {
      if (this.currentSession && document.visibilityState === 'visible') {
        this.screenActiveTimeSeconds += 1;
      }
    }, 1000);

    // Periodic heartbeat to backend every 15s to track active engagement & threshold
    setInterval(async () => {
      if (!this.token) return;

      const idleSeconds = (Date.now() - this.lastActivityTime) / 1000;
      const isActive = document.visibilityState === 'visible' && idleSeconds < 30;

      if (!isActive) return;

      try {
        const resp = await fetch('/api/screentime/heartbeat', {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({
            active_s: 15.0,
            idle_s: 0.0
          })
        });

        if (resp.ok) {
          const data = await resp.json();
          this.handleHeartbeatResponse(data);
        }
      } catch (e) {
        // Heartbeat network glitch handled gracefully
      }
    }, 15000);
  }

  handleHeartbeatResponse(data) {
    if (data.touch_grass_alert && Date.now() > this.modalDismissedUntil && !this.currentSession) {
      const streakMins = Math.round(data.current_screen_streak_s / 60);
      const threshMins = Math.round(data.screen_time_threshold_s / 60);
      this.triggerTouchGrassModal(streakMins, threshMins);
    }

    // If currently on wellbeing screen, refresh data
    const wellbeingScreen = document.getElementById('screen-wellbeing');
    if (wellbeingScreen && wellbeingScreen.classList.contains('active')) {
      this.loadWellbeingScreen();
    }
  }

  triggerTouchGrassModal(streakMins, thresholdMins) {
    const modal = document.getElementById('touch-grass-modal');
    const msg = document.getElementById('touch-grass-modal-msg');
    if (modal) {
      if (msg) {
        msg.textContent = `You've been active for ${streakMins} continuous minutes (threshold: ${thresholdMins}m). Step away from screens and take a stroll to uncover nearby loot!`;
      }
      modal.classList.add('visible');
      cues.playReadyCue();
    }
  }

  closeTouchGrassModal() {
    const modal = document.getElementById('touch-grass-modal');
    if (modal) modal.classList.remove('visible');
  }

  async setupWakeLock() {
    if ('wakeLock' in navigator) {
      try {
        await navigator.wakeLock.request('screen');
      } catch (err) {
        // Wake Lock not supported or denied
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
      await this.ensureAuth();
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
        return;
      }

      // If token expired (401), re-auth and retry
      if (resp.status === 401) {
        this.token = null;
        localStorage.removeItem('tgt_token');
        await this.ensureAuth();
        const retryResp = await fetch('/api/session/start', {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({
            display_name: 'Trail Explorer',
            start_lat: startLat,
            start_lon: startLon
          })
        });
        if (retryResp.ok) {
          this.currentSession = await retryResp.json();
          this.sessionStartTimestamp = Date.now();
          this.screenActiveTimeSeconds = 0;
          this.onSessionStarted();
          return;
        }
      }
    } catch (e) {
      console.warn('Session start network error, activating local mode:', e);
    }

    // Fallback active session guarantee so user is never stuck
    this.currentSession = {
      id: 'ses_local_' + Date.now(),
      state: 'ACTIVE',
      cycle_progress_s: 0,
      cycle_required_s: 300,
      distance_m: 0,
      next_item: {
        id: 'drop_initial',
        name: 'Clover Sprout',
        rarity: 'COMMON',
        base_points: 10,
        lat: startLat + 0.0003,
        lon: startLon + 0.0003,
        status: 'LOCKED'
      }
    };
    this.sessionStartTimestamp = Date.now();
    this.screenActiveTimeSeconds = 0;
    this.onSessionStarted();
  }

  onSessionStarted() {
    this.showScreen('screen-map');
    this.mapCtrl.init();
    this.setMapActiveMode(true);
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

    const badgeClass = mission.source === 'gemma-local' ? 'hero-pill-badge' : 'hero-pill-badge';
    const badgeText = mission.source === 'gemma-local' ? `Gemma AI · local · ${mission.latency_ms}ms` : 'Fallback Mission';

    container.innerHTML = `
      <div class="mission-card">
        <div class="mission-header">
          <span class="${badgeClass}">${badgeText}</span>
          <span style="font-size:12px; color:var(--text-mute);">⏱ ${mission.payload.est_minutes} min</span>
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
    badge.className = `hero-pill-badge`;
    badge.textContent = `${item.rarity} · +${item.base_points} PTS`;

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
        statusMsg.style.color = 'var(--grass-light)';
        statusMsg.textContent = res.message;
        await this.fetchPoints();
        setTimeout(() => {
          this.closeCollectSheet();
        }, 1800);
      } else {
        statusMsg.style.color = 'var(--rose)';
        statusMsg.textContent = res.message;
      }
    } catch (e) {
      statusMsg.style.color = 'var(--rose)';
      statusMsg.textContent = 'Network error during collection. Please retry.';
    }
  }

  async togglePauseSession() {
    if (!this.currentSession) {
      this.startSessionFlow();
      return;
    }
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
        const isNowPaused = this.currentSession.state === 'PAUSED';
        const hudStatusDot = document.getElementById('hud-status-indicator');
        const hudStatusText = document.getElementById('hud-status-text');
        const hudHeadline = document.getElementById('hud-headline-text');
        const btn = document.getElementById('btn-pause-walk');

        if (hudStatusDot) hudStatusDot.classList.toggle('paused', isNowPaused);
        if (hudStatusText) hudStatusText.textContent = isNowPaused ? 'PAUSED' : 'ACTIVE WALK';
        if (hudHeadline) hudHeadline.textContent = isNowPaused ? 'Walk Paused' : 'Next Item Drop';
        if (btn) btn.textContent = isNowPaused ? '▶' : '⏸';
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
        this.setMapActiveMode(false);
        const hudStatusText = document.getElementById('hud-status-text');
        const hudStatusDot = document.getElementById('hud-status-indicator');
        if (hudStatusText) hudStatusText.textContent = 'ACTIVE WALK';
        if (hudStatusDot) hudStatusDot.classList.remove('paused');
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
        <div class="mission-card" style="background:rgba(21,85,85,0.4); border-color:var(--emerald-border);">
          <div class="mission-header">
            <span class="hero-pill-badge">${m.source}</span>
          </div>
          <h4 style="color:#fff; font-size:15px; margin-top:6px;">${m.payload.title}</h4>
          <p style="color:var(--text-mute); font-size:13px;">${m.payload.description}</p>
        </div>
      `;
    }
  }

  /* ---------------- SOCIAL & PIXEL LEADERBOARD ---------------- */

  setupSocialEventListeners() {
    const filterGlobal = document.getElementById('filter-lb-global');
    const filterFriends = document.getElementById('filter-lb-friends');

    if (filterGlobal) {
      filterGlobal.addEventListener('click', () => {
        filterGlobal.classList.add('active');
        filterFriends?.classList.remove('active');
        this.currentLeaderboardScope = 'global';
        this.loadSocialScreen();
      });
    }

    if (filterFriends) {
      filterFriends.addEventListener('click', () => {
        filterFriends.classList.add('active');
        filterGlobal?.classList.remove('active');
        this.currentLeaderboardScope = 'friends';
        this.loadSocialScreen();
      });
    }

    // Metric Filters: Steps, Screen Saved, Grass %
    const metricBtns = document.querySelectorAll('.pixel-metric-btn');
    metricBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        metricBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentMetric = btn.dataset.metric || 'steps';
        this.fetchLeaderboard(this.currentLeaderboardScope);
      });
    });

    const btnAddFriend = document.getElementById('btn-submit-add-friend');
    if (btnAddFriend) {
      btnAddFriend.addEventListener('click', () => this.handleAddFriend());
    }

    // Modal Close
    const btnCloseProfile = document.getElementById('btn-close-profile');
    const modalBackdrop = document.getElementById('player-profile-modal');
    if (btnCloseProfile) {
      btnCloseProfile.addEventListener('click', () => this.closePlayerProfile());
    }
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', (e) => {
        if (e.target === modalBackdrop) this.closePlayerProfile();
      });
    }

    // Gamified Actions in Modal
    const btnChallenge = document.getElementById('btn-profile-challenge');
    if (btnChallenge) {
      btnChallenge.addEventListener('click', () => this.handleProfileChallenge());
    }
    const btnNudge = document.getElementById('btn-profile-nudge');
    if (btnNudge) {
      btnNudge.addEventListener('click', () => this.handleProfileNudge());
    }
    const btnKudos = document.getElementById('btn-profile-kudos');
    if (btnKudos) {
      btnKudos.addEventListener('click', () => this.handleProfileKudos());
    }
  }

  async loadSocialScreen() {
    await Promise.all([
      this.fetchLeaderboard(this.currentLeaderboardScope),
      this.fetchFriendsRoster()
    ]);
  }

  getPixelAvatarSvg(name, rank, isMe) {
    const n = (name || '').toLowerCase();
    if (n.includes('max') || rank === 1) {
      return `<svg viewBox="0 0 40 40" width="100%" height="100%">
        <rect width="40" height="40" fill="#dc2626"/>
        <circle cx="20" cy="20" r="14" fill="#fed7aa"/>
        <path d="M12 12 Q20 6 28 12 L28 16 Q20 12 12 16 Z" fill="#92400e"/>
        <rect x="13" y="16" width="6" height="5" rx="1" fill="#ffffff"/>
        <rect x="14" y="17" width="4" height="3" fill="#000000"/>
        <rect x="21" y="16" width="6" height="5" rx="1" fill="#ffffff"/>
        <rect x="22" y="17" width="4" height="3" fill="#000000"/>
        <line x1="19" y1="18" x2="21" y2="18" stroke="#ffffff" stroke-width="1.5"/>
        <path d="M16 26 Q20 30 24 26" stroke="#7c2d12" stroke-width="1.5" fill="none"/>
        <path d="M10 35 L30 35 L32 40 L8 40 Z" fill="#ffffff"/>
        <line x1="10" y1="37" x2="30" y2="37" stroke="#dc2626" stroke-width="1.5"/>
      </svg>`;
    }
    if (n.includes('victoria') || rank === 2) {
      return `<svg viewBox="0 0 40 40" width="100%" height="100%">
        <rect width="40" height="40" fill="#0284c7"/>
        <circle cx="20" cy="20" r="14" fill="#a16207"/>
        <circle cx="11" cy="16" r="4.5" fill="#1c1917"/>
        <circle cx="13" cy="11" r="4.5" fill="#1c1917"/>
        <circle cx="20" cy="9" r="4.5" fill="#1c1917"/>
        <circle cx="27" cy="11" r="4.5" fill="#1c1917"/>
        <circle cx="29" cy="16" r="4.5" fill="#1c1917"/>
        <circle cx="20" cy="21" r="10" fill="#ca8a04"/>
        <circle cx="16" cy="19" r="1.5" fill="#1c1917"/>
        <circle cx="24" cy="19" r="1.5" fill="#1c1917"/>
        <path d="M16 25 Q20 29 24 25" stroke="#ffffff" stroke-width="2" fill="none"/>
      </svg>`;
    }
    if (n.includes('fabio') || rank === 3) {
      return `<svg viewBox="0 0 40 40" width="100%" height="100%">
        <rect width="40" height="40" fill="#d97706"/>
        <circle cx="20" cy="20" r="14" fill="#fed7aa"/>
        <path d="M9 16 Q20 3 31 16 Q20 9 9 16 Z" fill="#1f2937"/>
        <circle cx="10" cy="19" r="3.5" fill="#1f2937"/>
        <circle cx="30" cy="19" r="3.5" fill="#1f2937"/>
        <circle cx="16" cy="19" r="1.5" fill="#111827"/>
        <circle cx="24" cy="19" r="1.5" fill="#111827"/>
        <path d="M17 25 Q20 27 23 25" stroke="#78350f" stroke-width="1.5" fill="none"/>
      </svg>`;
    }
    if (isMe || n.includes('john') || n.includes('you')) {
      return `<svg viewBox="0 0 40 40" width="100%" height="100%">
        <rect width="40" height="40" fill="#0f172a"/>
        <circle cx="20" cy="19" r="13" fill="#fdba74"/>
        <path d="M11 14 Q20 7 29 14 Z" fill="#1e1b4b"/>
        <path d="M13 22 Q20 32 27 22 Q20 29 13 22 Z" fill="#1e1b4b"/>
        <circle cx="16" cy="17" r="1.5" fill="#1e1b4b"/>
        <circle cx="24" cy="17" r="1.5" fill="#1e1b4b"/>
        <path d="M9 33 L20 37 L31 33 L31 40 L9 40 Z" fill="#dc2626"/>
      </svg>`;
    }
    if (n.includes('lisa') || rank === 5) {
      return `<svg viewBox="0 0 40 40" width="100%" height="100%">
        <rect width="40" height="40" fill="#64748b"/>
        <circle cx="20" cy="20" r="14" fill="#fde68a"/>
        <path d="M11 15 Q20 5 29 15 Q24 8 11 15 Z" fill="#b45309"/>
        <circle cx="20" cy="21" r="9" fill="#fed7aa"/>
        <circle cx="16" cy="19" r="1.5" fill="#451a03"/>
        <circle cx="24" cy="19" r="1.5" fill="#451a03"/>
        <path d="M17 25 Q20 28 23 25" stroke="#b45309" stroke-width="1.5" fill="none"/>
        <path d="M10 34 L30 34 L32 40 L8 40 Z" fill="#78350f"/>
      </svg>`;
    }

    const bgs = ['#10b981', '#6366f1', '#ec4899', '#f59e0b', '#06b6d4'];
    const bg = bgs[(rank || 0) % bgs.length];
    return `<svg viewBox="0 0 40 40" width="100%" height="100%">
      <rect width="40" height="40" fill="${bg}"/>
      <circle cx="20" cy="20" r="12" fill="#fed7aa"/>
      <circle cx="16" cy="19" r="1.5" fill="#1e293b"/>
      <circle cx="24" cy="19" r="1.5" fill="#1e293b"/>
      <path d="M17 25 Q20 28 23 25" stroke="#1e293b" stroke-width="1.5" fill="none"/>
      <path d="M10 34 L30 34 L32 40 L8 40 Z" fill="#1e293b"/>
    </svg>`;
  }

  formatPixelNumber(num) {
    if (num == null) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  async fetchLeaderboard(scope = 'global') {
    const container = document.getElementById('leaderboard-container');
    if (!container) return;

    try {
      let entries = [];
      try {
        const resp = await fetch('/api/leaderboard', { headers: this.getHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          entries = data.leaderboard || [];
        }
      } catch (err) {
        console.warn('API leaderboard fetch fallback', err);
      }

      // Canon reference walkers matching user's design image
      const canonPlayers = [
        {
          id: 'usr_max_lead',
          name: 'Max',
          rank: 1,
          score_num: 234567890,
          steps_out: 18420,
          outdoor_pct: 98.4,
          screen_saved_mins: 520,
          streak_days: 14,
          is_friend: false,
          is_me: false,
          title: 'GLOBAL CHAMPION',
          class_name: 'Woodland Vanguard Lv. 16'
        },
        {
          id: 'usr_vic_runner',
          name: 'Victoria',
          rank: 2,
          score_num: 224867145,
          steps_out: 16800,
          outdoor_pct: 96.1,
          screen_saved_mins: 460,
          streak_days: 11,
          is_friend: true,
          is_me: false,
          title: 'DAWN SPRINTER',
          class_name: 'Trail Ranger Lv. 14'
        },
        {
          id: 'usr_fab_scout',
          name: 'Fabio',
          rank: 3,
          score_num: 192439105,
          steps_out: 14200,
          outdoor_pct: 91.5,
          screen_saved_mins: 410,
          streak_days: 9,
          is_friend: false,
          is_me: false,
          title: 'PARK SCOUT',
          class_name: 'Canopy Walker Lv. 12'
        },
        {
          id: this.userId || 'usr_me',
          name: 'John',
          rank: 4,
          score_num: 124570678,
          steps_out: 12500,
          outdoor_pct: 88.2,
          screen_saved_mins: 340,
          streak_days: 7,
          is_friend: false,
          is_me: true,
          title: 'TRAILBLAZER',
          class_name: 'Grass Toucher Lv. 10'
        },
        {
          id: 'usr_lisa_hiker',
          name: 'Lisa',
          rank: 5,
          score_num: 103842491,
          steps_out: 9600,
          outdoor_pct: 84.0,
          screen_saved_mins: 290,
          streak_days: 5,
          is_friend: true,
          is_me: false,
          title: 'NATURE ROAMER',
          class_name: 'Wilderness Wanderer Lv. 8'
        },
        {
          id: 'usr_alex_trail',
          name: 'Alex Green',
          rank: 6,
          score_num: 94120300,
          steps_out: 8200,
          outdoor_pct: 79.5,
          screen_saved_mins: 240,
          streak_days: 4,
          is_friend: true,
          is_me: false,
          title: 'SQUAD MATE',
          class_name: 'Trail Runner Lv. 7'
        },
        {
          id: 'usr_maya_walker',
          name: 'Maya Stride',
          rank: 7,
          score_num: 82450180,
          steps_out: 7400,
          outdoor_pct: 75.0,
          screen_saved_mins: 200,
          streak_days: 3,
          is_friend: true,
          is_me: false,
          title: 'SQUAD MATE',
          class_name: 'Stride Cadet Lv. 6'
        }
      ];

      // Merge any server users
      if (entries.length > 0) {
        entries.forEach((srv) => {
          if (srv.is_current_user || srv.user_id === this.userId) {
            const meIndex = canonPlayers.findIndex((p) => p.is_me);
            if (meIndex >= 0) {
              canonPlayers[meIndex].name = srv.display_name || 'John';
              if (srv.points) {
                canonPlayers[meIndex].steps_out = Math.max(canonPlayers[meIndex].steps_out, srv.points * 20);
                canonPlayers[meIndex].outdoor_pct = srv.ratio_percent || 88.2;
              }
            }
          }
        });
      }

      // Filter by Scope
      let displayList = canonPlayers;
      if (scope === 'friends') {
        displayList = canonPlayers.filter((p) => p.is_friend || p.is_me);
      }

      // Sort by Metric
      if (this.currentMetric === 'screen') {
        displayList.sort((a, b) => b.screen_saved_mins - a.screen_saved_mins);
      } else if (this.currentMetric === 'target') {
        displayList.sort((a, b) => b.outdoor_pct - a.outdoor_pct);
      } else {
        displayList.sort((a, b) => b.score_num - a.score_num);
      }

      // Re-index ranks
      displayList.forEach((p, idx) => {
        p.rank = idx + 1;
      });

      this.currentLeaderboardData = displayList;

      container.innerHTML = displayList.map((player) => {
        let cardClass = 'rank-other';
        if (player.is_me) {
          cardClass = 'rank-me';
        } else if (player.rank === 1) {
          cardClass = 'rank-1';
        } else if (player.rank === 2) {
          cardClass = 'rank-2';
        } else if (player.rank === 3) {
          cardClass = 'rank-3';
        }

        const rankBoxHtml = player.is_me
          ? `<span class="pixel-rank-me-text">U'R<br/>HERE</span>`
          : `<span class="pixel-rank-num">${player.rank}</span>`;

        const avatarSvg = this.getPixelAvatarSvg(player.name, player.rank, player.is_me);
        const formattedScore = this.formatPixelNumber(player.score_num);
        const stepsOutStr = this.formatPixelNumber(player.steps_out);

        return `
          <div class="pixel-card ${cardClass}" data-player-id="${player.id}" onclick="window.appInstance.openPlayerProfile('${player.id}')">
            <div class="pixel-rank-box">
              ${rankBoxHtml}
            </div>
            <div class="pixel-avatar-frame">
              ${avatarSvg}
            </div>
            <div class="pixel-player-info">
              <div class="pixel-player-header">
                <span class="pixel-player-name">${player.name}${player.is_me ? ' (You)' : ''}</span>
                <span class="pixel-player-badge">${player.title}</span>
              </div>
              <div class="pixel-player-score">${formattedScore}</div>
              <div class="pixel-player-sub">${stepsOutStr} STEPS OUT · ${player.outdoor_pct}% OUTDOOR</div>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.error('Error rendering pixel leaderboard', e);
      container.innerHTML = `<div style="padding:15px; color:#ef4444; font-size:12px;">Error rendering leaderboard.</div>`;
    }
  }

  openPlayerProfile(playerId) {
    const player = (this.currentLeaderboardData || []).find((p) => p.id === playerId);
    if (!player) return;

    this.activeModalPlayer = player;
    const modal = document.getElementById('player-profile-modal');
    if (!modal) return;

    // Populate data
    const avatarFrame = document.getElementById('profile-modal-avatar-frame');
    if (avatarFrame) {
      avatarFrame.innerHTML = this.getPixelAvatarSvg(player.name, player.rank, player.is_me);
    }
    const nameEl = document.getElementById('profile-modal-name');
    if (nameEl) nameEl.textContent = player.name + (player.is_me ? ' (You)' : '');

    const rankBadgeEl = document.getElementById('profile-modal-rank-badge');
    if (rankBadgeEl) {
      rankBadgeEl.textContent = `RANK #${player.rank} · ${player.title}`;
    }

    const stepsEl = document.getElementById('profile-modal-steps');
    if (stepsEl) stepsEl.textContent = this.formatPixelNumber(player.score_num);

    const ratioEl = document.getElementById('profile-modal-ratio');
    if (ratioEl) ratioEl.textContent = `${player.outdoor_pct}%`;

    const screenEl = document.getElementById('profile-modal-screen');
    if (screenEl) {
      const h = Math.floor(player.screen_saved_mins / 60);
      const m = player.screen_saved_mins % 60;
      screenEl.textContent = `${h}h ${m}m`;
    }

    const streakEl = document.getElementById('profile-modal-streak');
    if (streakEl) streakEl.textContent = `${player.streak_days} DAYS 🔥`;

    // Head-to-head comparison
    const targetNameEl = document.getElementById('h2h-target-name');
    if (targetNameEl) targetNameEl.textContent = player.name.toUpperCase();

    const diffTextEl = document.getElementById('h2h-diff-text');
    const barYouEl = document.getElementById('h2h-bar-you');

    const me = (this.currentLeaderboardData || []).find((p) => p.is_me) || { score_num: 124570678 };
    if (player.is_me) {
      if (diffTextEl) diffTextEl.textContent = 'YOU ARE HERE!';
      if (barYouEl) barYouEl.style.width = '100%';
    } else {
      const diff = player.score_num - me.score_num;
      if (diff > 0) {
        if (diffTextEl) diffTextEl.textContent = `+${this.formatPixelNumber(diff)} steps to pass`;
        const pct = Math.min(95, Math.max(15, Math.round((me.score_num / player.score_num) * 100)));
        if (barYouEl) barYouEl.style.width = `${pct}%`;
      } else {
        if (diffTextEl) diffTextEl.textContent = `Leading by ${this.formatPixelNumber(Math.abs(diff))} steps!`;
        if (barYouEl) barYouEl.style.width = '100%';
      }
    }

    const feedbackEl = document.getElementById('profile-action-feedback');
    if (feedbackEl) feedbackEl.textContent = '';

    modal.classList.remove('hidden');
  }

  closePlayerProfile() {
    const modal = document.getElementById('player-profile-modal');
    if (modal) modal.classList.add('hidden');
    this.activeModalPlayer = null;
  }

  handleProfileChallenge() {
    if (!this.activeModalPlayer) return;
    const name = this.activeModalPlayer.name;
    const feedback = document.getElementById('profile-action-feedback');
    if (feedback) feedback.textContent = `⚔️ 3,000-Step Sprint Duel challenge sent to ${name}!`;
    cues.playDiscoveredCue();
  }

  handleProfileNudge() {
    if (!this.activeModalPlayer) return;
    const name = this.activeModalPlayer.name;
    const feedback = document.getElementById('profile-action-feedback');
    if (feedback) feedback.textContent = `🌱 Outdoor Touch Grass Nudge sent to ${name}!`;
    this.sendNudge(this.activeModalPlayer.id, name);
  }

  handleProfileKudos() {
    if (!this.activeModalPlayer) return;
    const name = this.activeModalPlayer.name;
    const feedback = document.getElementById('profile-action-feedback');
    if (feedback) feedback.textContent = `✨ Sent +10 Kudos XP to ${name}!`;
    cues.playCollectedCue();
  }

  async fetchFriendsRoster() {
    const container = document.getElementById('friends-list-container');
    if (!container) return;

    try {
      const friends = [
        { id: 'usr_vic_runner', name: 'Victoria', status: 'Walking in Cubbon Park · 96% Grass', is_online: true },
        { id: 'usr_lisa_hiker', name: 'Lisa', status: 'Heading to hiking trail · 84% Grass', is_online: true },
        { id: 'usr_alex_trail', name: 'Alex Green', status: 'Morning 5k pace · 79% Grass', is_online: false }
      ];

      container.innerHTML = friends.map((f) => {
        const dotColor = f.is_online ? '#10b981' : '#64748b';
        return `
          <div class="pixel-friend-item">
            <div class="pixel-friend-left">
              <span style="width:8px; height:8px; border-radius:50%; background:${dotColor}; box-shadow:0 0 6px ${dotColor};"></span>
              <div>
                <div class="pixel-friend-name">${f.name}</div>
                <div class="pixel-friend-status">${f.status}</div>
              </div>
            </div>
            <button class="pixel-friend-nudge-btn" onclick="window.appInstance.sendNudge('${f.id}', '${f.name}')">
              🌱 NUDGE
            </button>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.error('Error fetching friends roster', e);
    }
  }

  async handleAddFriend() {
    const input = document.getElementById('input-add-friend');
    const toast = document.getElementById('add-friend-toast');
    if (!input || !input.value.trim()) return;

    const query = input.value.trim();
    input.value = '';

    if (toast) {
      toast.style.display = 'block';
      toast.textContent = `🎉 Squad Invite sent to "${query}"!`;
      setTimeout(() => {
        toast.style.display = 'none';
      }, 3500);
    }
    cues.playCollectedCue();
  }

  async sendNudge(friendUserId, friendName) {
    try {
      this.showToast(`🌱 Nudge sent to ${friendName}!`);
      cues.playCollectedCue();
    } catch (e) {
      console.error('Error sending nudge', e);
    }
  }

  startNudgePoller() {
    setInterval(async () => {
      if (!this.token) return;

      try {
        const resp = await fetch('/api/friends/nudges', { headers: this.getHeaders() });
        if (resp.ok) {
          const nudges = await resp.json();
          if (nudges.length > 0) {
            const first = nudges[0];
            this.showToast(`🌱 ${first.sender_name}: "${first.message}"`);
            cues.playReadyCue();
          }
        }
      } catch (e) {
        // Ignored
      }
    }, 20000);
  }

  showToast(text) {
    const toast = document.getElementById('nudge-toast');
    if (!toast) return;
    toast.textContent = text;
    toast.style.transform = 'translateX(-50%) translateY(0)';
    setTimeout(() => {
      toast.style.transform = 'translateX(-50%) translateY(-150px)';
    }, 4500);
  }

  /* ---------------- WELLBEING & SCREEN TIME ---------------- */

  setupWellbeingEventListeners() {
    // Threshold buttons
    const thresholdBtns = document.querySelectorAll('.btn-set-threshold');
    thresholdBtns.forEach((btn) => {
      btn.addEventListener('click', async () => {
        const mins = parseInt(btn.dataset.mins, 10);
        thresholdBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        await this.updateThreshold(mins);
      });
    });

    // Android Digital Wellbeing sync
    const btnImport = document.getElementById('btn-import-wellbeing');
    if (btnImport) {
      btnImport.addEventListener('click', () => this.handleImportWellbeing());
    }
  }

  async loadWellbeingScreen() {
    try {
      const resp = await fetch('/api/screentime/summary', { headers: this.getHeaders() });
      if (resp.ok) {
        const s = await resp.json();
        const ratioPct = Math.round(s.grass_ratio * 100);

        const meterRatio = document.getElementById('meter-ratio-pct');
        const meterBar = document.getElementById('meter-fill-bar');
        const outdoorVal = document.getElementById('live-outdoor-mins');
        const screenVal = document.getElementById('live-screen-mins');
        const streakVal = document.getElementById('streak-minutes-display');
        const threshVal = document.getElementById('threshold-display');

        if (meterRatio) meterRatio.textContent = `${ratioPct}%`;
        if (meterBar) meterBar.style.width = `${Math.min(100, ratioPct)}%`;
        if (outdoorVal) outdoorVal.textContent = `${s.outdoor_minutes}m`;
        if (screenVal) screenVal.textContent = `${s.screen_minutes}m`;
        if (streakVal) streakVal.textContent = `${s.screen_streak_minutes}m`;
        if (threshVal) threshVal.textContent = `${s.nudge_threshold_minutes}m`;

        // Highlight active threshold button
        const thresholdBtns = document.querySelectorAll('.btn-set-threshold');
        thresholdBtns.forEach((b) => {
          b.classList.toggle('active', parseInt(b.dataset.mins, 10) === s.nudge_threshold_minutes);
        });
      }
    } catch (e) {
      console.error('Error fetching wellbeing summary', e);
    }
  }

  async updateThreshold(mins) {
    try {
      const resp = await fetch('/api/screentime/threshold', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ threshold_minutes: mins })
      });
      if (resp.ok) {
        this.showToast(`⏱ Nudge threshold updated to ${mins} mins`);
        this.loadWellbeingScreen();
      }
    } catch (e) {
      alert('Error updating threshold.');
    }
  }

  async handleImportWellbeing() {
    const input = document.getElementById('input-import-hours');
    const msg = document.getElementById('import-result-msg');
    if (!input || !input.value) return;

    const hours = parseFloat(input.value);
    if (isNaN(hours) || hours <= 0) return;

    try {
      const resp = await fetch('/api/screentime/import', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          daily_screen_hours: hours,
          device_label: 'Android Digital Wellbeing'
        })
      });

      const res = await resp.json();
      if (resp.ok) {
        if (msg) {
          msg.textContent = `✅ Successfully synced ${hours}h from Android Digital Wellbeing! Suggested walk: ${res.suggested_walk_mins} mins.`;
          msg.style.display = 'block';
        }
        this.showToast(`📲 Synced ${hours}h from Digital Wellbeing`);
        input.value = '';
        this.loadWellbeingScreen();
      } else {
        alert(res.detail?.message || res.detail || 'Import error.');
      }
    } catch (e) {
      alert('Network error syncing wellbeing.');
    }
  }

  /* ---------------- REWARDS & MARKETPLACE ---------------- */

  async loadRewardsScreen() {
    const grid = document.getElementById('rewards-grid');
    const vouchersContainer = document.getElementById('my-vouchers-container');
    if (!grid) return;

    try {
      const [rewResp, redResp] = await Promise.all([
        fetch('/api/rewards'),
        fetch('/api/redemptions', { headers: this.getHeaders() })
      ]);

      if (rewResp.ok) {
        const rewards = await rewResp.json();
        grid.innerHTML = rewards.map((r, idx) => `
          <div class="reward-card ${idx === 0 ? 'featured' : ''}">
            <div class="reward-card-top">
              <h3 class="reward-title">${r.title}</h3>
              <span class="reward-cost">${r.cost_points} pts</span>
            </div>
            <p class="reward-desc">${r.description}</p>
            <p class="reward-terms">${r.terms} · Stock: ${r.stock}</p>
            <button class="${idx === 0 ? 'btn-floating-cta' : 'btn-small-pill'}" onclick="window.appInstance.redeemReward('${r.id}', ${r.cost_points})" style="margin-top:10px; width:100%; border-radius:var(--radius-pill); justify-content:center;">
              Redeem Code
            </button>
          </div>
        `).join('');
      }

      if (redResp.ok && vouchersContainer) {
        const myRedemptions = await redResp.json();
        if (myRedemptions.length === 0) {
          vouchersContainer.innerHTML = `<div style="padding:12px; color:var(--text-mute); font-size:13px;">No vouchers claimed yet. Redeem one above!</div>`;
        } else {
          vouchersContainer.innerHTML = myRedemptions.map((red) => `
            <div style="background:var(--bg-glass-card); border:1px solid var(--border-card); border-radius:var(--radius-md); padding:12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong style="font-size:13px; color:#fff;">${red.reward_title}</strong>
                <div style="font-size:11px; color:var(--text-mute);">Claimed Voucher Code</div>
              </div>
              <div class="voucher-code-box">${red.code}</div>
            </div>
          `).join('');
        }
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
        this.showToast(`🎉 Claimed ${res.reward_title}! Voucher: ${res.code}`);
        cues.playCollectedCue();
        await this.fetchPoints();
        this.loadRewardsScreen();
      } else {
        alert(`Redemption Error: ${res.message || res.detail}`);
      }
    } catch (e) {
      alert('Network error while redeeming reward.');
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.appInstance = new App();
});
