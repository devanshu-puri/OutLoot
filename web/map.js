/**
 * map.js — Leaflet Open-Source Map Controller with Multi-Provider Support
 * 100% Free Open-Source tiles: OpenStreetMap, Carto Dark Matter, Carto Voyager, OpenTopoMap.
 * Zero API keys required.
 */

export class MapController {
  constructor(elementId = 'map') {
    this.elementId = elementId;
    this.map = null;
    this.userMarker = null;
    this.accuracyCircle = null;
    this.itemMarker = null;
    this.currentTileLayer = null;
    this.currentStyle = 'dark';
    this.hasCentered = false;

    // 100% Free Public Open-Source Map Providers — NO API KEY EVER REQUIRED & NO WATERMARKS
    this.tileProviders = {
      dark: {
        name: 'Dark (OSM)',
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>'
        }
      },
      osm: {
        name: 'OpenStreetMap Standard',
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>'
        }
      },
      voyager: {
        name: 'Nature & Walking Trails',
        url: 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a> | CyclOSM'
        }
      }
    };

    this.itemMarkers = new Map();
    this.selectedItemCallback = null;
  }

  init(defaultLat = 13.0827, defaultLon = 80.2707) {
    if (this.map) {
      this.map.invalidateSize();
      return;
    }

    const container = document.getElementById(this.elementId);
    if (!container) return;

    try {
      this.map = L.map(this.elementId, {
        zoomControl: false,
        attributionControl: false
      }).setView([defaultLat, defaultLon], 16);

      // Add Zoom Control at bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(this.map);

      // Set initial tile layer (Watermark-free Dark OSM by default)
      this.setTileProvider(this.currentStyle);

      // Minimal attribution control
      L.control.attribution({ position: 'bottomleft', prefix: false })
        .addAttribution('&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>')
        .addTo(this.map);

      // Recompute size on window resize
      window.addEventListener('resize', () => {
        if (this.map) this.map.invalidateSize();
      });

      // Quick timeout to ensure container dimensions are resolved
      setTimeout(() => {
        if (this.map) this.map.invalidateSize();
      }, 150);
    } catch (e) {
      console.error('Failed to initialize Leaflet map:', e);
    }
  }

  setTileProvider(styleKey) {
    if (!this.map) return;
    const provider = this.tileProviders[styleKey] || this.tileProviders.dark;
    this.currentStyle = styleKey;

    const mapContainer = document.getElementById(this.elementId);
    if (mapContainer) {
      if (styleKey === 'dark') {
        mapContainer.classList.add('map-dark-tiles');
      } else {
        mapContainer.classList.remove('map-dark-tiles');
      }
    }

    if (this.currentTileLayer) {
      this.map.removeLayer(this.currentTileLayer);
    }

    this.currentTileLayer = L.tileLayer(provider.url, provider.options);
    this.currentTileLayer.addTo(this.map);
  }

  toggleTheme() {
    const nextStyle = this.currentStyle === 'dark' ? 'osm' : 'dark';
    this.setTileProvider(nextStyle);
    return nextStyle;
  }

  updateUserPosition(lat, lon, accuracy_m = 5.0) {
    if (!this.map) this.init(lat, lon);

    if (!this.userMarker) {
      const userIcon = L.divIcon({
        className: 'user-location-marker-container',
        html: '<div class="user-location-marker"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });

      this.userMarker = L.marker([lat, lon], { icon: userIcon }).addTo(this.map);
      this.accuracyCircle = L.circle([lat, lon], {
        radius: accuracy_m,
        color: '#10b981',
        fillColor: '#10b981',
        fillOpacity: 0.15,
        weight: 1.5
      }).addTo(this.map);
    } else {
      this.userMarker.setLatLng([lat, lon]);
      this.accuracyCircle.setLatLng([lat, lon]);
      this.accuracyCircle.setRadius(accuracy_m);
    }

    if (!this.hasCentered) {
      this.map.setView([lat, lon], 17);
      this.hasCentered = true;
    }
  }

  getItemIconEmoji(item) {
    const name = (item.name || '').toLowerCase();
    const rarity = (item.rarity || '').toLowerCase();
    if (name.includes('clover') || rarity === 'common') return '🌱';
    if (name.includes('crystal') || rarity === 'uncommon') return '💎';
    if (name.includes('acorn') || rarity === 'rare') return '🌰';
    if (name.includes('bloom') || rarity === 'epic') return '🌸';
    if (name.includes('compass') || rarity === 'special') return '🧭';
    return '✦';
  }

  getItemColor(rarity) {
    const r = (rarity || '').toLowerCase();
    if (r === 'common') return '#10b981';
    if (r === 'uncommon') return '#06b6d4';
    if (r === 'rare') return '#f59e0b';
    if (r === 'epic') return '#ec4899';
    if (r === 'special') return '#ffd32a';
    return '#10b981';
  }

  updateItemDrop(item, userLat, userLon, onMarkerClick) {
    if (!this.map) return;
    if (!item || !item.lat || !item.lon) {
      if (this.itemMarker) {
        this.map.removeLayer(this.itemMarker);
        this.itemMarker = null;
      }
      return;
    }
    this.updateNearbyItems([item], userLat, userLon, onMarkerClick);
  }

  updateNearbyItems(items, userLat, userLon, onMarkerClick) {
    if (!this.map) return;
    if (onMarkerClick) this.selectedItemCallback = onMarkerClick;

    const validItems = (items || []).filter(it => it && it.lat != null && it.lon != null && it.status !== 'COLLECTED');
    const currentIds = new Set(validItems.map(it => it.id));

    // Remove markers that are no longer active
    for (const [id, marker] of this.itemMarkers.entries()) {
      if (!currentIds.has(id)) {
        this.map.removeLayer(marker);
        this.itemMarkers.delete(id);
      }
    }

    // Add or update markers
    validItems.forEach(item => {
      const emoji = this.getItemIconEmoji(item);
      const color = this.getItemColor(item.rarity);
      const dist = (userLat != null && userLon != null) ? this.computeDistance(userLat, userLon, item.lat, item.lon) : (item.distance_m || 100);
      const isNear = dist <= 35;
      const isReady = item.status === 'AVAILABLE' || isNear;

      const markerHtml = `
        <div class="drop-marker-wrapper ${isNear ? 'in-range' : ''}" style="--rarity-color:${color};">
          <div class="drop-radar-ring"></div>
          <div class="drop-marker-bubble ${isReady ? 'ready' : 'locked'}">
            <span class="drop-emoji">${emoji}</span>
          </div>
          <div class="drop-label-pill">
            <span class="drop-label-name">${item.name || 'Drop'}</span>
            <span class="drop-label-dist">${Math.round(dist)}m</span>
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'loot-drop-div-icon',
        html: markerHtml,
        iconSize: [44, 44],
        iconAnchor: [22, 22]
      });

      let marker = this.itemMarkers.get(item.id);
      if (!marker) {
        marker = L.marker([item.lat, item.lon], { icon: customIcon }).addTo(this.map);
        marker.on('click', () => {
          if (this.selectedItemCallback) {
            this.selectedItemCallback(item);
          }
        });
        this.itemMarkers.set(item.id, marker);
      } else {
        marker.setLatLng([item.lat, item.lon]);
        marker.setIcon(customIcon);
      }
    });

    // Also update this.itemMarker reference for backward compatibility
    if (validItems.length > 0) {
      this.itemMarker = this.itemMarkers.get(validItems[0].id);
    }
  }

  clearItemMarkers() {
    for (const marker of this.itemMarkers.values()) {
      if (this.map) this.map.removeLayer(marker);
    }
    this.itemMarkers.clear();
    this.itemMarker = null;
  }

  computeDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  centerOnUser() {
    if (this.userMarker && this.map) {
      this.map.panTo(this.userMarker.getLatLng());
      this.map.setZoom(17);
    } else if (navigator.geolocation && this.map) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.updateUserPosition(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy || 10);
          this.map.setView([pos.coords.latitude, pos.coords.longitude], 17);
        },
        (err) => console.warn('Could not locate user:', err)
      );
    }
  }
}
