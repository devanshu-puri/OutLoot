/**
 * hud.js — HUD Controller (Dotted clock dial, Walking Lottie animation & screen dimming)
 */

export class HUDController {
  constructor() {
    this.dotsSvg = document.getElementById('dial-dots-svg');
    this.countdownText = document.getElementById('hud-countdown-text');
    this.headlineText = document.getElementById('hud-headline-text');
    this.subtextText = document.getElementById('hud-subtext-text');
    this.statusIndicator = document.getElementById('hud-status-indicator');
    this.statusChipText = document.getElementById('hud-status-text');
    this.statusPill = document.getElementById('hud-status-pill');
    this.dimmer = document.getElementById('walk-mode-dimmer');
    this.dimmerText = document.getElementById('dimmer-countdown-text');
    this.lottieContainer = document.getElementById('walk-lottie-container');

    this.idleTimer = null;
    this.dotCount = 36;
    this.dots = [];
    this.lottieAnim = null;

    this.initDots();
    this.initLottieAnimation();
    this.setupDimmerEvents();
  }

  initDots() {
    if (!this.dotsSvg) return;
    this.dotsSvg.innerHTML = '';
    this.dots = [];

    const radius = 34; // Radius of dots ring
    const cx = 42;
    const cy = 42;
    const dotRadius = 2.4;

    for (let i = 0; i < this.dotCount; i++) {
      // Start at 12 o'clock (-PI / 2) and proceed clockwise
      const angle = (-Math.PI / 2) + (2 * Math.PI * i / this.dotCount);
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', x.toFixed(2));
      circle.setAttribute('cy', y.toFixed(2));
      circle.setAttribute('r', dotRadius.toString());
      circle.setAttribute('class', 'dial-dot');
      this.dotsSvg.appendChild(circle);
      this.dots.push(circle);
    }
  }

  initLottieAnimation() {
    if (!this.lottieContainer) return;

    const tryLoad = () => {
      try {
        if (window.lottie) {
          const config = {
            container: this.lottieContainer,
            renderer: 'svg',
            loop: true,
            autoplay: true
          };
          if (window.walkShoesData) {
            config.animationData = window.walkShoesData;
          } else {
            config.path = '/assets/walk_cycling_shoes.json';
          }
          this.lottieAnim = window.lottie.loadAnimation(config);
          return true;
        }
      } catch (e) {
        console.warn('Lottie animation failed:', e);
      }
      return false;
    };

    if (!tryLoad()) {
      setTimeout(tryLoad, 200);
      setTimeout(tryLoad, 800);
    }
  }

  setupDimmerEvents() {
    // Reset idle timer on any touch or click
    const resetIdle = () => {
      if (this.dimmer) this.dimmer.classList.remove('active');
      clearTimeout(this.idleTimer);
      this.idleTimer = setTimeout(() => {
        // Dim screen after 25 seconds of idle walking to conserve battery
        if (this.dimmer) this.dimmer.classList.add('active');
      }, 25000);
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
        this.statusIndicator.className = 'status-dot-active';
        this.statusChipText.textContent = 'ACTIVE WALK';
        if (this.lottieAnim && this.lottieAnim.isPaused) {
          this.lottieAnim.play();
        }
      } else if (session.state === 'PAUSED') {
        this.statusIndicator.className = 'status-dot-active paused';
        this.statusChipText.textContent = 'PAUSED';
        if (this.lottieAnim && !this.lottieAnim.isPaused) {
          this.lottieAnim.pause();
        }
      }
    }

    const progress = session.cycle_progress_s || 0;
    const required = session.cycle_required_s || 300;
    const remaining_s = Math.max(0, required - progress);

    // Progress Dotted Dial: fill each dot sequentially as time advances
    const fraction = Math.min(1.0, progress / required);
    const filledCount = Math.floor(fraction * this.dotCount);

    this.dots.forEach((dot, index) => {
      if (isItemAvailable) {
        dot.setAttribute('class', 'dial-dot filled ready');
      } else if (index < filledCount) {
        dot.setAttribute('class', 'dial-dot filled');
      } else {
        dot.setAttribute('class', 'dial-dot');
      }
    });

    // Format Countdown (mm:ss)
    const mins = Math.floor(remaining_s / 60);
    const secs = Math.floor(remaining_s % 60);
    const timeStr = `${mins}:${secs < 10 ? '0' : ''}${secs}`;

    if (isItemAvailable) {
      if (this.countdownText) this.countdownText.textContent = '✦';
      if (this.headlineText) this.headlineText.textContent = 'Item Drop Ready!';
      if (this.subtextText) this.subtextText.textContent = 'Tap glowing marker on map';
      if (this.dimmerText) this.dimmerText.textContent = '✦ ITEM READY — TAP TO VIEW';
    } else {
      if (this.countdownText) this.countdownText.textContent = timeStr;
      if (this.headlineText) {
        this.headlineText.textContent = session.state === 'PAUSED' ? 'Walk Paused' : 'Next Item Drop';
      }
      if (this.subtextText) {
        this.subtextText.textContent = `${(session.distance_m || 0).toFixed(0)}m walked so far`;
      }
      if (this.dimmerText) this.dimmerText.textContent = `${timeStr} until next drop`;
    }
  }
}
