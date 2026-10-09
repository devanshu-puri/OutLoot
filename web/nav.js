/**
 * nav.js — Animated Curved Bottom Navigation Bar
 * Implements smooth scooped notch cutout & floating active bubble transition.
 */

export class BottomNavAnimator {
  constructor() {
    this.path = document.getElementById('nav-bar-path');
    this.bubble = document.getElementById('nav-floating-bubble');
    this.bubbleIconSlot = document.getElementById('bubble-icon-slot');
    this.tabs = document.querySelectorAll('.tab-btn');
    this.currentIndex = 0;
    this.currentSvgX = 50;
    this.animId = null;

    this.init();
  }

  getBarPath(x, w = 400, h = 62, r = 26, scoopW = 32, scoopD = 25) {
    const x1 = Math.max(r, x - scoopW);
    const x2 = Math.min(w - r, x + scoopW);
    const c1x = x - scoopW * 0.45;
    const c2x = x + scoopW * 0.45;

    let d = `M 0,${r} A ${r},${r} 0 0 1 ${r},0 `;
    if (x1 > r) d += `L ${x1.toFixed(1)},0 `;
    d += `C ${c1x.toFixed(1)},0 ${c1x.toFixed(1)},${scoopD} ${x.toFixed(1)},${scoopD} `;
    d += `C ${c2x.toFixed(1)},${scoopD} ${c2x.toFixed(1)},0 ${x2.toFixed(1)},0 `;
    if (x2 < w - r) d += `L ${(w - r).toFixed(1)},0 `;
    d += `A ${r},${r} 0 0 1 ${w},${r} `;
    d += `A ${r},${r} 0 0 1 ${w - r},${h} `;
    d += `L ${r},${h} `;
    d += `A ${r},${r} 0 0 1 0,${r} Z`;
    return d;
  }

  init() {
    if (this.path) {
      this.path.setAttribute('d', this.getBarPath(50));
    }
    this.updateActiveTab(0, false);
  }

  updateActiveTab(index, animate = true) {
    if (index < 0 || index >= this.tabs.length) return;
    this.currentIndex = index;
    const targetSvgX = 50 + index * 100;

    // Update CSS transform on the floating bubble
    if (this.bubble) {
      const pct = 12.5 + index * 25;
      this.bubble.style.transform = `translateX(calc(${pct}% - 24px))`;
    }

    // Update active tab buttons & bubble icon
    this.tabs.forEach((tab, i) => {
      const isActive = (i === index);
      tab.classList.toggle('active', isActive);

      if (isActive && this.bubbleIconSlot) {
        const iconSvg = tab.querySelector('.tab-icon-wrap svg');
        if (iconSvg) {
          this.bubbleIconSlot.innerHTML = iconSvg.outerHTML;
          this.bubbleIconSlot.style.transform = 'scale(0.55)';
          this.bubbleIconSlot.style.opacity = '0';
          setTimeout(() => {
            if (this.bubbleIconSlot) {
              this.bubbleIconSlot.style.transform = 'scale(1)';
              this.bubbleIconSlot.style.opacity = '1';
            }
          }, 80);
        }
      }
    });

    if (!animate) {
      this.currentSvgX = targetSvgX;
      if (this.path) this.path.setAttribute('d', this.getBarPath(targetSvgX));
      return;
    }

    // Animate SVG path scoop smoothly using easeOutBack
    if (this.animId) cancelAnimationFrame(this.animId);
    const startX = this.currentSvgX;
    const startTime = performance.now();
    const duration = 380; // ms

    const easeOutBack = (t) => {
      const c1 = 1.35;
      const c3 = c1 + 1;
      return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    };

    const step = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      const eased = easeOutBack(progress);
      const currentX = startX + (targetSvgX - startX) * eased;
      this.currentSvgX = currentX;

      if (this.path) {
        this.path.setAttribute('d', this.getBarPath(currentX));
      }

      if (progress < 1) {
        this.animId = requestAnimationFrame(step);
      } else {
        this.currentSvgX = targetSvgX;
        if (this.path) {
          this.path.setAttribute('d', this.getBarPath(targetSvgX));
        }
      }
    };

    this.animId = requestAnimationFrame(step);
  }
}
