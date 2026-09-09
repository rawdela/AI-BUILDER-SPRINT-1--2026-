let startedAt = null;

function runSimulation() {
  const btn = document.getElementById("runBtn");
  btn.disabled = true;
  document.getElementById("results").innerHTML = "";
  startedAt = Date.now();

  fetch("/api/run", { method: "POST" })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(await response.text());
      }
      poll();
    })
    .catch((error) => {
      btn.disabled = false;
      showError(error.message);
    });
}

async function poll() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    const state = await response.json();
    updateStatus(state);

    if (state.status === "running") {
      setTimeout(poll, 900);
      return;
    }

    document.getElementById("runBtn").disabled = false;
    if (state.status === "complete") {
      renderResults(state.result);
    } else if (state.status === "error") {
      showError(state.error);
    }
  } catch (error) {
    setTimeout(poll, 1500);
  }
}

function updateStatus(state) {
  document.getElementById("message").textContent = state.message || "Working…";
  const pill = document.getElementById("pill");
  pill.textContent = (state.status || "idle").toUpperCase();
  pill.className = "pill " + (state.status || "");
  document.getElementById("statusBox").className =
    "status-card " + (state.status || "");

  if (state.status === "running") {
    const elapsed = startedAt ? Math.floor((Date.now() - startedAt) / 1000) : 0;
    document.getElementById("hint").textContent =
      `Simulation active in background · ${elapsed}s elapsed · keep this tab open.`;
    const bar = document.getElementById("bar");
    let current = parseFloat(bar.style.width) || 5;
    bar.style.width = Math.min(94, current + 2.5) + "%";
  } else if (state.status === "complete") {
    document.getElementById("bar").style.width = "100%";
    document.getElementById("hint").textContent =
      "Simulation finished: All candidates evaluated and finalized.";
  }
}

function showError(message) {
  document.getElementById("results").innerHTML = `
    <div class="card" style="border-left: 4px solid var(--red);">
      <strong style="color: var(--red); font-size: 16px;">Simulation error</strong>
      <p style="margin: 8px 0; color: #cbd5e1;">${escapeHtml(message || "Unknown error occurred.")}</p>
      <div class="meta">Check server console or API quota. Click Run simulation to retry.</div>
    </div>`;
}

function renderResults(result) {
  if (!result) return;
  const dossiers = result.dossiers || [];

  let html = `<div class="section-title">Candidate Evaluation Dossiers</div><div class="grid">`;

  for (const d of dossiers) {
    html += `
      <div class="card">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <h3>${escapeHtml(d.candidate_name || d.candidate_id)}</h3>
            <span class="pill" style="font-size: 10px;">${escapeHtml(d.candidate_id)}</span>
          </div>
          <div class="meta">${escapeHtml(d.model_used || "")}</div>
          
          <div class="metrics">
            <div class="metric">
              <div class="metric-score" style="color: #38bdf8;">${d.immediate_need_score ?? "-"}</div>
              <div class="metric-label">Need</div>
            </div>
            <div class="metric">
              <div class="metric-score" style="color: #10b981;">${d.community_multiplier_score ?? "-"}</div>
              <div class="metric-label">Community</div>
            </div>
            <div class="metric">
              <div class="metric-score" style="color: #a5b4fc;">${d.technical_readiness_score ?? "-"}</div>
              <div class="metric-label">Technical</div>
            </div>
          </div>
          
          <p class="rationale">${escapeHtml(d.summary_rationale || "")}</p>
        </div>
        
        ${
          d.revision_note && d.revision_note.toLowerCase() !== "none"
            ? `
          <div class="twist-box">
            <strong>Mid-Interview Pivot:</strong> ${escapeHtml(d.revision_note)}
          </div>`
            : ""
        }
      </div>`;
  }

  html += `</div>`;

  // Model Routing Section
  html += `
    <div class="section-title" style="margin-top: 36px;">Multi-Model Routing Map</div>
    <div class="routing-chips">`;
  for (const [id, model] of Object.entries(result.model_routing || {})) {
    html += `<span class="tag"><strong>${escapeHtml(id)}</strong> &rarr; ${escapeHtml(model)}</span>`;
  }
  html += `</div>`;

  // Final Selection parsed with Marked.js
  const parsedMarkdown = window.marked
    ? marked.parse(result.final_verdict || "")
    : result.final_verdict;
  html += `
    <div class="section-title">Final Committee Allocation & Justification</div>
    <div class="final-deliberation">
      <div class="markdown-body">
        ${parsedMarkdown}
      </div>
    </div>`;

  document.getElementById("results").innerHTML = html;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
