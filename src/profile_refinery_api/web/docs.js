(() => {
  "use strict";

  const healthIndicator = document.querySelector("#health-indicator");
  const capabilityNote = document.querySelector("#capability-note");
  const operationsRoot = document.querySelector("#openapi-operations");
  const endpointSearch = document.querySelector("#endpoint-search");
  const endpointCount = document.querySelector("#endpoint-count");
  let operations = [];

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const copyText = async (value, button) => {
    try {
      await navigator.clipboard.writeText(value);
      const previous = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => { button.textContent = previous; }, 1200);
    } catch {
      button.textContent = "Select + copy";
    }
  };

  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.copyTarget);
      if (target) copyText(target.textContent.trim(), button);
    });
  });

  const codeTabs = [...document.querySelectorAll("[data-code-tab]")];
  const codePanels = [...document.querySelectorAll("[data-code-panel]")];
  codeTabs.forEach((button) => {
    button.addEventListener("click", () => {
      codeTabs.forEach((candidate) => {
        const selected = candidate === button;
        candidate.classList.toggle("active", selected);
        candidate.setAttribute("aria-selected", String(selected));
      });
      codePanels.forEach((panel) => {
        panel.hidden = panel.dataset.codePanel !== button.dataset.codeTab;
      });
      const copy = document.querySelector(".copy-code");
      const selectedPanel = codePanels.find(
        (panel) => panel.dataset.codePanel === button.dataset.codeTab,
      );
      if (copy && selectedPanel) copy.dataset.copyTarget = selectedPanel.id;
    });
  });

  const renderOperations = () => {
    const query = endpointSearch.value.trim().toLowerCase();
    const visible = operations.filter((operation) => operation.search.includes(query));
    endpointCount.textContent = `${visible.length} of ${operations.length} operations`;
    if (!visible.length) {
      operationsRoot.innerHTML = '<p class="empty-state">No operations match this filter.</p>';
      return;
    }
    operationsRoot.innerHTML = visible.map((operation) => `
      <details class="operation-card">
        <summary>
          <span class="operation-method ${escapeHtml(operation.method)}">${escapeHtml(operation.method)}</span>
          <code class="operation-path">${escapeHtml(operation.path)}</code>
          <span class="operation-summary">${escapeHtml(operation.summary)}</span>
          <span class="operation-tag">${escapeHtml(operation.tag)}</span>
        </summary>
        <div class="operation-details">
          <div>
            <h4>Contract</h4>
            <p>${escapeHtml(operation.description || "No additional description is registered.")}</p>
            <p><strong>Operation ID:</strong> <code>${escapeHtml(operation.operationId)}</code></p>
          </div>
          <div>
            <h4>Responses</h4>
            <ul>${operation.responses.map((response) => `<li><code>${escapeHtml(response.status)}</code> ${escapeHtml(response.description)}</li>`).join("")}</ul>
          </div>
        </div>
      </details>
    `).join("");
  };

  const loadOpenApi = async () => {
    try {
      const response = await fetch("/openapi.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const document = await response.json();
      operations = Object.entries(document.paths || {}).flatMap(([path, pathItem]) =>
        Object.entries(pathItem)
          .filter(([method]) => ["get", "post", "put", "patch", "delete"].includes(method))
          .map(([method, operation]) => {
            const summary = operation.summary || operation.operationId || "API operation";
            const tag = operation.tags?.[0] || "untagged";
            const responses = Object.entries(operation.responses || {}).map(([status, item]) => ({
              status,
              description: item.description || "Documented response",
            }));
            return {
              method,
              path,
              summary,
              tag,
              description: operation.description || "",
              operationId: operation.operationId || "—",
              responses,
              search: `${method} ${path} ${summary} ${tag}`.toLowerCase(),
            };
          }),
      );
      operations.sort((left, right) => left.path.localeCompare(right.path) || left.method.localeCompare(right.method));
      renderOperations();
    } catch {
      endpointCount.textContent = "Contract unavailable";
      operationsRoot.innerHTML = '<p class="empty-state">The OpenAPI document could not be loaded. Use the curated reference above or open <a href="/openapi.json">/openapi.json</a> directly.</p>';
    }
  };

  const loadCapability = async () => {
    try {
      const [healthResponse, readyResponse] = await Promise.all([
        fetch("/healthz", { cache: "no-store" }),
        fetch("/readyz", { cache: "no-store" }),
      ]);
      healthIndicator.classList.add(healthResponse.ok ? "healthy" : "degraded");
      healthIndicator.lastChild.textContent = healthResponse.ok ? " API online" : " API degraded";
      const ready = await readyResponse.json();
      const state = ready.extraction_capability?.state || "UNKNOWN";
      const detail = ready.extraction_capability?.detail || "No capability detail returned.";
      capabilityNote.textContent = `Current capability: ${state}. ${detail}`;
    } catch {
      healthIndicator.classList.add("degraded");
      healthIndicator.lastChild.textContent = " status unavailable";
      capabilityNote.textContent = "Deployment capability could not be loaded from this page.";
    }
  };

  const navLinks = [...document.querySelectorAll(".rail nav a")];
  const observedSections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((link) => {
          link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
        });
      });
    }, { rootMargin: "-20% 0px -70%", threshold: 0 });
    observedSections.forEach((section) => observer.observe(section));
  }

  endpointSearch.addEventListener("input", renderOperations);
  loadCapability();
  loadOpenApi();
})();
