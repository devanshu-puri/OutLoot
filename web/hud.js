/**
 * hud.js — HUD Controller (One-glance progress ring & screen dimming)
 */

export class HUDController {
  constructor() {
    this.progressRing = document.getElementById('ring-progress-bar');
    this.countdownText = document.getElementById('hud-countdown-text');
    this.headlineText = document.getElementById('hud-headline-text');
    this.subtextText = document.getElementById('hud-subtext-text');
    this.statusIndicator = document.getElementById('hud-status-indicator');
    this.statusChipText = document.getElementById('hud-status-text');
    this.dimmer = document.getElementById('walk-mode-dimmer');
    this.dimmerText = document.getElementById('dimmer-countdown-text');

    this.idleTimer = null;
    this.circumference = 2 * Math.PI * 35; // r=35 in svg -> ~220
    this.setupDimmerEvents();
  }

  setupDimmerEvents() {
    // Reset idle timer on any touch or click
    const resetIdle = () => {
      if (this.dimmer) this.dimmer.classList.remove('active');
      clearTimeout(this.idleTimer);
      this.idleTimer = setTimeout(() => {
        // Dim screen after 15 seconds of idle walking to conserve battery
        if (this.dimmer) this.dimmer.classList.add('active');
      }, 15000);
    };

    window.addEventListener('touchstart', resetIdle, { passive: true });
    window.addEventListener('mousemove', resetIdle, { passive: true });
    window.addEventListener('click', resetIdle, { passive: true });
    resetIdle();
  }

  update(session, isItemAvailable = false) {
    if (!session) return;

    // Status chip
    if (this.statusIndicator && this.statusChipText) {
      if (session.state === 'ACTIVE') {
        this.statusIndicator.className = 'status-indicator';
        this.statusChipText.textContent = 'ACTIVE WALK';
      } else if (session.state === 'PAUSED') {
        this.statusIndicator.className = 'status-indicator paused';
        this.statusChipText.textContent = 'PAUSED';
      }
    }

    const progress = session.cycle_progress_s || 0;
    const required = session.cycle_required_s || 300;
    const remaining_s = Math.max(0, required - progress);

    // Progress Ring offset
    const fraction = Math.min(1.0, progress / required);
    const offset = this.circumference * (1 - fraction);
    if (this.progressRing) {
      this.progressRing.style.strokeDashoffset = offset;
    }

    // Format Countdown (mm:ss)
    const mins = Math.floor(remaining_s / 60);
    const secs = Math.floor(remaining_s % 60);
    const timeStr = `${mins}:${secs < 10 ? '0' : ''}${secs}`;

    if (isItemAvailable) {
      if (this.countdownText) this.countdownText.textContent = '✦';
      if (this.headlineText) this.headlineText.textContent = 'Item Drop Ready!';
      if (this.subtextText) this.subtextText.textContent = 'Tap glowing marker on map to collect';
      if (this.dimmerText) this.dimmerText.textContent = '✦ ITEM READY — TAP TO VIEW';
    } else {
      if (this.countdownText) this.countdownText.textContent = timeStr;
      if (this.headlineText) {
        this.headlineText.textContent = session.state === 'PAUSED' ? 'Walk paused' : 'Next Item Drop';
      }
      if (this.subtextText) {
        this.subtextText.textContent = `${(session.distance_m || 0).toFixed(0)}m walked so far`;
      }
      if (this.dimmerText) this.dimmerText.textContent = `${timeStr} until next drop`;
    }
  }
}
