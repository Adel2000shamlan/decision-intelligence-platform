(() => {
  "use strict";

  const app = document.getElementById("app");

  if (!app) {
    return;
  }

  app.innerHTML = `
    <section class="shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">DECISION INTELLIGENCE</p>
          <h1>Decision Intelligence Platform</h1>
        </div>
        <button class="icon-button" type="button" aria-label="Open settings">⚙</button>
      </header>

      <main class="content">
        <section class="welcome-card">
          <p class="eyebrow">CONTROL CENTER</p>
          <h2>Make better decisions with structured intelligence.</h2>
          <p class="muted">
            Manage organizations, projects, decisions, risks, execution and KPIs
            from one mobile-first workspace.
          </p>
        </section>

        <section class="grid" aria-label="Platform modules">
          <button class="module-card" type="button" data-module="organizations">
            <span class="module-icon">◎</span>
            <strong>Organizations</strong>
            <span>Manage organizations</span>
          </button>

          <button class="module-card" type="button" data-module="projects">
            <span class="module-icon">▣</span>
            <strong>Projects</strong>
            <span>Track project lifecycle</span>
          </button>

          <button class="module-card" type="button" data-module="decisions">
            <span class="module-icon">◇</span>
            <strong>Decisions</strong>
            <span>Analyze and govern decisions</span>
          </button>

          <button class="module-card" type="button" data-module="risks">
            <span class="module-icon">△</span>
            <strong>Risks</strong>
            <span>Assess and monitor risks</span>
          </button>

          <button class="module-card" type="button" data-module="execution">
            <span class="module-icon">→</span>
            <strong>Execution</strong>
            <span>Follow approved actions</span>
          </button>

          <button class="module-card" type="button" data-module="kpis">
            <span class="module-icon">↗</span>
            <strong>KPIs</strong>
            <span>Monitor performance</span>
          </button>
        </section>

        <section class="assistant-card">
          <div>
            <p class="eyebrow">AI ASSISTANT</p>
            <h3>Decision intelligence is ready.</h3>
            <p class="muted">Ask, analyze, compare and prepare evidence-based insights.</p>
          </div>
          <button class="primary-button" type="button" data-module="assistant">
            Open Assistant
          </button>
        </section>
      </main>

      <nav class="bottom-nav" aria-label="Primary navigation">
        <button class="nav-item active" type="button" data-module="dashboard">Home</button>
        <button class="nav-item" type="button" data-module="decisions">Decisions</button>
        <button class="nav-item" type="button" data-module="risks">Risks</button>
        <button class="nav-item" type="button" data-module="reports">Reports</button>
      </nav>

      <div class="toast" id="toast" role="status" aria-live="polite"></div>
    </section>
  `;

  const toast = document.getElementById("toast");

  document.querySelectorAll("[data-module]").forEach((element) => {
    element.addEventListener("click", () => {
      const moduleName = element.dataset.module;
      toast.textContent = `${moduleName} module selected`;
      toast.classList.add("visible");

      window.clearTimeout(window.__dipToastTimer);
      window.__dipToastTimer = window.setTimeout(() => {
        toast.classList.remove("visible");
      }, 1800);
    });
  });

})();
