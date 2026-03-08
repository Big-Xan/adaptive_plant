// ─────────────────────────────────────────────────────────────────────────────
// Adaptive Plant Card v6 — Card + Visual Editor
// ─────────────────────────────────────────────────────────────────────────────

class AdaptivePlantCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._tab          = null;
    this._expanded     = null;
    this._editingNotes = null;
    this._holdRaf      = null;
    this._holding      = false;
    this._initialized  = false;
  }

  static getConfigElement() {
    return document.createElement('adaptive-plant-card-editor');
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config       = config || {};
    this._showToday    = config.show_today    !== false;
    this._showUpcoming = config.show_upcoming !== false;
    this._showOverview = config.show_overview !== false;
    this._overdueColor = config.overdue_color || '#e05c5c';
    this._upcomingDays = config.upcoming_days || 30;

    const ic = config.icons || {};
    this._icons = {
      water:                ic.water                || '💧',
      water_color:          ic.water_color          || '#64b4ff',
      fertilize:            ic.fertilize            || '🌸',
      fertilize_color:      ic.fertilize_color      || '#7cb97e',
      snooze:               ic.snooze               || '🔔',
      snooze_color:         ic.snooze_color         || '#aaaaaa',
      fertilize_done:       ic.fertilize_done       || '✅',
      fertilize_done_color: ic.fertilize_done_color || '#7cb97e',
      water_done:           ic.water_done           || '✔',
      water_done_color:     ic.water_done_color     || '#64b4ff',
    };

    const h = config.health || {};
    const hc = h.colors || {};
    this._health = {
      ring:          h.ring          !== false,
      text:          h.text          === true,   // global text default OFF
      ring_today:    h.ring_today    !== undefined ? h.ring_today    : null,
      ring_upcoming: h.ring_upcoming !== undefined ? h.ring_upcoming : null,
      ring_overview: h.ring_overview !== undefined ? h.ring_overview : null,
      text_today:    h.text_today    !== undefined ? h.text_today    : null,
      text_upcoming: h.text_upcoming !== undefined ? h.text_upcoming : null,
      text_overview: h.text_overview !== undefined ? h.text_overview : null,
      ring_width:    h.ring_width || 3,
      colors: {
        Excellent: hc.Excellent || '#7cb97e',
        Good:      hc.Good      || '#a8cc8a',
        Poor:      hc.Poor      || '#e6a817',
        Sick:      hc.Sick      || '#e05c5c',
      },
    };

    if (!this._tab) {
      if (this._showToday)         this._tab = 'today';
      else if (this._showUpcoming) this._tab = 'upcoming';
      else if (this._showOverview) this._tab = 'overview';
    }
  }

  getCardSize() { return 5; }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._bootstrapShell();
      this._initialized = true;
    }
    if (!this._holding) this._updateContent();
  }

  // ── Health helpers ────────────────────────────────────────────────────────────

  _showRing(tab) {
    const o = this._health[`ring_${tab}`];
    return o !== null ? o : this._health.ring;
  }
  _showText(tab) {
    const o = this._health[`text_${tab}`];
    if (o !== null) return o;
    // Overview shows health text by default; other tabs do not
    if (tab === 'overview') return true;
    return this._health.text;
  }
  _healthColor(h) { return this._health.colors[h] || '#888'; }

  // ── Avatar ────────────────────────────────────────────────────────────────────

  _avatar(plant, tab) {
    const showRing  = tab && plant.health && this._showRing(tab);
    const ringColor = showRing ? this._healthColor(plant.health) : null;
    const rw        = this._health.ring_width;
    const ringStyle = showRing ? `box-shadow:0 0 0 ${rw}px ${ringColor};` : '';
    if (plant.image) {
      return `<div class="avatar-wrap"><div class="avatar" style="${ringStyle}"><img src="${plant.image}" alt="" /></div></div>`;
    }
    const initials = plant.name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
    return `<div class="avatar-wrap"><div class="avatar av-init" style="${ringStyle}">${initials}</div></div>`;
  }

  // ── Icon renderer ─────────────────────────────────────────────────────────────

  _renderIcon(value, color, size = '18px') {
    if (!value) return '';
    if (value.includes(':')) {
      return `<ha-icon icon="${value}" style="--mdc-icon-size:${size};color:${color};display:inline-flex;align-items:center;"></ha-icon>`;
    }
    return `<span class="emoji-icon">${value}</span>`;
  }

  // ── Shell ─────────────────────────────────────────────────────────────────────

  _bootstrapShell() {
    const cfg    = this._config || {};
    const height = cfg.height ? `${cfg.height}px` : null;
    const width  = cfg.width  ? `${cfg.width}px`  : null;

    const tabs = [
      this._showToday    && `<button class="tab ${this._tab==='today'    ?'active':''}" data-tab="today">Today</button>`,
      this._showUpcoming && `<button class="tab ${this._tab==='upcoming' ?'active':''}" data-tab="upcoming">Upcoming</button>`,
      this._showOverview && `<button class="tab ${this._tab==='overview' ?'active':''}" data-tab="overview">Overview</button>`,
    ].filter(Boolean).join('');

    this.shadowRoot.innerHTML = `
      <style>${this._css(height, width)}</style>
      <ha-card>
        <div class="tabs">${tabs}</div>
        <div class="content" id="content"></div>
      </ha-card>`;

    this.shadowRoot.querySelectorAll('[data-tab]').forEach(el =>
      el.addEventListener('click', () => {
        this._tab = el.dataset.tab;
        this.shadowRoot.querySelectorAll('.tab').forEach(t =>
          t.classList.toggle('active', t.dataset.tab === this._tab));
        this._updateContent();
      }));
  }

  // ── Content update ────────────────────────────────────────────────────────────

  _updateContent() {
    const contentEl = this.shadowRoot.getElementById('content');
    if (!contentEl) return;
    const plants = this._plants();
    let html = '';
    if      (this._tab === 'today')    html = this._renderToday(plants);
    else if (this._tab === 'upcoming') html = this._renderUpcoming(plants);
    else                               html = this._renderOverview(plants);
    contentEl.innerHTML = html;
    this._attachContentListeners(plants, contentEl);
    if (this._tab === 'today') this._attachHold(plants);
  }

  // ── Listeners ─────────────────────────────────────────────────────────────────

  _attachContentListeners(plants, root) {
    root.querySelectorAll('[data-entity]').forEach(el =>
      el.addEventListener('click', e => { e.stopPropagation(); this._press(el.dataset.entity); }));

    root.querySelectorAll('[data-expand]').forEach(el =>
      el.addEventListener('click', () => {
        this._expanded     = this._expanded === el.dataset.expand ? null : el.dataset.expand;
        this._editingNotes = null;
        this._updateContent();
      }));

    root.querySelectorAll('[data-health-entity]').forEach(el => {
      el.addEventListener('change',   e => { e.stopPropagation(); this._selectOption(el.dataset.healthEntity, el.value); });
      el.addEventListener('click',     e => e.stopPropagation());
      el.addEventListener('mousedown', e => e.stopPropagation());
    });

    root.querySelectorAll('[data-edit-notes]').forEach(el =>
      el.addEventListener('click', e => {
        e.stopPropagation();
        this._editingNotes = el.dataset.editNotes;
        this._updateContent();
      }));

    root.querySelectorAll('[data-notes-entity]').forEach(el =>
      el.addEventListener('click', e => {
        e.stopPropagation();
        const input = root.querySelector(`#notes-input-${el.dataset.plantId}`);
        if (input) this._setValue(el.dataset.notesEntity, input.value);
        this._editingNotes = null;
        this._updateContent();
      }));

    root.querySelectorAll('.notes-cancel').forEach(el =>
      el.addEventListener('click', e => {
        e.stopPropagation();
        this._editingNotes = null;
        this._updateContent();
      }));
  }

  // ── Data ─────────────────────────────────────────────────────────────────────

  _plants() {
    const hass = this._hass;
    if (!hass?.entities) return [];
    const byDevice = {};
    for (const [id, ent] of Object.entries(hass.entities)) {
      if (ent.platform !== 'adaptive_plant' || !ent.device_id) continue;
      (byDevice[ent.device_id] = byDevice[ent.device_id] || []).push(id);
    }
    return Object.entries(byDevice).map(([devId, ids]) => {
      const dev      = hass.devices?.[devId] || {};
      const areaName = dev.area_id ? (hass.areas?.[dev.area_id]?.name || 'No Area') : 'No Area';
      const find     = s => ids.find(id => id.endsWith(s));
      const st       = s => { const id = find(s); return id ? hass.states[id] : null; };
      const nwSt     = st('_next_watering');
      return {
        id:             devId,
        name:           dev.name || 'Plant',
        area:           areaName,
        image:          nwSt?.attributes?.entity_picture || null,
        nextWatering:   nwSt?.state,
        daysWater:      st('_days_until_watering')?.state,
        nextFertilized: st('_next_fertilization')?.state,
        daysFert:       st('_days_until_fertilization')?.state,
        health:         st('_health')?.state,
        healthEntityId: find('_health'),
        notes:          st('_notes')?.state || '',
        notesEntityId:  find('_notes'),
        btnWater:       find('_mark_watered'),
        btnSnooze:      find('_snooze_watering'),
        btnFert:        find('_mark_fertilized'),
      };
    }).sort((a, b) => a.name.localeCompare(b.name));
  }

  _daysNum(str) {
    if (!str) return 9999;
    if (str === 'Today') return 0;
    const m = str.match(/(\d+)/);
    const n = m ? parseInt(m[1]) : 0;
    return str.includes('Overdue') ? -n : n;
  }
  _isUrgent(str)  { return str === 'Today' || (!!str && str.includes('Overdue')); }
  _isOverdue(str) { return !!str && str.includes('Overdue'); }
  _groupByArea(plants) {
    const map = {};
    for (const p of plants) (map[p.area] = map[p.area] || []).push(p);
    return map;
  }
  _press(id)                { if (id) this._hass.callService('button', 'press',       { entity_id: id }); }
  _selectOption(id, option) { this._hass.callService('select', 'select_option',        { entity_id: id, option }); }
  _setValue(id, value)      { this._hass.callService('text',   'set_value',            { entity_id: id, value }); }

  // ── Chips ─────────────────────────────────────────────────────────────────────

  _waterChip(str) {
    const icon = this._renderIcon(this._icons.water, this._icons.water_color, '14px');
    if (this._isOverdue(str)) {
      const oc = this._overdueColor;
      return `<span class="chip" style="background:${oc}22;color:${oc}">${icon} ${str}</span>`;
    }
    return `<span class="chip chip-water">${icon} ${str === 'Today' ? 'Water today' : str}</span>`;
  }
  _fertChip(str) {
    const icon = this._renderIcon(this._icons.fertilize, this._icons.fertilize_color, '14px');
    if (this._isOverdue(str)) {
      const oc = this._overdueColor;
      return `<span class="chip" style="background:${oc}22;color:${oc}">${icon} ${str}</span>`;
    }
    return `<span class="chip chip-fert">${icon} ${str === 'Today' ? 'Fertilize today' : str}</span>`;
  }
  _actionBtn(cls, entity, iconKey, colorKey, title) {
    const icon = this._renderIcon(this._icons[iconKey], this._icons[colorKey], '16px');
    return `<button class="action-btn ${cls}" data-entity="${entity}" title="${title}">${icon}</button>`;
  }

  // ── Today ─────────────────────────────────────────────────────────────────────

  _renderToday(plants) {
    const waterDue = plants.filter(p => this._isUrgent(p.daysWater));
    const fertDue  = plants.filter(p => this._isUrgent(p.daysFert));
    const due      = [...new Set([...waterDue, ...fertDue])];
    const parts    = [];
    if (waterDue.length) parts.push(`${waterDue.length} ${waterDue.length === 1 ? 'Watering' : 'Waterings'}`);
    if (fertDue.length)  parts.push(`${fertDue.length} ${fertDue.length === 1 ? 'Fertilizing' : 'Fertilizings'}`);

    const summary = parts.length ? `
      <div class="summary-bar">
        <div class="summary-left">
          <span class="summary-icon">✓</span>
          <span>Today's tasks: <strong>${parts.join(' and ')}</strong></span>
        </div>
      </div>` : '';

    if (!due.length) return `${summary}<div class="empty"><span class="empty-icon">🌿</span><p>All caught up!</p></div>`;

    const byArea = this._groupByArea(due);
    const rows   = Object.entries(byArea).map(([area, ps]) => `
      <div class="area-group">
        <div class="area-header">${area}</div>
        ${ps.map(p => {
          const wu = this._isUrgent(p.daysWater);
          const fu = this._isUrgent(p.daysFert);
          return `
            <div class="plant-row">
              ${this._avatar(p, 'today')}
              <div class="plant-info">
                <div class="plant-name">${p.name}</div>
                ${this._showText('today') && p.health ? `<div class="plant-meta"><span class="health-badge" style="color:${this._healthColor(p.health)}">${p.health}</span></div>` : ''}
                <div class="chips">
                  ${wu ? this._waterChip(p.daysWater) : ''}
                  ${fu ? this._fertChip(p.daysFert)   : ''}
                </div>
              </div>
              <div class="row-actions">
                ${wu && p.btnSnooze ? this._actionBtn('btn-snooze', p.btnSnooze, 'snooze',         'snooze_color',         'Snooze')          : ''}
                ${fu && p.btnFert   ? this._actionBtn('btn-fert',   p.btnFert,   'fertilize_done', 'fertilize_done_color', 'Mark fertilized') : ''}
                ${wu && p.btnWater  ? this._actionBtn('btn-water',  p.btnWater,  'water_done',     'water_done_color',     'Mark watered')    : ''}
              </div>
            </div>`;
        }).join('')}
      </div>`).join('');

    return summary + rows + `
      <div class="hold-bar">
        <button class="hold-bar-btn" id="hold-all">
          <span class="hold-bar-label">Hold to Mark All Tasks Completed</span>
          <svg class="hold-ring" viewBox="0 0 36 36">
            <circle class="hold-track" cx="18" cy="18" r="15"/>
            <circle class="hold-fill" id="hold-fill-circle" cx="18" cy="18" r="15"
              stroke-dasharray="0 94.25" stroke-dashoffset="23.56"/>
          </svg>
        </button>
      </div>`;
  }

  // ── Upcoming ──────────────────────────────────────────────────────────────────

  _renderUpcoming(plants) {
    const cutoff = this._upcomingDays;
    const tasks  = [];
    for (const p of plants) {
      const wd = this._daysNum(p.daysWater);
      const fd = this._daysNum(p.daysFert);
      if (wd > 0 && wd <= cutoff) tasks.push({ plant: p, days: wd, type: 'water', label: p.daysWater });
      if (fd > 0 && fd <= cutoff) tasks.push({ plant: p, days: fd, type: 'fert',  label: p.daysFert  });
    }
    if (!tasks.length) return `<div class="empty"><span class="empty-icon">📅</span><p>Nothing in the next ${cutoff} days.</p></div>`;

    const byDay = {};
    for (const t of tasks) (byDay[t.days] = byDay[t.days] || []).push(t);

    return Object.entries(byDay).sort(([a],[b]) => a - b).map(([days, dayTasks]) => {
      const label  = days == 1 ? 'Tomorrow' : `In ${days} Days`;
      const byArea = {};
      for (const t of dayTasks) (byArea[t.plant.area] = byArea[t.plant.area] || []).push(t);
      return `
        <div class="day-group">
          <div class="day-header">${label}</div>
          ${Object.entries(byArea).map(([area, ts]) => `
            <div class="area-subgroup">
              <div class="area-sub-header">${area}</div>
              ${ts.map(t => `
                <div class="plant-row">
                  ${this._avatar(t.plant, 'upcoming')}
                  <div class="plant-info">
                    <div class="plant-name">${t.plant.name}</div>
                    ${this._showText('upcoming') && t.plant.health ? `<div class="plant-meta"><span class="health-badge" style="color:${this._healthColor(t.plant.health)}">${t.plant.health}</span></div>` : ''}
                    <span class="chip ${t.type === 'water' ? 'chip-water' : 'chip-fert'}">
                      ${this._renderIcon(
                        t.type === 'water' ? this._icons.water       : this._icons.fertilize,
                        t.type === 'water' ? this._icons.water_color : this._icons.fertilize_color,
                        '13px'
                      )} ${t.label}
                    </span>
                  </div>
                  ${t.type === 'water' && t.plant.btnWater
                    ? this._actionBtn('btn-water', t.plant.btnWater, 'water_done',    'water_done_color',    'Water early')
                    : t.type === 'fert' && t.plant.btnFert
                    ? this._actionBtn('btn-fert',  t.plant.btnFert,  'fertilize_done','fertilize_done_color','Fertilize early')
                    : ''}
                </div>`).join('')}
            </div>`).join('')}
        </div>`;
    }).join('');
  }

  // ── Overview ──────────────────────────────────────────────────────────────────

  _renderOverview(plants) {
    if (!plants.length) return `<div class="empty"><span class="empty-icon">🌱</span><p>No plants added yet.</p></div>`;
    const byArea = this._groupByArea(plants);
    return Object.entries(byArea).map(([area, ps]) => `
      <div class="area-group">
        <div class="area-header">${area}</div>
        ${ps.map(p => {
          const isExp        = this._expanded === p.id;
          const urgent       = this._isUrgent(p.daysWater) || this._isUrgent(p.daysFert);
          const editingNotes = this._editingNotes === p.id;
          const showText     = this._showText('overview');
          const healthOpts   = ['Excellent', 'Good', 'Poor', 'Sick'];
          return `
            <div class="plant-row plant-row-click" data-expand="${p.id}">
              ${this._avatar(p, 'overview')}
              <div class="plant-info">
                <div class="plant-name">
                  ${p.name}
                  ${urgent ? `<span class="urgent-dot"></span>` : ''}
                </div>
                <div class="plant-meta">
                  ${showText && p.health ? `<span class="health-badge" style="color:${this._healthColor(p.health)}">${p.health}</span>` : ''}
                  ${p.daysWater ? `<span class="meta-item">${this._renderIcon(this._icons.water, this._icons.water_color, '12px')} ${p.daysWater}</span>` : ''}
                  ${p.daysFert  ? `<span class="meta-item">${this._renderIcon(this._icons.fertilize, this._icons.fertilize_color, '12px')} ${p.daysFert}</span>`  : ''}
                </div>
              </div>
              <div class="chevron">${isExp ? '▲' : '▼'}</div>
            </div>
            ${isExp ? `
              <div class="plant-detail">
                ${p.nextWatering   ? `<div class="detail-row"><span class="detail-label">Next watering</span><span class="detail-value">${p.nextWatering}</span></div>` : ''}
                ${p.nextFertilized ? `<div class="detail-row"><span class="detail-label">Next fertilization</span><span class="detail-value">${p.nextFertilized}</span></div>` : ''}
                ${p.healthEntityId ? `
                  <div class="detail-row">
                    <span class="detail-label">Health</span>
                    <select class="health-select" data-health-entity="${p.healthEntityId}">
                      ${healthOpts.map(o => `<option value="${o}" ${o === p.health ? 'selected' : ''}>${o}</option>`).join('')}
                    </select>
                  </div>` : ''}
                ${p.notesEntityId ? `
                  <div class="notes-section">
                    ${editingNotes ? `
                      <textarea class="notes-input" id="notes-input-${p.id}" placeholder="Add notes...">${p.notes}</textarea>
                      <div class="notes-actions">
                        <button class="notes-save" data-notes-entity="${p.notesEntityId}" data-plant-id="${p.id}">Save</button>
                        <button class="notes-cancel" data-plant-id="${p.id}">Cancel</button>
                      </div>` : `
                      <div class="notes-display" data-edit-notes="${p.id}">
                        <span class="detail-label">Notes</span>
                        <span class="notes-value">${p.notes || '<span class="notes-placeholder">Tap to add notes\u2026</span>'}</span>
                        <span class="notes-edit-icon">✏️</span>
                      </div>`}
                  </div>` : ''}
                <div class="detail-actions">
                  ${p.btnWater ? `<button class="detail-btn btn-water" data-entity="${p.btnWater}">${this._renderIcon(this._icons.water, this._icons.water_color, '15px')} Mark Watered</button>` : ''}
                  ${p.btnFert  ? `<button class="detail-btn btn-fert"  data-entity="${p.btnFert}">${this._renderIcon(this._icons.fertilize, this._icons.fertilize_color, '15px')} Mark Fertilized</button>` : ''}
                </div>
              </div>` : ''}`;
        }).join('')}
      </div>`).join('');
  }

  // ── Hold ──────────────────────────────────────────────────────────────────────

  _attachHold(plants) {
    const btn = this.shadowRoot.getElementById('hold-all');
    if (!btn) return;
    const circle = this.shadowRoot.getElementById('hold-fill-circle');
    const CIRC = 94.25, DUR = 1500;
    let t0 = null;

    const tick = (ts) => {
      if (!t0) t0 = ts;
      const pct = Math.min((ts - t0) / DUR, 1);
      if (circle) circle.setAttribute('stroke-dasharray', `${pct * CIRC} ${CIRC}`);
      if (pct < 1) {
        this._holdRaf = requestAnimationFrame(tick);
      } else {
        // Wait one extra frame so the completed ring fully paints before actions fire
        requestAnimationFrame(() => {
          this._holding = false;
          plants.filter(p => this._isUrgent(p.daysWater) && p.btnWater).forEach(p => this._press(p.btnWater));
          plants.filter(p => this._isUrgent(p.daysFert)  && p.btnFert).forEach(p  => this._press(p.btnFert));
        });
      }
    };
    const start  = (e) => { e.preventDefault(); t0 = null; this._holding = true; this._holdRaf = requestAnimationFrame(tick); };
    const cancel = ()  => {
      this._holding = false;
      if (this._holdRaf) { cancelAnimationFrame(this._holdRaf); this._holdRaf = null; }
      if (circle) circle.setAttribute('stroke-dasharray', `0 ${CIRC}`);
    };
    btn.addEventListener('mousedown',  start);
    btn.addEventListener('touchstart', start, { passive: false });
    btn.addEventListener('mouseup',    cancel);
    btn.addEventListener('mouseleave', cancel);
    btn.addEventListener('touchend',   cancel);
  }

  // ── CSS ───────────────────────────────────────────────────────────────────────

  _css(height, width) {
    const oc = this._overdueColor;
    return `
      :host { display:block; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; ${width?`width:${width};`:''} }
      ha-card { background:var(--card-background-color,#1c1c1e); border-radius:16px; overflow:hidden; color:var(--primary-text-color,#e5e5e5); ${height?`height:${height};display:flex;flex-direction:column;`:''} }
      .tabs { display:flex; border-bottom:1px solid rgba(255,255,255,0.08); padding:0 16px; flex-shrink:0; }
      .tab { flex:1; padding:14px 0; text-align:center; cursor:pointer; font-size:14px; font-weight:500; color:var(--secondary-text-color,#888); border:none; border-bottom:2px solid transparent; background:none; outline:none; transition:color 0.2s,border-color 0.2s; }
      .tab.active { color:#7cb97e; border-bottom-color:#7cb97e; }
      .content { padding:8px 0 16px; ${height?'flex:1;overflow-y:auto;':'min-height:160px;'} }
      .content::-webkit-scrollbar { width:4px; }
      .content::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.1); border-radius:2px; }
      .summary-bar { display:flex; align-items:center; margin:8px 16px 4px; padding:10px 14px; background:rgba(124,185,126,0.1); border-radius:10px; font-size:14px; }
      .summary-left { display:flex; align-items:center; gap:10px; }
      .summary-icon { width:24px; height:24px; border-radius:50%; background:#7cb97e; color:#fff; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; flex-shrink:0; }
      .hold-bar { padding:12px 16px 4px; }
      .hold-bar-btn { position:relative; width:100%; padding:12px 16px; border-radius:12px; border:none; cursor:pointer; background:rgba(124,185,126,0.1); color:#7cb97e; font-size:14px; font-weight:600; display:flex; align-items:center; justify-content:center; gap:10px; user-select:none; -webkit-user-select:none; }
      .hold-bar-btn:hover { background:rgba(124,185,126,0.16); }
      .hold-bar-label { pointer-events:none; }
      .hold-ring { width:28px; height:28px; flex-shrink:0; transform:rotate(-90deg); }
      .hold-track { fill:none; stroke:rgba(124,185,126,0.2); stroke-width:2.5; }
      .hold-fill  { fill:none; stroke:#7cb97e; stroke-width:2.5; stroke-linecap:round; }
      .area-group { margin-bottom:4px; }
      .day-group { margin-bottom:16px; }
      .area-subgroup { margin-bottom:2px; }
      .area-header { padding:12px 16px 4px; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:var(--secondary-text-color,#888); }
      .day-header { padding:10px 16px 2px; font-size:16px; font-weight:700; }
      .area-sub-header { padding:4px 16px 2px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; color:var(--secondary-text-color,#555); }
      .plant-row { display:flex; align-items:center; padding:10px 16px; gap:12px; }
      .plant-row-click { cursor:pointer; }
      @media (hover:hover) { .plant-row-click:hover { background:rgba(255,255,255,0.04); } }
      .avatar-wrap { flex-shrink:0; }
      .avatar { width:44px; height:44px; border-radius:50%; overflow:hidden; background:#2a2a2a; display:flex; align-items:center; justify-content:center; transition:box-shadow 0.2s; }
      .avatar img { width:100%; height:100%; object-fit:cover; }
      .av-init { font-size:15px; font-weight:700; color:#7cb97e; }
      .plant-info { flex:1; min-width:0; }
      .plant-name { font-size:15px; font-weight:500; display:flex; align-items:center; gap:6px; }
      .plant-meta { display:flex; gap:8px; margin-top:3px; flex-wrap:wrap; align-items:center; }
      .meta-item { font-size:12px; color:var(--secondary-text-color,#888); display:flex; align-items:center; gap:3px; }
      .health-badge { font-size:12px; font-weight:600; }
      .urgent-dot { width:7px; height:7px; border-radius:50%; background:${oc}; display:inline-block; flex-shrink:0; }
      .chevron { font-size:10px; color:var(--secondary-text-color,#666); flex-shrink:0; }
      .chips { display:flex; gap:5px; margin-top:4px; flex-wrap:wrap; min-width:0; }
      .chip { font-size:12px; padding:2px 8px; border-radius:20px; font-weight:500; white-space:nowrap; display:inline-flex; align-items:center; gap:3px; flex:1 1 0; min-width:110px; }
      .chip-water { background:rgba(100,180,255,0.12); color:#64b4ff; }
      .chip-fert  { background:rgba(124,185,126,0.12); color:#7cb97e; }
      .emoji-icon { line-height:1; }
      .row-actions { display:flex; gap:6px; flex-shrink:0; }
      .action-btn { width:34px; height:34px; border-radius:50%; border:none; cursor:pointer; font-size:14px; display:flex; align-items:center; justify-content:center; transition:background 0.15s; }
      .btn-water  { background:rgba(100,180,255,0.15); color:#64b4ff; }
      .btn-water:hover  { background:rgba(100,180,255,0.3); }
      .btn-snooze { background:rgba(255,255,255,0.08); color:#aaaaaa; }
      .btn-snooze:hover { background:rgba(255,255,255,0.16); }
      .btn-fert   { background:rgba(124,185,126,0.15); color:#7cb97e; }
      .btn-fert:hover   { background:rgba(124,185,126,0.3); }
      .plant-detail { padding:4px 16px 12px 72px; border-bottom:1px solid rgba(255,255,255,0.06); }
      .detail-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; font-size:13px; }
      .detail-label { color:var(--secondary-text-color,#888); flex-shrink:0; margin-right:12px; }
      .detail-value { font-weight:500; }
      .health-select { background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:var(--primary-text-color,#e5e5e5); font-size:13px; padding:4px 8px; cursor:pointer; outline:none; }
      .notes-section { margin:6px 0; }
      .notes-display { display:flex; align-items:center; gap:8px; padding:6px 0; cursor:pointer; font-size:13px; }
      .notes-display:hover .notes-edit-icon { opacity:1; }
      .notes-value { flex:1; }
      .notes-placeholder { color:var(--secondary-text-color,#555); font-style:italic; }
      .notes-edit-icon { opacity:0.3; transition:opacity 0.15s; font-size:12px; }
      .notes-input { width:100%; box-sizing:border-box; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.15); border-radius:8px; color:var(--primary-text-color,#e5e5e5); font-size:13px; padding:8px; resize:vertical; min-height:72px; outline:none; font-family:inherit; }
      .notes-actions { display:flex; gap:8px; margin-top:6px; }
      .notes-save, .notes-cancel { padding:5px 14px; border-radius:16px; border:none; font-size:12px; font-weight:600; cursor:pointer; }
      .notes-save   { background:#7cb97e; color:#fff; }
      .notes-cancel { background:rgba(255,255,255,0.08); color:#aaa; }
      .detail-actions { display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; }
      .detail-btn { padding:7px 14px; border-radius:20px; border:none; cursor:pointer; font-size:13px; font-weight:500; display:inline-flex; align-items:center; gap:5px; transition:filter 0.15s; }
      .detail-btn.btn-water { background:rgba(100,180,255,0.15); color:#64b4ff; }
      .detail-btn.btn-fert  { background:rgba(124,185,126,0.15); color:#7cb97e; }
      .detail-btn:hover { filter:brightness(1.25); }
      .empty { display:flex; flex-direction:column; align-items:center; padding:48px 16px; color:var(--secondary-text-color,#888); gap:8px; }
      .empty-icon { font-size:36px; }
      .empty p { margin:0; font-size:14px; }
    `;
  }
}

customElements.define('adaptive-plant-card', AdaptivePlantCard);


// ─────────────────────────────────────────────────────────────────────────────
// Visual Editor
// ─────────────────────────────────────────────────────────────────────────────

class AdaptivePlantCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config    = {};
    this._sections  = { display: true, schedule: false, health: false, icons: false };
  }

  setConfig(config) {
    this._config = JSON.parse(JSON.stringify(config || {}));
    this._render();
  }

  // ── Fire config-changed ───────────────────────────────────────────────────────

  _dispatch() {
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    }));
  }

  // ── Deep set helpers ──────────────────────────────────────────────────────────

  _set(path, value) {
    const keys  = path.split('.');
    let   obj   = this._config;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]] || typeof obj[keys[i]] !== 'object') obj[keys[i]] = {};
      obj = obj[keys[i]];
    }
    if (value === null || value === undefined || value === '') {
      delete obj[keys[keys.length - 1]];
    } else {
      obj[keys[keys.length - 1]] = value;
    }
    this._dispatch();
    this._render();
  }

  _get(path, fallback = '') {
    const keys = path.split('.');
    let   obj  = this._config;
    for (const k of keys) {
      if (obj == null || typeof obj !== 'object') return fallback;
      obj = obj[k];
    }
    return obj !== undefined && obj !== null ? obj : fallback;
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  _render() {
    this.shadowRoot.innerHTML = `<style>${this._editorCss()}</style>${this._editorHtml()}`;
    this._attachEditorListeners();
  }

  _editorHtml() {
    return `
      <div class="editor">
        ${this._section('display',  '🖥️  Display',   this._displayFields())}
        ${this._section('schedule', '📅  Schedule',  this._scheduleFields())}
        ${this._section('health',   '🌡️  Health',    this._healthFields())}
        ${this._section('icons',    '🎨  Icons',     this._iconFields())}
      </div>`;
  }

  _section(key, title, content) {
    const open = this._sections[key];
    return `
      <div class="section">
        <div class="section-header" data-section="${key}">
          <span>${title}</span>
          <span class="section-chevron">${open ? '▲' : '▼'}</span>
        </div>
        ${open ? `<div class="section-body">${content}</div>` : ''}
      </div>`;
  }

  // ── Display fields ────────────────────────────────────────────────────────────

  _displayFields() {
    return `
      <div class="field-group">
        <div class="field-label">Visible Tabs</div>
        <div class="toggle-row">
          ${this._toggle('Today',    'show_today',    this._get('show_today', true))}
          ${this._toggle('Upcoming', 'show_upcoming', this._get('show_upcoming', true))}
          ${this._toggle('Overview', 'show_overview', this._get('show_overview', true))}
        </div>
      </div>
      <div class="field-row">
        ${this._textField('Height (px)', 'height', this._get('height', ''), 'e.g. 500', 'number')}
        ${this._textField('Width (px)',  'width',  this._get('width',  ''), 'e.g. 400', 'number')}
      </div>`;
  }

  // ── Schedule fields ───────────────────────────────────────────────────────────

  _scheduleFields() {
    return `
      <div class="field-row">
        ${this._textField('Upcoming days cutoff', 'upcoming_days', this._get('upcoming_days', 30), 'e.g. 14', 'number')}
        ${this._colorField('Overdue color', 'overdue_color', this._get('overdue_color', '#e05c5c'))}
      </div>`;
  }

  // ── Health fields ─────────────────────────────────────────────────────────────

  _healthFields() {
    // tri: On / Default / Off toggle. defaultOn controls what "Default" label says
    const tri = (path, label, globalKey, defaultOn) => {
      const val    = this._get(path);
      const global = this._get(globalKey);
      const defLabel = defaultOn !== undefined ? (defaultOn ? 'On' : 'Off') : (global !== false ? 'On' : 'Off');
      return `
        <div class="tri-toggle">
          <span class="tri-label">${label}</span>
          <div class="tri-btns">
            <button class="tri-btn ${val === true  ? 'active-on'  : ''}" data-tri="${path}" data-val="true">On</button>
            <button class="tri-btn ${val === ''    ? 'active-def' : ''}" data-tri="${path}" data-val="">Default (${defLabel})</button>
            <button class="tri-btn ${val === false ? 'active-off' : ''}" data-tri="${path}" data-val="false">Off</button>
          </div>
        </div>`;
    };

    return `
      <div class="field-group">
        <div class="field-label">Global defaults</div>
        <div class="toggle-row">
          ${this._toggle('Show health ring', 'health.ring', this._get('health.ring', true))}
          ${this._toggle('Show health text', 'health.text', this._get('health.text', false))}
        </div>
      </div>
      <div class="field-group">
        <div class="field-label">Ring width (px)</div>
        ${this._textField('', 'health.ring_width', this._get('health.ring_width', 3), '3', 'number')}
      </div>
      <div class="field-group">
        <div class="field-label">Per-tab health ring overrides</div>
        ${tri('health.ring_today',    'Today',    'health.ring', true)}
        ${tri('health.ring_upcoming', 'Upcoming', 'health.ring', true)}
        ${tri('health.ring_overview', 'Overview', 'health.ring', true)}
      </div>
      <div class="field-group">
        <div class="field-label">Per-tab health text overrides</div>
        ${tri('health.text_today',    'Today',    'health.text', false)}
        ${tri('health.text_upcoming', 'Upcoming', 'health.text', false)}
        ${tri('health.text_overview', 'Overview', 'health.text', true)}
      </div>
      <div class="field-group">
        <div class="field-label">Health level colors</div>
        <div class="field-hint">Click the color square, type a hex code (e.g. <strong>#e05c5c</strong>), or enter any CSS color name (e.g. <strong>red</strong>, <strong>coral</strong>, <strong>steelblue</strong>).</div>
        <div class="color-grid">
          ${this._colorField('Excellent', 'health.colors.Excellent', this._get('health.colors.Excellent', '#7cb97e'))}
          ${this._colorField('Good',      'health.colors.Good',      this._get('health.colors.Good',      '#a8cc8a'))}
          ${this._colorField('Poor',      'health.colors.Poor',      this._get('health.colors.Poor',      '#e6a817'))}
          ${this._colorField('Sick',      'health.colors.Sick',      this._get('health.colors.Sick',      '#e05c5c'))}
        </div>
      </div>`;
  }

  // ── Icon fields ───────────────────────────────────────────────────────────────

  _iconFields() {
    const row = (label, iconPath, colorPath, defaultIcon, defaultColor) => `
      <div class="icon-row">
        <span class="icon-label">${label}</span>
        <div class="icon-inputs">
          ${this._textField('Icon', iconPath, this._get(iconPath, defaultIcon), defaultIcon)}
          ${this._colorField('Color', colorPath, this._get(colorPath, defaultColor))}
        </div>
      </div>`;

    return `
      ${row('💧 Water chip',      'icons.water',           'icons.water_color',          '💧', '#64b4ff')}
      ${row('🌸 Fertilize chip',  'icons.fertilize',       'icons.fertilize_color',      '🌸', '#7cb97e')}
      ${row('🔔 Snooze button',   'icons.snooze',          'icons.snooze_color',         '🔔', '#aaaaaa')}
      ${row('✅ Fertilize done',  'icons.fertilize_done',  'icons.fertilize_done_color', '✅', '#7cb97e')}
      ${row('✔ Water done',       'icons.water_done',      'icons.water_done_color',     '✔',  '#64b4ff')}`;
  }

  // ── Field helpers ─────────────────────────────────────────────────────────────

  _toggle(label, path, value) {
    const checked = value !== false;
    return `
      <label class="toggle-label">
        <span>${label}</span>
        <div class="toggle-wrap">
          <input type="checkbox" class="toggle-input" data-path="${path}" ${checked ? 'checked' : ''} />
          <span class="toggle-slider"></span>
        </div>
      </label>`;
  }

  _textField(label, path, value, placeholder = '', type = 'text') {
    return `
      <div class="text-field">
        ${label ? `<div class="field-sublabel">${label}</div>` : ''}
        <input class="text-input" type="${type}" data-path="${path}"
          value="${value !== undefined && value !== null ? value : ''}"
          placeholder="${placeholder}" />
      </div>`;
  }

  _colorField(label, path, value) {
    return `
      <div class="color-field">
        ${label ? `<div class="field-sublabel">${label}</div>` : ''}
        <div class="color-wrap">
          <input type="color" class="color-swatch" data-path="${path}" value="${value}" />
          <input type="text"  class="color-text"   data-color-text="${path}" value="${value}" placeholder="#rrggbb" />
        </div>
      </div>`;
  }

  // ── Editor listeners ──────────────────────────────────────────────────────────

  _attachEditorListeners() {
    // Section toggles
    this.shadowRoot.querySelectorAll('.section-header').forEach(el =>
      el.addEventListener('click', () => {
        const key = el.dataset.section;
        this._sections[key] = !this._sections[key];
        this._render();
      }));

    // Checkboxes
    this.shadowRoot.querySelectorAll('.toggle-input').forEach(el =>
      el.addEventListener('change', () => this._set(el.dataset.path, el.checked)));

    // Text inputs (debounced)
    this.shadowRoot.querySelectorAll('.text-input').forEach(el => {
      el.addEventListener('change', () => {
        const val = el.type === 'number' ? (el.value === '' ? null : Number(el.value)) : el.value;
        this._set(el.dataset.path, val);
      });
    });

    // Color swatches — sync to text field and dispatch
    this.shadowRoot.querySelectorAll('.color-swatch').forEach(el => {
      el.addEventListener('input', () => {
        const txt = this.shadowRoot.querySelector(`[data-color-text="${el.dataset.path}"]`);
        if (txt) txt.value = el.value;
        this._set(el.dataset.path, el.value);
      });
    });

    // Color text fields — accept hex or CSS named colors
    this.shadowRoot.querySelectorAll('.color-text').forEach(el => {
      el.addEventListener('change', () => {
        const val = el.value.trim();
        if (!val) return;
        // Try to resolve to hex for the swatch using a temporary canvas
        const ctx = document.createElement('canvas').getContext('2d');
        ctx.fillStyle = val;
        const resolved = ctx.fillStyle; // browser normalises to hex if valid
        if (resolved !== '#000000' || val === 'black' || val === '#000000') {
          const swatch = this.shadowRoot.querySelector(`[data-path="${el.dataset.colorText}"].color-swatch`);
          if (swatch && /^#[0-9a-fA-F]{6}$/.test(resolved)) swatch.value = resolved;
          this._set(el.dataset.colorText, val); // store original (may be named color)
        }
      });
    });

    // Tri-state buttons (On / Default / Off)
    this.shadowRoot.querySelectorAll('.tri-btn').forEach(el => {
      el.addEventListener('click', () => {
        const raw = el.dataset.val;
        const val = raw === 'true' ? true : raw === 'false' ? false : null;
        this._set(el.dataset.tri, val);
      });
    });
  }

  // ── Editor CSS ────────────────────────────────────────────────────────────────

  _editorCss() {
    return `
      :host { display:block; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
      .editor { display:flex; flex-direction:column; gap:8px; padding:8px 0; }

      .section { border-radius:12px; overflow:hidden; background:var(--secondary-background-color,rgba(255,255,255,0.04)); }
      .section-header {
        display:flex; justify-content:space-between; align-items:center;
        padding:14px 16px; cursor:pointer; font-weight:600; font-size:14px;
        user-select:none;
      }
      .section-header:hover { background:rgba(255,255,255,0.04); }
      .section-chevron { font-size:10px; color:var(--secondary-text-color,#888); }
      .section-body { padding:4px 16px 16px; display:flex; flex-direction:column; gap:14px; }

      .field-group { display:flex; flex-direction:column; gap:8px; }
      .field-label { font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:var(--secondary-text-color,#888); margin-bottom:2px; }
      .field-sublabel { font-size:12px; color:var(--secondary-text-color,#888); margin-bottom:4px; }
      .field-hint { font-size:12px; color:var(--secondary-text-color,#888); line-height:1.5; margin-bottom:6px; }
      .field-row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }

      /* Toggles */
      .toggle-row { display:flex; flex-wrap:wrap; gap:10px; }
      .toggle-label { display:flex; align-items:center; justify-content:space-between; gap:10px; font-size:13px; min-width:100px; }
      .toggle-wrap { position:relative; width:38px; height:22px; flex-shrink:0; }
      .toggle-input { opacity:0; width:0; height:0; position:absolute; }
      .toggle-slider { position:absolute; inset:0; border-radius:11px; background:rgba(255,255,255,0.15); cursor:pointer; transition:background 0.2s; }
      .toggle-input:checked + .toggle-slider { background:#7cb97e; }
      .toggle-slider::after { content:''; position:absolute; width:16px; height:16px; left:3px; top:3px; border-radius:50%; background:#fff; transition:transform 0.2s; }
      .toggle-input:checked + .toggle-slider::after { transform:translateX(16px); }

      /* Text inputs */
      .text-field { display:flex; flex-direction:column; gap:4px; }
      .text-input {
        background:var(--input-fill-color,rgba(255,255,255,0.06));
        border:1px solid rgba(255,255,255,0.1); border-radius:8px;
        color:var(--primary-text-color,#e5e5e5); font-size:13px;
        padding:8px 10px; outline:none; width:100%; box-sizing:border-box;
      }
      .text-input:focus { border-color:#7cb97e; }

      /* Color fields */
      .color-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
      .color-field { display:flex; flex-direction:column; gap:4px; }
      .color-wrap { display:flex; align-items:center; gap:8px; }
      .color-swatch { width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); padding:2px; cursor:pointer; background:none; flex-shrink:0; }
      .color-text { flex:1; background:var(--input-fill-color,rgba(255,255,255,0.06)); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:var(--primary-text-color,#e5e5e5); font-size:12px; padding:8px 8px; outline:none; box-sizing:border-box; }
      .color-text:focus { border-color:#7cb97e; }

      /* Icon rows */
      .icon-row { display:flex; flex-direction:column; gap:6px; padding:10px 0; border-bottom:1px solid rgba(255,255,255,0.06); }
      .icon-row:last-child { border-bottom:none; }
      .icon-label { font-size:13px; font-weight:600; }
      .icon-inputs { display:grid; grid-template-columns:1fr 1fr; gap:10px; }

      /* Tri-state toggles */
      .tri-toggle { display:flex; align-items:center; justify-content:space-between; padding:4px 0; gap:12px; }
      .tri-label { font-size:13px; flex-shrink:0; min-width:70px; }
      .tri-btns { display:flex; gap:4px; }
      .tri-btn {
        padding:4px 10px; border-radius:16px; border:1px solid rgba(255,255,255,0.1);
        font-size:12px; font-weight:500; cursor:pointer;
        background:rgba(255,255,255,0.04); color:var(--secondary-text-color,#888);
        transition:all 0.15s;
      }
      .tri-btn.active-on  { background:rgba(124,185,126,0.2); color:#7cb97e; border-color:#7cb97e; }
      .tri-btn.active-def { background:rgba(255,255,255,0.1); color:var(--primary-text-color,#e5e5e5); border-color:rgba(255,255,255,0.2); }
      .tri-btn.active-off { background:rgba(224,92,92,0.2);   color:#e05c5c; border-color:#e05c5c; }
    `;
  }
}

customElements.define('adaptive-plant-card-editor', AdaptivePlantCardEditor);
