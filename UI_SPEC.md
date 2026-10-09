# UI_SPEC — adapted from the user's DESIGN.md ("Superhumon-style" tokens)
> We use the **design language** (tokens, rhythm, type), **not** the third-party brand: no "Superhumon" name/logo, no their portrait photography, no proprietary font. Substitute font = **Inter Variable** (Google Fonts) at weights 460 / 540 / 600 via `font-variation-settings`.

## 1. Three-canvas rhythm (keep it; don't add a 4th canvas color)
1. **Hero / active-session canvas:** indigo navy `#1b1938`, deeper `#0e0c1f`. Replace the portrait with a **dark-styled map** (or a soft violet→sky radial gradient `#c9b4fa → #1b1938`) so the outdoors is the visual hero.
2. **Body canvas:** white `#ffffff`, alt rows `#fafaf8`. Marketplace, history, rules.
3. **Closing band:** deep teal `#0e3030` (nested `#155555`). Used for: end-of-session summary and each page's closing CTA ("Take a break — start a walk").

## 2. Tokens (copy into `:root` in style.css)
```css
:root{
 --primary:#1b1938; --primary-deep:#0e0c1f; --on-primary:#fff;
 --ink:#292827; --ink-mute:#73706d; --ink-faint:#9a9794;
 --canvas:#fff; --canvas-soft:#fafaf8;
 --violet-soft:#c9b4fa; --teal-deep:#0e3030; --teal-mid:#155555;
 --hairline:#e8e4dd; --hairline-dark:#3f3a52;
 --on-dark-mute:#bcbac9; --on-dark-faint:#5a5772;
 --r-xs:4px; --r-sm:6px; --r-md:8px; --r-lg:12px; --r-xl:16px; --r-full:9999px;
 --sp-xs:4px; --sp-sm:8px; --sp-md:12px; --sp-lg:16px; --sp-xl:24px; --sp-xxl:32px; --sp-huge:64px;
}
body{font-family:'Inter',system-ui,sans-serif;font-variation-settings:"wght" 460;color:var(--ink);background:var(--canvas)}
```
Type scale (Inter Variable): display-xxl 64→**36 on mobile**, wght 540, lh .96 · display-lg 28/540/1.14/-0.63px · body-md 16/460/1.5 · button 16/700 · caption 14/460 · micro 12/540. Mobile is the primary target: stair-step 64→48→36→28→22.

## 3. Components
- **Primary button:** bg `--primary`, white text, radius 8px, padding 12×20, min-height 44px. Pressed → `--primary-deep`.
- **Hero pill button (only on dark hero/HUD):** bg `--violet-soft`, text `--primary`, radius full. ("Start walk", "Collect")
- **On-teal button:** white bg, teal text, radius 8px.
- **Cards:** white, radius 12, 1px `--hairline`, padding 32 (24 on mobile rows). Featured reward card inverted to `--primary`.
- **Pill tabs** for Map / Rewards / Me.
- **Inputs:** radius 6px, 1px hairline, 44px min height.
- **Links on light:** underlined `--ink`.
- One CTA per band. Never two competing CTAs.

## 4. Screens (mobile-first, 390px)
1. **Welcome / rules + permission explainer** (white): 3 lines on how it works, privacy bullets ("we keep recent GPS points for 7 days, only to validate your walk"), safety line ("stay on public paths; don't look at the screen while crossing roads"), button *Allow location & start*.
2. **Active walk HUD** (indigo, map behind): top = tiny status chip (ACTIVE/PAUSED); center = **one big number**: minutes until next drop or "Item ready — go to the glowing marker"; progress ring (violet-soft stroke); bottom = *Pause* (outline) and *End* (outline). **Nothing else.** Screen dims after 10 s of no interaction (CSS overlay "walk mode" with big text only; tap to wake). Cues: `navigator.vibrate([200,100,200])` + short WebAudio beep on ready/collected.
3. **Collect sheet** (bottom sheet, hero pill button): item name + rarity + points; distance text; error states are human ("You're 48 m away — walk a bit closer").
4. **Summary band** (teal): "Outside 14 min · 1.1 km · 3 drops · +95 pts · screen time 2 min 40 s" + mission card + CTA *See rewards*.
5. **Marketplace** (white): cards for rewards (cost, stock, "DEMO reward" label); featured reward = indigo inverted card; redeem confirm modal (radius 16); code screen with big monospace code.
6. **Me**: balance, last 10 ledger rows, session history (SHOULD), rules link.
7. **Mission card**: title, description, est. minutes, small badge: "Gemma · local · 1.4 s" or "Fallback". Item lore appears in collect sheet.

## 5. Accessibility & safety
- Contrast ≥ 4.5:1 (check violet-soft on indigo); touch targets ≥ 44×44; respects `prefers-reduced-motion`.
- Outdoor legibility: high-contrast HUD numbers (≥ 48px), no thin gray text on the HUD.
- "Screen time" measured as foreground-interaction seconds (count only touch-active periods); display honestly in the summary — it's the theme's proof.

## 6. Do / Don't (from source design, kept)
Do: sub-default weights (460/540), tight display leading, warm ink `#292827` (never pure black), one closing teal band, rounded-rect CTAs (pill only on dark hero). Don't: pill buttons in body, extra accent colors, pure-black text, omit the closing band.
