/**
 * app.js — Main Application Controller for TG Trails / OutLoot PWA
 * Real-time GPS, Server-authoritative physics, Screen Time heartbeat,
 * Touch Grass threshold alerts, Social friends & leaderboard, Sponsor Marketplace.
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
    this.isItemAvailable = false;
    this.lastActivityTime = Date.now();
    this.modalDismissedUntil = 0;
    this.currentLeaderboardScope = 'global';

    this.mapCtrl = new MapController('map');
    this.hudCtrl = null;
    this.simCtrl = null;

    this.init();
  }

  async init() {
    this.hudCtrl = new HUDController();
    this.simCtrl = new SimulatorController((sample) => this.handleSimSample(sample));

    this.setupNavigation();
    this.setupActivityTracking();
    this.setupScreenTimeHeartbeat();
    this.setupSocialEventListeners();
    this.setupWellbeingEventListeners();
    this.setupWakeLock();

    await this.ensureAuth();
    await this.fetchPoints();
    await this.checkActiveSession();

    // Start background nudge poller
    this.startNudgePoller();

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

  /* ---------------- SOCIAL & LEADERBOARD ---------------- */

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

    const btnAddFriend = document.getElementById('btn-submit-add-friend');
    if (btnAddFriend) {
      btnAddFriend.addEventListener('click', () => this.handleAddFriend());
    }
  }

  async loadSocialScreen() {
    await Promise.all([
      this.fetchLeaderboard(this.currentLeaderboardScope),
      this.fetchFriendsRoster()
    ]);
  }

  async fetchLeaderboard(scope = 'global') {
    const container = document.getElementById('leaderboard-container');
    if (!container) return;

    try {
      const resp = await fetch('/api/leaderboard', { headers: this.getHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        let entries = data.leaderboard || [];

        if (scope === 'friends') {
          entries = entries.filter((e) => e.is_friend || e.is_current_user);
        }

        if (entries.length === 0) {
          container.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-mute); font-size:13px;">No entries yet in this category. Be the first to touch grass!</div>`;
          return;
        }

        container.innerHTML = entries.map((entry) => {
          const rankDisplay = entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : `#${entry.rank}`;
          const isCurrentUser = entry.is_current_user || entry.user_id === this.userId;
          const avatar = entry.avatar_emoji || entry.display_name.charAt(0).toUpperCase();
          return `
            <div class="leaderboard-item ${isCurrentUser ? 'current-user' : ''}">
              <div class="lb-rank">${rankDisplay}</div>
              <div class="lb-avatar">${avatar}</div>
              <div class="lb-info">
                <div class="lb-name">${entry.display_name} ${isCurrentUser ? '(You)' : ''}</div>
                <div class="lb-sub">🌿 ${entry.outdoor_mins}m out · 📱 ${entry.screen_mins}m screen · ${entry.points} pts</div>
              </div>
              <div class="lb-score">${entry.ratio_percent}%</div>
            </div>
          `;
        }).join('');
      }
    } catch (e) {
      container.innerHTML = `<div style="padding:15px; color:var(--rose); font-size:12px;">Failed to load leaderboard.</div>`;
    }
  }

  async fetchFriendsRoster() {
    const container = document.getElementById('friends-list-container');
    if (!container) return;

    try {
      const resp = await fetch('/api/friends', { headers: this.getHeaders() });
      if (resp.ok) {
        const roster = await resp.json();
        if (roster.length === 0) {
          container.innerHTML = `<div style="padding:15px; text-align:center; color:var(--text-mute); font-size:13px;">No friends added yet. Enter a username or ID above to build your squad!</div>`;
          return;
        }

        container.innerHTML = roster.map((f) => {
          const statusDot = f.is_online ? 'background:var(--emerald);' : 'background:var(--text-faint);';
          const avatar = f.avatar_emoji || f.display_name.charAt(0).toUpperCase();
          return `
            <div class="leaderboard-item">
              <div class="lb-avatar" style="position:relative;">
                ${avatar}
                <span style="position:absolute; bottom:0; right:0; width:9px; height:9px; border-radius:50%; ${statusDot} border:2px solid #0f0c20;"></span>
              </div>
              <div class="lb-info">
                <div class="lb-name">${f.display_name}</div>
                <div class="lb-sub">${f.status_msg} · 🌿 ${f.outdoor_mins}m walk</div>
              </div>
              <div>
                <button class="btn-nudge" onclick="window.appInstance.sendNudge('${f.user_id}', '${f.display_name}')">
                  🌱 Nudge
                </button>
              </div>
            </div>
          `;
        }).join('');
      }
    } catch (e) {
      console.error('Error fetching friends roster', e);
    }
  }

  async handleAddFriend() {
    const input = document.getElementById('input-add-friend');
    if (!input || !input.value.trim()) return;

    const query = input.value.trim();
    try {
      const resp = await fetch('/api/friends/add', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ friend_code_or_name: query })
      });

      const res = await resp.json();
      if (resp.ok) {
        input.value = '';
        this.showToast(`🎉 Added ${res.display_name} to your Squad!`);
        this.loadSocialScreen();
      } else {
        alert(res.detail?.message || res.detail || 'Could not add friend.');
      }
    } catch (e) {
      alert('Network error adding friend.');
    }
  }

  async sendNudge(friendUserId, friendName) {
    try {
      const resp = await fetch('/api/friends/nudge', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          friend_id: friendUserId,
          message: '🌿 Step away from the screen and touch grass with me!'
        })
      });

      const res = await resp.json();
      if (resp.ok) {
        this.showToast(`🌱 Nudge sent to ${friendName}!`);
        cues.playCollectedCue();
      } else {
        alert(res.detail?.message || res.detail || 'Could not send nudge.');
      }
    } catch (e) {
      alert('Network error sending nudge.');
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
