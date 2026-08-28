"""Interactive demo page for the Tross LinkedIn Profile API."""
from __future__ import annotations

DEMO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Tross LinkedIn Profile API — Fixture Demo</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  :root{
    --bg:#0a0a0f;--surface:#12121a;--surface2:#1a1a26;--surface3:#22223a;
    --border:#2a2a40;--border2:#3a3a55;
    --accent:#6366f1;--accent2:#8b5cf6;--accent3:#06b6d4;
    --green:#10b981;--red:#ef4444;--yellow:#f59e0b;
    --text:#f1f5f9;--text2:#94a3b8;--text3:#64748b;
    --glow:rgba(99,102,241,0.15);
  }
  html{scroll-behavior:smooth}
  body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}

  /* Background */
  body::before{content:'';position:fixed;inset:0;background:
    radial-gradient(ellipse 80% 60% at 20% 0%,rgba(99,102,241,0.08) 0%,transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 100%,rgba(139,92,246,0.06) 0%,transparent 60%);
    pointer-events:none;z-index:0}

  .container{max-width:1100px;margin:0 auto;padding:0 24px;position:relative;z-index:1}

  /* Header */
  header{padding:48px 0 40px;text-align:center}
  .badge{display:inline-flex;align-items:center;gap:8px;background:rgba(99,102,241,0.12);
    border:1px solid rgba(99,102,241,0.3);border-radius:100px;padding:6px 16px;
    font-size:12px;font-weight:600;color:var(--accent);letter-spacing:0.05em;
    text-transform:uppercase;margin-bottom:24px}
  .badge-dot{width:6px;height:6px;border-radius:50%;background:var(--green);
    box-shadow:0 0 6px var(--green);animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
  h1{font-size:clamp(32px,5vw,56px);font-weight:800;letter-spacing:-0.03em;
    background:linear-gradient(135deg,#fff 0%,#c7d2fe 50%,#a5b4fc 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;line-height:1.1;margin-bottom:16px}
  .subtitle{font-size:18px;color:var(--text2);font-weight:400;max-width:520px;margin:0 auto 40px}

  /* Stats bar */
  .stats{display:flex;justify-content:center;gap:40px;margin-bottom:56px;flex-wrap:wrap}
  .stat{text-align:center}
  .stat-val{font-size:28px;font-weight:700;color:var(--text);letter-spacing:-0.02em}
  .stat-label{font-size:12px;color:var(--text3);text-transform:uppercase;letter-spacing:0.05em;margin-top:2px}

  /* Card */
  .card{background:var(--surface);border:1px solid var(--border);border-radius:16px;overflow:hidden;margin-bottom:24px}
  .card-header{display:flex;align-items:center;gap:12px;padding:20px 24px;border-bottom:1px solid var(--border);background:var(--surface2)}
  .card-icon{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
  .card-title{font-weight:600;font-size:15px}
  .card-subtitle{font-size:12px;color:var(--text3);margin-top:2px}
  .card-body{padding:24px}

  /* Step number */
  .step-num{width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;
    font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}

  /* Input group */
  .input-group{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
  label{display:block;font-size:13px;font-weight:500;color:var(--text2);margin-bottom:8px}
  input[type=text],input[type=password]{width:100%;background:var(--surface3);border:1px solid var(--border);
    border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;
    font-family:'Inter',sans-serif;outline:none;transition:border 0.2s,box-shadow 0.2s}
  input[type=text]:focus,input[type=password]:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--glow)}
  input[type=text]::placeholder,input[type=password]::placeholder{color:var(--text3)}

  /* Presets */
  .presets{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
  .preset-btn{background:var(--surface3);border:1px solid var(--border);border-radius:8px;
    padding:6px 14px;font-size:12px;color:var(--text2);cursor:pointer;transition:all 0.15s;
    font-family:'Inter',sans-serif;font-weight:500}
  .preset-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--glow)}
  .preset-btn.active{border-color:var(--accent);color:var(--accent);background:rgba(99,102,241,0.1)}

  /* Buttons */
  .btn{display:inline-flex;align-items:center;gap:8px;padding:13px 28px;border-radius:10px;
    font-size:14px;font-weight:600;cursor:pointer;border:none;transition:all 0.2s;
    font-family:'Inter',sans-serif;text-decoration:none}
  .btn-primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;
    box-shadow:0 4px 20px rgba(99,102,241,0.3)}
  .btn-primary:hover{transform:translateY(-1px);box-shadow:0 6px 28px rgba(99,102,241,0.4)}
  .btn-primary:active{transform:translateY(0)}
  .btn-primary:disabled{opacity:0.5;cursor:not-allowed;transform:none}
  .btn-ghost{background:var(--surface3);border:1px solid var(--border);color:var(--text2)}
  .btn-ghost:hover{border-color:var(--border2);color:var(--text)}
  .btn-sm{padding:8px 16px;font-size:12px;border-radius:8px}

  /* Request preview */
  .request-box{background:#0d0d14;border:1px solid var(--border);border-radius:12px;
    padding:16px 20px;font-family:'JetBrains Mono',monospace;font-size:12.5px;
    line-height:1.7;overflow-x:auto;margin-bottom:16px}
  .req-method{color:#f472b6;font-weight:500}
  .req-url{color:#a5b4fc}
  .req-header-key{color:#94a3b8}
  .req-header-val{color:#6ee7b7}
  .req-comment{color:#4a5568}

  /* Response panel */
  #response-panel{display:none}
  .status-bar{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}
  .status-badge{padding:5px 12px;border-radius:6px;font-size:12px;font-weight:700;font-family:'JetBrains Mono',monospace}
  .status-200{background:rgba(16,185,129,0.15);color:var(--green);border:1px solid rgba(16,185,129,0.3)}
  .status-4xx{background:rgba(239,68,68,0.15);color:var(--red);border:1px solid rgba(239,68,68,0.3)}
  .timing{font-size:12px;color:var(--text3)}

  /* Profile card */
  .profile-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
  @media(max-width:640px){.profile-grid{grid-template-columns:1fr}}
  .profile-section{background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px}
  .section-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
    color:var(--text3);margin-bottom:12px}
  .field{margin-bottom:10px}
  .field-key{font-size:11px;color:var(--text3);margin-bottom:2px}
  .field-val{font-size:13px;color:var(--text);font-weight:500;word-break:break-word}
  .field-val.mono{font-family:'JetBrains Mono',monospace;font-size:11px;color:#a5b4fc}
  .tag{display:inline-flex;align-items:center;gap:4px;background:rgba(99,102,241,0.1);
    border:1px solid rgba(99,102,241,0.2);border-radius:6px;padding:3px 10px;
    font-size:11px;color:#a5b4fc;margin:3px 3px 0 0}
  .exp-item{border-left:2px solid var(--border2);padding-left:14px;margin-bottom:14px}
  .exp-title{font-size:13px;font-weight:600;color:var(--text)}
  .exp-company{font-size:12px;color:var(--accent);margin-top:2px}
  .exp-dates{font-size:11px;color:var(--text3);margin-top:2px}

  /* JSON viewer */
  .json-toggle{display:flex;align-items:center;gap:8px;margin-top:16px}
  .json-box{display:none;background:#0d0d14;border:1px solid var(--border);border-radius:12px;
    padding:16px;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.8;
    max-height:400px;overflow-y:auto;margin-top:12px;white-space:pre-wrap;word-break:break-all}
  .json-box.show{display:block}
  .j-key{color:#93c5fd}.j-str{color:#86efac}.j-num{color:#fbbf24}
  .j-bool{color:#f472b6}.j-null{color:#94a3b8}

  /* Loading spinner */
  .spinner{width:18px;height:18px;border:2px solid rgba(255,255,255,0.2);
    border-top-color:#fff;border-radius:50%;animation:spin 0.7s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}

  /* Auth section */
  .key-display{display:flex;align-items:center;gap:10px}
  .key-text{flex:1;font-family:'JetBrains Mono',monospace;font-size:13px;color:#86efac;
    background:var(--surface3);border:1px solid var(--border);border-radius:8px;
    padding:10px 14px;word-break:break-all}
  .copy-btn{flex-shrink:0;cursor:pointer;background:var(--surface3);border:1px solid var(--border);
    border-radius:8px;padding:10px 14px;color:var(--text2);font-size:12px;font-family:'Inter',sans-serif;
    font-weight:500;transition:all 0.15s}
  .copy-btn:hover{border-color:var(--green);color:var(--green)}
  .copy-btn.copied{border-color:var(--green);color:var(--green)}

  /* Error */
  .error-box{background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);
    border-radius:12px;padding:16px;color:#fca5a5;font-size:13px;display:none}

  /* Footer */
  footer{padding:40px 0;text-align:center;color:var(--text3);font-size:13px;border-top:1px solid var(--border);margin-top:48px}
  footer a{color:var(--accent);text-decoration:none}
  footer a:hover{text-decoration:underline}

  /* Separator */
  .sep{height:1px;background:var(--border);margin:4px 0}

  /* Mode banner */
  .mode-banner{background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);
    border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:10px;
    margin-bottom:20px;font-size:13px;color:#fcd34d}
  .mode-icon{font-size:16px}

  /* Animate in */
  .fade-in{animation:fadeIn 0.4s ease}
  @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>
<div class="container">

  <header>
    <div class="badge"><span class="badge-dot"></span>Verified Fixture Demo</div>
    <h1>Tross LinkedIn<br>Profile API</h1>
    <p class="subtitle">Registry-driven, browserless profile normalization with explicit synthetic provenance.</p>
    <div class="stats">
      <div class="stat"><div class="stat-val">12</div><div class="stat-label">Profile Fields</div></div>
      <div class="stat"><div class="stat-val">Fixture</div><div class="stat-label">Evidence Mode</div></div>
      <div class="stat"><div class="stat-val">56</div><div class="stat-label">Tests Passing</div></div>
      <div class="stat"><div class="stat-val">OpenAPI 3.1</div><div class="stat-label">API Contract</div></div>
    </div>
  </header>

  <!-- Step 1: Auth -->
  <div class="card">
    <div class="card-header">
      <div class="step-num">1</div>
      <div class="card-icon" style="background:rgba(16,185,129,0.1)">🔑</div>
      <div>
        <div class="card-title">API Key Authentication</div>
        <div class="card-subtitle">API key sent in the X-API-Key header</div>
      </div>
    </div>
    <div class="card-body">
      <label>Your Demo API Key</label>
      <div class="key-display">
        <input type="password" id="key-input" placeholder="Enter your deployment API key" autocomplete="off"/>
        <button class="copy-btn" onclick="copyKey()" id="copy-key-btn">Copy</button>
      </div>
      <p style="margin-top:10px;font-size:12px;color:var(--text3)">
        Send as <code style="color:#a5b4fc;font-family:'JetBrains Mono',monospace">X-Api-Key: &lt;key&gt;</code> — reject without it returns 401.
      </p>
    </div>
  </div>

  <!-- Step 2: Request builder -->
  <div class="card">
    <div class="card-header">
      <div class="step-num">2</div>
      <div class="card-icon" style="background:rgba(99,102,241,0.1)">⚡</div>
      <div>
        <div class="card-title">Build Your Request</div>
        <div class="card-subtitle">Enter any LinkedIn profile URL</div>
      </div>
    </div>
    <div class="card-body">
      <div class="mode-banner">
        <span class="mode-icon">⚠️</span>
        <span><strong>Fixture mode</strong> — accepts only the synthetic demonstration journey. Live mode remains unavailable until current authorized operations and session material are configured.</span>
      </div>

      <label>Synthetic profile fixture</label>
      <div class="presets" id="presets">
        <button class="preset-btn active" onclick="setUrl('https://www.linkedin.com/in/synthetic-profile',this)">synthetic-profile</button>
      </div>

      <label>LinkedIn Profile URL</label>
      <input type="text" id="url-input" placeholder="https://www.linkedin.com/in/username"
        value="https://www.linkedin.com/in/synthetic-profile"/>

      <div style="margin-top:16px">
        <label>Live Request Preview</label>
        <div class="request-box" id="request-preview">
<span class="req-comment"># HTTP GET Request</span>
<span class="req-method">GET</span> <span class="req-url" id="preview-url">https://tross-linkedin-profile-api.vercel.app/v1/profiles?url=https://www.linkedin.com/in/synthetic-profile</span>

<span class="req-header-key">Host:</span>          <span class="req-header-val">tross-linkedin-profile-api.vercel.app</span>
<span class="req-header-key">X-API-Key:</span>     <span class="req-header-val" id="preview-key">enter-your-api-key</span>
<span class="req-header-key">Accept:</span>        <span class="req-header-val">application/json</span>
        </div>

        <button class="btn btn-primary" id="send-btn" onclick="sendRequest()">
          <span id="btn-icon">▶</span>
          <span id="btn-label">Send Request</span>
        </button>
        &nbsp;
        <button class="btn btn-ghost" onclick="resetPanel()">Reset</button>
      </div>
    </div>
  </div>

  <!-- Response panel -->
  <div id="response-panel" class="card fade-in">
    <div class="card-header">
      <div class="step-num">3</div>
      <div class="card-icon" style="background:rgba(16,185,129,0.1)">✅</div>
      <div>
        <div class="card-title">Normalised Profile Response</div>
        <div class="card-subtitle" id="response-subtitle">Parsed and validated against JSON Schema</div>
      </div>
    </div>
    <div class="card-body">
      <div class="status-bar">
        <span class="status-badge status-200" id="status-badge">200 OK</span>
        <span class="timing" id="timing-badge">⏱ 0ms</span>
        <span class="timing" id="size-badge"></span>
      </div>

      <div id="error-box" class="error-box"></div>

      <!-- Identity + Summary -->
      <div class="profile-grid" id="profile-top">
        <div class="profile-section">
          <div class="section-label">👤 Identity</div>
          <div class="field"><div class="field-key">Full Name</div><div class="field-val" id="pf-name">—</div></div>
          <div class="field"><div class="field-key">Vanity Slug</div><div class="field-val mono" id="pf-slug">—</div></div>
          <div class="field"><div class="field-key">Member URN</div><div class="field-val mono" id="pf-urn">—</div></div>
          <div class="field"><div class="field-key">Location</div><div class="field-val" id="pf-location">—</div></div>
        </div>
        <div class="profile-section">
          <div class="section-label">💼 Professional</div>
          <div class="field"><div class="field-key">Headline</div><div class="field-val" id="pf-headline">—</div></div>
          <div class="field"><div class="field-key">Connections</div><div class="field-val" id="pf-connections">—</div></div>
          <div class="field"><div class="field-key">Observed At</div><div class="field-val mono" id="pf-observed">—</div></div>
          <div class="field"><div class="field-key">Partial</div><div class="field-val" id="pf-partial">—</div></div>
        </div>
      </div>

      <!-- Experience -->
      <div class="profile-section" style="margin-bottom:16px" id="exp-section">
        <div class="section-label">🏢 Experience</div>
        <div id="exp-list"></div>
      </div>

      <!-- Skills + Education -->
      <div class="profile-grid">
        <div class="profile-section" id="skills-section">
          <div class="section-label">🛠 Skills</div>
          <div id="skills-list"></div>
        </div>
        <div class="profile-section" id="edu-section">
          <div class="section-label">🎓 Education</div>
          <div id="edu-list"></div>
        </div>
      </div>

      <!-- Raw JSON toggle -->
      <div class="json-toggle" style="margin-top:20px">
        <button class="btn btn-ghost btn-sm" onclick="toggleJson()" id="json-toggle-btn">Show Raw JSON</button>
        <button class="btn btn-ghost btn-sm" onclick="copyJson()">Copy JSON</button>
        <button class="btn btn-ghost btn-sm" onclick="openDocs()">📖 Full Schema</button>
      </div>
      <div class="json-box" id="json-box"></div>
    </div>
  </div>

  <!-- Footer -->
  <footer>
    <p>Tross LinkedIn Profile API · Fixture Mode · Built by <a href="https://github.com/shoryamishra61">shoryamishra61</a></p>
    <p style="margin-top:8px">
      <a href="/docs">Swagger UI</a> &nbsp;·&nbsp;
      <a href="/openapi.json">OpenAPI Spec</a> &nbsp;·&nbsp;
      <a href="/healthz">Health</a>
    </p>
  </footer>

</div>

<script>
const API_BASE = '';  // same origin
let lastJson   = null;

// Update preview as user types
document.getElementById('url-input').addEventListener('input', updatePreview);

function updatePreview() {
  const url = document.getElementById('url-input').value.trim();
  const full = API_BASE + '/v1/profiles?url=' + encodeURIComponent(url);
  document.getElementById('preview-url').textContent = 'https://tross-linkedin-profile-api.vercel.app/v1/profiles?url=' + url;
}

function setUrl(url, btn) {
  document.getElementById('url-input').value = url;
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  updatePreview();
}

async function sendRequest() {
  const url = document.getElementById('url-input').value.trim();
  const apiKey = document.getElementById('key-input').value.trim();
  if (!url) { alert('Enter a LinkedIn URL'); return; }
  if (!apiKey) { alert('Enter your API key'); return; }

  const btn = document.getElementById('send-btn');
  const icon = document.getElementById('btn-icon');
  const label = document.getElementById('btn-label');
  btn.disabled = true;
  icon.innerHTML = '<div class="spinner"></div>';
  label.textContent = 'Fetching…';

  const panel = document.getElementById('response-panel');
  panel.style.display = 'none';
  document.getElementById('error-box').style.display = 'none';

  const t0 = performance.now();
  try {
    const res = await fetch(API_BASE + '/v1/profiles?url=' + encodeURIComponent(url), {
      headers: { 'X-API-Key': apiKey, 'Accept': 'application/json' }
    });
    const elapsed = Math.round(performance.now() - t0);
    const text = await res.text();
    const data = JSON.parse(text);

    panel.style.display = 'block';
    panel.classList.add('fade-in');

    const statusBadge = document.getElementById('status-badge');
    statusBadge.textContent = res.status + ' ' + (res.ok ? 'OK' : 'Error');
    statusBadge.className = 'status-badge ' + (res.ok ? 'status-200' : 'status-4xx');

    document.getElementById('timing-badge').textContent = '⏱ ' + elapsed + 'ms';
    document.getElementById('size-badge').textContent = '📦 ' + (text.length / 1024).toFixed(1) + ' KB';
    document.getElementById('response-subtitle').textContent = 'schema_version: ' + (data.schema_version || '—');

    if (!res.ok) {
      const eb = document.getElementById('error-box');
      eb.style.display = 'block';
      eb.textContent = JSON.stringify(data, null, 2);
    } else {
      renderProfile(data);
    }

    lastJson = text;
    document.getElementById('json-box').innerHTML = syntaxHighlight(data);
  } catch(e) {
    panel.style.display = 'block';
    const eb = document.getElementById('error-box');
    eb.style.display = 'block';
    eb.textContent = 'Network error: ' + e.message;
  } finally {
    btn.disabled = false;
    icon.textContent = '▶';
    label.textContent = 'Send Request';
    setTimeout(() => panel.classList.remove('fade-in'), 500);
  }
}

function renderProfile(data) {
  const p = data.profile || {};
  const get = (obj, ...keys) => {
    let cur = obj;
    for (const k of keys) cur = cur?.[k];
    return cur;
  };
  const val = (v) => (v !== undefined && v !== null && v !== '') ? v : '—';

  // Identity
  document.getElementById('pf-name').textContent = val(get(p,'display_name','value'));
  document.getElementById('pf-slug').textContent = val(get(p,'identity','value','vanity_slug'));
  document.getElementById('pf-urn').textContent = val(get(p,'identity','value','member_urn'));
  document.getElementById('pf-location').textContent = val(get(p,'location','value','display_text') || get(p,'location','value'));

  // Professional
  document.getElementById('pf-headline').textContent = val(get(p,'headline','value'));
  document.getElementById('pf-connections').textContent = val(get(p,'connection_count','value'));
  document.getElementById('pf-observed').textContent = (data.observed_at || '—').replace('T',' ').replace('Z',' UTC');
  document.getElementById('pf-partial').textContent = data.partial === false ? '✅ Complete' : '⚠️ Partial';

  // Experience
  const exps = get(p,'experience','value') || [];
  const expEl = document.getElementById('exp-list');
  if (exps.length) {
    expEl.innerHTML = exps.slice(0,4).map(e => `
      <div class="exp-item">
        <div class="exp-title">${e.title || '—'}</div>
        <div class="exp-company">${e.company_name || e.company || '—'}</div>
        <div class="exp-dates">${e.started_at || ''} ${e.started_at && e.ended_at ? '→' : ''} ${e.ended_at || (e.started_at ? 'Present' : '')}</div>
      </div>`).join('');
  } else {
    expEl.innerHTML = '<span style="color:var(--text3);font-size:13px">No experience data</span>';
  }

  // Skills
  const skills = get(p,'skills','value') || [];
  const skillsEl = document.getElementById('skills-list');
  if (skills.length) {
    skillsEl.innerHTML = skills.slice(0,12).map(s => `<span class="tag">${s.name || s}</span>`).join('');
  } else {
    skillsEl.innerHTML = '<span style="color:var(--text3);font-size:13px">No skills data</span>';
  }

  // Education
  const edu = get(p,'education','value') || [];
  const eduEl = document.getElementById('edu-list');
  if (edu.length) {
    eduEl.innerHTML = edu.slice(0,3).map(e => `
      <div class="exp-item">
        <div class="exp-title">${e.school_name || e.school || '—'}</div>
        <div class="exp-company">${e.degree_name || ''} ${e.field_of_study ? '· ' + e.field_of_study : ''}</div>
        <div class="exp-dates">${e.started_at || ''} ${e.ended_at ? '→ ' + e.ended_at : ''}</div>
      </div>`).join('');
  } else {
    eduEl.innerHTML = '<span style="color:var(--text3);font-size:13px">No education data</span>';
  }
}

function syntaxHighlight(json) {
  const str = JSON.stringify(json, null, 2);
  return str.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, m => {
    if (/^"/.test(m)) {
      if (/:$/.test(m)) return '<span class="j-key">' + m + '</span>';
      return '<span class="j-str">' + m + '</span>';
    }
    if (/true|false/.test(m)) return '<span class="j-bool">' + m + '</span>';
    if (/null/.test(m)) return '<span class="j-null">' + m + '</span>';
    return '<span class="j-num">' + m + '</span>';
  });
}

function toggleJson() {
  const box = document.getElementById('json-box');
  const btn = document.getElementById('json-toggle-btn');
  box.classList.toggle('show');
  btn.textContent = box.classList.contains('show') ? 'Hide Raw JSON' : 'Show Raw JSON';
}

function copyJson() {
  if (!lastJson) return;
  navigator.clipboard.writeText(lastJson);
  const btn = event.target;
  btn.textContent = 'Copied!';
  setTimeout(() => btn.textContent = 'Copy JSON', 1500);
}

function copyKey() {
  const key = document.getElementById('key-input').value.trim();
  if (!key) return;
  navigator.clipboard.writeText(key);
  const btn = document.getElementById('copy-key-btn');
  btn.textContent = 'Copied!';
  btn.classList.add('copied');
  setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1500);
}

function openDocs() { window.open('/docs', '_blank'); }

function resetPanel() {
  document.getElementById('response-panel').style.display = 'none';
  lastJson = null;
}
</script>
</body>
</html>
"""
