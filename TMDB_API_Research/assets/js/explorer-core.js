/**
 * TMDB API Research - Shared Explorer Core
 * Provides auth handling, live API fetcher, mock data fallback,
 * interactive JSON tree viewer, and dynamic schema analyzer.
 */

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/';

class TMDBExplorer {
  constructor(options = {}) {
    this.endpoint = options.endpoint || '';
    this.mockKey = options.mockKey || '';
    this.defaultParams = options.defaultParams || {};
    this.onRenderVisual = options.onRenderVisual || null;
    this.currentData = null;

    this.init();
  }

  init() {
    this.bindEvents();
    this.updateStatusBadge();
    this.injectKeyModal();
  }

  getApiKey() {
    return localStorage.getItem('tmdb_api_key') || '';
  }

  setApiKey(key) {
    if (key && key.trim()) {
      localStorage.setItem('tmdb_api_key', key.trim());
    } else {
      localStorage.removeItem('tmdb_api_key');
    }
    this.updateStatusBadge();
  }

  updateStatusBadge() {
    const badge = document.getElementById('api-status-badge');
    if (!badge) return;
    const hasKey = !!this.getApiKey();
    if (hasKey) {
      badge.className = 'badge badge-live';
      badge.innerHTML = '<span class="badge-dot"></span> Live API Mode';
    } else {
      badge.className = 'badge badge-mock';
      badge.innerHTML = '<span class="badge-dot"></span> Simulated Mode (Mock)';
    }
  }

  injectKeyModal() {
    if (document.getElementById('key-modal-overlay')) return;
    const modalHtml = `
      <div id="key-modal-overlay" class="modal-overlay">
        <div class="modal-card">
          <h3 class="modal-title">Configure TMDB API Key</h3>
          <p class="modal-desc">Enter your TMDB v3 API Key to enable live requests. The key is stored locally in your browser's localStorage and never transmitted elsewhere.</p>
          <div class="input-group">
            <label class="input-label" for="modal-key-input">TMDB API Key (v3 auth)</label>
            <input type="password" id="modal-key-input" class="input-field" placeholder="Paste your 32-character key..." />
          </div>
          <div class="modal-actions">
            <button id="modal-clear-btn" class="btn-secondary" style="color: var(--danger);">Clear Key</button>
            <button id="modal-cancel-btn" class="btn-secondary">Cancel</button>
            <button id="modal-save-btn" class="btn-primary">Save Key</button>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const overlay = document.getElementById('key-modal-overlay');
    const input = document.getElementById('modal-key-input');
    const saveBtn = document.getElementById('modal-save-btn');
    const cancelBtn = document.getElementById('modal-cancel-btn');
    const clearBtn = document.getElementById('modal-clear-btn');

    document.querySelectorAll('.open-key-modal').forEach(btn => {
      btn.addEventListener('click', () => {
        input.value = this.getApiKey();
        overlay.style.display = 'flex';
      });
    });

    cancelBtn.addEventListener('click', () => {
      overlay.style.display = 'none';
    });

    saveBtn.addEventListener('click', () => {
      this.setApiKey(input.value);
      overlay.style.display = 'none';
      alert('API Key updated! Live requests are now active.');
      this.execute();
    });

    clearBtn.addEventListener('click', () => {
      this.setApiKey('');
      input.value = '';
      overlay.style.display = 'none';
      alert('API Key removed. Switched to offline simulated mode.');
      this.execute();
    });
  }

  bindEvents() {
    // Tab switching
    document.querySelectorAll('.view-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.view-pane').forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        const targetId = `pane-${tab.dataset.tab}`;
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add('active');
      });
    });

    // Copy JSON button
    const copyBtn = document.getElementById('btn-copy-json');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        if (!this.currentData) return;
        navigator.clipboard.writeText(JSON.stringify(this.currentData, null, 2))
          .then(() => {
            const original = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => { copyBtn.textContent = original; }, 1500);
          })
          .catch(err => alert('Failed to copy: ' + err));
      });
    }

    // Expand/Collapse JSON buttons
    const expandBtn = document.getElementById('btn-expand-json');
    const collapseBtn = document.getElementById('btn-collapse-json');
    if (expandBtn) {
      expandBtn.addEventListener('click', () => {
        document.querySelectorAll('.json-collapsible').forEach(el => el.classList.remove('collapsed'));
        document.querySelectorAll('.json-toggle').forEach(el => { el.textContent = '▼'; });
      });
    }
    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => {
        document.querySelectorAll('.json-collapsible').forEach(el => el.classList.add('collapsed'));
        document.querySelectorAll('.json-toggle').forEach(el => { el.textContent = '▶'; });
      });
    }
  }

  async execute(customEndpoint = null, customParams = {}) {
    const endpoint = customEndpoint || this.endpoint;
    const params = { ...this.defaultParams, ...customParams };
    const apiKey = this.getApiKey();

    const visualPane = document.getElementById('pane-visual');
    const jsonPane = document.getElementById('pane-json');
    const schemaPane = document.getElementById('pane-schema');

    // Show loading spinner
    if (visualPane) visualPane.innerHTML = '<div class="state-message"><div class="spinner"></div><p>Querying TMDB API...</p></div>';

    let data = null;
    let isLive = false;

    if (apiKey) {
      params['api_key'] = apiKey;
      const queryStr = Object.entries(params)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
      const url = `https://api.themoviedb.org/3${endpoint}${queryStr ? '?' + queryStr : ''}`;

      try {
        const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
        if (!response.ok) {
          throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
        }
        data = await response.json();
        isLive = true;
      } catch (err) {
        console.warn('Live API request failed, falling back to mock fixture:', err);
        if (visualPane) {
          visualPane.innerHTML = `
            <div class="state-message" style="border-color: var(--danger); color: var(--danger);">
              <strong>Live Request Notice:</strong> ${err.message}<br/>
              <span style="color: var(--text-muted); font-size: 12px; margin-top: 6px; display: inline-block;">
                Displaying cached fixture data instead. Check your API key or network connection.
              </span>
            </div>
          `;
        }
        // Fallback to mock data
        data = (window.TMDB_MOCK_DATA && window.TMDB_MOCK_DATA[this.mockKey]) ? window.TMDB_MOCK_DATA[this.mockKey] : null;
      }
    } else {
      // Offline mock data
      data = (window.TMDB_MOCK_DATA && window.TMDB_MOCK_DATA[this.mockKey]) ? window.TMDB_MOCK_DATA[this.mockKey] : null;
    }

    if (!data) {
      if (visualPane) visualPane.innerHTML = '<div class="state-message">No data available for this query.</div>';
      return;
    }

    this.currentData = data;

    // Render Visual View
    if (this.onRenderVisual && visualPane) {
      try {
        visualPane.innerHTML = '';
        this.onRenderVisual(data, visualPane);
      } catch (e) {
        visualPane.innerHTML = `<div class="state-message" style="color: var(--danger);">Error rendering visual representation: ${e.message}</div>`;
      }
    }

    // Render JSON View
    if (jsonPane) {
      jsonPane.innerHTML = '<div class="json-container">' + this.formatJsonTree(data) + '</div>';
      this.bindJsonCollapsibles(jsonPane);
    }

    // Render Schema View
    if (schemaPane) {
      schemaPane.innerHTML = this.generateSchemaTable(data);
    }
  }

  formatJsonTree(obj, level = 0) {
    if (obj === null) return '<span class="json-null">null</span>';
    if (typeof obj === 'boolean') return `<span class="json-boolean">${obj}</span>`;
    if (typeof obj === 'number') return `<span class="json-number">${obj}</span>`;
    if (typeof obj === 'string') return `<span class="json-string">"${this.escapeHtml(obj)}"</span>`;

    const isArray = Array.isArray(obj);
    const keys = Object.keys(obj);

    if (keys.length === 0) {
      return isArray ? '[]' : '{}';
    }

    const openBracket = isArray ? '[' : '{';
    const closeBracket = isArray ? ']' : '}';

    let html = `<span class="json-toggle">▼</span>${openBracket}<div class="json-collapsible" style="padding-left: 20px;">`;

    keys.forEach((key, idx) => {
      const val = obj[key];
      const isLast = idx === keys.length - 1;
      html += '<div class="json-line">';
      if (!isArray) {
        html += `<span class="json-key">"${this.escapeHtml(key)}"</span>: `;
      }
      html += this.formatJsonTree(val, level + 1);
      if (!isLast) html += ',';
      html += '</div>';
    });

    html += `</div>${closeBracket}`;
    return html;
  }

  bindJsonCollapsibles(container) {
    container.querySelectorAll('.json-toggle').forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        const collapsible = toggle.nextElementSibling?.nextElementSibling || toggle.nextElementSibling;
        if (!collapsible || !collapsible.classList.contains('json-collapsible')) return;
        const isCollapsed = collapsible.classList.toggle('collapsed');
        toggle.textContent = isCollapsed ? '▶' : '▼';
        collapsible.style.display = isCollapsed ? 'none' : 'block';
      });
    });
  }

  generateSchemaTable(data) {
    const rows = [];
    this.extractSchemaRows('', data, rows, 0);

    let html = `
      <div class="schema-table-container">
        <table class="schema-table">
          <thead>
            <tr>
              <th style="width: 30%;">Field Path</th>
              <th style="width: 20%;">Inferred Type</th>
              <th style="width: 15%;">Nullable</th>
              <th style="width: 35%;">Sample Value</th>
            </tr>
          </thead>
          <tbody>
    `;

    rows.forEach(r => {
      const nullableBadge = r.nullable
        ? '<span class="schema-nullable nullable-yes">Nullable</span>'
        : '<span class="schema-nullable nullable-no">Required</span>';
      html += `
        <tr>
          <td><span class="schema-field">${this.escapeHtml(r.path)}</span></td>
          <td><span class="schema-type">${this.escapeHtml(r.type)}</span></td>
          <td>${nullableBadge}</td>
          <td><span class="schema-sample">${this.escapeHtml(r.sample)}</span></td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
    `;
    return html;
  }

  extractSchemaRows(prefix, val, rows, depth = 0) {
    if (depth > 5) return;
    if (val === null || val === undefined) {
      rows.push({
        path: prefix || 'root',
        type: 'null',
        nullable: true,
        sample: 'null'
      });
      return;
    }

    if (Array.isArray(val)) {
      const elemType = val.length > 0 ? (typeof val[0]) : 'unknown';
      rows.push({
        path: prefix || 'results[]',
        type: `Array<${elemType}> (length: ${val.length})`,
        nullable: false,
        sample: val.length > 0 ? JSON.stringify(val[0]).slice(0, 75) + '...' : '[]'
      });
      if (val.length > 0 && typeof val[0] === 'object' && val[0] !== null) {
        this.extractSchemaRows(`${prefix}[0]`, val[0], rows, depth + 1);
      }
      return;
    }

    if (typeof val === 'object') {
      Object.entries(val).forEach(([k, v]) => {
        const fieldPath = prefix ? `${prefix}.${k}` : k;
        if (v === null) {
          rows.push({
            path: fieldPath,
            type: 'string | number | null',
            nullable: true,
            sample: 'null'
          });
        } else if (Array.isArray(v)) {
          const itemType = v.length > 0 ? (typeof v[0]) : 'empty';
          rows.push({
            path: fieldPath,
            type: `Array<${itemType}>`,
            nullable: false,
            sample: `[${v.length} items]`
          });
          if (v.length > 0 && typeof v[0] === 'object' && v[0] !== null) {
            this.extractSchemaRows(`${fieldPath}[0]`, v[0], rows, depth + 1);
          }
        } else if (typeof v === 'object') {
          rows.push({
            path: fieldPath,
            type: 'Object',
            nullable: false,
            sample: '{...}'
          });
          this.extractSchemaRows(fieldPath, v, rows, depth + 1);
        } else {
          rows.push({
            path: fieldPath,
            type: typeof v,
            nullable: false,
            sample: String(v).slice(0, 80)
          });
        }
      });
      return;
    }

    rows.push({
      path: prefix || 'value',
      type: typeof val,
      nullable: false,
      sample: String(val).slice(0, 80)
    });
  }

  escapeHtml(str) {
    if (typeof str !== 'string') str = String(str);
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

window.TMDBExplorer = TMDBExplorer;
