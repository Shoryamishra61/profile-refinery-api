// docs.js - Interactive field manual & OpenAPI explorer
(function () {
  'use strict';

  const SNIPPETS = {
    curl: `curl -X POST "https://profile-refinery-api.vercel.app/v1/session-extractions" \\
  -H "Content-Type: application/json" \\
  -H "X-Request-ID: my-first-profile" \\
  -d '{
    "url": "https://www.linkedin.com/in/example-member",
    "li_at": "AQEDAT...",
    "jsessionid": "ajax:1234567890123456789",
    "bcookie": "v=2&..."
  }'`,
    python: `import httpx

payload = {
    "url": "https://www.linkedin.com/in/example-member",
    "li_at": "AQEDAT...",
    "jsessionid": "ajax:1234567890123456789",
    "bcookie": "v=2&..."
}

response = httpx.post(
    "https://profile-refinery-api.vercel.app/v1/session-extractions",
    json=payload,
    headers={"X-Request-ID": "my-first-profile"},
    timeout=20.0
)
data = response.json()
print("Profile name:", data["profile"]["name"]["value"])`,
    node: `const payload = {
  url: "https://www.linkedin.com/in/example-member",
  li_at: "AQEDAT...",
  jsessionid: "ajax:1234567890123456789",
  bcookie: "v=2&..."
};

const res = await fetch("https://profile-refinery-api.vercel.app/v1/session-extractions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Request-ID": "my-first-profile"
  },
  body: JSON.stringify(payload)
});
const data = await res.json();
console.log(data);`
  };

  // 1. Code tabs switcher
  const codeTabs = document.querySelectorAll('[data-code-tab]');
  const quickCode = document.getElementById('quick-code');
  codeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      codeTabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      const lang = tab.getAttribute('data-code-tab');
      if (quickCode && SNIPPETS[lang]) {
        quickCode.innerHTML = '<code>' + escapeHtml(SNIPPETS[lang]) + '</code>';
      }
    });
  });

  // 2. Copy Code Buttons
  document.querySelectorAll('.copy-code').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-copy-target');
      const target = document.getElementById(targetId);
      if (target) {
        navigator.clipboard.writeText(target.innerText).then(() => {
          const original = btn.innerText;
          btn.innerText = 'Copied!';
          setTimeout(() => { btn.innerText = original; }, 2000);
        });
      }
    });
  });

  // 3. Health & Capability Check
  const healthIndicator = document.getElementById('health-indicator');
  const capabilityNote = document.getElementById('capability-note');
  fetch('/healthz')
    .then(r => r.json())
    .then(d => {
      if (healthIndicator && d.status === 'ok') {
        healthIndicator.innerHTML = '<i style="background:#10b981;box-shadow:0 0 8px #10b981"></i> API live & responsive';
      }
    })
    .catch(() => {
      if (healthIndicator) {
        healthIndicator.innerHTML = '<i style="background:#f43f5e"></i> offline / connecting';
      }
    });

  fetch('/v1/capability')
    .then(r => {
      if (r.status === 401) {
        if (capabilityNote) capabilityNote.innerText = 'Capability metrics are protected by product API key.';
        return null;
      }
      return r.json();
    })
    .then(d => {
      if (d && capabilityNote) {
        capabilityNote.innerText = `Breaker: ${d.extraction_capability?.state || 'ONLINE'} · Queue depth: ${d.queue?.queue_depth || 0}`;
      }
    })
    .catch(() => {});

  // 4. Live OpenAPI 3.1 Explorer
  const operationsContainer = document.getElementById('openapi-operations');
  const endpointCount = document.getElementById('endpoint-count');
  const endpointSearch = document.getElementById('endpoint-search');
  let openapiSpec = null;

  fetch('/openapi.json')
    .then(r => r.json())
    .then(spec => {
      openapiSpec = spec;
      renderOpenApiOperations(spec);
    })
    .catch(err => {
      if (operationsContainer) {
        operationsContainer.innerHTML = '<p class="error-msg">Failed to load /openapi.json specification.</p>';
      }
    });

  function renderOpenApiOperations(spec, filter = '') {
    if (!operationsContainer || !spec || !spec.paths) return;
    const paths = spec.paths;
    const operations = [];

    Object.keys(paths).forEach(pathKey => {
      const pathItem = paths[pathKey];
      ['get', 'post', 'put', 'delete', 'patch'].forEach(method => {
        if (pathItem[method]) {
          const op = pathItem[method];
          operations.push({
            path: pathKey,
            method: method.toUpperCase(),
            summary: op.summary || '',
            description: op.description || '',
            tags: op.tags || [],
            parameters: op.parameters || [],
            responses: op.responses || {}
          });
        }
      });
    });

    const filtered = operations.filter(op => {
      if (!filter) return true;
      const q = filter.toLowerCase();
      return (
        op.path.toLowerCase().includes(q) ||
        op.method.toLowerCase().includes(q) ||
        op.summary.toLowerCase().includes(q) ||
        op.description.toLowerCase().includes(q) ||
        op.tags.some(t => t.toLowerCase().includes(q))
      );
    });

    if (endpointCount) {
      endpointCount.innerText = `${filtered.length} of ${operations.length} operations`;
    }

    if (filtered.length === 0) {
      operationsContainer.innerHTML = '<p style="color:#94a3b8;padding:24px 0;">No matching endpoints found.</p>';
      return;
    }

    operationsContainer.innerHTML = filtered.map(op => {
      const methodClass = op.method === 'GET' ? 'method-get' : op.method === 'POST' ? 'method-post' : 'method-other';
      const paramList = (op.parameters || []).map(p => `
        <tr>
          <td><code>${escapeHtml(p.name)}</code></td>
          <td><small>${escapeHtml(p.in || 'query')}</small></td>
          <td><span>${p.required ? '<b style="color:#f43f5e">required</b>' : '<span style="color:#64748b">optional</span>'}</span></td>
          <td>${escapeHtml(p.description || '')}</td>
        </tr>
      `).join('');

      return `
        <article class="operation-card">
          <div class="operation-header">
            <span class="op-badge ${methodClass}">${op.method}</span>
            <span class="op-path">${escapeHtml(op.path)}</span>
            <span class="op-summary">${escapeHtml(op.summary)}</span>
          </div>
          <div class="operation-body">
            ${op.description ? `<p class="op-desc">${escapeHtml(op.description)}</p>` : ''}
            ${paramList ? `
              <h4 style="font-size:12px;text-transform:uppercase;color:#64748b;margin:12px 0 6px;">Parameters</h4>
              <table class="op-table">
                <thead><tr><th>Name</th><th>In</th><th>Requirement</th><th>Description</th></tr></thead>
                <tbody>${paramList}</tbody>
              </table>
            ` : ''}
          </div>
        </article>
      `;
    }).join('');
  }

  if (endpointSearch) {
    endpointSearch.addEventListener('input', (e) => {
      if (openapiSpec) {
        renderOpenApiOperations(openapiSpec, e.target.value);
      }
    });
  }

  // 5. Active Rail Link Observer
  const sections = document.querySelectorAll('main > section[id]');
  const railLinks = document.querySelectorAll('.rail nav a');

  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(sec => {
      const top = sec.offsetTop - 120;
      if (window.scrollY >= top) {
        current = sec.getAttribute('id');
      }
    });
    railLinks.forEach(a => {
      a.classList.remove('active');
      if (a.getAttribute('href') === '#' + current) {
        a.classList.add('active');
      }
    });
  }, { passive: true });

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();
